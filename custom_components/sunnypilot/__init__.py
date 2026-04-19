"""The sunnypilot integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import SunnylinkClient, SunnylinkError
from .const import CONF_DEVICE_ID, CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import SunnypilotCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch", "select", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sunnypilot from a config entry."""
    client = SunnylinkClient(entry.data[CONF_REFRESH_TOKEN])
    try:
        await hass.async_add_executor_job(client.authenticate)
    except SunnylinkError as err:
        _LOGGER.error("Authentication failed: %s", err)
        return False

    coordinator = SunnypilotCoordinator(hass, client, entry.data[CONF_DEVICE_ID])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
