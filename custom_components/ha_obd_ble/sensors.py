"""Sensor descriptions for Generic OBD BLE integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfTemperature, UnitOfPressure

SENSOR_DESCRIPTIONS = [
    # Core sensors (available on most vehicles)
    SensorEntityDescription(
        key="010D",
        name="Odometer",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="010C",
        name="Engine RPM",
        native_unit_of_measurement="rpm",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    SensorEntityDescription(
        key="0105",
        name="Coolant Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    SensorEntityDescription(
        key="0114",
        name="Fuel Tank Level",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fuel",
    ),
    SensorEntityDescription(
        key="0110",
        name="Fuel Pressure",
        native_unit_of_measurement=UnitOfPressure.KPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    SensorEntityDescription(
        key="010F",
        name="Intake Manifold Absolute Pressure",
        native_unit_of_measurement=UnitOfPressure.KPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    # Additional sensors
    SensorEntityDescription(
        key="0106",
        name="Short Term Fuel Trim Bank 1",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
    ),
    SensorEntityDescription(
        key="0120",
        name="Fuel Injection Timing",
        native_unit_of_measurement="°",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:angle-acute",
    ),
    SensorEntityDescription(
        key="0132",
        name="Evap System Vapor Pressure",
        native_unit_of_measurement="Pa",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    SensorEntityDescription(
        key="0133",
        name="Barometric Pressure",
        native_unit_of_measurement=UnitOfPressure.KPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
]
