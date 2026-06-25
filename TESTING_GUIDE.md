# OBD BLE Integration — Testing Guide for Toyota Highlander

This guide will help you test the Generic OBD BLE integration with your 2017 Toyota Highlander V6.

## Prerequisites

- Home Assistant instance (2023.6.0 or later)
- 2017 Toyota Highlander V6 with OBD2 port
- BLE OBD2 adapter (LeLink2 or similar ELM327 BLE)
- Vehicle battery in good condition
- Home Assistant Bluetooth support (native or via Bluetooth Proxy)

## Step 1: Physical Setup

### Locate the OBD2 Port
- **Toyota Highlander**: Usually located under the steering wheel column, on the left side
- Look for a rectangular port, approximately 2.5cm wide
- May have a plastic cover that needs to be removed

### Insert the OBD Adapter
1. Power on the OBD adapter (may have a button or auto-power from the vehicle)
2. Plug it directly into the OBD2 port
3. Do NOT turn on the vehicle yet

### Test Adapter Bluetooth Signal
1. Check your Home Assistant instance's Bluetooth support:
   - Settings → Devices & Services → Bluetooth
   - You should see available Bluetooth adapters
2. Power on the vehicle (ignition on, engine can be off)
3. The OBD adapter should appear in the Bluetooth list (e.g., "OBDBLE", "LeLink2")

## Step 2: Install the Integration

### Option A: Manual Installation (Recommended)
1. Copy `custom_components/ha_obd_ble` to your Home Assistant config directory:
   ```
   ~/.homeassistant/custom_components/ha_obd_ble/
   ```
2. Restart Home Assistant: Settings → System → Restart

### Option B: Using HA File Editor
1. Install the "File Editor" add-on in Home Assistant if not already installed
2. Create folder: `config/custom_components/ha_obd_ble/`
3. Copy all files from this repository
4. Restart Home Assistant

## Step 3: Add the Integration

1. In Home Assistant: Settings → Devices & Services
2. Click **Create Integration** button
3. Search for "Generic OBD BLE"
4. Click on the integration

### Step 3a: Select Adapter
- You should see a dropdown with available OBD adapters
- Select your adapter (e.g., "OBDBLE (XX:XX:XX:XX:XX:XX)")
- If no adapters appear:
  - Ensure vehicle is on (ignition position)
  - Check that adapter is within BLE range
  - Verify it appears in Settings → Devices & Services → Bluetooth
  - Restart the integration discovery

### Step 3b: Configure BLE UUIDs (Optional)
- For standard adapters (LeLink2, generic ELM327), keep defaults
- Only modify if you're using a non-standard adapter with different UUIDs
- Standard defaults: Service UUID `0000ffe0-…`, Read/Write `0000ffe1-…`

### Step 3c: Submit
- Click Submit
- HA should create the device and sensors

## Step 4: Check Initial Data

After setup, you should see a new device "Generic OBD BLE" with sensors. Initial values may take a moment to populate:

### Expected Sensors
- **Odometer**: Total distance (km) — CRITICAL TEST SENSOR
- **Engine RPM**: Should show 0 if engine is off, or actual RPM if running
- **Coolant Temperature**: Should be around 80-95°C when warm
- **Fuel Tank Level**: Percentage (0-100%)

### Check Sensor Values
1. Settings → Devices & Services → Devices
2. Find "Generic OBD BLE" device
3. Click on it to see all sensors
4. Values should show within a few seconds if the vehicle is on

## Step 5: Verify Odometer Reading

This is the primary goal of the integration:

1. Check the `sensor.generic_obd_ble_odometer` value in Home Assistant
2. Compare it with your vehicle's dashboard odometer
3. **Values should match closely** (may be off by a few km if codes were previously cleared)

### Troubleshooting Odometer
- If **0 km**: Vehicle doesn't support PID 010D or distance was recently cleared
- If **very high**: Vehicle used a different mode for odometer
- If **no value**: See Debug Logging section below

## Step 6: Test Polling Behavior

### Test Fast Polling (Vehicle On)
1. Turn on the vehicle (ignition ON, engine can run or be off)
2. Check coordinator last refresh: Settings → Devices & Services
3. Sensor values should update every 10 seconds (default fast_poll)
4. Note timestamps to verify polling is happening

### Test Slow Polling (Vehicle Off)
1. Turn off the vehicle (ignition OFF)
2. OBD adapter should still be powered
3. Polling should switch to 300 seconds (default slow_poll)
4. Values should update every 5 minutes

### Test Persistence
1. Note the odometer reading in Home Assistant
2. Restart Home Assistant: Settings → System → Restart
3. Immediately after restart, check the sensor value
4. **Value should appear immediately** without needing to turn on vehicle

## Step 7: Configuration Tuning

For your specific testing, you may want to adjust polling intervals:

1. Settings → Devices & Services → Generic OBD BLE
2. Click **Configure**
3. Adjust intervals (in seconds):
   - **Fast poll**: 10 s (when vehicle is on) — good for odometer tracking
   - **Slow poll**: 300 s (when off but in range) — 5 minutes
   - **Extra-slow poll**: 3600 s (out of range) — 1 hour
4. Save changes

For faster testing, try:
- Fast: 5 seconds
- Slow: 60 seconds
- Extra-slow: 600 seconds

## Step 8: Enable Debug Logging

Create or edit `config/configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.ha_obd_ble: debug
    bleak: debug
    bleak_retry_connector: debug
```

Then check logs: Settings → System → Logs

### Expected Debug Output
```
[custom_components.ha_obd_ble.coordinator] Connected to OBD adapter
[custom_components.ha_obd_ble.obd_api] Querying PID 010D with command: 010D
[custom_components.ha_obd_ble.obd_api] Response for PID 010D: 41 0D 12 34
[custom_components.ha_obd_ble.obd_api] PID 010D: 4660
```

## Step 9: Automation Testing

Once sensors are working, create an automation to track odometer changes:

```yaml
automation:
  - alias: "Log Odometer Changes"
    trigger:
      platform: state
      entity_id: sensor.generic_obd_ble_odometer
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: system_log.write
        data:
          level: info
          message: "Odometer changed from {{ trigger.from_state.state }} to {{ trigger.to_state.state }}"
```

## Known Issues & Workarounds

### Issue: No Sensors Appear
- **Cause**: Adapter not detected or BLE connection failed
- **Fix**: 
  - Power cycle the adapter
  - Ensure ignition is on
  - Check Bluetooth range
  - Verify adapter appears in Bluetooth settings

### Issue: Sensors Show But Don't Update
- **Cause**: OBD communication failing
- **Fix**:
  - Enable debug logging
  - Check vehicle supports the PID
  - Try restarting the integration
  - Some Toyotas may require specific mode switches

### Issue: Odometer Stuck at Last Value
- **Cause**: Vehicle off and out of range (persistence kicking in)
- **Fix**: This is expected behavior
  - Turn on vehicle to trigger refresh
  - Check "Extra-slow poll" interval — may be 1 hour

### Issue: Coolant Temperature Way Off
- **Cause**: Formula issue or vehicle doesn't support PID 0105
- **Fix**:
  - Enable debug logging to see raw values
  - Compare with vehicle's temperature gauge
  - Toyota may use different PID

## Hardware Verification Checklist

- [ ] OBD adapter appears in Bluetooth list when vehicle is on
- [ ] Adapter pairs/connects successfully
- [ ] At least one sensor (RPM) shows a value
- [ ] Odometer value matches dashboard
- [ ] Values update when vehicle is running
- [ ] Values persist after HA restart
- [ ] Debug logs show successful OBD queries

## Toyota Highlander Specific Notes

### Known Working
- Engine RPM (PID 010C)
- Fuel Tank Level (PID 0114) 
- Odometer should be available

### Vehicle-Specific PID Support
Not all PIDs work on all vehicles. If a sensor never updates:
1. It may not be supported on V6 model
2. Try enabling debug logging to see which PIDs respond
3. Toyota may use proprietary extensions

### OBD Port Location
- Usually below steering wheel, left side
- May have removable plastic cover
- No power needed (powered from vehicle)

## What to Test

1. **Odometer Reading**: Verify accuracy against dashboard
2. **RPM**: Check responds when engine is running
3. **Fuel Level**: Compare with gauge when refueling
4. **Persistence**: Restart HA and check values reappear
5. **Polling**: Check logs show regular updates
6. **Range**: Test BLE range from your HA location

## Reporting Results

If you encounter issues, please report with:
1. Vehicle year/model/engine
2. OBD adapter model
3. Which sensors work/don't work
4. Debug log excerpts showing the issue
5. Expected vs. actual values

## Next Steps

Once basic functionality is working, you can:
1. Create automations based on odometer changes
2. Track fuel consumption patterns
3. Monitor coolant/engine temperature
4. Set up alerts for maintenance intervals
5. Graph historical odometer data

## Support

For issues or improvements:
1. Check debug logs first: Settings → System → Logs
2. Enable detailed logging as shown above
3. Report specific PID failures with debug output
4. Check if vehicle supports the PID using external OBD apps

Good luck! The odometer reading should give you a solid foundation for tracking vehicle usage in Home Assistant.
