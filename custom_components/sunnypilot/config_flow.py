"""Config flow for sunnypilot — device flow auth then device selection."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .client import SunnylinkClient, SunnylinkError, request_device_code, poll_device_token
from .const import CONF_DEVICE_ID, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({})  # no inputs — just a "start" button


class SunnypilotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the sunnypilot config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_resp: dict = {}
        self._token_payload: dict = {}
        self._poll_task: asyncio.Task | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: initiate device flow and wait for authorization."""
        if not self._device_resp:
            try:
                self._device_resp = await self.hass.async_add_executor_job(
                    request_device_code
                )
            except SunnylinkError as err:
                _LOGGER.error("Failed to start device flow: %s", err)
                return self.async_abort(reason="cannot_connect")

        if self._poll_task is None:
            self._poll_task = self.hass.async_create_task(self._poll_for_token())

        if not self._poll_task.done():
            return self.async_show_progress(
                step_id="user",
                progress_action="waiting_for_auth",
                progress_task=self._poll_task,
                description_placeholders={
                    "url": self._device_resp.get("verification_uri_complete", ""),
                    "code": self._device_resp.get("user_code", ""),
                },
            )

        try:
            self._token_payload = self._poll_task.result()
        except HomeAssistantError as err:
            return self.async_abort(reason=str(err))
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Device flow polling error: %s", err)
            return self.async_abort(reason="auth_failed")

        return self.async_show_progress_done(next_step_id="device")

    async def _poll_for_token(self) -> dict:
        """Poll Logto until authorized or expired. Runs as an async task."""
        device_code = self._device_resp["device_code"]
        interval = int(self._device_resp.get("interval", 5))
        expires_in = int(self._device_resp.get("expires_in", 600))
        deadline = asyncio.get_event_loop().time() + expires_in

        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(interval)
            token_payload, error_code = await self.hass.async_add_executor_job(
                poll_device_token, device_code
            )
            if token_payload is not None:
                return token_payload
            if error_code == "authorization_pending":
                continue
            if error_code == "slow_down":
                interval += 5
            elif error_code == "access_denied":
                raise HomeAssistantError("access_denied")
            elif error_code == "expired_token":
                raise HomeAssistantError("device_code_expired")
            else:
                raise HomeAssistantError("auth_failed")

        raise HomeAssistantError("device_code_expired")

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: pick device (auto-select if only one)."""
        refresh_token = self._token_payload.get("refresh_token", "")
        client = SunnylinkClient(refresh_token)

        try:
            await self.hass.async_add_executor_job(client.authenticate)
            devices = await self.hass.async_add_executor_job(client.get_devices)
        except SunnylinkError as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            return self.async_abort(reason="cannot_connect")

        if not devices:
            return self.async_abort(reason="no_devices")

        # If the user submitted a device choice
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            device_name = next(
                (d.get("name") or d.get("dongleId") or device_id for d in devices if d.get("dongleId") == device_id),
                device_id,
            )
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"sunnypilot ({device_name})",
                data={
                    CONF_REFRESH_TOKEN: client.current_refresh_token,
                    CONF_DEVICE_ID: device_id,
                },
            )

        # Auto-select if exactly one device
        if len(devices) == 1:
            device = devices[0]
            device_id = device.get("dongleId") or device.get("id") or ""
            device_name = device.get("name") or device_id
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"sunnypilot ({device_name})",
                data={
                    CONF_REFRESH_TOKEN: client.current_refresh_token,
                    CONF_DEVICE_ID: device_id,
                },
            )

        # Multiple devices — show selector
        device_options = {
            d.get("dongleId") or d.get("id"): d.get("name") or d.get("dongleId") or "Unknown"
            for d in devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(device_options),
            }),
        )
