"""Data update coordinator for Generic OBD BLE."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.bluetooth.api import async_address_present
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CHARACTERISTIC_UUID_READ,
    CONF_CHARACTERISTIC_UUID_WRITE,
    CONF_SERVICE_UUID,
    DEFAULT_CHARACTERISTIC_UUID_READ,
    DEFAULT_CHARACTERISTIC_UUID_WRITE,
    DEFAULT_FAST_POLL,
    DEFAULT_FETCH_TIMEOUT,
    DEFAULT_SERVICE_UUID,
    DEFAULT_SLOW_POLL,
    DEFAULT_XS_POLL,
    DOMAIN,
    REQUIRED_PIDS,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class GenericObdCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches OBD data and persists it across HA restarts."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_FAST_POLL),
            always_update=True,
        )

        self._address: str = entry.data[CONF_ADDRESS]
        self.api = api
        self._hass = hass

        # Persistent cache — populated from storage before the first poll so
        # sensors immediately reflect the last known values after a restart.
        self._cache_data: dict[str, Any] = {}

        # Per-entry storage file for data persistence
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}"
        )

        # Configuration
        self._options: dict = {}
        self.options = entry.options or {}  # triggers the setter

    @property
    def options(self) -> dict:
        """Current configuration options."""
        return self._options

    @options.setter
    def options(self, value: dict) -> None:
        """Apply new options and recalculate poll intervals."""
        self._options = value
        self._fast_poll = int(value.get("fast_poll", DEFAULT_FAST_POLL))
        self._slow_poll = int(value.get("slow_poll", DEFAULT_SLOW_POLL))
        self._xs_poll = int(value.get("xs_poll", DEFAULT_XS_POLL))
        self._fetch_timeout = float(value.get("fetch_timeout", DEFAULT_FETCH_TIMEOUT))
        self._service_uuid = value.get(CONF_SERVICE_UUID, DEFAULT_SERVICE_UUID)
        self._char_uuid_read = value.get(
            CONF_CHARACTERISTIC_UUID_READ, DEFAULT_CHARACTERISTIC_UUID_READ
        )
        self._char_uuid_write = value.get(
            CONF_CHARACTERISTIC_UUID_WRITE, DEFAULT_CHARACTERISTIC_UUID_WRITE
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Load persisted data on startup, then do first poll."""
        # Load cached data from storage
        try:
            stored = await self._store.async_load()
            if stored:
                self._cache_data = stored.get("data", {})
                _LOGGER.debug("Loaded persisted sensor data: %s", self._cache_data)
        except Exception as err:
            _LOGGER.error("Failed to load persisted data: %s", err)

        # Do the first actual poll
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from OBD adapter."""
        try:
            # Check if adapter is still in BLE range
            device_present = await async_address_present(self._hass, self._address)
            if not device_present:
                _LOGGER.debug("OBD adapter %s not in BLE range", self._address)
                # Return cached data when out of range
                return self._cache_data or {}

            # Query OBD adapter for requested PIDs
            data = await self._fetch_obd_data()

            # Merge with cached data (so we retain values when one PID fails)
            if data:
                self._cache_data.update(data)
                # Persist to storage
                try:
                    await self._store.async_save({"data": self._cache_data})
                except Exception as err:
                    _LOGGER.error("Failed to persist data: %s", err)

            return self._cache_data

        except Exception as err:
            _LOGGER.error("Error fetching OBD data: %s", err)
            raise UpdateFailed(f"Failed to fetch OBD data: {err}") from err

    async def _fetch_obd_data(self) -> dict[str, Any]:
        """Fetch data from OBD adapter for all requested PIDs."""
        try:
            obd_data = {}

            # Try to fetch each required PID
            for pid in REQUIRED_PIDS:
                try:
                    value = await asyncio.wait_for(
                        self.api.query_pid(pid),
                        timeout=self._fetch_timeout,
                    )
                    if value is not None:
                        obd_data[pid] = value
                        _LOGGER.debug("PID %s: %s", pid, value)
                except asyncio.TimeoutError:
                    _LOGGER.warning("Timeout querying PID %s", pid)
                except Exception as err:
                    _LOGGER.debug("Failed to query PID %s: %s", pid, err)

            return obd_data

        except Exception as err:
            _LOGGER.error("Error fetching OBD data: %s", err)
            return {}
