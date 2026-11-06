"""Sensors from the status bean and the electricity-statistics endpoints."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ERROR_TEXT
from .helpers import as_int, device_info, sum_array

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    status = runtime.get("status")
    aux = runtime.get("aux")
    if not device or not status:
        return

    entities = [
        PanasonicStatusSensor(status, device, entry, description)
        for description in device.profile.get("status_sensors", [])
    ]
    if aux:
        entities.extend(
            PanasonicAuxSensor(aux, device, entry, description)
            for description in device.profile.get("aux_sensors", [])
        )
    async_add_entities(entities)


class _BaseSensor(CoordinatorEntity, SensorEntity):
    """Common naming, identity and device grouping."""

    def __init__(self, coordinator, device, entry, description):
        super().__init__(coordinator)
        self._device = device
        self._description = description
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = (
            f"panasonic_{device.device_id}_{description['key']}_sensor"
        )
        self._attr_device_info = device_info(device, entry.title)
        self._attr_native_unit_of_measurement = description.get("unit")
        self._attr_device_class = description.get("device_class")
        self._attr_state_class = description.get("state_class")


class PanasonicStatusSensor(_BaseSensor):
    """A field directly from the 15s status bean."""

    @property
    def available(self):
        data = self.coordinator.data or {}
        return (
            self.coordinator.last_update_success
            and self._description["field"] in data
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        raw = data.get(self._description["field"])
        if raw is None:
            return None
        if self._description.get("kind") == "text":
            return str(raw)

        value = as_int(raw)
        if value is None:
            return None
        if self._description.get("temperature"):
            if value in (127, 128, 255, 65535) or value > 80:
                return None
            scale = self._device.detected_temp_scale or (2 if value > 45 else 1)
            return round(value / scale, 1)
        return value

    @property
    def extra_state_attributes(self):
        if self._description.get("kind") != "text":
            return None
        data = self.coordinator.data or {}
        raw = data.get(self._description["field"])
        description = ERROR_TEXT.get(str(raw)) if raw is not None else None
        return {"description": description} if description else None


class PanasonicAuxSensor(_BaseSensor):
    """A value from the 60s electricity-statistics coordinator."""

    @property
    def available(self):
        data = (self.coordinator.data or {}).get(self._description["source"])
        return (
            self.coordinator.last_update_success
            and isinstance(data, dict)
            and self._description["field"] in data
        )

    @property
    def native_value(self):
        section = (self.coordinator.data or {}).get(self._description["source"])
        if not isinstance(section, dict):
            return None
        raw = section.get(self._description["field"])
        if raw is None:
            return None
        if self._description.get("sum_array"):
            return sum_array(raw)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
