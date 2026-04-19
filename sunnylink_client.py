#!/usr/bin/env python3

import argparse
import base64
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


LOGTO_TOKEN_URL = "https://logto.sunnypilot.ai/oidc/token"
LOGTO_DEVICE_AUTH_URL = "https://logto.sunnypilot.ai/oidc/device/auth"
SUNNYLINK_API_ROOT = "https://stg.api.sunnypilot.ai"
SUNNYLINK_API_BASE = f"{SUNNYLINK_API_ROOT}/v1"
LOGTO_CLIENT_ID = "6mjzxmevkp3ly5c6asvu8"
DEFAULT_SCOPE = "openid offline_access profile"
SUNNYLINK_ORIGIN = "https://www.sunnylink.ai"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"


class SunnylinkError(RuntimeError):
  pass


def _sunnylink_headers(bearer_token: str, *, content_type: str | None = None) -> dict[str, str]:
  headers = {
    "Accept": "*/*",
    "Authorization": f"Bearer {bearer_token}",
    "Origin": SUNNYLINK_ORIGIN,
    "Referer": f"{SUNNYLINK_ORIGIN}/",
    "User-Agent": DEFAULT_USER_AGENT,
  }
  if content_type:
    headers["Content-Type"] = content_type
  return headers


def _request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: bytes | None = None, error_ok: bool = False) -> tuple[int, dict]:
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


def request_device_code(scope: str = DEFAULT_SCOPE) -> dict:
  body = urllib.parse.urlencode({
    "client_id": LOGTO_CLIENT_ID,
    "scope": scope,
  }).encode("utf-8")
  _, payload = _request(
    LOGTO_DEVICE_AUTH_URL,
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    body=body,
  )
  return payload


def poll_device_token(device_code: str, scope: str = DEFAULT_SCOPE) -> tuple[dict | None, str | None]:
  body = urllib.parse.urlencode({
    "client_id": LOGTO_CLIENT_ID,
    "device_code": device_code,
    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    "scope": scope,
  }).encode("utf-8")
  status, payload = _request(
    LOGTO_TOKEN_URL,
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    body=body,
    error_ok=True,
  )
  if status == 200:
    return payload, None
  error_code = payload.get("error")
  return None, error_code


def device_flow_login(scope: str = DEFAULT_SCOPE) -> dict:
  resp = request_device_code(scope)
  device_code = resp.get("device_code")
  user_code = resp.get("user_code")
  verification_uri = resp.get("verification_uri_complete") or resp.get("verification_uri")
  expires_in = int(resp.get("expires_in", 600))
  interval = int(resp.get("interval", 5))

  if not device_code or not user_code:
    raise SunnylinkError(f"Device authorization response missing required fields: {resp}")

  print(f"\nOpen this URL on your phone to log in:\n  {verification_uri}")
  print(f"\nYour code: {user_code}  (expires in {expires_in}s)")
  print("Waiting", end="", flush=True)

  deadline = time.monotonic() + expires_in
  poll_interval = interval
  while time.monotonic() < deadline:
    time.sleep(poll_interval)
    token_payload, error_code = poll_device_token(device_code, scope)
    if token_payload is not None:
      print(" authorized.")
      return token_payload
    if error_code == "authorization_pending":
      print(".", end="", flush=True)
    elif error_code == "slow_down":
      poll_interval += 5
      print(".", end="", flush=True)
    elif error_code == "expired_token":
      raise SunnylinkError("Device code expired. Run login again.")
    elif error_code == "access_denied":
      raise SunnylinkError("Authorization denied.")
    else:
      raise SunnylinkError(f"Unexpected error during device flow: {error_code}")

  raise SunnylinkError("Timed out waiting for authorization.")


def sunnylink_get(path: str, bearer_token: str, query: dict[str, list[str] | str] | None = None) -> dict:
  url = f"{SUNNYLINK_API_BASE}{path}"
  if query:
    url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
  _, payload = _request(
    url,
    headers=_sunnylink_headers(bearer_token),
  )
  return payload


def sunnylink_post(path: str, bearer_token: str, payload: list[dict]) -> dict:
  _, response_payload = _request(
    f"{SUNNYLINK_API_ROOT}{path}",
    method="POST",
    headers=_sunnylink_headers(bearer_token, content_type="application/json"),
    body=json.dumps(payload).encode("utf-8"),
  )
  return response_payload


def encode_param_value(param_type: str, value: object) -> str | None:
  if value is None:
    return None

  if param_type == "Bytes":
    if not isinstance(value, str):
      raise SunnylinkError("Bytes params must already be base64 strings.")
    return value

  if param_type == "Bool":
    string_value = "1" if bool(value) else "0"
  elif param_type in {"Int", "Float"}:
    string_value = str(value)
  elif param_type == "Json":
    string_value = value if isinstance(value, str) else json.dumps(value)
  else:
    string_value = str(value)

  return base64.b64encode(string_value.encode("utf-8")).decode("ascii")


def build_param_update(key: str, value: object, *, param_type: str) -> dict[str, object]:
  return {
    "key": key,
    "value": encode_param_value(param_type, value),
    "is_compressed": False,
  }


def parse_bool_state(value: str) -> bool:
  normalized = value.strip().lower()
  if normalized in {"on", "true", "1", "yes"}:
    return True
  if normalized in {"off", "false", "0", "no"}:
    return False
  raise SunnylinkError(f"Unsupported boolean state: {value}")


_MISSING = object()
PARAM_TYPE_NAMES = {
  0: "String",
  1: "Bool",
  2: "Int",
  3: "Float",
  4: "Json",
  5: "Bytes",
  6: "Time",
}


def canonical_param_type(raw_type: object) -> str:
  if isinstance(raw_type, str):
    return raw_type
  if isinstance(raw_type, int):
    return PARAM_TYPE_NAMES.get(raw_type, str(raw_type))
  return "String"


def decode_param_value(param: dict[str, object]) -> object:
  value = param.get("value")
  if value is None:
    return None

  param_type = canonical_param_type(param.get("type"))
  if param_type == "Bytes":
    return value

  try:
    decoded = base64.b64decode(str(value)).decode("utf-8")
  except (ValueError, UnicodeDecodeError) as e:
    raise SunnylinkError(f"Failed to decode param {param.get('key')}: {e}") from e

  if param_type == "Bool":
    return decoded == "1" or decoded.lower() == "true"
  if param_type == "Int":
    return int(decoded)
  if param_type == "Float":
    return float(decoded)
  if param_type == "Json":
    return json.loads(decoded)
  return decoded


def decode_params_metadata(payload: dict[str, object]) -> list[dict[str, object]]:
  encoded = payload.get("params_metadata")
  if not isinstance(encoded, str):
    raise SunnylinkError("params metadata response is missing params_metadata")

  try:
    compressed = base64.b64decode(encoded)
    decoded = gzip.decompress(compressed).decode("utf-8")
    metadata = json.loads(decoded)
  except (ValueError, OSError, json.JSONDecodeError) as e:
    raise SunnylinkError(f"Failed to decode params metadata: {e}") from e

  if not isinstance(metadata, list):
    raise SunnylinkError("Decoded params metadata is not a list")
  return metadata


class SunnylinkSession:
  def __init__(self, refresh_token: str, *, device_id: str | None = None, token_json_path: str | None = None):
    self.refresh_token = refresh_token
    self.device_id = device_id
    self.token_json_path = token_json_path
    self.token_payload: dict[str, object] | None = None
    self._params_metadata_by_device: dict[str, dict[str, dict[str, object]]] = {}

  def authenticate(self) -> dict[str, object]:
    self.token_payload = refresh_tokens(self.refresh_token)
    maybe_write_token_json(self.token_json_path, self.token_payload)
    rotated_refresh = self.token_payload.get("refresh_token")
    if isinstance(rotated_refresh, str) and rotated_refresh:
      self.refresh_token = rotated_refresh
    return self.token_payload

  def id_token(self) -> str:
    if self.token_payload is None:
      self.authenticate()
    id_token = self.token_payload.get("id_token") if self.token_payload else None
    if not isinstance(id_token, str) or not id_token:
      raise SunnylinkError("Refresh succeeded but no id_token was returned.")
    return id_token

  def resolve_device_id(self, override: str | None = None) -> str:
    device_id = override or self.device_id
    if not device_id:
      raise SunnylinkError("Missing device ID. Set SUNNYLINK_DEVICE_ID or pass --device-id.")
    return device_id

  def get(self, path: str, query: dict[str, list[str] | str] | None = None) -> dict:
    return sunnylink_get(path, self.id_token(), query=query)

  def post(self, path: str, payload: list[dict[str, object]]) -> dict:
    return sunnylink_post(path, self.id_token(), payload)

  def devices(self) -> dict:
    return self.get("/users/self/devices")

  def raw_params_metadata(self, *, device_id: str | None = None) -> dict:
    return self.get(f"/settings/{self.resolve_device_id(device_id)}/paramsMetadata")

  def params_metadata(self, *, device_id: str | None = None, force_refresh: bool = False) -> dict[str, dict[str, object]]:
    resolved_device_id = self.resolve_device_id(device_id)
    if not force_refresh and resolved_device_id in self._params_metadata_by_device:
      return self._params_metadata_by_device[resolved_device_id]

    decoded = decode_params_metadata(self.raw_params_metadata(device_id=resolved_device_id))
    metadata_by_key = {
      str(item["key"]): item
      for item in decoded
      if isinstance(item, dict) and item.get("key")
    }
    self._params_metadata_by_device[resolved_device_id] = metadata_by_key
    return metadata_by_key

  def param_metadata(self, key: str, *, device_id: str | None = None) -> dict[str, object]:
    metadata = self.params_metadata(device_id=device_id)
    try:
      return metadata[key]
    except KeyError as e:
      raise SunnylinkError(f"No metadata found for param: {key}") from e

  def param_options(self, key: str, *, device_id: str | None = None) -> list[dict[str, object]]:
    meta = self.param_metadata(key, device_id=device_id)
    extra = meta.get("_extra")
    if isinstance(extra, dict):
      options = extra.get("options")
      if isinstance(options, list):
        return [option for option in options if isinstance(option, dict)]
    return []

  def _match_option_value(self, raw_value: object, options: list[dict[str, object]]) -> object:
    for option in options:
      option_value = option.get("value")
      if raw_value == option_value:
        return option_value
      if isinstance(raw_value, str) and raw_value == str(option_value):
        return option_value

    if isinstance(raw_value, str):
      normalized = raw_value.strip().lower()
      for option in options:
        label = option.get("label")
        if isinstance(label, str) and normalized == label.strip().lower():
          return option.get("value")

    return _MISSING

  def normalize_value(self, key: str, value: object, *, device_id: str | None = None) -> tuple[str, object]:
    meta = self.param_metadata(key, device_id=device_id)
    param_type = canonical_param_type(meta.get("type"))
    extra = meta.get("_extra")
    extra_dict = extra if isinstance(extra, dict) else {}
    options = self.param_options(key, device_id=device_id)

    matched_option = self._match_option_value(value, options)
    if matched_option is not _MISSING:
      value = matched_option

    if param_type == "Bool":
      normalized_value = parse_bool_state(value) if isinstance(value, str) else bool(value)
    elif param_type == "Int":
      normalized_value = int(value)
    elif param_type == "Float":
      normalized_value = float(value)
    elif param_type == "Json":
      if isinstance(value, str):
        try:
          normalized_value = json.loads(value)
        except json.JSONDecodeError:
          normalized_value = value
      else:
        normalized_value = value
    else:
      normalized_value = str(value)

    if options and matched_option is _MISSING:
      allowed = ", ".join(
        f"{option.get('label', option.get('value'))} ({option.get('value')})"
        for option in options
      )
      raise SunnylinkError(f"{key} does not accept {value!r}. Allowed options: {allowed}")

    if param_type in {"Int", "Float"}:
      min_value = extra_dict.get("min")
      max_value = extra_dict.get("max")
      if isinstance(min_value, (int, float)) and normalized_value < min_value:
        raise SunnylinkError(f"{key} must be >= {min_value}")
      if isinstance(max_value, (int, float)) and normalized_value > max_value:
        raise SunnylinkError(f"{key} must be <= {max_value}")

    return param_type, normalized_value

  def set_param(self, key: str, value: object, *, device_id: str | None = None) -> dict:
    resolved_device_id = self.resolve_device_id(device_id)
    param_type, normalized_value = self.normalize_value(key, value, device_id=resolved_device_id)
    return self.post(
      f"/settings/{resolved_device_id}",
      [build_param_update(key, normalized_value, param_type=param_type)],
    )

  def set_params(self, updates: dict[str, object], *, device_id: str | None = None) -> dict:
    resolved_device_id = self.resolve_device_id(device_id)
    payload: list[dict[str, object]] = []
    for key, value in updates.items():
      param_type, normalized_value = self.normalize_value(key, value, device_id=resolved_device_id)
      payload.append(build_param_update(key, normalized_value, param_type=param_type))
    return self.post(f"/settings/{resolved_device_id}", payload)

  # Device
  def set_offroad_mode(self, enabled: bool) -> dict:
    return self.set_param("OffroadMode", enabled)

  def set_device_boot_mode(self, value: object) -> dict:
    return self.set_param("DeviceBootMode", value)

  def set_metric_units(self, enabled: bool) -> dict:
    return self.set_param("IsMetric", enabled)

  def set_quiet_mode(self, enabled: bool) -> dict:
    return self.set_param("QuietMode", enabled)

  def set_onroad_uploads(self, enabled: bool) -> dict:
    return self.set_param("OnroadUploads", enabled)

  def set_language(self, value: object) -> dict:
    return self.set_param("LanguageSetting", value)

  def set_record_front(self, enabled: bool) -> dict:
    return self.set_param("RecordFront", enabled)

  def set_record_audio(self, enabled: bool) -> dict:
    return self.set_param("RecordAudio", enabled)

  def set_gsm_metered(self, enabled: bool) -> dict:
    return self.set_param("GsmMetered", enabled)

  def set_gsm_roaming(self, enabled: bool) -> dict:
    return self.set_param("GsmRoaming", enabled)

  def set_gsm_apn(self, value: object) -> dict:
    return self.set_param("GsmApn", value)

  def create_backup(self, value: object) -> dict:
    return self.set_param("BackupManager_CreateBackup", value)

  def restore_backup_version(self, value: object) -> dict:
    return self.set_param("BackupManager_RestoreVersion", value)

  def uninstall_software(self, value: object) -> dict:
    return self.set_param("DoUninstall", value)

  def set_max_time_offroad(self, value: object) -> dict:
    return self.set_param("MaxTimeOffroad", value)

  def force_power_down(self, value: object) -> dict:
    return self.set_param("ForcePowerDown", value)

  def reboot_device(self, value: object) -> dict:
    return self.set_param("DoReboot", value)

  def shutdown_device(self, value: object) -> dict:
    return self.set_param("DoShutdown", value)

  # Toggles
  def set_openpilot_enabled(self, enabled: bool) -> dict:
    return self.set_param("OpenpilotEnabledToggle", enabled)

  def set_longitudinal_personality(self, value: object) -> dict:
    return self.set_param("LongitudinalPersonality", value)

  def set_ldw_enabled(self, enabled: bool) -> dict:
    return self.set_param("IsLdwEnabled", enabled)

  def set_disengage_on_accelerator(self, enabled: bool) -> dict:
    return self.set_param("DisengageOnAccelerator", enabled)

  def set_wide_camera(self, enabled: bool) -> dict:
    return self.set_param("EnableWideCamera", enabled)

  def set_always_on_dm(self, enabled: bool) -> dict:
    return self.set_param("AlwaysOnDM", enabled)

  def set_disable_logging(self, enabled: bool) -> dict:
    return self.set_param("DisableLogging", enabled)

  def set_disable_onroad_uploads(self, enabled: bool) -> dict:
    return self.set_param("DisableOnroadUploads", enabled)

  def set_disable_power_down(self, enabled: bool) -> dict:
    return self.set_param("DisablePowerDown", enabled)

  def set_disable_updates(self, enabled: bool) -> dict:
    return self.set_param("DisableUpdates", enabled)

  def set_subaru_stop_and_go(self, enabled: bool) -> dict:
    return self.set_param("SubaruStopAndGo", enabled)

  def set_subaru_manual_parking_brake(self, enabled: bool) -> dict:
    return self.set_param("SubaruStopAndGoManualParkingBrake", enabled)

  def set_camera_offset(self, value: object) -> dict:
    return self.set_param("CameraOffset", value)

  def set_lagd_toggle(self, enabled: bool) -> dict:
    return self.set_param("LagdToggle", enabled)

  def set_lagd_toggle_delay(self, value: object) -> dict:
    return self.set_param("LagdToggleDelay", value)

  def set_lane_turn_desire(self, enabled: bool) -> dict:
    return self.set_param("LaneTurnDesire", enabled)

  def set_lane_turn_value(self, value: object) -> dict:
    return self.set_param("LaneTurnValue", value)

  # Steering
  def set_mads(self, enabled: bool) -> dict:
    return self.set_param("Mads", enabled)

  def set_mads_steering_mode(self, value: object) -> dict:
    return self.set_param("MadsSteeringMode", value)

  def set_mads_main_cruise_allowed(self, enabled: bool) -> dict:
    return self.set_param("MadsMainCruiseAllowed", enabled)

  def set_mads_unified_engagement_mode(self, enabled: bool) -> dict:
    return self.set_param("MadsUnifiedEngagementMode", enabled)

  def set_enforce_torque_control(self, enabled: bool) -> dict:
    return self.set_param("EnforceTorqueControl", enabled)

  def set_torque_control_tune(self, value: object) -> dict:
    return self.set_param("TorqueControlTune", value)

  def set_live_torque_params(self, enabled: bool) -> dict:
    return self.set_param("LiveTorqueParamsToggle", enabled)

  def set_live_torque_params_relaxed(self, enabled: bool) -> dict:
    return self.set_param("LiveTorqueParamsRelaxedToggle", enabled)

  def set_custom_torque_params(self, enabled: bool) -> dict:
    return self.set_param("CustomTorqueParams", enabled)

  def set_torque_params_override_enabled(self, enabled: bool) -> dict:
    return self.set_param("TorqueParamsOverrideEnabled", enabled)

  def set_torque_params_override_lat_accel_factor(self, value: object) -> dict:
    return self.set_param("TorqueParamsOverrideLatAccelFactor", value)

  def set_torque_params_override_friction(self, value: object) -> dict:
    return self.set_param("TorqueParamsOverrideFriction", value)

  def set_blinker_min_lateral_control_speed(self, value: object) -> dict:
    return self.set_param("BlinkerMinLateralControlSpeed", value)

  def set_blinker_pause_lateral_control(self, enabled: bool) -> dict:
    return self.set_param("BlinkerPauseLateralControl", enabled)

  def set_auto_lane_change_timer(self, value: object) -> dict:
    return self.set_param("AutoLaneChangeTimer", value)

  def set_auto_lane_change_bsm_delay(self, value: object) -> dict:
    return self.set_param("AutoLaneChangeBsmDelay", value)

  def set_hkg_tuning_overriding_cycles(self, value: object) -> dict:
    return self.set_param("HkgTuningOverridingCycles", value)

  def set_hkg_active_torque_reduction_gain(self, value: object) -> dict:
    return self.set_param("HkgTuningAngleActiveTorqueReductionGain", value)

  def set_hkg_min_torque_reduction_gain(self, value: object) -> dict:
    return self.set_param("HkgTuningAngleMinTorqueReductionGain", value)

  def set_hkg_angle_smoothing_factor_enabled(self, enabled: bool) -> dict:
    return self.set_param("EnableHkgTuningAngleSmoothingFactor", enabled)

  def set_hkg_max_torque_reduction_gain(self, value: object) -> dict:
    return self.set_param("HkgTuningAngleMaxTorqueReductionGain", value)

  def set_tesla_coop_steering(self, enabled: bool) -> dict:
    return self.set_param("TeslaCoopSteering", enabled)

  def set_neural_network_lateral_control(self, enabled: bool) -> dict:
    return self.set_param("NeuralNetworkLateralControl", enabled)

  # Cruise
  def set_alpha_longitudinal_enabled(self, enabled: bool) -> dict:
    return self.set_param("AlphaLongitudinalEnabled", enabled)

  def set_experimental_mode(self, enabled: bool) -> dict:
    return self.set_param("ExperimentalMode", enabled)

  def set_dynamic_experimental_control(self, enabled: bool) -> dict:
    return self.set_param("DynamicExperimentalControl", enabled)

  def set_speed_limit_mode(self, value: object) -> dict:
    return self.set_param("SpeedLimitMode", value)

  def set_speed_limit_policy(self, value: object) -> dict:
    return self.set_param("SpeedLimitPolicy", value)

  def set_speed_limit_offset_type(self, value: object) -> dict:
    return self.set_param("SpeedLimitOffsetType", value)

  def set_speed_limit_value_offset(self, value: object) -> dict:
    return self.set_param("SpeedLimitValueOffset", value)

  def set_smart_cruise_control_vision(self, enabled: bool) -> dict:
    return self.set_param("SmartCruiseControlVision", enabled)

  def set_smart_cruise_control_map(self, enabled: bool) -> dict:
    return self.set_param("SmartCruiseControlMap", enabled)

  def set_custom_acc_increments_enabled(self, enabled: bool) -> dict:
    return self.set_param("CustomAccIncrementsEnabled", enabled)

  def set_custom_acc_short_press_increment(self, value: object) -> dict:
    return self.set_param("CustomAccShortPressIncrement", value)

  def set_custom_acc_long_press_increment(self, value: object) -> dict:
    return self.set_param("CustomAccLongPressIncrement", value)

  def set_intelligent_cruise_button_management(self, enabled: bool) -> dict:
    return self.set_param("IntelligentCruiseButtonManagement", enabled)

  def set_hyundai_longitudinal_tuning(self, value: object) -> dict:
    return self.set_param("HyundaiLongitudinalTuning", value)

  # Developer
  def set_ssh_enabled(self, enabled: bool) -> dict:
    return self.set_param("SshEnabled", enabled)

  def set_adb_enabled(self, enabled: bool) -> dict:
    return self.set_param("AdbEnabled", enabled)

  def set_sunnylink_uploader_enabled(self, enabled: bool) -> dict:
    return self.set_param("EnableSunnylinkUploader", enabled)

  def set_show_advanced_controls(self, enabled: bool) -> dict:
    return self.set_param("ShowAdvancedControls", enabled)

  def set_quick_boot(self, enabled: bool) -> dict:
    return self.set_param("QuickBootToggle", enabled)

  def set_enable_copyparty(self, enabled: bool) -> dict:
    return self.set_param("EnableCopyparty", enabled)

  def set_joystick_debug_mode(self, enabled: bool) -> dict:
    return self.set_param("JoystickDebugMode", enabled)

  def set_longitudinal_maneuver_mode(self, enabled: bool) -> dict:
    return self.set_param("LongitudinalManeuverMode", enabled)

  def set_enable_github_runner(self, enabled: bool) -> dict:
    return self.set_param("EnableGithubRunner", enabled)

  def set_github_runner_sufficient_voltage(self, value: object) -> dict:
    return self.set_param("GithubRunnerSufficientVoltage", value)


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

  sub.add_parser("login", help="Authenticate via device flow (RFC 8628) and save tokens.")
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

  options = sub.add_parser("options", help="Show metadata and allowed options for a param key.")
  options.add_argument("--device-id-override", help="Override device ID for this command.")
  options.add_argument("param_key", help="Sunnylink param key.")

  set_param_cmd = sub.add_parser("set", help="Set any param using metadata-aware coercion.")
  set_param_cmd.add_argument("--device-id-override", help="Override device ID for this command.")
  set_param_cmd.add_argument("param_key", help="Sunnylink param key.")
  set_param_cmd.add_argument("value", help="Value to apply. Labels are accepted for option-based params.")

  offroad = sub.add_parser("offroad", help="Turn OffroadMode on or off.")
  offroad.add_argument("--device-id-override", help="Override device ID for this command.")
  offroad.add_argument("state", choices=["on", "off"], help="Set OffroadMode on or off.")

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

  if args.command == "login":
    token_payload = device_flow_login()
    maybe_write_token_json(args.write_token_json, token_payload)
    print(json.dumps(token_payload, indent=2))
    return 0

  refresh_token = require_refresh_token(args)
  session = SunnylinkSession(
    refresh_token,
    device_id=args.device_id,
    token_json_path=args.write_token_json,
  )
  token_payload = session.authenticate()

  if args.command == "refresh":
    print(json.dumps(token_payload, indent=2))
    return 0

  if args.command == "devices":
    payload = session.devices()
  elif args.command == "params":
    payload = session.raw_params_metadata(device_id=args.device_id_override)
  elif args.command == "values":
    payload = session.get(
      f"/settings/{session.resolve_device_id(args.device_id_override)}/values",
      query={"paramKeys": args.param_keys},
    )
  elif args.command == "async-values":
    payload = session.get(
      f"/settings/{session.resolve_device_id(args.device_id_override)}/async/values",
      query={"paramKeys": args.param_keys},
    )
  elif args.command == "poll":
    payload = session.get(
      f"/settings/{session.resolve_device_id(args.device_id_override)}/async/poll/{args.request_id}",
    )
  elif args.command == "options":
    meta = session.param_metadata(args.param_key, device_id=args.device_id_override)
    payload = {
      "key": args.param_key,
      "type": meta.get("type"),
      "type_name": canonical_param_type(meta.get("type")),
      "default_value": meta.get("default_value"),
      "_extra": meta.get("_extra"),
      "options": session.param_options(args.param_key, device_id=args.device_id_override),
    }
  elif args.command == "set":
    payload = session.set_param(args.param_key, args.value, device_id=args.device_id_override)
  elif args.command == "offroad":
    payload = session.set_offroad_mode(parse_bool_state(args.state))
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
