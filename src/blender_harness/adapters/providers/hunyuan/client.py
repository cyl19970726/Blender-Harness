from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from ....io import ContractError


HOST = "ai3d.tencentcloudapi.com"
SERVICE = "ai3d"
REGION = "ap-guangzhou"
VERSION = "2025-05-13"


@dataclass(frozen=True)
class Credentials:
    secret_id: str
    secret_key: str

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Credentials":
        secret_id = os.environ.get("TENCENT_SECRET_ID") or os.environ.get("TENCENTCLOUD_SECRET_ID")
        secret_key = os.environ.get("TENCENT_SECRET_KEY") or os.environ.get("TENCENTCLOUD_SECRET_KEY")
        credential_path = path or Path.home() / ".config" / "hunyuan" / "credentials"
        values: Dict[str, str] = {}
        if credential_path.exists():
            for line in credential_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        secret_id = secret_id or values.get("TENCENT_SECRET_ID") or values.get("TENCENTCLOUD_SECRET_ID")
        secret_key = secret_key or values.get("TENCENT_SECRET_KEY") or values.get("TENCENTCLOUD_SECRET_KEY")
        if not secret_id or not secret_key:
            raise ContractError("missing Tencent credentials: both secret id and secret key are required")
        return cls(secret_id=secret_id, secret_key=secret_key)


class HunyuanApiError(RuntimeError):
    def __init__(self, message: str, code: str = "TransportError", request_id: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.request_id = request_id
        self.retryable = retryable


def _hmac(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def signed_request(
    credentials: Credentials,
    action: str,
    payload: Dict[str, Any],
    timestamp: int,
    host: str = HOST,
    region: str = REGION,
    version: str = VERSION,
) -> Tuple[bytes, Dict[str, str]]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    content_type = "application/json; charset=utf-8"
    canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (content_type, host, action.lower())
    signed_headers = "content-type;host;x-tc-action"
    canonical_request = "POST\n/\n\n%s\n%s\n%s" % (
        canonical_headers,
        signed_headers,
        hashlib.sha256(body).hexdigest(),
    )
    scope = "%s/%s/tc3_request" % (date, SERVICE)
    string_to_sign = "TC3-HMAC-SHA256\n%d\n%s\n%s" % (
        timestamp,
        scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    )
    secret_date = _hmac(("TC3" + credentials.secret_key).encode("utf-8"), date)
    secret_service = _hmac(secret_date, SERVICE)
    secret_signing = _hmac(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = "TC3-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s" % (
        credentials.secret_id,
        scope,
        signed_headers,
        signature,
    )
    headers = {
        "Authorization": authorization,
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }
    return body, headers


class TencentAi3dTransport:
    def __init__(
        self,
        credentials: Credentials,
        host: str = HOST,
        region: str = REGION,
        version: str = VERSION,
        timeout_seconds: int = 90,
        clock: Callable[[], float] = time.time,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ):
        self.credentials = credentials
        self.host = host
        self.region = region
        self.version = version
        self.timeout_seconds = timeout_seconds
        self.clock = clock
        self.opener = opener

    def call(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = int(self.clock())
        body, headers = signed_request(
            self.credentials, action, payload, timestamp, self.host, self.region, self.version
        )
        request = urllib.request.Request("https://" + self.host, data=body, headers=headers, method="POST")
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            message = raw.decode("utf-8", "replace")
            raise HunyuanApiError(message, code="HTTP%d" % exc.code, retryable=exc.code == 429 or exc.code >= 500) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise HunyuanApiError(str(exc), code="TransportError", retryable=True) from exc
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HunyuanApiError("provider returned malformed JSON", code="MalformedResponse") from exc
        response = decoded.get("Response", decoded)
        if not isinstance(response, dict):
            raise HunyuanApiError("provider response is not an object", code="MalformedResponse")
        error = response.get("Error")
        if isinstance(error, dict):
            code = str(error.get("Code") or "ProviderError")
            retryable = code in {"RequestLimitExceeded", "InternalError"} or code.startswith("InternalError.")
            raise HunyuanApiError(
                str(error.get("Message") or code),
                code=code,
                request_id=response.get("RequestId"),
                retryable=retryable,
            )
        return response
