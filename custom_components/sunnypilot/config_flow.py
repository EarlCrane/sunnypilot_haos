"""Config flow for sunnypilot — refresh token entry then device selection."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .client import SunnylinkClient, SunnylinkError
from .const import CONF_DEVICE_ID, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SunnypilotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the sunnypilot config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._refresh_token: str = ""
        self._client: SunnylinkClient | None = None
        self._devices: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: enter refresh token."""
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
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_REFRESH_TOKEN): str,
            }),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: pick device (auto-select if only one)."""
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

        # Auto-select if exactly one device
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

        # Multiple devices — show selector
        device_options = {
            _device_id(d): _device_name(d) for d in self._devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(device_options),
            }),
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when token is invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show re-auth form and update the config entry on success."""
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
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_REFRESH_TOKEN: client.current_refresh_token,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_REFRESH_TOKEN): str}),
            errors=errors,
        )
