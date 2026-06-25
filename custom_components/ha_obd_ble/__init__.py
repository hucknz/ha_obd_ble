"""Generic OBD BLE integration for Home Assistant."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, STARTUP_MESSAGE
from .coordinator import GenericObdCoordinator
from .obd_api import GenericObdApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    _LOGGER.info(STARTUP_MESSAGE)

    hass.data.setdefault(DOMAIN, {})

    try:
        # Create the OBD API interface
        api = GenericObdApi(hass, entry)
        
        # Create the data coordinator
        coordinator = GenericObdCoordinator(hass, entry, api)
        
        # Load persisted data and do first poll
        await coordinator.async_config_entry_first_refresh()

        # Store the coordinator
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Set up the sensor platform
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Handle option updates
        entry.async_on_change_callback(
            lambda: _handle_options_update(coordinator, entry)
        )

        return True

    except Exception as err:
        _LOGGER.error("Failed to set up integration: %s", err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator:
            await coordinator.api.disconnect()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


def _handle_options_update(coordinator: GenericObdCoordinator, entry: ConfigEntry) -> None:
    """Handle option updates."""
    coordinator.options = entry.options or {}
