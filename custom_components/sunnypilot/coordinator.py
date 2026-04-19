"""DataUpdateCoordinator for sunnypilot."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SunnylinkClient, SunnylinkError, decode_param_value
from .const import ALL_PARAM_KEYS, CONF_REFRESH_TOKEN, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SunnypilotCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Polls Sunnylink /values for all registered params every UPDATE_INTERVAL seconds."""

    def __init__(
        self, hass: HomeAssistant, client: SunnylinkClient, entry: ConfigEntry
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self._entry = entry
        self.device_id: str = entry.data["device_id"]

    async def _async_update_data(self) -> dict[str, object]:
        try:
            raw = await self.hass.async_add_executor_job(
                self.client.get_values, self.device_id, ALL_PARAM_KEYS
            )
        except SunnylinkError as err:
            raise UpdateFailed(f"Sunnylink API error: {err}") from err

        # Persist rotated refresh token if it changed during the API call
        # (_id_token() may have silently re-authenticated due to id_token expiry)
        new_token = self.client.current_refresh_token
        if new_token != self._entry.data.get(CONF_REFRESH_TOKEN):
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={**self._entry.data, CONF_REFRESH_TOKEN: new_token},
            )

        values_list = raw.get("values") or raw.get("data") or []
        if isinstance(raw, list):
            values_list = raw

        result: dict[str, object] = {}
        for item in values_list:
            if isinstance(item, dict) and "key" in item:
                result[item["key"]] = decode_param_value(item)
        return result
