from __future__ import annotations

import json
import struct
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .contracts import ArtifactFile, ArtifactManifest, RunRecord, RunSpec
from .io import ContractError, read_json, sha256_file, sha256_json, utc_now, write_json_atomic
from .media import inspect_png


# v1 hashes only the input file itself. Keep the accepted boundary to the
# self-contained GLB container until dependency tracing exists for .blend,
# .gltf, .fbx, and .obj inputs.
SUPPORTED_INPUTS = {".glb"}
REQUIRED_VIEWS = ("hero", "front", "back", "left", "right", "top", "closeup")
REQUIRED_VIEW_ROLES = frozenset(name + "-view" for name in REQUIRED_VIEWS)
ARTIFACT_SCHEMA = "blender-harness.artifact-manifest.v1"
SUBJECT_MODES = {"single_object", "whole_scene"}
GLB_JSON_CHUNK = 0x4E4F534A


def blender_version(blender: str) -> str:
    process = subprocess.run([blender, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise ContractError("cannot execute Blender at %s: %s" % (blender, process.stderr.strip()))
    return process.stdout.splitlines()[0].strip()


def _action_script() -> Path:
    return Path(__file__).resolve().parent / "blender_runtime" / "quicklook_action.py"


def validate_self_contained_glb(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ContractError("quicklook input is not a GLB container: %s" % path)
    version, declared_length = struct.unpack("<II", data[4:12])
    if version != 2 or declared_length != len(data):
        raise ContractError("quicklook GLB has an invalid version or declared length: %s" % path)
    offset = 12
    json_payload = None
    while offset < len(data):
        if offset + 8 > len(data):
            raise ContractError("quicklook GLB has a truncated chunk header: %s" % path)
        chunk_length, chunk_type = struct.unpack("<II", data[offset : offset + 8])
        chunk_end = offset + 8 + chunk_length
        if chunk_end > len(data):
            raise ContractError("quicklook GLB has a truncated chunk: %s" % path)
        if json_payload is None and chunk_type == GLB_JSON_CHUNK:
            json_payload = data[offset + 8 : chunk_end]
        offset = chunk_end
    if offset != len(data) or json_payload is None:
        raise ContractError("quicklook GLB is missing a valid JSON chunk: %s" % path)
    try:
        document = json.loads(json_payload.rstrip(b" \t\r\n\0").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("quicklook GLB JSON chunk cannot be decoded: %s" % path) from exc

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "uri" and isinstance(child, str) and not child.startswith("data:"):
                    raise ContractError(
                        "quicklook v1 requires a self-contained GLB; external URI found: %s" % child
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)


def _artifact_identity(
    run_id: str,
    producer: Dict[str, Any],
    inputs: List[Dict[str, Any]],
    files: List[Dict[str, Any]],
) -> Dict[str, Any]:
    normalized_files = []
    for item in files:
        normalized_files.append({
            "role": item["role"],
            "path": item["path"],
            "media_type": item["media_type"],
            "sha256": item["sha256"],
            "size_bytes": item["size_bytes"],
            "metadata": item.get("metadata", {}),
        })
    return {
        "schema": ARTIFACT_SCHEMA,
        "run_id": run_id,
        "producer": producer,
        "inputs": inputs,
        "files": sorted(normalized_files, key=lambda value: (value["role"], value["path"])),
    }


def artifact_id_for(
    run_id: str,
    producer: Dict[str, Any],
    inputs: List[Dict[str, Any]],
    files: List[Dict[str, Any]],
) -> str:
    return "sha256:" + sha256_json(_artifact_identity(run_id, producer, inputs, files))


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


class QuicklookRunner:
    def __init__(self, blender: str):
        self.blender = blender

    def _verify_completed(
        self,
        run_dir: Path,
        expected_run_id: str,
        input_path: Path,
        input_hash: str,
        producer: Dict[str, Any],
    ) -> Dict[str, Any]:
        manifest_path = run_dir / "artifact-manifest.v1.json"
        manifest = read_json(manifest_path)
        if manifest.get("schema") != ARTIFACT_SCHEMA:
            raise ContractError("cached quicklook has an unexpected artifact schema")
        if manifest.get("run_id") != expected_run_id or run_dir.name != expected_run_id:
            raise ContractError("cached quicklook run_id does not match its content-addressed directory")
        if manifest.get("producer") != producer:
            raise ContractError("cached quicklook producer does not match the requested runtime")
        expected_inputs = [{"path": str(input_path), "sha256": input_hash}]
        if manifest.get("inputs") != expected_inputs:
            raise ContractError("cached quicklook input lineage does not match the requested input")
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise ContractError("cached quicklook artifact manifest has no files")
        roles = []
        relative_paths = []
        for item in files:
            if not isinstance(item, dict):
                raise ContractError("cached quicklook contains an invalid file entry")
            for key in ("role", "path", "media_type", "sha256", "size_bytes"):
                if key not in item:
                    raise ContractError("cached quicklook file entry is missing %s" % key)
            if not all(isinstance(item[key], str) and item[key] for key in ("role", "path", "media_type")):
                raise ContractError("cached quicklook file role/path/media_type must be non-empty strings")
            if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
                raise ContractError("cached quicklook file has an invalid sha256")
            if not isinstance(item["size_bytes"], int) or item["size_bytes"] < 0:
                raise ContractError("cached quicklook file has an invalid size_bytes")
            roles.append(item["role"])
            relative_paths.append(item["path"])
            path = (run_dir / item["path"]).resolve()
            try:
                path.relative_to(run_dir.resolve())
            except ValueError as exc:
                raise ContractError("cached quicklook file escapes its run directory") from exc
            if not path.is_file() or sha256_file(path) != item["sha256"]:
                raise ContractError("cached quicklook artifact is missing or changed: %s" % path)
            if path.stat().st_size != item["size_bytes"]:
                raise ContractError("cached quicklook artifact size does not match its manifest: %s" % path)
            if item.get("media_type") == "image/png":
                inspect_png(path)
        if len(roles) != len(set(roles)) or len(relative_paths) != len(set(relative_paths)):
            raise ContractError("cached quicklook contains duplicate roles or paths")
        if not REQUIRED_VIEW_ROLES.issubset(set(roles)):
            missing = sorted(REQUIRED_VIEW_ROLES.difference(roles))
            raise ContractError("cached quicklook is missing required view roles: %s" % ", ".join(missing))
        expected_artifact_id = artifact_id_for(expected_run_id, producer, expected_inputs, files)
        if manifest.get("artifact_id") != expected_artifact_id:
            raise ContractError("cached quicklook artifact identity does not match its manifest")
        return manifest

    def run(
        self,
        input_path: Path,
        output_root: Path,
        intent: str,
        size: int = 512,
        timeout_seconds: int = 600,
        force: bool = False,
        subject_mode: str = "single_object",
    ) -> Path:
        input_path = input_path.resolve()
        output_root = output_root.resolve()
        if not input_path.is_file():
            raise ContractError("quicklook input does not exist: %s" % input_path)
        if input_path.suffix.lower() not in SUPPORTED_INPUTS:
            raise ContractError(
                "unsupported quicklook input: %s; v1 accepts self-contained GLB only until dependency tracing exists"
                % input_path.suffix
            )
        validate_self_contained_glb(input_path)
        if size < 128 or size > 4096:
            raise ContractError("quicklook size must be 128..4096")
        if subject_mode not in SUBJECT_MODES:
            raise ContractError("quicklook subject_mode must be single_object or whole_scene")
        input_hash = sha256_file(input_path)
        version = blender_version(self.blender)
        spec = RunSpec(
            intent=intent,
            input_path=str(input_path),
            recipe="quicklook-v1",
            blender_version=version,
            parameters={"views": list(REQUIRED_VIEWS), "size": size, "subject_mode": subject_mode},
            budget={"timeout_seconds": timeout_seconds},
        )
        spec_dict = spec.to_dict()
        base_run_id = "run-" + sha256_json({"spec": spec_dict, "input_sha256": input_hash})[:20]
        versioned_producer = {"kind": "blender-runtime", "harness_version": __version__, "blender": version}
        run_id = base_run_id
        if force:
            run_id = base_run_id + "-attempt-" + uuid.uuid4().hex[:12]
        run_dir = output_root / run_id
        if run_dir.exists():
            self._verify_completed(run_dir, run_id, input_path, input_hash, versioned_producer)
            return run_dir

        output_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".%s." % run_id, dir=str(output_root)))
        logs = staging / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        write_json_atomic(staging / "run-spec.v1.json", spec_dict)
        command = [
            self.blender,
            "-b",
            "--factory-startup",
            "--python",
            str(_action_script()),
            "--",
            "--input",
            str(input_path),
            "--output",
            str(staging),
            "--size",
            str(size),
            "--subject-mode",
            subject_mode,
        ]
        started = utc_now()
        start_time = time.monotonic()
        run_record = RunRecord(run_id, "running", "run-spec.v1.json", command, started)
        write_json_atomic(staging / "run-record.v1.json", run_record.to_dict())
        failure_exit_code = 2
        try:
            try:
                process = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                failure_exit_code = 124
                (logs / "stdout.log").write_text(_text(exc.stdout), encoding="utf-8")
                timeout_message = "Blender quicklook timed out after %d seconds" % timeout_seconds
                partial_stderr = _text(exc.stderr)
                (logs / "stderr.log").write_text(
                    partial_stderr + ("\n" if partial_stderr else "") + timeout_message + "\n",
                    encoding="utf-8",
                )
                raise ContractError(timeout_message) from exc
            (logs / "stdout.log").write_text(_text(process.stdout), encoding="utf-8")
            (logs / "stderr.log").write_text(_text(process.stderr), encoding="utf-8")
            duration_ms = int((time.monotonic() - start_time) * 1000)
            report = read_json(staging / "quicklook-report.raw.json")
            if process.returncode != 0 or report.get("status") != "succeeded":
                raise ContractError("Blender quicklook failed: %s" % (report.get("error") or process.stderr.strip()))
            files: List[ArtifactFile] = []
            for name in REQUIRED_VIEWS:
                path = staging / "views" / (name + ".png")
                media = inspect_png(path)
                files.append(ArtifactFile(
                    role=name + "-view",
                    path=str(path.relative_to(staging)),
                    media_type="image/png",
                    sha256=media["sha256"],
                    size_bytes=media["size_bytes"],
                    metadata={"width": media["width"], "height": media["height"]},
                ))
            for role, relative, media_type in (
                ("quicklook-report", "quicklook-report.raw.json", "application/json"),
                ("blender-stdout", "logs/stdout.log", "text/plain"),
                ("blender-stderr", "logs/stderr.log", "text/plain"),
            ):
                path = staging / relative
                files.append(ArtifactFile(
                    role=role,
                    path=relative,
                    media_type=media_type,
                    sha256=sha256_file(path),
                    size_bytes=path.stat().st_size,
                ))
            input_lineage = [{"path": str(input_path), "sha256": input_hash}]
            file_dicts = [item.__dict__ for item in files]
            artifact_id = artifact_id_for(run_id, versioned_producer, input_lineage, file_dicts)
            manifest = ArtifactManifest(
                artifact_id=artifact_id,
                run_id=run_id,
                producer=versioned_producer,
                inputs=input_lineage,
                files=files,
                metrics=report["metrics"],
                exit_code=process.returncode,
                duration_ms=duration_ms,
            )
            write_json_atomic(staging / "artifact-manifest.v1.json", manifest.to_dict())
            run_record.status = "succeeded"
            run_record.completed_at = utc_now()
            run_record.exit_code = process.returncode
            write_json_atomic(staging / "run-record.v1.json", run_record.to_dict())
            staging.rename(run_dir)
            return run_dir
        except Exception as exc:
            stdout_path = logs / "stdout.log"
            stderr_path = logs / "stderr.log"
            if not stdout_path.exists():
                stdout_path.write_text("", encoding="utf-8")
            if not stderr_path.exists():
                stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
            run_record.status = "failed"
            run_record.completed_at = utc_now()
            run_record.exit_code = failure_exit_code
            run_record.error = str(exc)
            write_json_atomic(staging / "run-record.v1.json", run_record.to_dict())
            failed_dir = output_root / (run_id + ".failed-" + uuid.uuid4().hex[:12])
            staging.rename(failed_dir)
            raise
