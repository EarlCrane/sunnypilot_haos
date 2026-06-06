"""Config flow for sunnypilot — device-code OAuth or manual token, then device selection."""
from __future__ import annotations

import logging
import time as _time
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .client import (
    SunnylinkClient,
    SunnylinkError,
    poll_device_token,
    request_device_code,
)
from .const import CONF_DEVICE_ID, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_METHOD_DEVICE_CODE = "device_code"
AUTH_METHOD_MANUAL = "manual"


class SunnypilotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the sunnypilot config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._refresh_token: str = ""
        self._client: SunnylinkClient | None = None
        self._devices: list[dict] = []
        # Device-code flow state
        self._device_code: str = ""
        self._user_code: str = ""
        self._verification_uri: str = ""
        self._poll_interval: int = 5
        self._device_code_expires_at: float = 0.0

    # ── Entry points ────────────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 0: choose auth method."""
        if user_input is not None:
            method = user_input.get("auth_method", AUTH_METHOD_DEVICE_CODE)
            if method == AUTH_METHOD_MANUAL:
                return await self.async_step_manual_token()
            return await self.async_step_device_code_start()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("auth_method", default=AUTH_METHOD_DEVICE_CODE): vol.In({
                    AUTH_METHOD_DEVICE_CODE: "Sign in via browser (GitHub, Google, Discord…)",
                    AUTH_METHOD_MANUAL: "Paste refresh token manually",
                }),
            }),
        )

    # ── Device-code OAuth flow ──────────────────────────────────────────────

    async def async_step_device_code_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Request a device code from Logto and proceed to the poll step."""
        try:
            resp = await self.hass.async_add_executor_job(request_device_code)
        except (SunnylinkError, Exception) as err:  # noqa: BLE001
            _LOGGER.error("Failed to request device code: %s", err, exc_info=True)
            return self.async_abort(reason="cannot_connect")

        self._device_code = resp.get("device_code", "")
        self._user_code = resp.get("user_code", "")
        self._verification_uri = (
            resp.get("verification_uri_complete")
            or resp.get("verification_uri", "https://auth.sunnypilot.ai/")
        )
        self._poll_interval = max(5, int(resp.get("interval", 5)))
        self._device_code_expires_at = _time.monotonic() + int(resp.get("expires_in", 300))

        return await self.async_step_device_code_poll()

    async def async_step_device_code_poll(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the verification URL and poll for authorization on each submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if _time.monotonic() > self._device_code_expires_at:
                return self.async_abort(reason="device_code_expired")

            try:
                tokens, error_code = await self.hass.async_add_executor_job(
                    poll_device_token, self._device_code
                )
            except (SunnylinkError, Exception) as err:  # noqa: BLE001
                _LOGGER.error("Token poll error: %s", err, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                if tokens:
                    refresh_token = tokens.get("refresh_token", "")
                    if not refresh_token:
                        errors["base"] = "invalid_auth"
                    else:
                        client = SunnylinkClient(refresh_token)
                        # Inject the already-valid token payload so we skip a round-trip
                        client._token_payload = tokens  # noqa: SLF001
                        client._token_obtained_at = _time.monotonic()  # noqa: SLF001
                        self._refresh_token = client.current_refresh_token
                        self._client = client
                        return await self.async_step_device()
                elif error_code in ("authorization_pending", "slow_down"):
                    errors["base"] = "auth_pending"
                elif error_code == "access_denied":
                    return self.async_abort(reason="access_denied")
                else:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="device_code_poll",
            data_schema=vol.Schema({}),
            description_placeholders={
                "url": self._verification_uri,
                "user_code": self._user_code,
            },
            errors=errors,
        )

    # ── Manual token flow ───────────────────────────────────────────────────

    async def async_step_manual_token(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter a refresh token by hand (fallback path)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_REFRESH_TOKEN].strip()
            client = SunnylinkClient(token)
            try:
                await self.hass.async_add_executor_job(client.authenticate)
            except SunnylinkError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Unexpected auth error: %s", err, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                self._refresh_token = client.current_refresh_token
                self._client = client
                return await self.async_step_device()

        return self.async_show_form(
            step_id="manual_token",
            data_schema=vol.Schema({vol.Required(CONF_REFRESH_TOKEN): str}),
            errors=errors,
        )

    # ── Device selection ────────────────────────────────────────────────────

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick device (auto-select if only one)."""
        assert self._client is not None

        if not self._devices:
            try:
                self._devices = await self.hass.async_add_executor_job(
                    self._client.get_devices
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Failed to fetch devices: %s", err, exc_info=True)
                return self.async_abort(reason="cannot_connect")

        if not self._devices:
            return self.async_abort(reason="no_devices")

        def _device_id(d: dict) -> str:
            return d.get("device_id") or d.get("dongleId") or d.get("id") or ""

        def _device_name(d: dict) -> str:
            return d.get("name") or _device_id(d) or "Unknown"

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            device = next((d for d in self._devices if _device_id(d) == device_id), {})
            return self.async_create_entry(
                title=f"sunnypilot ({_device_name(device)})",
                data={
                    CONF_REFRESH_TOKEN: self._refresh_token,
                    CONF_DEVICE_ID: device_id,
                },
            )

        if len(self._devices) == 1:
            device = self._devices[0]
            device_id = _device_id(device)
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"sunnypilot ({_device_name(device)})",
                data={
                    CONF_REFRESH_TOKEN: self._refresh_token,
                    CONF_DEVICE_ID: device_id,
                },
            )

        device_options = {_device_id(d): _device_name(d) for d in self._devices}
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(device_options)}),
        )

    # ── Re-authentication ───────────────────────────────────────────────────

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when token is invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose reauth method."""
        if user_input is not None:
            method = user_input.get("auth_method", AUTH_METHOD_DEVICE_CODE)
            if method == AUTH_METHOD_MANUAL:
                return await self.async_step_reauth_manual()
            return await self.async_step_reauth_device_code_start()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required("auth_method", default=AUTH_METHOD_DEVICE_CODE): vol.In({
                    AUTH_METHOD_DEVICE_CODE: "Sign in via browser (GitHub, Google, Discord…)",
                    AUTH_METHOD_MANUAL: "Paste refresh token manually",
                }),
            }),
        )

    async def async_step_reauth_device_code_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start device-code flow for reauth."""
        try:
            resp = await self.hass.async_add_executor_job(request_device_code)
        except (SunnylinkError, Exception) as err:  # noqa: BLE001
            _LOGGER.error("Failed to request device code (reauth): %s", err, exc_info=True)
            return self.async_abort(reason="cannot_connect")

        self._device_code = resp.get("device_code", "")
        self._user_code = resp.get("user_code", "")
        self._verification_uri = (
            resp.get("verification_uri_complete")
            or resp.get("verification_uri", "https://auth.sunnypilot.ai/")
        )
        self._poll_interval = max(5, int(resp.get("interval", 5)))
        self._device_code_expires_at = _time.monotonic() + int(resp.get("expires_in", 300))

        return await self.async_step_reauth_device_code_poll()

    async def async_step_reauth_device_code_poll(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Poll for reauth device-code authorization."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if _time.monotonic() > self._device_code_expires_at:
                return self.async_abort(reason="device_code_expired")

            try:
                tokens, error_code = await self.hass.async_add_executor_job(
                    poll_device_token, self._device_code
                )
            except (SunnylinkError, Exception) as err:  # noqa: BLE001
                _LOGGER.error("Token poll error (reauth): %s", err, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                if tokens:
                    refresh_token = tokens.get("refresh_token", "")
                    if not refresh_token:
                        errors["base"] = "invalid_auth"
                    else:
                        return await self._finish_reauth(refresh_token)
                elif error_code in ("authorization_pending", "slow_down"):
                    errors["base"] = "auth_pending"
                elif error_code == "access_denied":
                    return self.async_abort(reason="access_denied")
                else:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth_device_code_poll",
            data_schema=vol.Schema({}),
            description_placeholders={
                "url": self._verification_uri,
                "user_code": self._user_code,
            },
            errors=errors,
        )

    async def async_step_reauth_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reauth by pasting a token manually."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_REFRESH_TOKEN].strip()
            client = SunnylinkClient(token)
            try:
                await self.hass.async_add_executor_job(client.authenticate)
            except SunnylinkError as err:
                _LOGGER.error("Re-auth failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Unexpected re-auth error: %s", err, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                return await self._finish_reauth(client.current_refresh_token)

        return self.async_show_form(
            step_id="reauth_manual",
            data_schema=vol.Schema({vol.Required(CONF_REFRESH_TOKEN): str}),
            errors=errors,
        )

    async def _finish_reauth(self, new_refresh_token: str) -> ConfigFlowResult:
        """Persist updated token and reload the entry."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry:
            self.hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_REFRESH_TOKEN: new_refresh_token},
            )
            await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_abort(reason="reauth_successful")
