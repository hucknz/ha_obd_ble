"""Constants for Generic OBD BLE integration."""

NAME = "OBD BLE"
DOMAIN = "ha_obd_ble"
VERSION = "0.1.0"

ISSUE_URL = "https://github.com/hamish/ha_obd_ble/issues"

# Configuration keys
CONF_SERVICE_UUID = "service_uuid"
CONF_CHARACTERISTIC_UUID_READ = "characteristic_uuid_read"
CONF_CHARACTERISTIC_UUID_WRITE = "characteristic_uuid_write"

# Default BLE UUIDs (ELM327 / LeLink2 / OBDBLE dongle)
DEFAULT_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_READ = "0000ffe1-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_WRITE = "0000ffe1-0000-1000-8000-00805f9b34fb"

# BLE local names to search for when scanning for adapters
BLE_LOCAL_NAMES = {"OBDBLE", "OBD-BLE", "OBD BLE", "LeLink", "LeLink2", "ELM327"}

# Standard OBD2 PIDs (Mode 01) for generic vehicles
# Format: (PID_HEX, NAME, UNIT, DEVICE_CLASS, STATE_CLASS)
OBD2_PIDS = {
    "010D": ("Odometer", "km", "distance", "total_increasing"),
    "010C": ("RPM", "rpm", None, "measurement"),
    "0105": ("Coolant Temperature", "°C", "temperature", "measurement"),
    "0106": ("Short Term Fuel Trim Bank 1", "%", None, "measurement"),
    "0114": ("Fuel Tank Level", "%", None, "measurement"),
    "0110": ("Fuel Pressure", "kPa", "pressure", "measurement"),
    "010F": ("Intake Manifold Abs Pressure", "kPa", "pressure", "measurement"),
    "0120": ("Fuel Injection Timing", "°", None, "measurement"),
    "0132": ("Evap System Vapor Pressure", "Pa", "pressure", "measurement"),
    "0133": ("Barometric Pressure", "kPa", "pressure", "measurement"),
}

# Core PIDs to always query (others are optional)
REQUIRED_PIDS = ["010D", "010C"]  # Odometer and RPM are most important

# Default polling intervals (seconds)
DEFAULT_FAST_POLL = 10      # When vehicle is on
DEFAULT_SLOW_POLL = 300     # When vehicle is off but in range
DEFAULT_XS_POLL = 3600      # When out of range (once per hour)
DEFAULT_FETCH_TIMEOUT = 30  # Max time to wait for OBD response

# Storage — persists last-known sensor values across HA restarts
STORAGE_KEY = f"{DOMAIN}.sensor_cache"
STORAGE_VERSION = 1

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
Generic OBD2 integration via Bluetooth Low Energy
Report issues at: {ISSUE_URL}
-------------------------------------------------------------------
"""
