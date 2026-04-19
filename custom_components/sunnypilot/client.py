"""Sunnylink API client — self-contained, sync, called via executor from HA."""
from __future__ import annotations

import base64
import json
import logging
import time as _time
import urllib.error
import urllib.parse
import urllib.request

_LOGGER = logging.getLogger(__name__)

LOGTO_TOKEN_URL = "https://logto.sunnypilot.ai/oidc/token"
LOGTO_DEVICE_AUTH_URL = "https://logto.sunnypilot.ai/oidc/device/auth"
LOGTO_CLIENT_ID = "6mjzxmevkp3ly5c6asvu8"
DEFAULT_SCOPE = "openid offline_access profile"
SUNNYLINK_API_ROOT = "https://stg.api.sunnypilot.ai"
SUNNYLINK_API_BASE = f"{SUNNYLINK_API_ROOT}/v1"
SUNNYLINK_ORIGIN = "https://www.sunnylink.ai"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

PARAM_TYPE_NAMES: dict[int, str] = {
    0: "String",
    1: "Bool",
    2: "Int",
    3: "Float",
    4: "Json",
    5: "Bytes",
    6: "Time",
}


class SunnylinkError(Exception):
    """Raised when the Sunnylink API returns an error."""


def _request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    error_ok: bool = False,
) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        if error_ok:
            return e.code, payload
        raise SunnylinkError(f"HTTP {e.code} {method} {url}: {payload}") from e
    except urllib.error.URLError as e:
        raise SunnylinkError(f"Request failed {method} {url}: {e}") from e


def _api_headers(bearer: str, *, content_type: str | None = None) -> dict[str, str]:
    h = {
        "Accept": "*/*",
        "Authorization": f"Bearer {bearer}",
        "Origin": SUNNYLINK_ORIGIN,
        "Referer": f"{SUNNYLINK_ORIGIN}/",
        "User-Agent": _USER_AGENT,
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


# ── Auth helpers (called from config_flow via executor) ────────────────────

def refresh_tokens(refresh_token: str) -> dict:
    body = urllib.parse.urlencode({
        "client_id": LOGTO_CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": DEFAULT_SCOPE,
    }).encode()
    _, payload = _request(
        LOGTO_TOKEN_URL,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    return payload


def request_device_code() -> dict:
    body = urllib.parse.urlencode({
        "client_id": LOGTO_CLIENT_ID,
        "scope": DEFAULT_SCOPE,
    }).encode()
    _, payload = _request(
        LOGTO_DEVICE_AUTH_URL,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    return payload


def poll_device_token(device_code: str) -> tuple[dict | None, str | None]:
    body = urllib.parse.urlencode({
        "client_id": LOGTO_CLIENT_ID,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "scope": DEFAULT_SCOPE,
    }).encode()
    status, payload = _request(
        LOGTO_TOKEN_URL,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
        error_ok=True,
    )
    if status == 200:
        return payload, None
    return None, payload.get("error")


# ── Value encoding/decoding ────────────────────────────────────────────────

def canonical_param_type(raw_type: object) -> str:
    if isinstance(raw_type, str):
        return raw_type
    if isinstance(raw_type, int):
        return PARAM_TYPE_NAMES.get(raw_type, "String")
    return "String"


def encode_param_value(param_type: str, value: object) -> str | None:
    if value is None:
        return None
    if param_type == "Bool":
        s = "1" if bool(value) else "0"
    elif param_type in {"Int", "Float"}:
        s = str(value)
    elif param_type == "Json":
        s = value if isinstance(value, str) else json.dumps(value)
    else:
        s = str(value)
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def decode_param_value(param: dict) -> object:
    value = param.get("value")
    if value is None:
        return None
    param_type = canonical_param_type(param.get("type"))
    if param_type == "Bytes":
        return value
    try:
        decoded = base64.b64decode(str(value)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if param_type == "Bool":
        return decoded == "1" or decoded.lower() == "true"
    if param_type == "Int":
        try:
            return int(decoded)
        except ValueError:
            return None
    if param_type == "Float":
        try:
            return float(decoded)
        except ValueError:
            return None
    if param_type == "Json":
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return decoded
    return decoded


# ── API client class ────────────────────────────────────────────────────────

class SunnylinkClient:
    """Thin sync API client. All methods are called via hass.async_add_executor_job."""

    def __init__(self, refresh_token: str) -> None:
        self._refresh_token = refresh_token
        self._token_payload: dict | None = None
        self._token_obtained_at: float = 0.0

    def authenticate(self) -> None:
        payload = refresh_tokens(self._refresh_token)
        self._token_payload = payload
        self._token_obtained_at = _time.monotonic()
        rotated = payload.get("refresh_token")
        if isinstance(rotated, str) and rotated:
            self._refresh_token = rotated

    @property
    def current_refresh_token(self) -> str:
        return self._refresh_token

    @property
    def refresh_token_expires_in(self) -> int | None:
        """Return refresh_token_expires_in from last token response, or None."""
        val = (self._token_payload or {}).get("refresh_token_expires_in")
        if isinstance(val, (int, float)):
            return int(val)
        return None

    def _id_token(self) -> str:
        """Return a valid id_token, re-authenticating if expired or absent."""
        if self._token_payload is not None:
            expires_in = (self._token_payload or {}).get("expires_in", 3600)
            age = _time.monotonic() - self._token_obtained_at
            if age < (int(expires_in) - 60):
                token = self._token_payload.get("id_token")
                if isinstance(token, str) and token:
                    return token
        # Token absent or within 60 s of expiry — re-authenticate
        self.authenticate()
        token = (self._token_payload or {}).get("id_token")
        if not isinstance(token, str) or not token:
            raise SunnylinkError("No id_token available after authentication.")
        return token

    def get_devices(self) -> list[dict]:
        _, payload = _request(
            f"{SUNNYLINK_API_BASE}/users/self/devices",
            headers=_api_headers(self._id_token()),
        )
        _LOGGER.debug("get_devices raw response: %s", payload)
        # Handle bare list response
        if isinstance(payload, list):
            return payload
        # Try common dict keys
        for key in ("devices", "data", "results", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
        # If the dict itself looks like a single device, wrap it
        if payload.get("dongleId") or payload.get("id"):
            return [payload]
        _LOGGER.error("get_devices: unrecognised response shape: %s", payload)
        return []

    def get_values(self, device_id: str, param_keys: list[str]) -> dict:
        qs = urllib.parse.urlencode({"paramKeys": param_keys}, doseq=True)
        _, payload = _request(
            f"{SUNNYLINK_API_BASE}/settings/{device_id}/values?{qs}",
            headers=_api_headers(self._id_token()),
        )
        return payload

    def set_value(self, device_id: str, key: str, value: object, param_type: str) -> dict:
        body = json.dumps([{
            "key": key,
            "value": encode_param_value(param_type, value),
            "is_compressed": False,
        }]).encode("utf-8")
        _, payload = _request(
            f"{SUNNYLINK_API_ROOT}/settings/{device_id}",
            method="POST",
            headers=_api_headers(self._id_token(), content_type="application/json"),
            body=body,
        )
        return payload
