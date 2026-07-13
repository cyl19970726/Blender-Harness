from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from ....io import ContractError, sha256_file, sha256_json, utc_now, write_json_atomic
from .operations import OPERATIONS, OperationSpec, validate_request


NORMALIZED_STATES = {"WAIT", "RUN", "DONE", "FAIL", "UNKNOWN"}
ARTIFACT_STATES = {"NOT_READY", "PENDING", "FETCHING", "FETCH_FAILED", "VERIFIED"}
SUBMISSION_STATES = {"RESERVED", "SUBMITTING", "SUBMIT_UNKNOWN", "SUBMIT_FAILED", "SUBMITTED"}


class Transport(Protocol):
    def call(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...


class Downloader(Protocol):
    def download(self, url: str, destination: Path) -> None: ...


@dataclass
class JobHandle:
    handle_id: str
    provider: str
    operation: str
    submit_action: str
    status_action: Optional[str]
    job_id: Optional[str]
    request_id: Optional[str]
    request_hash: str
    idempotency_key: str
    provider_status: str
    artifact_status: str
    submission_status: str
    submitted_at: str
    updated_at: str
    artifact_deadline: str
    warnings: List[str] = field(default_factory=list)
    last_response: Dict[str, Any] = field(default_factory=dict)
    artifact_error: Optional[str] = None
    submission_error: Optional[str] = None
    schema: str = "blender-harness.hunyuan-job-handle.v1"

    @property
    def status(self) -> str:
        """Compatibility alias for callers that still display provider status as status."""
        return self.provider_status

    def to_dict(self) -> Dict[str, Any]:
        if self.provider_status not in NORMALIZED_STATES:
            raise ContractError("invalid Hunyuan provider status: %s" % self.provider_status)
        if self.artifact_status not in ARTIFACT_STATES:
            raise ContractError("invalid Hunyuan artifact status: %s" % self.artifact_status)
        if self.submission_status not in SUBMISSION_STATES:
            raise ContractError("invalid Hunyuan submission status: %s" % self.submission_status)
        value = asdict(self)
        value["status"] = self.provider_status
        return value


class JobStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def run_dir(self, handle_id: str) -> Path:
        if not re.match(r"^[a-f0-9]{24}$", handle_id):
            raise ContractError("invalid handle id")
        return self.root / handle_id

    def handle_path(self, handle_id: str) -> Path:
        return self.run_dir(handle_id) / "job.json"

    @contextmanager
    def exclusive(self, handle_id: str, timeout_seconds: float = 10.0):
        lock_path = self.run_dir(handle_id) / ".job.lock"
        deadline = time.monotonic() + timeout_seconds
        fd = None
        while fd is None:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, ("pid=%d\n" % os.getpid()).encode("ascii"))
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise ContractError("Hunyuan job is locked: %s" % handle_id)
                time.sleep(0.05)
        try:
            yield
        finally:
            if fd is not None:
                os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def load(self, handle_id: str) -> JobHandle:
        value = json.loads(self.handle_path(handle_id).read_text(encoding="utf-8"))
        legacy_status = value.pop("status", None)
        value.setdefault("provider_status", legacy_status or "UNKNOWN")
        value.setdefault("artifact_status", "PENDING" if value["provider_status"] == "DONE" else "NOT_READY")
        value.setdefault("submission_status", "SUBMITTED")
        return JobHandle(**value)

    def save(self, handle: JobHandle) -> None:
        write_json_atomic(self.handle_path(handle.handle_id), handle.to_dict())

    def save_request(self, handle: JobHandle, request: Dict[str, Any]) -> None:
        write_json_atomic(self.run_dir(handle.handle_id) / "request.json", request)

    def load_request(self, handle_id: str) -> Dict[str, Any]:
        return json.loads((self.run_dir(handle_id) / "request.json").read_text(encoding="utf-8"))

    def reserve(self, handle: JobHandle, request: Dict[str, Any]) -> bool:
        """Atomically reserve an idempotency key before any provider call."""
        self.root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".reserve-", dir=str(self.root)))
        try:
            write_json_atomic(staging / "job.json", handle.to_dict())
            write_json_atomic(staging / "request.json", request)
            try:
                os.rename(str(staging), str(self.run_dir(handle.handle_id)))
            except OSError:
                if self.run_dir(handle.handle_id).exists():
                    return False
                raise
            return True
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def save_response(self, handle: JobHandle, action: str, response: Dict[str, Any]) -> Path:
        history = self.run_dir(handle.handle_id) / "responses"
        history.mkdir(parents=True, exist_ok=True)
        sequence = len(list(history.glob("*.json"))) + 1
        path = history / ("%03d-%s.json" % (sequence, action))
        write_json_atomic(path, response)
        return path

    def save_private_result_files(self, handle_id: str, files: List[Dict[str, Any]]) -> None:
        path = self.run_dir(handle_id) / "result-urls.private.json"
        write_json_atomic(path, {"files": files})
        os.chmod(path, 0o600)

    def load_private_result_files(self, handle_id: str) -> List[Dict[str, Any]]:
        path = self.run_dir(handle_id) / "result-urls.private.json"
        if not path.exists():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        return value.get("files", []) if isinstance(value, dict) else []


class CurlDownloader:
    def __init__(self, retries: int = 3):
        self.retries = retries

    def download(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".part", dir=str(destination.parent))
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            curl = shutil.which("curl")
            if curl:
                process = subprocess.run(
                    [
                        curl, "-sS", "-L", "--fail-with-body", "--retry", str(self.retries),
                        "--retry-all-errors", "--retry-delay", "1", "--output", str(temp_path), url,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if process.returncode != 0:
                    raise ContractError("curl download failed: %s" % process.stderr.strip())
            else:
                last_error = None
                for attempt in range(self.retries + 1):
                    try:
                        with urlopen(url, timeout=90) as response, temp_path.open("wb") as output:
                            shutil.copyfileobj(response, output)
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt < self.retries:
                            time.sleep(min(2 ** attempt, 4))
                if last_error is not None:
                    raise ContractError("provider download failed after retries: %s" % last_error)
            if temp_path.stat().st_size <= 0:
                raise ContractError("provider download is empty")
            os.replace(str(temp_path), str(destination))
        finally:
            if temp_path.exists():
                temp_path.unlink()


def normalize_status(response: Dict[str, Any]) -> str:
    raw = str(response.get("Status") or response.get("JobStatus") or "").upper()
    if raw in {"WAIT", "RUN", "DONE", "FAIL"}:
        return raw
    return "UNKNOWN"


def redact_url(value: str) -> str:
    parsed = urlparse(value)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def scrub_response_urls(value: Any, key: Optional[str] = None) -> Any:
    if isinstance(value, dict):
        return {item_key: scrub_response_urls(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [scrub_response_urls(item, key) for item in value]
    if isinstance(value, str) and key in {"Url", "URL", "FileUrl", "PreviewImageUrl", "ResultFile3D"}:
        return redact_url(value)
    return value


def _type_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix
    return suffix[1:].upper() if re.match(r"^\.[A-Za-z0-9]{1,8}$", suffix) else ""


def extract_result_files(response: Dict[str, Any], fallback_type: str = "") -> List[Dict[str, Any]]:
    candidates: List[Any] = []
    for key in ("ResultFile3Ds", "ResultFile3D", "File3Ds", "Files"):
        if response.get(key) is not None:
            value = response[key]
            candidates.extend(value if isinstance(value, list) else [value])
    files: List[Dict[str, Any]] = []
    for item in candidates:
        if isinstance(item, str) and item:
            files.append({
                "type": (fallback_type or _type_from_url(item)).upper(),
                "url": item,
                "preview_url": None,
            })
            continue
        if not isinstance(item, dict):
            continue
        url = item.get("Url") or item.get("URL") or item.get("FileUrl")
        if isinstance(url, str) and url:
            files.append({
                "type": str(item.get("Type") or fallback_type or _type_from_url(url)).upper(),
                "url": url,
                "preview_url": item.get("PreviewImageUrl"),
            })
    return files


def _extension(file_type: str, url: str) -> str:
    if file_type:
        return "." + re.sub(r"[^a-z0-9]", "", file_type.lower())
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if re.match(r"^\.[a-z0-9]{1,8}$", suffix) else ".bin"


def _validate_magic(path: Path, file_type: str) -> None:
    head = path.read_bytes()[:32]
    if not head:
        raise ContractError("downloaded artifact is empty: %s" % path)
    kind = file_type.upper()
    if kind == "GLB" and not head.startswith(b"glTF"):
        raise ContractError("GLB artifact has invalid magic: %s" % path)
    if kind == "FBX" and not (head.startswith(b"Kaydara FBX Binary") or b"FBX" in head.upper()):
        raise ContractError("FBX artifact has invalid magic: %s" % path)
    if kind == "PNG" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ContractError("PNG artifact has invalid magic: %s" % path)
    if kind == "GIF" and not (head.startswith(b"GIF87a") or head.startswith(b"GIF89a")):
        raise ContractError("GIF artifact has invalid magic: %s" % path)
    if kind == "MP4" and not (len(head) >= 12 and head[4:8] == b"ftyp"):
        raise ContractError("MP4 artifact has invalid magic: %s" % path)
    if kind == "USDZ" and not head.startswith(b"PK\x03\x04"):
        raise ContractError("USDZ artifact has invalid magic: %s" % path)
    if kind == "STL" and path.stat().st_size < 84 and not head.lstrip().lower().startswith(b"solid"):
        raise ContractError("STL artifact is too small to be valid: %s" % path)


class HunyuanAdapter:
    provider = "hunyuan"
    api_version = "2025-05-13"

    def __init__(self, transport: Transport, store: JobStore, downloader: Optional[Downloader] = None):
        self.transport = transport
        self.store = store
        self.downloader = downloader or CurlDownloader()

    def capabilities(self) -> Dict[str, Any]:
        actions = []
        for spec in OPERATIONS.values():
            actions.append(spec.submit_action)
            if spec.status_action:
                actions.append(spec.status_action)
        return {
            "provider": self.provider,
            "api_version": self.api_version,
            "operation_count": len(OPERATIONS),
            "action_count": len(actions),
            "operations": [spec.to_dict() for spec in OPERATIONS.values()],
        }

    def submit(self, operation: str, request: Dict[str, Any], idempotency_key: str) -> JobHandle:
        warnings = validate_request(operation, request)
        if not idempotency_key.strip():
            raise ContractError("idempotency_key is required")
        spec = OPERATIONS[operation]
        request_hash = sha256_json({"operation": operation, "request": request})
        handle_id = sha256_json({"idempotency_key": idempotency_key})[:24]
        submitted_at = utc_now()
        deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).replace(microsecond=0).isoformat()
        handle = JobHandle(
            handle_id=handle_id,
            provider=self.provider,
            operation=operation,
            submit_action=spec.submit_action,
            status_action=spec.status_action,
            job_id=None,
            request_id=None,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            provider_status="UNKNOWN",
            artifact_status="NOT_READY",
            submission_status="RESERVED",
            submitted_at=submitted_at,
            updated_at=submitted_at,
            artifact_deadline=deadline,
            warnings=warnings,
            last_response={},
        )
        if not self.store.reserve(handle, request):
            existing = self.store.load(handle_id)
            if existing.request_hash != request_hash or existing.operation != operation:
                raise ContractError("idempotency key was already used for a different request")
            return existing

        handle.submission_status = "SUBMITTING"
        handle.updated_at = utc_now()
        self.store.save(handle)
        try:
            response = self.transport.call(spec.submit_action, request)
        except Exception as exc:
            handle.submission_status = "SUBMIT_UNKNOWN" if getattr(exc, "retryable", False) else "SUBMIT_FAILED"
            handle.submission_error = str(exc)
            handle.updated_at = utc_now()
            self.store.save(handle)
            raise

        job_id = response.get("JobId") if spec.is_async else None
        scrubbed_response = scrub_response_urls(response)
        if spec.is_async and (not isinstance(job_id, str) or not job_id):
            handle.submission_status = "SUBMIT_FAILED"
            handle.submission_error = "provider submit response did not include JobId"
            handle.last_response = scrubbed_response
            self.store.save_response(handle, spec.submit_action, scrubbed_response)
            self.store.save(handle)
            raise ContractError(handle.submission_error)

        fallback_type = str(request.get("Format") or "") if not spec.is_async else ""
        result_files = extract_result_files(response, fallback_type)
        if result_files:
            self.store.save_private_result_files(handle.handle_id, result_files)
        handle.job_id = job_id
        handle.request_id = response.get("RequestId")
        handle.provider_status = "WAIT" if spec.is_async else "DONE"
        handle.artifact_status = "NOT_READY" if spec.is_async else "PENDING"
        handle.submission_status = "SUBMITTED"
        handle.submission_error = None
        handle.last_response = scrubbed_response
        handle.updated_at = utc_now()
        self.store.save_response(handle, spec.submit_action, scrubbed_response)
        self.store.save(handle)
        return handle

    def poll_once(self, handle_id: str) -> JobHandle:
        with self.store.exclusive(handle_id):
            handle = self.store.load(handle_id)
            if handle.provider_status in {"DONE", "FAIL"}:
                return handle
            if not handle.status_action or not handle.job_id:
                raise ContractError("job handle is missing status action or JobId")
            response = self.transport.call(handle.status_action, {"JobId": handle.job_id})
            handle.provider_status = normalize_status(response)
            if handle.provider_status == "DONE":
                result_files = extract_result_files(response)
                if result_files:
                    self.store.save_private_result_files(handle.handle_id, result_files)
                handle.artifact_status = "PENDING"
            elif handle.provider_status == "FAIL":
                handle.artifact_status = "NOT_READY"
            handle.updated_at = utc_now()
            handle.last_response = scrub_response_urls(response)
            self.store.save_response(handle, handle.status_action, handle.last_response)
            self.store.save(handle)
            return handle

    def fetch(self, handle_id: str) -> Path:
        with self.store.exclusive(handle_id):
            handle = self.store.load(handle_id)
            if handle.provider_status != "DONE":
                raise ContractError("cannot fetch Hunyuan artifacts before DONE")
            handle.artifact_status = "FETCHING"
            handle.artifact_error = None
            handle.updated_at = utc_now()
            self.store.save(handle)
            try:
                return self._fetch_verified(handle)
            except Exception as exc:
                handle.artifact_status = "FETCH_FAILED"
                handle.artifact_error = str(exc)
                handle.updated_at = utc_now()
                self.store.save(handle)
                raise

    def _fetch_verified(self, handle: JobHandle) -> Path:
        handle_id = handle.handle_id
        manifest_path = self.store.run_dir(handle_id) / "artifact-manifest.v1.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest.get("files", []):
                path = self.store.run_dir(handle_id) / item["path"]
                if not path.is_file() or sha256_file(path) != item["sha256"]:
                    raise ContractError("cached Hunyuan artifact is missing or changed: %s" % path)
                _validate_magic(path, str(item.get("type") or ""))
            if not manifest.get("files"):
                raise ContractError("cached Hunyuan manifest contains no files")
            handle.artifact_status = "VERIFIED"
            handle.artifact_error = None
            handle.updated_at = utc_now()
            self.store.save(handle)
            return manifest_path
        spec: OperationSpec = OPERATIONS[handle.operation]
        request = self.store.load_request(handle_id)
        fallback_type = str(request.get("Format") or "") if handle.operation == "format.convert" else ""
        result_files = self.store.load_private_result_files(handle_id)
        if not result_files:
            result_files = extract_result_files(handle.last_response, fallback_type)
        if not result_files:
            raise ContractError("provider reported DONE without downloadable result files")
        output_dir = self.store.run_dir(handle_id) / "artifacts"
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_files: List[Dict[str, Any]] = []
        for index, item in enumerate(result_files, start=1):
            item_type = str(item.get("type") or fallback_type or _type_from_url(item["url"])).upper()
            if item_type not in spec.expected_types:
                raise ContractError(
                    "provider returned unexpected artifact type %s for %s (expected %s)"
                    % (item_type or "<empty>", handle.operation, ", ".join(spec.expected_types))
                )
            extension = _extension(item_type, item["url"])
            destination = output_dir / ("%02d-%s%s" % (index, spec.artifact_role, extension))
            fd, staged_name = tempfile.mkstemp(prefix=".download-", suffix=extension, dir=str(output_dir))
            os.close(fd)
            staged = Path(staged_name)
            try:
                self.downloader.download(item["url"], staged)
                _validate_magic(staged, item_type)
                os.replace(str(staged), str(destination))
            finally:
                if staged.exists():
                    staged.unlink()
            manifest_files.append({
                "role": spec.artifact_role,
                "type": item_type,
                "path": str(destination.relative_to(self.store.run_dir(handle_id))),
                "sha256": sha256_file(destination),
                "size_bytes": destination.stat().st_size,
                "source_url": redact_url(item["url"]),
                "preview_url": redact_url(item["preview_url"]) if item.get("preview_url") else None,
            })
        manifest = {
            "schema": "blender-harness.hunyuan-artifact-manifest.v1",
            "provider": self.provider,
            "api_version": self.api_version,
            "handle_id": handle.handle_id,
            "operation": handle.operation,
            "status": handle.provider_status,
            "provider_status": handle.provider_status,
            "artifact_status": "VERIFIED",
            "provider_done_is_asset_approval": False,
            "warnings": handle.warnings,
            "request_hash": handle.request_hash,
            "job_id": handle.job_id,
            "request_id": handle.request_id,
            "submitted_at": handle.submitted_at,
            "downloaded_at": utc_now(),
            "artifact_deadline": handle.artifact_deadline,
            "result_credit_consumed": handle.last_response.get("ResultCreditConsumed"),
            "result_credit_details": handle.last_response.get("ResultCreditDetails"),
            "files": manifest_files,
        }
        write_json_atomic(manifest_path, manifest)
        handle.artifact_status = "VERIFIED"
        handle.artifact_error = None
        handle.updated_at = utc_now()
        self.store.save(handle)
        return manifest_path
