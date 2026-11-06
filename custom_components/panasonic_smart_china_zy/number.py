"""Electricity price number entity for Panasonic Smart China ZY."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PanasonicApiError
from .const import DOMAIN
from .helpers import device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    aux = runtime.get("aux")
    description = (device.profile.get("charge_number") if device else None)
    if not device or not aux or not description:
        return
    async_add_entities([PanasonicChargeNumber(aux, device, entry, description)])


class PanasonicChargeNumber(CoordinatorEntity, NumberEntity):
    """Unit price used by the App's electricity-cost charts."""

    def __init__(self, coordinator, device, entry, description):
        super().__init__(coordinator)
        self._device = device
        self._description = description
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = (
            f"panasonic_{device.device_id}_{description['key']}_number"
        )
        self._attr_device_info = device_info(device, entry.title)
        self._attr_native_min_value = description["min"]
        self._attr_native_max_value = description["max"]
        self._attr_native_step = description["step"]
        self._attr_native_unit_of_measurement = description["unit"]
        self._attr_icon = "mdi:currency-cny"

    @property
    def available(self):
        section = (self.coordinator.data or {}).get(self._description["source"])
        return (
            self.coordinator.last_update_success
            and isinstance(section, dict)
            and self._description["field"] in section
        )

    @property
    def native_value(self):
        section = (self.coordinator.data or {}).get(self._description["source"])
        if not isinstance(section, dict):
            return None
        raw = section.get(self._description["field"])
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self._device.set_charge(value)
        except PanasonicApiError as err:
            _LOGGER.error("Failed to set electricity price: %s", err)
            return
        await self.coordinator.async_request_refresh()
