#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


LOGTO_TOKEN_URL = "https://logto.sunnypilot.ai/oidc/token"
SUNNYLINK_API_BASE = "https://stg.api.sunnypilot.ai/v1"
LOGTO_CLIENT_ID = "6mjzxmevkp3ly5c6asvu8"
DEFAULT_SCOPE = "openid offline_access profile"
SUNNYLINK_ORIGIN = "https://www.sunnylink.ai"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"


class SunnylinkError(RuntimeError):
  pass


def _request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: bytes | None = None) -> tuple[int, dict]:
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
    raise SunnylinkError(f"HTTP {e.code} for {method} {url}: {payload}") from e
  except urllib.error.URLError as e:
    raise SunnylinkError(f"Request failed for {method} {url}: {e}") from e


def refresh_tokens(refresh_token: str, scope: str = DEFAULT_SCOPE) -> dict:
  body = urllib.parse.urlencode({
    "client_id": LOGTO_CLIENT_ID,
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
    "scope": scope,
  }).encode("utf-8")
  _, payload = _request(
    LOGTO_TOKEN_URL,
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    body=body,
  )
  return payload


def sunnylink_get(path: str, bearer_token: str, query: dict[str, list[str] | str] | None = None) -> dict:
  url = f"{SUNNYLINK_API_BASE}{path}"
  if query:
    url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
  _, payload = _request(
    url,
    headers={
      "Accept": "*/*",
      "Authorization": f"Bearer {bearer_token}",
      "Origin": SUNNYLINK_ORIGIN,
      "Referer": f"{SUNNYLINK_ORIGIN}/",
      "User-Agent": DEFAULT_USER_AGENT,
    },
  )
  return payload


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Refresh Logto auth and call Sunnylink APIs.")
  parser.add_argument(
    "--refresh-token",
    default=os.getenv("SUNNYLINK_REFRESH_TOKEN"),
    help="Logto refresh token. Defaults to SUNNYLINK_REFRESH_TOKEN.",
  )
  parser.add_argument(
    "--device-id",
    default=os.getenv("SUNNYLINK_DEVICE_ID"),
    help="Sunnylink device ID. Defaults to SUNNYLINK_DEVICE_ID.",
  )
  parser.add_argument(
    "--write-token-json",
    default=os.getenv("SUNNYLINK_TOKEN_JSON"),
    help="Optional path to write refreshed token payload.",
  )
  parser.add_argument(
    "--read-token-json",
    default=os.getenv("SUNNYLINK_TOKEN_JSON"),
    help="Optional path to read the last saved token payload.",
  )

  sub = parser.add_subparsers(dest="command", required=True)

  sub.add_parser("refresh", help="Refresh Logto tokens and print the payload.")
  sub.add_parser("devices", help="List devices from Sunnylink.")

  params = sub.add_parser("params", help="Fetch settings metadata for a device.")
  params.add_argument("--device-id-override", help="Override device ID for this command.")

  values = sub.add_parser("values", help="Fetch current values for selected param keys.")
  values.add_argument("--device-id-override", help="Override device ID for this command.")
  values.add_argument("param_keys", nargs="+", help="One or more Sunnylink param keys.")

  async_values = sub.add_parser("async-values", help="Request async values for selected param keys.")
  async_values.add_argument("--device-id-override", help="Override device ID for this command.")
  async_values.add_argument("param_keys", nargs="+", help="One or more Sunnylink param keys.")

  poll = sub.add_parser("poll", help="Poll an async request ID.")
  poll.add_argument("--device-id-override", help="Override device ID for this command.")
  poll.add_argument("request_id", help="Async request ID returned by async-values.")

  return parser.parse_args()


def require_refresh_token(args: argparse.Namespace) -> str:
  if args.refresh_token:
    return args.refresh_token

  if args.read_token_json:
    try:
      with open(args.read_token_json, "r", encoding="utf-8") as f:
        payload = json.load(f)
      refresh_token = payload.get("refresh_token")
      if refresh_token:
        return refresh_token
    except FileNotFoundError:
      pass
    except json.JSONDecodeError as e:
      raise SunnylinkError(f"Invalid token JSON in {args.read_token_json}: {e}") from e

  raise SunnylinkError(
    "Missing refresh token. Pass --refresh-token once, or set SUNNYLINK_TOKEN_JSON/--read-token-json to a saved token file."
  )


def require_device_id(args: argparse.Namespace, override: str | None = None) -> str:
  device_id = override or args.device_id
  if not device_id:
    raise SunnylinkError("Missing device ID. Set SUNNYLINK_DEVICE_ID or pass --device-id.")
  return device_id


def maybe_write_token_json(path: str | None, payload: dict) -> None:
  if not path:
    return
  with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")


def main() -> int:
  args = parse_args()
  refresh_token = require_refresh_token(args)
  token_payload = refresh_tokens(refresh_token)
  maybe_write_token_json(args.write_token_json, token_payload)

  if args.command == "refresh":
    print(json.dumps(token_payload, indent=2))
    return 0

  id_token = token_payload.get("id_token")
  if not id_token:
    raise SunnylinkError("Refresh succeeded but no id_token was returned.")

  if args.command == "devices":
    payload = sunnylink_get("/users/self/devices", id_token)
  elif args.command == "params":
    payload = sunnylink_get(f"/settings/{require_device_id(args, args.device_id_override)}/paramsMetadata", id_token)
  elif args.command == "values":
    payload = sunnylink_get(
      f"/settings/{require_device_id(args, args.device_id_override)}/values",
      id_token,
      query={"paramKeys": args.param_keys},
    )
  elif args.command == "async-values":
    payload = sunnylink_get(
      f"/settings/{require_device_id(args, args.device_id_override)}/async/values",
      id_token,
      query={"paramKeys": args.param_keys},
    )
  elif args.command == "poll":
    payload = sunnylink_get(
      f"/settings/{require_device_id(args, args.device_id_override)}/async/poll/{args.request_id}",
      id_token,
    )
  else:
    raise SunnylinkError(f"Unsupported command: {args.command}")

  print(json.dumps(payload, indent=2))
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except SunnylinkError as e:
    print(f"error: {e}", file=sys.stderr)
    raise SystemExit(1)
