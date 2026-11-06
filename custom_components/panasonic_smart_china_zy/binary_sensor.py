"""Binary sensors derived from the Panasonic status bean."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .helpers import as_int, device_info


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    status = runtime.get("status")
    if not device or not status:
        return
    entities = [
        PanasonicBinarySensor(status, device, entry, description)
        for description in device.profile.get("binary_sensors", [])
    ]
    async_add_entities(entities)


class PanasonicBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """A status flag (non-zero error, filter due, fresh-air running)."""

    def __init__(self, coordinator, device, entry, description):
        super().__init__(coordinator)
        self._device = device
        self._description = description
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = (
            f"panasonic_{device.device_id}_{description['key']}_binary_sensor"
        )
        self._attr_device_info = device_info(device, entry.title)
        self._attr_device_class = description.get("device_class")

    @property
    def available(self):
        data = self.coordinator.data or {}
        return (
            self.coordinator.last_update_success
            and self._description["field"] in data
        )

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        raw = data.get(self._description["field"])

        if self._description.get("erv_running"):
            return as_int(data.get("ervCheck")) == 1 or (
                as_int(raw) == self._description["equals"]
                and as_int(data.get("runStatus")) == self._device.power_on_value
            )
        if self._description.get("equals") is not None:
            return as_int(raw) == self._description["equals"]
        if self._description.get("nonzero"):
            return raw not in (0, "0", "0000", "", None)
        return as_int(raw) == 1
