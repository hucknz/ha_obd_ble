# Generic OBD BLE — Development Reference

## Project Structure

```
custom_components/ha_generic_obd_ble/
├── __init__.py              # Integration entry point
├── manifest.json            # HA integration metadata
├── const.py                 # Constants and OBD2 PID definitions
├── config_flow.py           # Setup wizard
├── coordinator.py           # Data polling and persistence
├── entity.py                # Base entity class
├── sensor.py                # Sensor platform
├── sensors.py               # Sensor descriptions
├── obd_api.py               # OBD adapter communication
├── strings.json             # Localization strings
└── py.typed                 # Type hints marker
```

## Key Classes

### GenericObdApi (`obd_api.py`)
Handles BLE communication with the OBD adapter.

**Methods**:
- `async connect()` - Connect to BLE device
- `async disconnect()` - Disconnect
- `async query_pid(pid)` - Query a single PID and get parsed value

**Key Features**:
- Bleak-based BLE communication
- Automatic connection management
- OBD response parsing with standard decoders
- Timeout handling

### GenericObdCoordinator (`coordinator.py`)
Manages data polling and persistence.

**Extends**: HomeAssistant's `DataUpdateCoordinator`

**Key Features**:
- Configurable fast/slow/extra-slow polling intervals
- Automatic data persistence to `.storage/`
- Device presence detection for smart polling
- Cached data restoration on restart

### GenericObdBleSensor (`sensor.py`)
Individual sensor entity for each OBD PID.

**Attributes**:
- `native_value` - Gets current value from coordinator
- Supports all standard HA sensor features
- Native units and device classes

## Adding New OBD PIDs

### 1. Add Sensor Description
Edit `sensors.py`, add to `SENSOR_DESCRIPTIONS`:

```python
SensorEntityDescription(
    key="010F",
    name="Intake Manifold Pressure",
    native_unit_of_measurement=UnitOfPressure.KPA,
    device_class=SensorDeviceClass.PRESSURE,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:gauge",
),
```

### 2. Add Decoder (if needed)
In `obd_api.py`, add to `_parse_obd_response()`:

```python
elif pid == "010F":  # Intake Manifold Pressure
    if len(data) >= 1:
        return data[0]  # kPa
    return None
```

### 3. Add to Required PIDs (if critical)
In `const.py`, add to `REQUIRED_PIDS`:

```python
REQUIRED_PIDS = ["010D", "010C", "010F"]
```

## OBD2 PID Format

Standard OBD2 Mode 01 PID format:
- **Structure**: `01XX` where XX is the parameter ID
- **Example**: `010D` = Mode 01, Parameter 0D (Odometer)
- **Response Format**: `41 XX YY ZZ ...` where:
  - `41` = Response to mode 01
  - `XX` = Echo of parameter ID
  - `YY ZZ ...` = Data bytes

## Polling Strategy

```
Vehicle On (Ignition) → Fast Poll (10s)
                        ↓
Vehicle Off → Slow Poll (300s)
             ↓
Out of Range → Extra-Slow Poll (3600s)
               ↓
              Serve Cached Values
```

## Data Persistence

Cached data stored at:
```
~/.homeassistant/.storage/ha_generic_obd_ble.sensor_cache.[ENTRY_ID]
```

**Format**:
```json
{
  "version": 1,
  "data": {
    "010D": 45234,
    "010C": 1250,
    "0105": 85
  }
}
```

## Common OBD PIDs by Vehicle Type

### Gasoline Engines
- `010D` - Odometer (distance since clear)
- `010C` - RPM
- `0105` - Coolant temperature
- `0114` - Fuel tank level
- `0110` - Fuel pressure
- `010F` - Intake manifold pressure

### Diesel Engines
Same as gasoline, some additional:
- `0106` - Fuel trim
- `0120` - Fuel injection timing

### EV/Hybrid (May not work)
- Limited OBD2 support
- Different protocol for battery data
- See nissan_leaf integration for EV approach

## Testing New PIDs

### 1. With Real Vehicle
```python
# Edit obd_api.py temporarily
async def query_pid(self, pid: str) -> Optional[Any]:
    # ... existing code ...
    response = self._read_buffer.decode()
    print(f"Raw response for {pid}: {response!r}")
    # Verify raw hex output
```

### 2. Enable Debug Logging
```yaml
logger:
  logs:
    custom_components.ha_generic_obd_ble: debug
```

### 3. Check Log Output
```
Response for PID 010C: 41 0C 04 D0
```

### 4. Update Decoder
Adjust parsing logic in `_parse_obd_response()` for correct interpretation.

## Common Parsing Issues

### Issue: "No Data" Response
- Vehicle doesn't support this PID
- Wrong mode/PID combination
- ECU not responding

### Issue: Wrong Values
- Incorrect byte order (big-endian vs little-endian)
- Wrong divisor/formula
- Sign extension needed for negative values

### Issue: Intermittent Failures
- Timing issue (wait longer for response)
- BLE connection instability
- ECU busy

## Debugging Tips

1. **Enable full debug logging** - See coordinator and obd_api debug output
2. **Check raw responses** - Modify _parse_obd_response to log raw hex
3. **Test with multiple runs** - PIDs sometimes fail intermittently
4. **Compare with other OBD apps** - Verify expected values
5. **Check BLE connection** - Look for connection/disconnect logs

## Error Handling

### Coordinator Errors
- Logged but don't crash integration
- Values persist across restarts
- Network issues handled gracefully

### OBD Query Timeouts
- 5 second timeout per query
- Returns None if timeout occurs
- Coordinator retries on next poll

### Persistence Errors
- Gracefully continues without persistence
- Logs error but doesn't fail
- Values still available in memory

## Platform Integration

This integration follows standard HA patterns:

- **Config Flow**: Standard setup wizard + options
- **Persistence**: Storage API for data retention
- **Coordinator**: Proper update patterns
- **Entities**: Standard sensor platform
- **Logging**: Python logging with custom namespace

## Toyota Highlander V6 Specific

Known working PIDs on 2017 model:
- `010D` - Odometer (primary target)
- `010C` - RPM
- `0105` - Coolant temperature
- `0114` - Fuel level

PIDs to test further:
- `0110` - Fuel pressure
- `010F` - MAP
- `0106` - Fuel trim

## Future Enhancements

1. **Binary sensors** - Engine on/off detection
2. **Climate entity** - Temperature monitoring
3. **Fuel economy calculation** - Based on distance/consumption
4. **Diagnostic codes** - Read/clear DTCs
5. **Live graphing** - Dashboard support
6. **Multi-vehicle** - Support multiple OBD adapters
7. **Vehicle profiles** - Model-specific decoders

## References

- [OBD-II PIDs](https://en.wikipedia.org/wiki/OBD-II_PID)
- [ELM327 Protocol](https://www.elmelectronics.com/DSheets/)
- [Home Assistant Integration Documentation](https://developers.home-assistant.io/)
- [Bleak Library](https://bleak.readthedocs.io/)
