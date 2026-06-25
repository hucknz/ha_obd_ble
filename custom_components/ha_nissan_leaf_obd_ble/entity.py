"""Base entity class for Nissan Leaf OBD BLE."""

from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION


class NissanLeafObdBleEntity(CoordinatorEntity):
    """Shared base for all ha_nissan_leaf_obd_ble entities."""

    def __init__(self, coordinator, config_entry) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this entity."""
        return f"{self.config_entry.data[CONF_ADDRESS]}-{self.name}"

    @property
    def device_info(self) -> dict:
        """Return device information so all entities share one HA device."""
        from .const import GENERATION_OPTIONS  # noqa: PLC0415

        address: str = self.config_entry.data[CONF_ADDRESS]
        generation: str = self.config_entry.data.get("generation", "auto")
        gen_label = GENERATION_OPTIONS.get(generation, generation)

        return {
            "identifiers": {(DOMAIN, address)},
            "name": f"{NAME} ({address})",
            "model": gen_label,
            "manufacturer": "Nissan / OBD BLE",
            "sw_version": VERSION,
        }
