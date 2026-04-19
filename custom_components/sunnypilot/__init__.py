"""The sunnypilot integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

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
        raise ConfigEntryAuthFailed(str(err)) from err

    # Persist rotated refresh token (Logto rotates on every use)
    if client.current_refresh_token != entry.data[CONF_REFRESH_TOKEN]:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_REFRESH_TOKEN: client.current_refresh_token},
        )

    coordinator = SunnypilotCoordinator(hass, client, entry)
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
