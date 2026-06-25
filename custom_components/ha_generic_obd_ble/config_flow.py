"""Config flow for Generic OBD BLE."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

try:
    from bluetooth_data_tools import human_readable_name
except ImportError:  # pragma: no cover
    def human_readable_name(_manufacturer, name, address):
        return name or address

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    BLE_LOCAL_NAMES,
    CONF_CHARACTERISTIC_UUID_READ,
    CONF_CHARACTERISTIC_UUID_WRITE,
    CONF_SERVICE_UUID,
    DEFAULT_CHARACTERISTIC_UUID_READ,
    DEFAULT_CHARACTERISTIC_UUID_WRITE,
    DEFAULT_FAST_POLL,
    DEFAULT_SERVICE_UUID,
    DEFAULT_SLOW_POLL,
    DEFAULT_XS_POLL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Generic OBD BLE."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._selected_device: BluetoothServiceInfoBleak | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return OptionsFlow(config_entry)

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle automatic Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": human_readable_name(None, discovery_info.name, discovery_info.address)
        }
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices.get(address)
            if discovery_info is None:
                errors[CONF_ADDRESS] = "device_not_found"
            else:
                await self.async_set_unique_id(
                    discovery_info.address, raise_on_progress=False
                )
                self._abort_if_unique_id_configured()
                self._selected_device = discovery_info
                return await self.async_step_configure()

        # Populate discovered devices
        if self._discovery_info:
            self._discovered_devices[self._discovery_info.address] = (
                self._discovery_info
            )

        already_configured = self._async_current_ids()
        for info in async_discovered_service_info(self.hass):
            if (
                info.address in already_configured
                or info.address in self._discovered_devices
            ):
                continue
            # Accept both name-matched devices and any device with OBD-like UUIDs
            if any(info.name.startswith(n) for n in BLE_LOCAL_NAMES) or (
                info.service_uuids and any(
                    uuid.startswith("0000ff") for uuid in info.service_uuids
                )
            ):
                self._discovered_devices[info.address] = info

        if self._discovered_devices:
            device_choices = {
                addr: f"{info.name} ({addr})"
                for addr, info in self._discovered_devices.items()
            }
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(device_choices)}),
                errors=errors,
                description_placeholders={
                    "num_devices": str(len(device_choices)),
                },
            )
        
        # No devices found via discovery - allow manual entry
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): str,
            }),
            errors=errors,
            description_placeholders={
                "num_devices": "0",
            },
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle BLE UUID configuration (optional)."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"OBD ({self._selected_device.address})",
                data={
                    CONF_ADDRESS: self._selected_device.address,
                },
                options={
                    CONF_SERVICE_UUID: user_input.get(
                        CONF_SERVICE_UUID, DEFAULT_SERVICE_UUID
                    ),
                    CONF_CHARACTERISTIC_UUID_READ: user_input.get(
                        CONF_CHARACTERISTIC_UUID_READ, DEFAULT_CHARACTERISTIC_UUID_READ
                    ),
                    CONF_CHARACTERISTIC_UUID_WRITE: user_input.get(
                        CONF_CHARACTERISTIC_UUID_WRITE, DEFAULT_CHARACTERISTIC_UUID_WRITE
                    ),
                    "fast_poll": DEFAULT_FAST_POLL,
                    "slow_poll": DEFAULT_SLOW_POLL,
                    "xs_poll": DEFAULT_XS_POLL,
                },
            )

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema({
                vol.Optional(CONF_SERVICE_UUID, default=DEFAULT_SERVICE_UUID): str,
                vol.Optional(
                    CONF_CHARACTERISTIC_UUID_READ, default=DEFAULT_CHARACTERISTIC_UUID_READ
                ): str,
                vol.Optional(
                    CONF_CHARACTERISTIC_UUID_WRITE,
                    default=DEFAULT_CHARACTERISTIC_UUID_WRITE,
                ): str,
            }),
            description_placeholders={
                "name": f"{self._selected_device.name} ({self._selected_device.address})",
            },
        )


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options or {}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "fast_poll", default=options.get("fast_poll", DEFAULT_FAST_POLL)
                ): int,
                vol.Optional(
                    "slow_poll", default=options.get("slow_poll", DEFAULT_SLOW_POLL)
                ): int,
                vol.Optional(
                    "xs_poll", default=options.get("xs_poll", DEFAULT_XS_POLL)
                ): int,
                vol.Optional(
                    CONF_SERVICE_UUID,
                    default=options.get(CONF_SERVICE_UUID, DEFAULT_SERVICE_UUID),
                ): str,
                vol.Optional(
                    CONF_CHARACTERISTIC_UUID_READ,
                    default=options.get(
                        CONF_CHARACTERISTIC_UUID_READ, DEFAULT_CHARACTERISTIC_UUID_READ
                    ),
                ): str,
                vol.Optional(
                    CONF_CHARACTERISTIC_UUID_WRITE,
                    default=options.get(
                        CONF_CHARACTERISTIC_UUID_WRITE, DEFAULT_CHARACTERISTIC_UUID_WRITE
                    ),
                ): str,
            }),
        )
