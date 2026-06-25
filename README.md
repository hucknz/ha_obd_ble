# Generic OBD BLE — Home Assistant Custom Integration

A Home Assistant custom integration for monitoring vehicle data via a Bluetooth Low Energy OBD2 adapter. Unlike the Nissan Leaf-specific integration, this works with any petrol or diesel vehicle that has an OBD2 port and a compatible BLE adapter.

## Features

- **Standard OBD2 PIDs**: Support for all standard OBD2 parameters
- **Odometer Reading**: Primary goal — track total distance traveled
- **Data Persistence**: Sensor values persist across Home Assistant restarts
- **Flexible Polling**: Configurable polling intervals for on/off/out-of-range states
- **Device Detection**: Automatic polling trigger when BLE device detected (vehicle running)
- **BLE Adapter Agnostic**: Works with LeLink2, generic ELM327 adapters, and others

## Supported Hardware

- **LeLink2 ELM327 BLE OBD-II adapter** (tested)
- Any ELM327 BLE OBD-II adapter advertising as OBDBLE
- ESPHome Bluetooth Proxy setups

## Supported Vehicles

- **Any vehicle with OBD2 port** (2001+ gasoline, 2004+ diesel)
- Primary testing: 2017 Toyota Highlander V6
- Should work with all standard OBD2-compliant vehicles

## Installation

### Option 1 — Manual (Recommended for Testing)

1. Copy the `custom_components/ha_generic_obd_ble/` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to Settings → Devices & Services → Add Integration → Generic OBD BLE.

### Option 2 — HACS (When Available)

1. Open HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/hamish/ha_obd_ble` with category Integration.
3. Find Generic OBD BLE and click Download.
4. Restart Home Assistant.

## Setup

1. Plug the OBD adapter into your vehicle's OBD-II port.
2. Turn on the vehicle ignition or ensure the adapter is powered.
3. In Home Assistant: Settings → Devices & Services → Create Integration → Generic OBD BLE.
4. **Step 1** — Select your OBD adapter from the dropdown.
5. **Step 2** — (Optional) Configure BLE UUIDs if using a non-standard adapter.
6. Click Submit. HA will create the device and sensor entities.

## Sensors

The integration provides the following sensors (availability depends on your vehicle):

| Sensor | Unit | Description |
|--------|------|-------------|
| **Odometer** | km | Total distance traveled ⭐ |
| **Engine RPM** | rpm | Current engine speed |
| **Coolant Temperature** | °C | Engine coolant temperature |
| **Fuel Tank Level** | % | Remaining fuel |
| **Fuel Pressure** | kPa | Fuel system pressure |
| **Intake Manifold Pressure** | kPa | Intake manifold absolute pressure |
| **Short Term Fuel Trim** | % | Fuel trim adjustment |
| **Fuel Injection Timing** | ° | Injection timing |
| **EVAP System Pressure** | Pa | Evaporative emissions pressure |
| **Barometric Pressure** | kPa | Atmospheric pressure |

## Configuration Options

After setup, click **Configure** on the integration card to adjust:

| Setting | Default | Description |
|---------|---------|-------------|
| Fast poll interval | 10 s | When vehicle is on and in range |
| Slow poll interval | 300 s | When in range but vehicle is off |
| Extra-slow poll interval | 3600 s | When out of BLE range |
| BLE Service UUID | 0000ffe0-… | GATT service UUID |
| BLE Read Characteristic UUID | 0000ffe1-… | Read characteristic UUID |
| BLE Write Characteristic UUID | 0000ffe1-… | Write characteristic UUID |

## Data Persistence

Sensor values are automatically saved to HA's `.storage/` directory after each successful poll. After a Home Assistant restart, sensors immediately display their last known values — no need to drive the vehicle home first.

## Polling Strategy

The integration supports two polling modes:

1. **Device Detection** (Preferred): Polls faster when the OBD adapter is detected via Bluetooth (vehicle is running and within range).
2. **Time-Based** (Fallback): Uses configured polling intervals when device detection is unavailable.

## Troubleshooting

### No adapters appear in the dropdown
- Ensure the OBD adapter is plugged into the vehicle's OBD-II port
- Turn on the vehicle ignition or accessory mode
- Check that the adapter is within Bluetooth range
- Verify in Settings → Devices & Services → Bluetooth that HA can see the adapter
- Try power-cycling the adapter

### Sensors stay at last known value indefinitely
- This is the persistence feature working as designed
- Values update the next time the vehicle is in range with ignition on
- Check the coordinator's last refresh time in Settings → Devices & Services

### Specific sensors not updating
- Not all vehicles support all OBD2 PIDs
- Some sensors may be vehicle-specific
- Check your vehicle's OBD2 compatibility
- Enable debug logging to see which PIDs are responding

### Enable Debug Logging

Add this to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.ha_generic_obd_ble: debug
```

Then check **Settings → System → Logs** for detailed debug output.

## OBD2 PID Reference

Common OBD2 PIDs supported:

| PID | Description | Units |
|-----|-------------|-------|
| 010D | Odometer (distance since codes cleared) | km |
| 010C | Engine RPM | rpm |
| 0105 | Engine Coolant Temperature | °C |
| 0114 | Fuel Tank Level | % |
| 0110 | Fuel Pressure | kPa |
| 010F | Intake Manifold Absolute Pressure | kPa |
| 0106 | Short-Term Fuel Trim Bank 1 | % |
| 0120 | Fuel Injection Timing | ° |
| 0132 | Evaporative System Vapor Pressure | Pa |
| 0133 | Barometric Pressure | kPa |

## Development / Testing

To test with your 2017 Toyota Highlander V6:

1. Install the integration following the Manual Installation option above
2. Connect the OBD adapter to the Highlander's OBD-II port (usually under the steering wheel)
3. Turn on ignition and follow setup steps
4. Check which sensors report values and which don't (vehicle-specific)
5. Enable debug logging and check logs for detailed communication
6. Report any issues with specific PIDs or vehicles on GitHub

## Contributing

Found a bug or want to improve the integration? Please open an issue on GitHub.

## License

GPL-2.0-or-later (inherited from python-OBD lineage)

## Credits

- Based on [hucknz/ha_nissan_leaf_obd_ble](https://github.com/hucknz/ha_nissan_leaf_obd_ble)
- ELM327 protocol implementation
- OBD2 specification reference
