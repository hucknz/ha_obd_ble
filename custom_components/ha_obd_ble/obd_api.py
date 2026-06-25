"""OBD API for communicating with generic OBD2 BLE adapters."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from bleak import BleakClient, BleakError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHARACTERISTIC_UUID_READ,
    CONF_CHARACTERISTIC_UUID_WRITE,
    CONF_SERVICE_UUID,
    DEFAULT_CHARACTERISTIC_UUID_READ,
    DEFAULT_CHARACTERISTIC_UUID_WRITE,
    DEFAULT_SERVICE_UUID,
)

_LOGGER = logging.getLogger(__name__)

# OBD2 Standard Commands
OBD_COMMANDS = {
    "010D": {"name": "Odometer", "format": "distance"},  # Kilometers since codes cleared
    "010C": {"name": "RPM", "format": "rpm"},           # Engine RPM
    "0105": {"name": "Coolant Temp", "format": "temp"}, # Coolant temperature
    "0114": {"name": "Fuel Level", "format": "percent"}, # Fuel tank level
    "0110": {"name": "Fuel Pressure", "format": "pressure"},  # Fuel pressure
    "010F": {"name": "MAP", "format": "pressure"},       # Intake manifold pressure
    "0106": {"name": "STFT B1", "format": "percent"},   # Short term fuel trim bank 1
    "0120": {"name": "Fuel Inj Timing", "format": "angle"},  # Fuel injection timing
    "0132": {"name": "EVAP Pressure", "format": "pressure"},  # EVAP system vapor pressure
    "0133": {"name": "Baro Pressure", "format": "pressure"},  # Barometric pressure
}


class GenericObdApi:
    """Interface to communicate with generic OBD2 adapters via BLE."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the OBD API."""
        self.hass = hass
        self._address = entry.data[CONF_ADDRESS]
        self._client: Optional[BleakClient] = None
        self._connected = False

        # Get BLE UUIDs from options
        options = entry.options or {}
        self._service_uuid = options.get(CONF_SERVICE_UUID, DEFAULT_SERVICE_UUID)
        self._char_uuid_read = options.get(
            CONF_CHARACTERISTIC_UUID_READ, DEFAULT_CHARACTERISTIC_UUID_READ
        )
        self._char_uuid_write = options.get(
            CONF_CHARACTERISTIC_UUID_WRITE, DEFAULT_CHARACTERISTIC_UUID_WRITE
        )

        self._read_buffer = bytearray()
        self._response_event = asyncio.Event()

    async def connect(self) -> bool:
        """Connect to the OBD adapter."""
        try:
            if self._connected:
                return True

            _LOGGER.debug("Connecting to OBD adapter at %s", self._address)
            self._client = BleakClient(self._address)
            await self._client.connect()

            # Set up notification handler for read characteristic
            await self._client.start_notify(
                self._char_uuid_read, self._notification_handler
            )

            self._connected = True
            _LOGGER.info("Connected to OBD adapter %s", self._address)
            return True

        except BleakError as err:
            _LOGGER.error("Failed to connect to OBD adapter: %s", err)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the OBD adapter."""
        try:
            if self._client and self._connected:
                await self._client.stop_notify(self._char_uuid_read)
                await self._client.disconnect()
                self._connected = False
                _LOGGER.info("Disconnected from OBD adapter")
        except Exception as err:
            _LOGGER.error("Error disconnecting from OBD adapter: %s", err)

    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle notifications from the BLE adapter."""
        self._read_buffer.extend(data)
        # Signal that data is available
        self._response_event.set()

    async def query_pid(self, pid: str) -> Optional[Any]:
        """Query a specific OBD PID.

        Args:
            pid: PID in hex format, e.g., "010D" for odometer

        Returns:
            Parsed value or None if query failed
        """
        try:
            # Ensure connected
            if not self._connected:
                if not await self.connect():
                    return None

            # Send the OBD command
            cmd = self._build_obd_command(pid)
            _LOGGER.debug("Querying PID %s with command: %s", pid, cmd)

            # Clear buffer and event
            self._read_buffer.clear()
            self._response_event.clear()

            # Send command to adapter
            await self._client.write_gatt_char(
                self._char_uuid_write, cmd.encode() + b"\r"
            )

            # Wait for response
            await asyncio.wait_for(self._response_event.wait(), timeout=5.0)

            # Parse the response
            response = self._read_buffer.decode("utf-8", errors="ignore").strip()
            _LOGGER.debug("Response for PID %s: %s", pid, response)

            # Parse and return the value
            value = self._parse_obd_response(pid, response)
            return value

        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout waiting for PID %s response", pid)
            return None
        except Exception as err:
            _LOGGER.error("Error querying PID %s: %s", pid, err)
            return None

    def _build_obd_command(self, pid: str) -> str:
        """Build an OBD command string for the given PID.

        Args:
            pid: PID in format "01XX" where XX is the parameter ID

        Returns:
            Command string for the ELM327 adapter
        """
        # Most ELM327 adapters accept standard OBD format
        # Mode 01 (current data) + PID
        return f"{pid}"

    def _parse_obd_response(self, pid: str, response: str) -> Optional[Any]:
        """Parse an OBD response for the given PID.

        Args:
            pid: The queried PID
            response: Raw response from the adapter

        Returns:
            Parsed value or None if parsing failed
        """
        try:
            # Remove common prefixes/whitespace
            response = response.replace("\r", "").replace("\n", "").strip()

            # Typical ELM327 response format: ">41XX..." where XX are data bytes
            # or "010D" might return "41 0D 12 34" (mode response + PID + data bytes)

            if "NO DATA" in response or "?" in response:
                _LOGGER.debug("No data for PID %s", pid)
                return None

            # Extract hex bytes from response
            parts = response.split()
            if len(parts) < 3:
                _LOGGER.debug("Invalid response format for PID %s: %s", pid, response)
                return None

            # Skip mode response byte and PID echo, get data bytes
            data_bytes = parts[2:]

            # Convert to integers
            data = bytes([int(b, 16) for b in data_bytes])

            # Decode based on PID type
            if pid == "010D":  # Odometer
                # Single 16-bit value representing km (or potentially 24-bit)
                if len(data) >= 2:
                    value = (data[0] << 8) | data[1]
                    return value
                return None

            elif pid == "010C":  # RPM
                # 2 bytes: ((A*256)+B)/4
                if len(data) >= 2:
                    value = ((data[0] * 256) + data[1]) / 4
                    return int(value)
                return None

            elif pid == "0105":  # Coolant Temperature
                # 1 byte: A - 40
                if len(data) >= 1:
                    return data[0] - 40
                return None

            elif pid == "0114":  # Fuel Tank Level
                # 1 byte: (A*100)/255
                if len(data) >= 1:
                    return (data[0] * 100) / 255
                return None

            elif pid == "0110":  # Fuel Pressure
                # 1 byte: A * 3
                if len(data) >= 1:
                    return data[0] * 3
                return None

            elif pid == "010F":  # MAP
                # 1 byte: A
                if len(data) >= 1:
                    return data[0]
                return None

            elif pid == "0106":  # STFT Bank 1
                # 1 byte: ((A - 128) * 100 / 128)
                if len(data) >= 1:
                    return ((data[0] - 128) * 100 / 128)
                return None

            elif pid == "0120":  # Fuel Injection Timing
                # 2 bytes: ((A*256)+B)/128 - 210
                if len(data) >= 2:
                    return (((data[0] * 256) + data[1]) / 128) - 210
                return None

            elif pid in ["0132", "0133"]:  # Pressures
                # 1 byte: A * 0.25 (kPa)
                if len(data) >= 1:
                    return data[0] * 0.25
                return None

            else:
                _LOGGER.debug("No decoder for PID %s", pid)
                return data[0] if data else None

        except (ValueError, IndexError, AttributeError) as err:
            _LOGGER.debug("Error parsing response for PID %s: %s", pid, err)
            return None
