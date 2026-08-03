from __future__ import annotations

from homeassistant.const import CONF_NAME, PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from .entity import async_device_device_info_fn
from .qingping import Qingping
from .qingping.events import SENSOR_DATA_UPDATE

async def async_setup_entry(hass, config_entry, async_add_entities):
    instance: Qingping = config_entry.runtime_data
    async_add_entities([
        QingpingTemperatureSensor(instance, config_entry),
        QingpingHumiditySensor(instance, config_entry),
        QingpingBatterySensor(instance, config_entry)
    ])


class QingpingTemperatureSensor(SensorEntity):
    def __init__(self, instance: Qingping, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Temperature"
        self._attr_unique_id = f"{instance.name}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_native_value = instance.sensor_data.get("temperature")

        instance.eventbus.add_listener(SENSOR_DATA_UPDATE, self.sensor_data_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def sensor_data_updated(self, sensor_data: dict):
        if "temperature" in sensor_data:
            self._attr_native_value = sensor_data["temperature"]
            self.schedule_update_ha_state()


class QingpingHumiditySensor(SensorEntity):
    def __init__(self, instance: Qingping, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Humidity"
        self._attr_unique_id = f"{instance.name}_humidity"
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_value = instance.sensor_data.get("humidity")

        instance.eventbus.add_listener(SENSOR_DATA_UPDATE, self.sensor_data_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def sensor_data_updated(self, sensor_data: dict):
        if "humidity" in sensor_data:
            self._attr_native_value = sensor_data["humidity"]
            self.schedule_update_ha_state()


class QingpingBatterySensor(SensorEntity):
    def __init__(self, instance: Qingping, config_entry):
        self._instance: Qingping = instance
        self._config_entry = config_entry
        self._attr_name = f"{config_entry.data[CONF_NAME]} Battery"
        self._attr_unique_id = f"{instance.name}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = instance.sensor_data.get("battery")

        instance.eventbus.add_listener(SENSOR_DATA_UPDATE, self.sensor_data_updated)

    @property
    def device_info(self) -> DeviceInfo:
        return async_device_device_info_fn(self._instance, self._config_entry.data[CONF_NAME])

    async def sensor_data_updated(self, sensor_data: dict):
        if "battery" in sensor_data:
            self._attr_native_value = sensor_data["battery"]
            self.schedule_update_ha_state()
