from __future__ import annotations

import json
import fcntl
import ipaddress
import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from ....io import ContractError, sha256_file, sha256_json, utc_now, write_json_atomic
from .client import TransportResult
from .operations import OPERATIONS, OperationSpec, validate_request


NORMALIZED_STATES = {"WAIT", "RUN", "DONE", "FAIL", "UNKNOWN"}
ARTIFACT_STATES = {"NOT_READY", "PENDING", "FETCHING", "FETCH_FAILED", "VERIFIED"}
SUBMISSION_STATES = {"RESERVED", "SUBMITTING", "SUBMIT_UNKNOWN", "SUBMIT_FAILED", "SUBMITTED"}
VIEW_ORDER = ("front", "left", "back", "right")
MAX_IMAGE_BYTES = 20 * 1024 * 1024


class Transport(Protocol):
    credentials: Any

    def request(
        self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> TransportResult: ...

    def upload(self, path: Path) -> TransportResult: ...


class Downloader(Protocol):
    def download(self, url: str, destination: Path) -> None: ...


@dataclass
class JobHandle:
    handle_id: str
    provider: str
    operation: str
    submit_endpoint: str
    task_id: Optional[str]
    request_hash: str
    idempotency_key: str
    credential_fingerprint: str
    trace_id: Optional[str]
    provider_status: str
    artifact_status: str
    submission_status: str
    submitted_at: str
    updated_at: str
    artifact_deadline: Optional[str]
    result_url_observed_at: Optional[str] = None
    result_url_expires_at: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    last_response: Dict[str, Any] = field(default_factory=dict)
    artifact_error: Optional[str] = None
    submission_error: Optional[str] = None
    schema: str = "blender-harness.tripo-job-handle.v1"

    @property
    def status(self) -> str:
        return self.provider_status

    def to_dict(self) -> Dict[str, Any]:
        if self.provider_status not in NORMALIZED_STATES:
            raise ContractError("invalid Tripo provider status: %s" % self.provider_status)
        if self.artifact_status not in ARTIFACT_STATES:
            raise ContractError("invalid Tripo artifact status: %s" % self.artifact_status)
        if self.submission_status not in SUBMISSION_STATES:
            raise ContractError("invalid Tripo submission status: %s" % self.submission_status)
        if self.provider_status in {"RUN", "DONE", "FAIL"} and self.submission_status != "SUBMITTED":
            raise ContractError("Tripo provider terminal/running state requires SUBMITTED")
        if self.artifact_status in {"PENDING", "FETCHING", "FETCH_FAILED", "VERIFIED"}:
            if self.provider_status != "DONE":
                raise ContractError("Tripo artifact work requires provider DONE")
        if self.artifact_status == "VERIFIED" and self.artifact_error is not None:
            raise ContractError("verified Tripo artifact cannot retain artifact_error")
        return asdict(self)


class JobStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def run_dir(self, handle_id: str) -> Path:
        if not re.match(r"^[a-f0-9]{24}$", handle_id):
            raise ContractError("invalid Tripo handle id")
        return self.root / handle_id

    def handle_path(self, handle_id: str) -> Path:
        return self.run_dir(handle_id) / "job.json"

    @contextmanager
    def exclusive(self, handle_id: str, timeout_seconds: float = 10.0):
        lock_path = self.run_dir(handle_id) / ".job.lock"
        deadline = time.monotonic() + timeout_seconds
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        locked = False
        while not locked:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise ContractError("Tripo job is locked: %s" % handle_id)
                time.sleep(0.05)
        try:
            os.ftruncate(fd, 0)
            os.write(fd, ("pid=%d\n" % os.getpid()).encode("ascii"))
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def load(self, handle_id: str) -> JobHandle:
        value = json.loads(self.handle_path(handle_id).read_text(encoding="utf-8"))
        value.pop("status", None)
        return JobHandle(**value)

    def save(self, handle: JobHandle) -> None:
        write_json_atomic(self.handle_path(handle.handle_id), handle.to_dict())

    def reserve(
        self,
        handle: JobHandle,
        public_request: Dict[str, Any],
        private_request: Dict[str, Any],
    ) -> bool:
        self.root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".reserve-", dir=str(self.root)))
        try:
            write_json_atomic(staging / "job.json", handle.to_dict())
            write_json_atomic(staging / "request.json", public_request)
            write_json_atomic(staging / "request.private.json", private_request)
            os.chmod(staging / "request.private.json", 0o600)
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

    def load_request(self, handle_id: str) -> Dict[str, Any]:
        return json.loads((self.run_dir(handle_id) / "request.json").read_text(encoding="utf-8"))

    def load_private_request(self, handle_id: str) -> Dict[str, Any]:
        return json.loads(
            (self.run_dir(handle_id) / "request.private.json").read_text(encoding="utf-8")
        )

    def save_response(self, handle: JobHandle, label: str, response: Dict[str, Any]) -> Path:
        history = self.run_dir(handle.handle_id) / "responses"
        history.mkdir(parents=True, exist_ok=True)
        sequence = len(list(history.glob("*.json"))) + 1
        safe_label = re.sub(r"[^a-z0-9-]", "-", label.lower()).strip("-") or "response"
        path = history / ("%03d-%s.json" % (sequence, safe_label))
        write_json_atomic(path, response)
        return path

    def save_uploads(self, handle_id: str, uploads: List[Dict[str, Any]]) -> None:
        path = self.run_dir(handle_id) / "uploads.private.json"
        write_json_atomic(path, {"uploads": uploads})
        os.chmod(path, 0o600)

    def load_uploads(self, handle_id: str) -> List[Dict[str, Any]]:
        path = self.run_dir(handle_id) / "uploads.private.json"
        if not path.exists():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        return value.get("uploads", []) if isinstance(value, dict) else []

    def save_private_results(self, handle_id: str, files: List[Dict[str, Any]]) -> None:
        path = self.run_dir(handle_id) / "result-urls.private.json"
        generations: List[Dict[str, Any]] = []
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                generations = existing.get("generations", [])
                if not generations and isinstance(existing.get("files"), list):
                    generations = [{"observed_at": None, "files": existing["files"]}]
        generations.append({"observed_at": utc_now(), "files": files})
        write_json_atomic(path, {"generations": generations})
        os.chmod(path, 0o600)

    def load_private_results(self, handle_id: str) -> List[Dict[str, Any]]:
        path = self.run_dir(handle_id) / "result-urls.private.json"
        if not path.exists():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return []
        generations = value.get("generations")
        if isinstance(generations, list) and generations:
            latest = generations[-1]
            return latest.get("files", []) if isinstance(latest, dict) else []
        return value.get("files", []) if isinstance(value.get("files"), list) else []

    def save_reconciliation(self, handle_id: str, record: Dict[str, Any]) -> Path:
        directory = self.run_dir(handle_id) / "reconciliations"
        directory.mkdir(parents=True, exist_ok=True)
        sequence = len(list(directory.glob("*.json"))) + 1
        path = directory / ("%03d.json" % sequence)
        write_json_atomic(path, record)
        return path


class CurlDownloader:
    def __init__(self, retries: int = 3, max_bytes: int = 1024 * 1024 * 1024):
        self.retries = retries
        self.max_bytes = max_bytes

    def download(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=destination.name + ".", suffix=".part", dir=str(destination.parent)
        )
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            curl = shutil.which("curl")
            if curl:
                process = subprocess.run(
                    [
                        curl, "-sS", "-L", "--fail", "--proto", "=https",
                        "--proto-redir", "=https", "--connect-timeout", "20", "--max-time", "180",
                        "--max-filesize", str(self.max_bytes), "--retry", str(self.retries),
                        "--retry-all-errors", "--retry-delay", "1", "--output", str(temp_path), url,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if process.returncode != 0:
                    raise ContractError("Tripo artifact download failed")
            else:
                last_error: Optional[Exception] = None
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
                    raise ContractError("Tripo artifact download failed") from last_error
            if temp_path.stat().st_size <= 0:
                raise ContractError("Tripo artifact download is empty")
            if temp_path.stat().st_size > self.max_bytes:
                raise ContractError("Tripo artifact exceeds the download size limit")
            os.replace(str(temp_path), str(destination))
        finally:
            if temp_path.exists():
                temp_path.unlink()


def redact_url(value: str) -> str:
    parsed = urlparse(value)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def scrub_urls(value: Any, key: Optional[str] = None) -> Any:
    if isinstance(value, dict):
        return {item_key: scrub_urls(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [scrub_urls(item, key) for item in value]
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        return redact_url(value)
    return value


def normalize_status(data: Dict[str, Any]) -> str:
    raw = str(data.get("status") or "").lower()
    if raw in {"queued", "pending", "waiting"}:
        return "WAIT"
    if raw in {"running", "processing"}:
        return "RUN"
    if raw in {"success", "succeeded", "completed"}:
        return "DONE"
    if raw in {"failed", "cancelled", "canceled", "banned", "expired"}:
        return "FAIL"
    return "UNKNOWN"


def _response_data(result: TransportResult) -> Dict[str, Any]:
    data = result.body.get("data")
    if not isinstance(data, dict):
        raise ContractError("Tripo response is missing a data object")
    return data


def _validate_input_image(path: Path) -> str:
    if not path.is_file():
        raise ContractError("Tripo input image does not exist: %s" % path)
    size = path.stat().st_size
    if size <= 0 or size > MAX_IMAGE_BYTES:
        raise ContractError("Tripo input image must be between 1 byte and 20 MB: %s" % path)
    with path.open("rb") as handle:
        head = handle.read(16)
        if size >= 2:
            handle.seek(-2, os.SEEK_END)
            tail = handle.read(2)
        else:
            tail = b""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "PNG"
    elif head.startswith(b"\xff\xd8\xff") and tail == b"\xff\xd9":
        detected = "JPEG"
    else:
        raise ContractError("Tripo input image must be PNG or JPEG: %s" % path)
    suffix = path.suffix.lower()
    if detected == "PNG" and suffix != ".png":
        raise ContractError("Tripo PNG input must use a .png suffix: %s" % path)
    if detected == "JPEG" and suffix not in {".jpg", ".jpeg"}:
        raise ContractError("Tripo JPEG input must use a .jpg or .jpeg suffix: %s" % path)
    return detected


def _input_identity(request: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    canonical = json.loads(json.dumps(request))
    local_files: List[Dict[str, Any]] = []
    inputs = request.get("inputs")
    if isinstance(inputs, list) and inputs and all(isinstance(item, dict) and "path" in item for item in inputs):
        canonical_inputs = []
        for item in inputs:
            path = Path(str(item["path"])).expanduser().resolve()
            file_type = _validate_input_image(path)
            record = {
                "view": str(item["view"]).lower(),
                "path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "type": file_type,
            }
            local_files.append(record)
            canonical_inputs.append({key: record[key] for key in ("view", "sha256", "size_bytes", "type")})
        canonical["inputs"] = canonical_inputs
    elif isinstance(inputs, list) and inputs and all(isinstance(item, str) for item in inputs):
        canonical["inputs"] = [
            {"private_input_sha256": sha256_json({"value": item})} for item in inputs
        ]
    return canonical, local_files


def _infer_model_type(url: str, fallback: str = "GLB") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return {
        ".glb": "GLB", ".gltf": "GLTF", ".fbx": "FBX", ".obj": "OBJ",
        ".stl": "STL", ".usdz": "USDZ",
    }.get(suffix, fallback)


def extract_result_files(
    data: Dict[str, Any], request: Dict[str, Any], spec: OperationSpec
) -> List[Dict[str, Any]]:
    output = data.get("output")
    if not isinstance(output, dict):
        return []
    files: List[Dict[str, Any]] = []
    fallback = str(request.get("out_format") or request.get("format") or "GLB").upper()
    allowed_fields = set(spec.primary_output_fields) | set(spec.preview_output_fields)
    unknown_url_fields = [
        key for key, value in output.items()
        if key not in allowed_fields and (
            isinstance(value, str) and value.startswith(("https://", "http://"))
            or isinstance(value, list) and any(
                isinstance(item, str) and item.startswith(("https://", "http://"))
                for item in value
            )
        )
    ]
    if unknown_url_fields:
        raise ContractError(
            "Tripo returned unrecognized output URL fields: %s" % ", ".join(sorted(unknown_url_fields))
        )
    for key in spec.primary_output_fields:
        value = output.get(key)
        urls = value if isinstance(value, list) else [value]
        for url in urls:
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                files.append({
                    "role": spec.artifact_role,
                    "type": _infer_model_type(url, fallback),
                    "url": url,
                    "field": key,
                })
    for key in spec.preview_output_fields:
        value = output.get(key)
        urls = value if isinstance(value, list) else [value]
        for url in urls:
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                files.append({"role": "preview_image", "type": "IMAGE", "url": url, "field": key})
    return files


def _detect_image(path: Path) -> Tuple[str, str]:
    with path.open("rb") as handle:
        head = handle.read(16)
        if path.stat().st_size >= 2:
            handle.seek(-2, os.SEEK_END)
            tail = handle.read(2)
        else:
            tail = b""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG", ".png"
    if head.startswith(b"\xff\xd8\xff") and tail == b"\xff\xd9":
        return "JPEG", ".jpg"
    raise ContractError("Tripo preview is neither PNG nor JPEG")


def _validate_artifact(path: Path, file_type: str) -> None:
    with path.open("rb") as handle:
        head = handle.read(32)
    if not head:
        raise ContractError("downloaded Tripo artifact is empty")
    kind = file_type.upper()
    if kind == "GLB":
        size = path.stat().st_size
        if size < 20 or not head.startswith(b"glTF"):
            raise ContractError("Tripo GLB artifact has invalid header")
        magic, version, declared_length = struct.unpack("<4sII", head[:12])
        if magic != b"glTF" or version != 2 or declared_length != size:
            raise ContractError("Tripo GLB artifact has invalid version or declared length")
        offset = 12
        chunk_index = 0
        with path.open("rb") as handle:
            while offset < size:
                handle.seek(offset)
                chunk_header = handle.read(8)
                if len(chunk_header) != 8:
                    raise ContractError("Tripo GLB artifact has a truncated chunk header")
                chunk_length, chunk_type = struct.unpack("<I4s", chunk_header)
                if chunk_length % 4 != 0 or offset + 8 + chunk_length > size:
                    raise ContractError("Tripo GLB artifact has invalid chunk bounds")
                if chunk_index == 0 and chunk_type != b"JSON":
                    raise ContractError("Tripo GLB artifact does not start with a JSON chunk")
                offset += 8 + chunk_length
                chunk_index += 1
        if offset != size or chunk_index == 0:
            raise ContractError("Tripo GLB artifact has an invalid chunk table")
    if kind == "FBX" and not (head.startswith(b"Kaydara FBX Binary") or b"FBX" in head.upper()):
        raise ContractError("Tripo FBX artifact has invalid magic")
    if kind == "OBJ":
        text = path.read_text(encoding="utf-8", errors="replace")[:1024 * 1024]
        if not re.search(r"(?m)^\s*v\s+[-+0-9.]", text) or not re.search(r"(?m)^\s*f\s+", text):
            raise ContractError("Tripo OBJ artifact is malformed")
    if kind not in {"GLB", "FBX", "OBJ"}:
        raise ContractError("Tripo artifact validator is not implemented for %s" % kind)


def _validate_https_artifact_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ContractError("Tripo artifact URL must be credential-free HTTPS")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ContractError("Tripo artifact URL must not target localhost")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
        raise ContractError("Tripo artifact URL must not target a private address")


class TripoAdapter:
    provider = "tripo"
    api_version = "v3"

    def __init__(self, transport: Transport, store: JobStore, downloader: Optional[Downloader] = None):
        self.transport = transport
        self.store = store
        self.downloader = downloader or CurlDownloader()

    def capabilities(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "api_version": self.api_version,
            "operation_count": len(OPERATIONS),
            "provider_done_is_asset_approval": False,
            "operations": [spec.to_dict() for spec in OPERATIONS.values()],
        }

    def submit(self, operation: str, request: Dict[str, Any], idempotency_key: str) -> JobHandle:
        warnings = list(validate_request(operation, request))
        if not idempotency_key.strip():
            raise ContractError("idempotency_key is required")
        spec = OPERATIONS[operation]
        canonical, local_files = _input_identity(request)
        credential_fingerprint = str(self.transport.credentials.fingerprint)
        request_hash = sha256_json({
            "provider": self.provider,
            "operation": operation,
            "request": canonical,
            "credential_fingerprint": credential_fingerprint,
        })
        handle_id = sha256_json({"provider": self.provider, "idempotency_key": idempotency_key})[:24]
        now = utc_now()
        handle = JobHandle(
            handle_id=handle_id,
            provider=self.provider,
            operation=operation,
            submit_endpoint=spec.endpoint,
            task_id=None,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            credential_fingerprint=credential_fingerprint,
            trace_id=None,
            provider_status="UNKNOWN",
            artifact_status="NOT_READY",
            submission_status="RESERVED",
            submitted_at=now,
            updated_at=now,
            artifact_deadline=None,
            warnings=warnings,
        )
        public_request = {"canonical_request": canonical, "local_files": local_files}
        private_request = {"request": request}
        if not self.store.reserve(handle, public_request, private_request):
            existing = self.store.load(handle_id)
            if (
                existing.request_hash != request_hash
                or existing.operation != operation
                or existing.credential_fingerprint != credential_fingerprint
            ):
                raise ContractError("Tripo idempotency key was already used for a different request")
            if existing.submission_status == "RESERVED":
                return self._submit_reserved(existing)
            if existing.submission_status == "SUBMITTING" and not existing.task_id:
                existing.submission_status = "SUBMIT_UNKNOWN"
                existing.submission_error = "local process ended during paid Tripo submission"
                existing.updated_at = utc_now()
                self.store.save(existing)
            return existing
        return self._submit_reserved(handle)

    def _submit_reserved(self, handle: JobHandle) -> JobHandle:
        spec = OPERATIONS[handle.operation]
        stored = self.store.load_request(handle.handle_id)
        request = self.store.load_private_request(handle.handle_id)["request"]
        payload = json.loads(json.dumps(request))
        local_files = stored.get("local_files") or []
        if local_files:
            uploads = self.store.load_uploads(handle.handle_id)
            by_identity = {(item["view"], item["sha256"]): item for item in uploads}
            tokens: List[str] = []
            for item in local_files:
                identity = (item["view"], item["sha256"])
                existing = by_identity.get(identity)
                if existing:
                    tokens.append(existing["file_token"])
                    continue
                result = self.transport.upload(Path(item["path"]))
                data = _response_data(result)
                token = data.get("file_token")
                if not isinstance(token, str) or not token:
                    raise ContractError("Tripo upload response is missing file_token")
                record = {
                    "view": item["view"],
                    "sha256": item["sha256"],
                    "size_bytes": item["size_bytes"],
                    "type": item["type"],
                    "file_token": token,
                    "trace_id": result.trace_id,
                    "uploaded_at": utc_now(),
                }
                uploads.append(record)
                by_identity[identity] = record
                self.store.save_uploads(handle.handle_id, uploads)
                self.store.save_response(handle, "upload-%s" % item["view"], {
                    "view": item["view"],
                    "sha256": item["sha256"],
                    "size_bytes": item["size_bytes"],
                    "trace_id": result.trace_id,
                    "file_token_persisted_privately": True,
                })
                tokens.append(token)
            payload["inputs"] = tokens

        handle.submission_status = "SUBMITTING"
        handle.submission_error = None
        handle.updated_at = utc_now()
        self.store.save(handle)
        try:
            result = self.transport.request(spec.method, spec.endpoint, payload)
        except Exception as exc:
            outcome = str(getattr(exc, "submission_outcome", "ambiguous"))
            handle.submission_status = "SUBMIT_FAILED" if outcome == "definite_reject" else "SUBMIT_UNKNOWN"
            handle.submission_error = str(exc)
            handle.trace_id = getattr(exc, "trace_id", None)
            handle.updated_at = utc_now()
            self.store.save(handle)
            raise

        data = _response_data(result)
        scrubbed = scrub_urls(data)
        self.store.save_response(handle, "submit", {"data": scrubbed, "trace_id": result.trace_id})
        handle.trace_id = result.trace_id
        handle.last_response = scrubbed
        if spec.is_async:
            task_id = data.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                handle.submission_status = "SUBMIT_UNKNOWN"
                handle.submission_error = "Tripo submit response did not include task_id"
                self.store.save(handle)
                raise ContractError(handle.submission_error)
            handle.task_id = task_id
            handle.provider_status = "WAIT"
            handle.artifact_status = "NOT_READY"
        else:
            handle.provider_status = "DONE"
            handle.artifact_status = "PENDING"
        handle.submission_status = "SUBMITTED"
        handle.updated_at = utc_now()
        self.store.save(handle)
        return handle

    def poll_once(self, handle_id: str) -> JobHandle:
        with self.store.exclusive(handle_id):
            handle = self.store.load(handle_id)
            if handle.provider_status in {"DONE", "FAIL"}:
                return handle
            if handle.submission_status != "SUBMITTED" or not handle.task_id:
                raise ContractError("Tripo job is not safely submitted and cannot be polled")
            result = self.transport.request("GET", "/tasks/" + handle.task_id)
            data = _response_data(result)
            handle.provider_status = normalize_status(data)
            handle.trace_id = result.trace_id or handle.trace_id
            handle.last_response = scrub_urls(data)
            handle.updated_at = utc_now()
            self.store.save_response(handle, "poll", {
                "data": handle.last_response,
                "trace_id": result.trace_id,
            })
            if handle.provider_status == "DONE":
                request = self.store.load_private_request(handle_id)["request"]
                spec = OPERATIONS[handle.operation]
                files = extract_result_files(data, request, spec)
                if files:
                    self.store.save_private_results(handle_id, files)
                handle.artifact_status = "PENDING"
                handle.result_url_observed_at = utc_now()
                handle.result_url_expires_at = data.get("result_url_expires_at")
            elif handle.provider_status == "FAIL":
                handle.artifact_status = "NOT_READY"
            self.store.save(handle)
            return handle

    def reconcile(
        self,
        handle_id: str,
        reason: str,
        task_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        confirmed_not_created: bool = False,
    ) -> JobHandle:
        if not reason.strip():
            raise ContractError("Tripo reconciliation requires a reason")
        if bool(task_id) == bool(confirmed_not_created):
            raise ContractError(
                "Tripo reconciliation requires exactly one of task_id or confirmed_not_created"
            )
        with self.store.exclusive(handle_id):
            handle = self.store.load(handle_id)
            if handle.submission_status != "SUBMIT_UNKNOWN":
                raise ContractError("only SUBMIT_UNKNOWN Tripo jobs can be reconciled")
            record = {
                "schema": "blender-harness.tripo-reconciliation.v1",
                "recorded_at": utc_now(),
                "previous_submission_status": handle.submission_status,
                "reason": reason,
                "task_id": task_id,
                "trace_id": trace_id,
                "confirmed_not_created": confirmed_not_created,
            }
            if task_id:
                handle.task_id = task_id
                handle.trace_id = trace_id or handle.trace_id
                handle.submission_status = "SUBMITTED"
                handle.submission_error = None
                handle.provider_status = "WAIT"
            else:
                handle.submission_status = "SUBMIT_FAILED"
                handle.submission_error = "owner confirmed provider task was not created: " + reason
                handle.provider_status = "UNKNOWN"
            handle.updated_at = utc_now()
            record["new_submission_status"] = handle.submission_status
            self.store.save_reconciliation(handle_id, record)
            self.store.save(handle)
            return handle

    def fetch(self, handle_id: str) -> Path:
        with self.store.exclusive(handle_id):
            handle = self.store.load(handle_id)
            if handle.provider_status != "DONE":
                raise ContractError("cannot fetch Tripo artifacts before DONE")
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
        run_dir = self.store.run_dir(handle.handle_id)
        manifest_path = run_dir / "artifact-manifest.v1.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest.get("files")
            if not isinstance(files, list) or not files:
                raise ContractError("cached Tripo manifest contains no files")
            for item in files:
                path = run_dir / item["path"]
                if not path.is_file() or sha256_file(path) != item["sha256"]:
                    raise ContractError("cached Tripo artifact is missing or changed: %s" % path)
                if path.stat().st_size != item["size_bytes"]:
                    raise ContractError("cached Tripo artifact size changed: %s" % path)
                if item["type"] in {"PNG", "JPEG"}:
                    detected, _ = _detect_image(path)
                    if detected != item["type"]:
                        raise ContractError("cached Tripo preview type changed: %s" % path)
                elif item["type"] != "JSON":
                    _validate_artifact(path, item["type"])
            handle.artifact_status = "VERIFIED"
            handle.artifact_error = None
            handle.updated_at = utc_now()
            self.store.save(handle)
            return manifest_path

        spec: OperationSpec = OPERATIONS[handle.operation]
        stored = self.store.load_request(handle.handle_id)
        request = self.store.load_private_request(handle.handle_id)["request"]
        output_dir = run_dir / "artifacts"
        if output_dir.exists():
            raise ContractError("uncommitted Tripo artifact directory already exists")
        attempts_dir = run_dir / "fetch-attempts"
        attempts_dir.mkdir(parents=True, exist_ok=True)
        attempt_dir = attempts_dir / (
            "attempt-%s-%s" % (utc_now().replace(":", "").replace("+", ""), uuid.uuid4().hex[:8])
        )
        staged_output = attempt_dir / "artifacts"
        staged_output.mkdir(parents=True)
        attempt_record = {
            "schema": "blender-harness.tripo-fetch-attempt.v1",
            "started_at": utc_now(),
            "status": "running",
            "handle_id": handle.handle_id,
        }
        write_json_atomic(attempt_dir / "attempt.json", attempt_record)
        manifest_files: List[Dict[str, Any]] = []
        try:
            if not spec.is_async:
                destination = staged_output / ("01-%s.json" % spec.artifact_role)
                write_json_atomic(destination, handle.last_response)
                manifest_files.append({
                    "role": spec.artifact_role,
                    "type": "JSON",
                    "path": "artifacts/" + destination.name,
                    "sha256": sha256_file(destination),
                    "size_bytes": destination.stat().st_size,
                    "source_url": None,
                })
            else:
                result_files = self.store.load_private_results(handle.handle_id)
                if not result_files:
                    result_files = extract_result_files(handle.last_response, request, spec)
                if not result_files:
                    raise ContractError("Tripo reported DONE without downloadable result files")
                primary = [item for item in result_files if item.get("role") == spec.artifact_role]
                if not primary:
                    raise ContractError("Tripo result set is missing the required primary geometry")
                if handle.operation == "geometry.multiview" and (
                    len(primary) != 1 or str(primary[0].get("type")).upper() != "GLB"
                ):
                    raise ContractError("Tripo multiview requires exactly one primary GLB")
                for item in result_files:
                    file_type = str(item["type"]).upper()
                    if file_type != "IMAGE" and file_type not in spec.expected_types:
                        raise ContractError(
                            "Tripo returned unexpected artifact type %s for %s (expected %s)"
                            % (file_type, handle.operation, ", ".join(spec.expected_types))
                        )
                    _validate_https_artifact_url(item["url"])
                for index, item in enumerate(result_files, start=1):
                    file_type = str(item["type"]).upper()
                    staged = staged_output / (".%02d.download" % index)
                    self.downloader.download(item["url"], staged)
                    if file_type == "IMAGE":
                        detected, extension = _detect_image(staged)
                        final_type = detected
                        role = "preview_image"
                    else:
                        _validate_artifact(staged, file_type)
                        final_type = file_type
                        extension = "." + file_type.lower()
                        role = spec.artifact_role
                    destination = staged_output / ("%02d-%s%s" % (index, role, extension))
                    os.replace(str(staged), str(destination))
                    manifest_files.append({
                        "role": role,
                        "type": final_type,
                        "provider_field": item.get("field"),
                        "path": "artifacts/" + destination.name,
                        "sha256": sha256_file(destination),
                        "size_bytes": destination.stat().st_size,
                        "source_url": redact_url(item["url"]),
                    })
            os.rename(str(staged_output), str(output_dir))
            attempt_record["status"] = "published"
            attempt_record["completed_at"] = utc_now()
            attempt_record["file_count"] = len(manifest_files)
            write_json_atomic(attempt_dir / "attempt.json", attempt_record)
        except Exception as exc:
            attempt_record["status"] = "failed"
            attempt_record["completed_at"] = utc_now()
            attempt_record["error"] = str(exc)
            write_json_atomic(attempt_dir / "attempt.json", attempt_record)
            raise

        manifest = {
            "schema": "blender-harness.tripo-artifact-manifest.v1",
            "provider": self.provider,
            "api_version": self.api_version,
            "handle_id": handle.handle_id,
            "operation": handle.operation,
            "status": handle.provider_status,
            "provider_status": handle.provider_status,
            "artifact_status": "VERIFIED",
            "provider_done_is_asset_approval": False,
            "request_hash": handle.request_hash,
            "credential_fingerprint": handle.credential_fingerprint,
            "task_id": handle.task_id,
            "trace_id": handle.trace_id,
            "credits_consumed": handle.last_response.get("credits_consumed"),
            "submitted_at": handle.submitted_at,
            "downloaded_at": utc_now(),
            "artifact_deadline": handle.artifact_deadline,
            "result_url_observed_at": handle.result_url_observed_at,
            "result_url_expires_at": handle.result_url_expires_at,
            "warnings": handle.warnings,
            "input_files": stored.get("local_files") or [],
            "files": manifest_files,
        }
        write_json_atomic(manifest_path, manifest)
        handle.artifact_status = "VERIFIED"
        handle.artifact_error = None
        handle.updated_at = utc_now()
        self.store.save(handle)
        return manifest_path
