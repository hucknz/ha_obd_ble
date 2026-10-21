"""OBD API for communicating with generic OBD2 BLE adapters."""

from __future__ import annotations

import asyncio
import logging
import re
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
    LEGACY_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)

# OBD2 Standard Commands
OBD_COMMANDS = {
    "010D": {"name": "Vehicle Speed", "format": "speed"},
    "220103": {"name": "Toyota Odometer", "format": "distance"},
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
        self._command_lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Connect to the OBD adapter."""
        try:
            if self._connected:
                return True

            _LOGGER.debug("Connecting to OBD adapter at %s", self._address)
            self._client = BleakClient(self._address)
            await self._client.connect()

            configured_read = self._char_uuid_read
            try:
                await self._client.start_notify(
                    configured_read, self._notification_handler
                )
            except BleakError as initial_error:
                fallbacks = (
                    (DEFAULT_CHARACTERISTIC_UUID_READ, DEFAULT_CHARACTERISTIC_UUID_WRITE),
                    (LEGACY_CHARACTERISTIC_UUID, LEGACY_CHARACTERISTIC_UUID),
                )
                last_error = initial_error
                for fallback_read, fallback_write in fallbacks:
                    if fallback_read.lower() == configured_read.lower():
                        continue
                    try:
                        await self._client.start_notify(
                            fallback_read, self._notification_handler
                        )
                    except BleakError as err:
                        last_error = err
                        continue

                    _LOGGER.warning(
                        "Configured read characteristic %s unavailable; using %s",
                        configured_read,
                        fallback_read,
                    )
                    if self._char_uuid_write.lower() == configured_read.lower():
                        self._char_uuid_write = fallback_write
                    self._char_uuid_read = fallback_read
                    break
                else:
                    raise last_error

            self._connected = True
            await self._initialize_adapter()
            _LOGGER.info("Connected to OBD adapter %s", self._address)
            return True

        except BleakError as err:
            _LOGGER.error("Failed to connect to OBD adapter: %s", err)
            self._connected = False
            return False
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timed out initializing OBD adapter: %s", err)
            self._connected = False
            if self._client and self._client.is_connected:
                await self._client.disconnect()
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
            pid: Mode/PID in hex, e.g., "010C" or Toyota-specific "220103"

        Returns:
            Parsed value or None if query failed
        """
        try:
            # Ensure connected
            if not self._connected:
                if not await self.connect():
                    return None

            if pid == "220103":
                async with self._command_lock:
                    try:
                        await self._send_command("ATSH700")
                        response = await self._send_command("220103")
                    finally:
                        await self._send_command("ATSH7DF")
                return self._parse_toyota_odometer(response)

            cmd = self._build_obd_command(pid)
            _LOGGER.debug("Querying PID %s with command: %s", pid, cmd)
            async with self._command_lock:
                response = await self._send_command(cmd)
            _LOGGER.debug("Response for PID %s: %s", pid, response)

            return self._parse_obd_response(pid, response)

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

    async def _send_command(self, command: str, timeout: float = 5.0) -> str:
        """Send one ELM command and collect notifications through the prompt."""
        if not self._client or not self._connected:
            raise BleakError("OBD adapter is not connected")

        self._read_buffer.clear()
        self._response_event.clear()
        try:
            await self._client.write_gatt_char(
                self._char_uuid_write, command.encode() + b"\r"
            )
        except BleakError:
            fallback_uuid = self._char_uuid_read
            if self._char_uuid_write.lower() == fallback_uuid.lower():
                raise
            _LOGGER.warning(
                "Configured write characteristic %s rejected command; retrying on %s",
                self._char_uuid_write,
                fallback_uuid,
            )
            self._char_uuid_write = fallback_uuid
            await self._client.write_gatt_char(
                self._char_uuid_write, command.encode() + b"\r"
            )

        while b">" not in self._read_buffer:
            self._response_event.clear()
            if b">" in self._read_buffer:
                break
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)

        return self._read_buffer.decode("ascii", errors="ignore").strip()

    async def _initialize_adapter(self) -> None:
        """Reset the ELM adapter and configure predictable response formatting."""
        response = await self._send_command("ATZ", timeout=10.0)
        if "ELM" not in response.upper():
            _LOGGER.warning(
                "Unexpected response while resetting OBD adapter: %s", response
            )

        for command in ("ATE0", "ATH1", "ATS0", "ATAT1", "ATAL", "ATST64", "ATSP0"):
            response = await self._send_command(command)
            if "?" in response or "ERROR" in response.upper():
                _LOGGER.warning(
                    "OBD adapter did not accept initialization command %s: %s",
                    command,
                    response,
                )

    @staticmethod
    def _parse_toyota_odometer(response: str) -> Optional[int]:
        """Extract the Toyota odometer's three-byte kilometer value."""
        compact = re.sub(r"[^0-9A-F]", "", response.upper())
        match = re.search(r"708(?:07)?62010301([0-9A-F]{6})", compact)
        if not match:
            _LOGGER.debug("No Toyota odometer value in response: %s", response)
            return None
        return int(match.group(1), 16)

    def _parse_obd_response(self, pid: str, response: str) -> Optional[Any]:
        """Parse an OBD response for the given PID.

        Args:
            pid: The queried PID
            response: Raw response from the adapter

        Returns:
            Parsed value or None if parsing failed
        """
        try:
            response = response.upper()

            if "NO DATA" in response or "?" in response:
                _LOGGER.debug("No data for PID %s", pid)
                return None

            # ELM replies can be compact and include CAN IDs (for example
            # 7E803410D00), so locate the positive mode/PID response directly.
            match = re.search(rf"41{re.escape(pid[2:])}([0-9A-F]+)", response)
            if not match:
                _LOGGER.debug("Invalid response format for PID %s: %s", pid, response)
                return None

            data = bytes.fromhex(match.group(1)[: len(match.group(1)) // 2 * 2])

            # Decode based on PID type
            if pid == "010D":  # Vehicle speed
                return data[0] if data else None

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
