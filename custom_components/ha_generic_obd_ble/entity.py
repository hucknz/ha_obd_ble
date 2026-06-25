"""Base entity class for Generic OBD BLE."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME


class GenericObdBleEntity(CoordinatorEntity):
    """Base entity for Generic OBD BLE integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=NAME,
            manufacturer="Generic OBD2",
            model="OBD2 BLE Adapter",
        )
