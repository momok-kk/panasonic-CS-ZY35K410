"""Select entities for Panasonic AirconCommon devices (swing position)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import async_run_command
from .const import DOMAIN, icon_for
from .helpers import ZY35K410Entity, as_int, capability_ok, device_info, resolve_key


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    coordinator = runtime.get("status")
    if not device or not coordinator:
        return
    entities = [
        PanasonicRemoteSelect(coordinator, device, entry, description)
        for description in device.profile.get("remote_selects", [])
    ]
    async_add_entities(entities)


class PanasonicRemoteSelect(ZY35K410Entity, CoordinatorEntity, SelectEntity):
    """A labelled status field with a label -> protocol value map."""

    def __init__(self, coordinator, device, entry, description):
        super().__init__(coordinator)
        self._device = device
        self._key = description["key"]
        self._aliases = tuple(description.get("aliases", ()))
        self._capability = description.get("capability")
        self._options_map = description["options"]
        self._value_to_option = {
            value: option for option, value in self._options_map.items()
        }
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = f"panasonic_{device.device_id}_{self._key}_select"
        self._attr_options = list(self._options_map.keys())
        # Some selects duplicate the climate entity's swing mode.  They are
        # registered but disabled by default so the UI stays uncluttered while
        # the capability remains available from the entity registry.
        self._attr_entity_registry_enabled_default = description.get(
            "enabled_default", True
        )
        self._attr_icon = icon_for("select", self._key)
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
    def current_option(self):
        return self._value_to_option.get(as_int(self._data.get(self._active_key)))

    async def async_select_option(self, option):
        value = self._options_map.get(option)
        if value is None:
            return
        await async_run_command(
            self._device,
            self._device.send_command({self._active_key: value}),
            f"设置扫风位置 {self._key}",
        )
