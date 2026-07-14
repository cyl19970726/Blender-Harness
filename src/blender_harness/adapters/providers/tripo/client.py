from __future__ import annotations

import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ....io import ContractError


BASE_URL = "https://openapi.tripo3d.ai/v3"
KEYCHAIN_SERVICE = "blender-harness.tripo"


@dataclass(frozen=True)
class Credentials:
    api_key: str = field(repr=False)
    source: str = "environment"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(("tripo-v3:" + self.api_key).encode("utf-8")).hexdigest()[:16]

    @classmethod
    def load(
        cls,
        keychain_service: str = KEYCHAIN_SERVICE,
        account: Optional[str] = None,
        runner: Callable[..., Any] = subprocess.run,
    ) -> "Credentials":
        value = os.environ.get("TRIPO_API_KEY")
        if value is not None:
            if "\r" in value or "\n" in value:
                raise ContractError("TRIPO_API_KEY must not contain line breaks")
            value = value.strip()
            if value:
                return cls(value, "environment")
        security = Path("/usr/bin/security")
        if sys.platform == "darwin" and security.is_file():
            command = [
                str(security),
                "find-generic-password",
                "-w",
                "-a",
                account or getpass.getuser(),
                "-s",
                keychain_service,
            ]
            try:
                result = runner(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                )
            except subprocess.TimeoutExpired as exc:
                raise ContractError("Tripo macOS Keychain lookup timed out") from exc
            if result.returncode == 0 and result.stdout.strip():
                key = result.stdout.strip()
                if "\r" in key or "\n" in key:
                    raise ContractError("Tripo macOS Keychain returned an invalid credential")
                return cls(key, "macos-keychain")
        raise ContractError(
            "missing Tripo credential: set TRIPO_API_KEY or macOS Keychain service %s"
            % keychain_service
        )


@dataclass(frozen=True)
class TransportResult:
    body: Dict[str, Any]
    trace_id: Optional[str]
    status_code: int


class TripoApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        code: str = "TransportError",
        trace_id: Optional[str] = None,
        retryable: bool = False,
        response_received: bool = False,
        submission_outcome: str = "ambiguous",
    ):
        super().__init__(message)
        self.code = code
        self.trace_id = trace_id
        self.retryable = retryable
        self.response_received = response_received
        self.submission_outcome = submission_outcome


class TripoTransport:
    def __init__(
        self,
        credentials: Credentials,
        base_url: str = BASE_URL,
        timeout_seconds: int = 90,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ):
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TransportResult:
        body = None
        headers = {"Authorization": "Bearer " + self.credentials.api_key}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + endpoint,
            data=body,
            headers=headers,
            method=method.upper(),
        )
        return self._open(request)

    def upload(self, path: Path) -> TransportResult:
        boundary = "----blender-harness-" + uuid.uuid4().hex
        filename = path.name.replace('"', "")
        content_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        prefix = (
            "--%s\r\n"
            "Content-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
            "Content-Type: %s\r\n\r\n" % (boundary, filename, content_type)
        ).encode("utf-8")
        body = prefix + path.read_bytes() + ("\r\n--%s--\r\n" % boundary).encode("ascii")
        request = urllib.request.Request(
            self.base_url + "/files",
            data=body,
            headers={
                "Authorization": "Bearer " + self.credentials.api_key,
                "Content-Type": "multipart/form-data; boundary=" + boundary,
            },
            method="POST",
        )
        return self._open(request)

    def _open(self, request: urllib.request.Request) -> TransportResult:
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                headers = response.headers
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            trace_id = exc.headers.get("X-Tripo-Trace-ID") if exc.headers else None
            message = raw.decode("utf-8", "replace")
            raise TripoApiError(
                message,
                code="HTTP%d" % exc.code,
                trace_id=trace_id,
                retryable=exc.code == 429 or exc.code >= 500,
                response_received=True,
                submission_outcome="ambiguous" if exc.code >= 500 else "definite_reject",
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TripoApiError(
                str(exc), retryable=True, response_received=False, submission_outcome="ambiguous"
            ) from exc
        trace_id = headers.get("X-Tripo-Trace-ID") if headers else None
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TripoApiError(
                "Tripo returned invalid JSON",
                code="InvalidJSON",
                trace_id=trace_id,
                retryable=False,
                response_received=True,
                submission_outcome="ambiguous",
            ) from exc
        if not isinstance(decoded, dict):
            raise TripoApiError(
                "Tripo returned a non-object response",
                code="InvalidResponse",
                trace_id=trace_id,
                response_received=True,
                submission_outcome="ambiguous",
            )
        code = decoded.get("code", 0)
        if code not in (0, "0", None):
            message = str(decoded.get("message") or decoded.get("msg") or "Tripo API error")
            raise TripoApiError(
                message,
                code=str(code),
                trace_id=trace_id,
                retryable=str(code) in {"429", "RATE_LIMIT", "SERVER_ERROR"},
                response_received=True,
                submission_outcome="definite_reject",
            )
        return TransportResult(decoded, trace_id, int(status))
