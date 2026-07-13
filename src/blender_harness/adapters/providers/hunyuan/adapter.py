from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from ....io import ContractError, sha256_file, sha256_json, utc_now, write_json_atomic
from .operations import OPERATIONS, OperationSpec, validate_request


NORMALIZED_STATES = {"WAIT", "RUN", "DONE", "FAIL", "UNKNOWN"}
ARTIFACT_STATES = {"NOT_READY", "PENDING", "FETCHING", "FETCH_FAILED", "VERIFIED"}
SUBMISSION_STATES = {"RESERVED", "SUBMITTING", "SUBMIT_UNKNOWN", "SUBMIT_FAILED", "SUBMITTED"}

MAX_ZIP_ENTRIES = 512
MAX_ZIP_MEMBER_BYTES = 512 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_ZIP_COMPRESSION_RATIO = 1000
TEXTURE_MTL_DIRECTIVES = {
    "bump", "disp", "decal", "norm", "refl",
}
MTL_SINGLE_VALUE_OPTIONS = {
    "-blendu", "-blendv", "-boost", "-cc", "-clamp", "-colorspace",
    "-imfchan", "-texres", "-type", "-bm",
}
MTL_DOUBLE_VALUE_OPTIONS = {"-mm"}
MTL_VECTOR_OPTIONS = {"-o", "-s", "-t"}


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


def _zip_member_path(name: str) -> PurePosixPath:
    if not name or "\x00" in name or "\\" in name:
        raise ContractError("ZIP contains an unsafe member path: %r" % name)
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise ContractError("ZIP contains an absolute member path: %s" % name)
    path = PurePosixPath(name.rstrip("/"))
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError("ZIP contains a traversing member path: %s" % name)
    return path


def _checked_zip_entries(archive: zipfile.ZipFile) -> List[Tuple[zipfile.ZipInfo, PurePosixPath]]:
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise ContractError("ZIP contains too many entries: %d" % len(infos))
    checked: List[Tuple[zipfile.ZipInfo, PurePosixPath]] = []
    seen: Set[str] = set()
    total_size = 0
    for info in infos:
        member_path = _zip_member_path(info.filename)
        collision_key = member_path.as_posix().casefold()
        if collision_key in seen:
            raise ContractError("ZIP contains duplicate or case-conflicting member: %s" % info.filename)
        seen.add(collision_key)
        unix_mode = (info.external_attr >> 16) & 0xFFFF
        file_kind = stat.S_IFMT(unix_mode)
        if file_kind == stat.S_IFLNK:
            raise ContractError("ZIP symlink members are not allowed: %s" % info.filename)
        if file_kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise ContractError("ZIP special-file members are not allowed: %s" % info.filename)
        if info.flag_bits & 0x1:
            raise ContractError("encrypted ZIP members are not supported: %s" % info.filename)
        if info.file_size > MAX_ZIP_MEMBER_BYTES:
            raise ContractError("ZIP member exceeds size limit: %s" % info.filename)
        total_size += info.file_size
        if total_size > MAX_ZIP_TOTAL_BYTES:
            raise ContractError("ZIP uncompressed size exceeds limit")
        if info.file_size and info.compress_size == 0:
            raise ContractError("ZIP member has impossible compression metadata: %s" % info.filename)
        if info.compress_size and info.file_size / info.compress_size > MAX_ZIP_COMPRESSION_RATIO:
            raise ContractError("ZIP member exceeds compression-ratio limit: %s" % info.filename)
        checked.append((info, member_path))
    return checked


def _verify_zip_crc(path: Path) -> List[Tuple[zipfile.ZipInfo, PurePosixPath]]:
    try:
        with zipfile.ZipFile(path) as archive:
            checked = _checked_zip_entries(archive)
            corrupt = archive.testzip()
            if corrupt is not None:
                raise ContractError("ZIP member failed CRC verification: %s" % corrupt)
            return checked
    except ContractError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ContractError("invalid ZIP container: %s" % exc) from exc


def _extract_zip_safely(path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            checked = _checked_zip_entries(archive)
            destination.mkdir(parents=True, exist_ok=False)
            for info, member_path in checked:
                target = destination.joinpath(*member_path.parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if target.stat().st_size != info.file_size:
                    raise ContractError("ZIP member size changed while extracting: %s" % info.filename)
            corrupt = archive.testzip()
            if corrupt is not None:
                raise ContractError("ZIP member failed CRC verification: %s" % corrupt)
    except ContractError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ContractError("invalid ZIP container: %s" % exc) from exc


def _asset_reference(base: Path, reference: str, root: Path, source_kind: str) -> Path:
    if not reference or "\x00" in reference or "\\" in reference:
        raise ContractError("%s contains an unsafe asset reference: %r" % (source_kind, reference))
    relative = PurePosixPath(reference)
    if relative.is_absolute() or re.match(r"^[A-Za-z]:", reference):
        raise ContractError("%s contains an absolute asset reference: %s" % (source_kind, reference))
    if any(part in {"", ".", ".."} for part in relative.parts):
        # A material in a subdirectory may legitimately use ../textures/foo.png.
        candidate = (base / reference).resolve()
    else:
        candidate = base.joinpath(*relative.parts).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ContractError("%s asset reference escapes its bundle: %s" % (source_kind, reference)) from exc
    if not candidate.is_file():
        raise ContractError("%s references a missing file: %s" % (source_kind, reference))
    return candidate


def _read_asset_text(path: Path, kind: str) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContractError("%s is not UTF-8 text: %s" % (kind, path)) from exc
    if "\x00" in text:
        raise ContractError("%s contains NUL bytes: %s" % (kind, path))
    return text


def _mtl_texture_reference(value: str, line_number: int, material_path: Path) -> str:
    try:
        tokens = shlex.split(value, posix=True)
    except ValueError as exc:
        raise ContractError("MTL texture reference is malformed at line %d: %s" % (line_number, material_path)) from exc
    index = 0
    while index < len(tokens) and tokens[index].startswith("-"):
        option = tokens[index].lower()
        index += 1
        if option in MTL_SINGLE_VALUE_OPTIONS:
            count = 1
        elif option in MTL_DOUBLE_VALUE_OPTIONS:
            count = 2
        elif option in MTL_VECTOR_OPTIONS:
            count = 0
            while index + count < len(tokens) and count < 3:
                try:
                    float(tokens[index + count])
                except ValueError:
                    break
                count += 1
            if count == 0:
                raise ContractError("MTL texture option %s has no value at line %d: %s" % (option, line_number, material_path))
        else:
            raise ContractError("MTL texture option %s is unsupported at line %d: %s" % (option, line_number, material_path))
        if index + count > len(tokens):
            raise ContractError("MTL texture option %s is incomplete at line %d: %s" % (option, line_number, material_path))
        index += count
    if index >= len(tokens):
        raise ContractError("MTL texture reference is empty at line %d: %s" % (line_number, material_path))
    return " ".join(tokens[index:])


def _validate_obj_closure(obj_path: Path, root: Path) -> Tuple[Set[Path], Set[Path]]:
    text = _read_asset_text(obj_path, "OBJ")
    vertex_count = 0
    face_count = 0
    face_indices: List[int] = []
    material_paths: Set[Path] = set()
    texture_paths: Set[Path] = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        directive = parts[0].lower()
        if directive == "v":
            if len(parts) < 4:
                raise ContractError("OBJ vertex is malformed at line %d: %s" % (line_number, obj_path))
            try:
                coordinates = tuple(float(value) for value in parts[1:4])
            except ValueError as exc:
                raise ContractError("OBJ vertex is malformed at line %d: %s" % (line_number, obj_path)) from exc
            if not all(math.isfinite(value) for value in coordinates):
                raise ContractError("OBJ vertex is non-finite at line %d: %s" % (line_number, obj_path))
            vertex_count += 1
        elif directive == "f":
            if len(parts) < 4:
                raise ContractError("OBJ face is malformed at line %d: %s" % (line_number, obj_path))
            try:
                indices = [int(value.split("/", 1)[0]) for value in parts[1:]]
            except (ValueError, IndexError) as exc:
                raise ContractError("OBJ face is malformed at line %d: %s" % (line_number, obj_path)) from exc
            if any(index == 0 for index in indices):
                raise ContractError("OBJ face uses forbidden zero index at line %d: %s" % (line_number, obj_path))
            face_indices.extend(indices)
            face_count += 1
        elif directive == "mtllib":
            try:
                references = shlex.split(line[len(parts[0]):].strip(), posix=True)
            except ValueError as exc:
                raise ContractError("OBJ mtllib is malformed at line %d: %s" % (line_number, obj_path)) from exc
            if not references:
                raise ContractError("OBJ mtllib is empty at line %d: %s" % (line_number, obj_path))
            for reference in references:
                material_paths.add(_asset_reference(obj_path.parent, reference, root, "OBJ"))
    if vertex_count < 3 or face_count < 1:
        raise ContractError("OBJ must contain at least three vertices and one face: %s" % obj_path)
    if any(index > vertex_count or index < -vertex_count for index in face_indices):
        raise ContractError("OBJ face references a vertex outside the file: %s" % obj_path)
    for material_path in material_paths:
        material_text = _read_asset_text(material_path, "MTL")
        for line_number, raw_line in enumerate(material_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            directive = parts[0].lower()
            if directive not in TEXTURE_MTL_DIRECTIVES and not directive.startswith("map_"):
                continue
            if len(parts) != 2:
                raise ContractError("MTL texture reference is empty at line %d: %s" % (line_number, material_path))
            reference = _mtl_texture_reference(parts[1], line_number, material_path)
            texture_paths.add(_asset_reference(material_path.parent, reference, root, "MTL"))
    return material_paths, texture_paths


def _validate_obj_bundle(root: Path) -> Tuple[Path, Set[Path], Set[Path]]:
    obj_files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() == ".obj")
    if len(obj_files) != 1:
        raise ContractError("OBJ ZIP bundle must contain exactly one primary OBJ; found %d" % len(obj_files))
    materials, textures = _validate_obj_closure(obj_files[0], root)
    return obj_files[0], materials, textures


def _unpacked_manifest(
    root: Path,
    run_dir: Path,
    primary: Path,
    materials: Set[Path],
    textures: Set[Path],
) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        role = "auxiliary"
        if path == primary:
            role = "primary_geometry"
        elif path in materials:
            role = "material_library"
        elif path in textures:
            role = "texture"
        files.append({
            "path": str(path.relative_to(run_dir)),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "role": role,
            "format": path.suffix[1:].upper() if path.suffix else "BIN",
        })
    return files


def _crc32_file(path: Path) -> int:
    checksum = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum = zlib.crc32(chunk, checksum)
    return checksum & 0xFFFFFFFF


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
                if item.get("size_bytes") is not None and path.stat().st_size != item["size_bytes"]:
                    raise ContractError("cached Hunyuan artifact size changed: %s" % path)
                provider_type = str(item.get("provider_type") or item.get("type") or "").upper()
                container_type = str(item.get("container_type") or provider_type).upper()
                if container_type == "ZIP":
                    if provider_type != "OBJ":
                        raise ContractError("ZIP containers are currently supported only for provider Type=OBJ")
                    entries = _verify_zip_crc(path)
                    unpacked_root_value = item.get("unpacked_root")
                    primary_value = item.get("primary_entrypoint")
                    unpacked_files = item.get("unpacked_files")
                    if not unpacked_root_value or not primary_value or not isinstance(unpacked_files, list):
                        raise ContractError("cached OBJ ZIP manifest is missing unpacked bundle metadata")
                    unpacked_root = self.store.run_dir(handle_id) / unpacked_root_value
                    root_resolved = unpacked_root.resolve()
                    if not unpacked_root.is_dir():
                        raise ContractError("cached OBJ ZIP unpacked root is missing: %s" % unpacked_root)
                    archive_metadata = {
                        member.as_posix(): (info.file_size, info.CRC)
                        for info, member in entries if not info.is_dir()
                    }
                    recorded_paths: Set[str] = set()
                    for member in unpacked_files:
                        member_path = self.store.run_dir(handle_id) / member["path"]
                        try:
                            member_path.resolve().relative_to(root_resolved)
                        except ValueError as exc:
                            raise ContractError("cached OBJ ZIP member escapes unpacked root: %s" % member_path) from exc
                        if not member_path.is_file() or sha256_file(member_path) != member["sha256"]:
                            raise ContractError("cached Hunyuan unpacked member is missing or changed: %s" % member_path)
                        if member_path.stat().st_size != member["size_bytes"]:
                            raise ContractError("cached Hunyuan unpacked member size changed: %s" % member_path)
                        relative_member = member_path.relative_to(unpacked_root).as_posix()
                        recorded_paths.add(relative_member)
                        archive_size_crc = archive_metadata.get(relative_member)
                        if archive_size_crc is None or archive_size_crc != (
                            member_path.stat().st_size,
                            _crc32_file(member_path),
                        ):
                            raise ContractError("cached Hunyuan unpacked member differs from its ZIP container: %s" % member_path)
                    actual_paths = {
                        candidate.relative_to(unpacked_root).as_posix()
                        for candidate in unpacked_root.rglob("*") if candidate.is_file()
                    }
                    archive_paths = {member.as_posix() for info, member in entries if not info.is_dir()}
                    if recorded_paths != actual_paths or archive_paths != actual_paths:
                        raise ContractError("cached OBJ ZIP member set does not match its container manifest")
                    primary, _, _ = _validate_obj_bundle(unpacked_root)
                    recorded_primary = self.store.run_dir(handle_id) / primary_value
                    if primary.resolve() != recorded_primary.resolve():
                        raise ContractError("cached OBJ ZIP primary entrypoint changed")
                else:
                    _validate_magic(path, provider_type)
                    if provider_type == "OBJ":
                        _validate_obj_closure(path, path.parent)
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
        all_unpacked_files: List[Dict[str, Any]] = []
        primary_entrypoints: List[str] = []
        for index, item in enumerate(result_files, start=1):
            provider_type = str(item.get("type") or fallback_type or _type_from_url(item["url"])).upper()
            if provider_type not in spec.expected_types:
                raise ContractError(
                    "provider returned unexpected artifact type %s for %s (expected %s)"
                    % (provider_type or "<empty>", handle.operation, ", ".join(spec.expected_types))
                )
            extension = _extension(provider_type, item["url"])
            destination = output_dir / ("%02d-%s%s" % (index, spec.artifact_role, extension))
            fd, staged_name = tempfile.mkstemp(prefix=".download-", suffix=extension, dir=str(output_dir))
            os.close(fd)
            staged = Path(staged_name)
            bundle_stage: Optional[Path] = None
            try:
                self.downloader.download(item["url"], staged)
                is_obj_zip = provider_type == "OBJ" and zipfile.is_zipfile(staged)
                if is_obj_zip:
                    _verify_zip_crc(staged)
                    bundle_stage = Path(tempfile.mkdtemp(prefix=".obj-bundle-", dir=str(output_dir)))
                    staged_container = bundle_stage / ("%02d-%s.zip" % (index, spec.artifact_role))
                    os.replace(str(staged), str(staged_container))
                    unpacked_stage = bundle_stage / "unpacked"
                    _extract_zip_safely(staged_container, unpacked_stage)
                    primary_stage, _, _ = _validate_obj_bundle(unpacked_stage)
                    final_bundle = output_dir / ("%02d-%s-bundle" % (index, spec.artifact_role))
                    if final_bundle.exists():
                        raise ContractError("unmanifested Hunyuan bundle already exists: %s" % final_bundle)
                    os.replace(str(bundle_stage), str(final_bundle))
                    bundle_stage = None
                    destination = final_bundle / staged_container.name
                    unpacked_root = final_bundle / "unpacked"
                    primary = unpacked_root / primary_stage.relative_to(unpacked_stage)
                    materials, textures = _validate_obj_closure(primary, unpacked_root)
                    unpacked_files = _unpacked_manifest(
                        unpacked_root,
                        self.store.run_dir(handle_id),
                        primary,
                        materials,
                        textures,
                    )
                    primary_entrypoint = str(primary.relative_to(self.store.run_dir(handle_id)))
                    all_unpacked_files.extend(unpacked_files)
                    primary_entrypoints.append(primary_entrypoint)
                    manifest_files.append({
                        "role": spec.artifact_role,
                        "type": provider_type,
                        "provider_type": provider_type,
                        "container_type": "ZIP",
                        "path": str(destination.relative_to(self.store.run_dir(handle_id))),
                        "sha256": sha256_file(destination),
                        "size_bytes": destination.stat().st_size,
                        "container_sha256": sha256_file(destination),
                        "container_size_bytes": destination.stat().st_size,
                        "unpacked_root": str(unpacked_root.relative_to(self.store.run_dir(handle_id))),
                        "primary_entrypoint": primary_entrypoint,
                        "unpacked_files": unpacked_files,
                        "source_url": redact_url(item["url"]),
                        "preview_url": redact_url(item["preview_url"]) if item.get("preview_url") else None,
                    })
                    continue
                _validate_magic(staged, provider_type)
                if provider_type == "OBJ":
                    _validate_obj_closure(staged, staged.parent)
                os.replace(str(staged), str(destination))
            finally:
                if staged.exists():
                    staged.unlink()
                if bundle_stage is not None and bundle_stage.exists():
                    shutil.rmtree(bundle_stage)
            manifest_files.append({
                "role": spec.artifact_role,
                "type": provider_type,
                "provider_type": provider_type,
                "container_type": provider_type,
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
        if len(primary_entrypoints) == 1:
            manifest["primary_entrypoint"] = primary_entrypoints[0]
        if all_unpacked_files:
            manifest["unpacked_files"] = all_unpacked_files
        write_json_atomic(manifest_path, manifest)
        handle.artifact_status = "VERIFIED"
        handle.artifact_error = None
        handle.updated_at = utc_now()
        self.store.save(handle)
        return manifest_path
