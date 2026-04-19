"""DataUpdateCoordinator for sunnypilot."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SunnylinkClient, SunnylinkError, decode_param_value
from .const import ALL_PARAM_KEYS, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SunnypilotCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Polls Sunnylink /values for all registered params every UPDATE_INTERVAL seconds."""

    def __init__(self, hass: HomeAssistant, client: SunnylinkClient, device_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self.device_id = device_id

    async def _async_update_data(self) -> dict[str, object]:
        try:
            raw = await self.hass.async_add_executor_job(
                self.client.get_values, self.device_id, ALL_PARAM_KEYS
            )
        except SunnylinkError as err:
            raise UpdateFailed(f"Sunnylink API error: {err}") from err

        values_list = raw.get("values") or raw.get("data") or []
        if isinstance(raw, list):
            values_list = raw

        result: dict[str, object] = {}
        for item in values_list:
            if isinstance(item, dict) and "key" in item:
                result[item["key"]] = decode_param_value(item)
        return result
