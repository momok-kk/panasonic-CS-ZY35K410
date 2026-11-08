"""One-shot remote buttons (power toggle, filter reset, clean reset)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .api import async_run_command
from .const import DOMAIN, icon_for
from .helpers import ZY35K410Entity, device_info


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    coordinator = runtime.get("status")
    if not device or not coordinator:
        return
    entities = [
        PanasonicRemoteButton(coordinator, device, entry, description)
        for description in device.profile.get("remote_buttons", [])
    ]
    async_add_entities(entities)


class PanasonicRemoteButton(ZY35K410Entity, ButtonEntity):
    """Stateless command button; availability follows the shared coordinator."""

    def __init__(self, coordinator, device, entry, description):
        self._coordinator = coordinator
        self._device = device
        self._key = description["key"]
        self._press_value = description.get("press", 1)
        self._toggle = description.get("toggle", False)
        self._payload = description.get("payload")
        self._attr_name = f"{entry.title} {description['name']}"
        self._attr_unique_id = f"panasonic_{device.device_id}_{self._key}_button"
        self._attr_device_info = device_info(device, entry.title)
        self._attr_icon = icon_for("button", self._key)

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return self._coordinator.last_update_success

    async def async_press(self):
        if self._payload:
            await self._send(dict(self._payload))
            return
        if not self._toggle:
            await self._send({self._key: self._press_value})
            return
        params = self._coordinator.data or {}
        value = (
            self._device.power_off_value
            if self._device.is_on(params)
            else self._device.power_on_value
        )
        await self._send({self._key: value})

    async def _send(self, changes):
        await async_run_command(
            self._device,
            self._device.send_command(changes),
            f"按钮 {self._key}",
        )
