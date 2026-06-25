"""Sensor platform for Generic OBD BLE."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NAME
from .entity import GenericObdBleEntity
from .sensors import SENSOR_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create a sensor for each OBD PID
    async_add_entities(
        GenericObdBleSensor(coordinator, entry, desc)
        for desc in SENSOR_DESCRIPTIONS
    )


class GenericObdBleSensor(GenericObdBleEntity, SensorEntity):
    """A single OBD sensor entity."""

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self.entity_description = description
        self._attr_name = f"{NAME} {description.name}"
        self._attr_unique_id = (
            f"{config_entry.data[CONF_ADDRESS]}-{description.key}"
        )

    @property
    def native_value(self):
        """Return the current sensor value from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def icon(self) -> str | None:
        """Return the icon defined in the entity description."""
        return self.entity_description.icon
