"""Feature switches for Panasonic AirconCommon devices.

Entity unique_ids are kept stable: "key" is the legacy identifier while
"aliases" resolve to the actual field in the status bean.
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PanasonicApiError
from .const import DOMAIN
from .helpers import as_int, capability_ok, device_info, resolve_key

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    coordinator = runtime.get("status")
    if not device or not coordinator:
        return
    entities = [
        PanasonicRemoteSwitch(coordinator, device, entry, description)
        for description in device.profile.get("remote_switches", [])
    ]
    timer_description = device.profile.get("timer_switch")
    if timer_description and runtime.get("aux"):
        entities.append(
            PanasonicTimerSwitch(runtime["aux"], device, entry, timer_description)
        )
    async_add_entities(entities)


class PanasonicRemoteSwitch(CoordinatorEntity, SwitchEntity):
    """A 0/1 feature toggle gated by the official *Ex capability flag."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, device, entry, description):
        super().__init__(coordinator)
        self._device = device
        self._key = description["key"]
        self._aliases = tuple(description.get("aliases", ()))
        self._capability = description.get("capability")
        self._on_value = description.get("on", 1)
        self._off_value = description.get("off", 0)
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = f"panasonic_{device.device_id}_{self._key}_switch"
        self._attr_device_info = device_info(device, entry.title)

    @property
    def _data(self):
        return self.coordinator.data or {}

    @property
    def _active_key(self):
        return resolve_key(self._data, self._key, self._aliases)

    @property
    def available(self):
        data = self._data
        return (
            self.coordinator.last_update_success
            and self._active_key in data
            and capability_ok(data, self._capability)
        )

    @property
    def is_on(self):
        return as_int(self._data.get(self._active_key)) == self._on_value

    async def _set(self, value):
        try:
            await self._device.send_command({self._active_key: value})
        except PanasonicApiError as err:
            _LOGGER.error("Switch %s command failed: %s", self._key, err)

    async def async_turn_on(self, **kwargs):
        await self._set(self._on_value)

    async def async_turn_off(self, **kwargs):
        await self._set(self._off_value)


class PanasonicTimerSwitch(CoordinatorEntity, SwitchEntity):
    """Master enable/disable for the weekly timer (its own cloud endpoint)."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, device, entry, description):
        super().__init__(coordinator)
        self._device = device
        self._description = description
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = (
            f"panasonic_{device.device_id}_{description['key']}_switch"
        )
        self._attr_device_info = device_info(device, entry.title)

    @property
    def _status(self):
        section = (self.coordinator.data or {}).get(self._description["source"])
        return section if isinstance(section, dict) else {}

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            and self._description["field"] in self._status
        )

    @property
    def is_on(self):
        return (
            as_int(self._status.get(self._description["field"]))
            == self._description["on"]
        )

    async def _set(self, value):
        try:
            await self._device.set_fix_time_status(
                value == self._description["on"]
            )
        except PanasonicApiError as err:
            _LOGGER.error("Timer switch command failed: %s", err)
            return
        data = dict(self.coordinator.data or {})
        section = dict(data.get(self._description["source"]) or {})
        section[self._description["field"]] = value
        data[self._description["source"]] = section
        self.coordinator.async_set_updated_data(data)

    async def async_turn_on(self, **kwargs):
        await self._set(self._description["on"])

    async def async_turn_off(self, **kwargs):
        await self._set(self._description["off"])
