"""Climate entity for Panasonic Smart China ZY air conditioners."""

from __future__ import annotations

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_AUTO,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PanasonicApiError
from .const import CONF_SENSOR_ID, DOMAIN, FAN_MUTE, NO_EXTERNAL_SENSOR
from .helpers import device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device = runtime.get("device")
    coordinator = runtime.get("status")
    if not device or not coordinator:
        return
    async_add_entities([PanasonicACEntity(coordinator, device, entry)])


class PanasonicACEntity(CoordinatorEntity, ClimateEntity):
    """Main AC control; state is pushed by the shared coordinator."""

    def __init__(self, coordinator, device, entry):
        super().__init__(coordinator)
        self._hass = coordinator.hass
        self._device = device
        self._sensor_id = entry.data.get(CONF_SENSOR_ID, NO_EXTERNAL_SENSOR)
        self._profile = device.profile
        self._attr_name = entry.title
        self._attr_unique_id = f"panasonic_{device.device_id}"
        self._attr_device_info = device_info(device, entry.title)

        self._hvac_map = self._profile.get("hvac_mapping", {})
        self._fan_map = self._profile.get("fan_mapping", {})
        self._fan_overrides = self._profile.get("fan_payload_overrides", {})
        self._vertical_swing_map = self._profile.get("vertical_swing_mapping", {})
        self._horizontal_swing_map = self._profile.get("horizontal_swing_mapping", {})

        self._is_on = False
        self._hvac_mode = next(iter(self._hvac_map.keys()), HVACMode.COOL)
        self._current_temperature = None
        self._target_temperature = 26.0
        self._fan_mode = FAN_AUTO
        self._swing_mode = self._first_mode(self._vertical_swing_map)
        self._swing_horizontal_mode = self._first_mode(self._horizontal_swing_map)

    @staticmethod
    def _first_mode(mode_map):
        return next(iter(mode_map.keys()), None)

    @staticmethod
    def _mode_from_value(mode_map, value, current_mode=None):
        for name, mapped_value in mode_map.items():
            if mapped_value == value:
                return name
        return current_mode or PanasonicACEntity._first_mode(mode_map)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._update_local_state(self.coordinator.data or {})

    def _handle_coordinator_update(self):
        self._update_local_state(self.coordinator.data or {})
        self.async_write_ha_state()

    @property
    def supported_features(self):
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.FAN_MODE
        )
        if self._vertical_swing_map:
            features |= ClimateEntityFeature.SWING_MODE
        horizontal_feature = getattr(ClimateEntityFeature, "SWING_HORIZONTAL_MODE", 0)
        if self._horizontal_swing_map and horizontal_feature:
            features |= horizontal_feature
        return features

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def min_temp(self):
        return 16.0

    @property
    def max_temp(self):
        return 30.0

    @property
    def target_temperature_step(self):
        return 1.0

    @property
    def hvac_modes(self):
        return [HVACMode.OFF, *self._hvac_map.keys()]

    @property
    def hvac_mode(self):
        if not self._is_on:
            return HVACMode.OFF
        return self._hvac_mode

    @property
    def fan_modes(self):
        modes = list(self._fan_map.keys())
        for mode in self._fan_overrides:
            if mode not in modes:
                modes.append(mode)
        return modes

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def swing_modes(self):
        return list(self._vertical_swing_map.keys())

    @property
    def swing_mode(self):
        return self._swing_mode

    @property
    def swing_horizontal_modes(self):
        return list(self._horizontal_swing_map.keys())

    @property
    def swing_horizontal_mode(self):
        return self._swing_horizontal_mode

    @property
    def current_temperature(self):
        state = None
        if self._sensor_id and self._sensor_id != NO_EXTERNAL_SENSOR:
            state = self._hass.states.get(self._sensor_id)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                return float(state.state)
            except ValueError:
                pass
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    def _update_local_state(self, res):
        self._is_on = self._device.is_on(res)
        self._target_temperature = self._device.read_target_temperature(
            res, self._target_temperature
        )
        self._current_temperature = self._device.read_current_temperature(res)
        self._hvac_mode = self._mode_from_value(
            self._hvac_map, res.get("runMode"), self._hvac_mode
        )
        if (
            res.get("windSet") == 10
            and res.get("muteMode") == 1
            and FAN_MUTE in self._fan_overrides
        ):
            self._fan_mode = FAN_MUTE
        else:
            self._fan_mode = self._mode_from_value(
                self._fan_map, res.get("windSet"), self._fan_mode
            )
        self._swing_mode = self._mode_from_value(
            self._vertical_swing_map, res.get("portraitWindSet"), self._swing_mode
        )
        self._swing_horizontal_mode = self._mode_from_value(
            self._horizontal_swing_map,
            res.get("orientationWindSet"),
            self._swing_horizontal_mode,
        )

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            await self._send_command({"runStatus": self._device.power_off_value})
            return
        p_mode = self._hvac_map.get(hvac_mode)
        if p_mode is None:
            _LOGGER.warning("Unsupported HVAC mode requested: %s", hvac_mode)
            return
        await self._send_command(
            {"runStatus": self._device.power_on_value, "runMode": p_mode}
        )

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self._send_command(self._device.build_temperature_payload(temp))

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode in self._fan_overrides:
            changes = self._fan_overrides[fan_mode].copy()
        else:
            val = self._fan_map.get(fan_mode)
            if val is None:
                _LOGGER.warning("Unsupported fan mode requested: %s", fan_mode)
                return
            changes = {"windSet": val}
            if FAN_MUTE in self._fan_overrides:
                changes["muteMode"] = 0
        await self._send_command(changes)

    async def async_set_swing_mode(self, swing_mode):
        val = self._vertical_swing_map.get(swing_mode)
        if val is None:
            _LOGGER.warning("Unsupported vertical swing mode: %s", swing_mode)
            return
        await self._send_command({"portraitWindSet": val})

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode):
        val = self._horizontal_swing_map.get(swing_horizontal_mode)
        if val is None:
            _LOGGER.warning(
                "Unsupported horizontal swing mode: %s", swing_horizontal_mode
            )
            return
        await self._send_command({"orientationWindSet": val})

    async def async_turn_on(self):
        await self._send_command({"runStatus": self._device.power_on_value})

    async def async_turn_off(self):
        await self._send_command({"runStatus": self._device.power_off_value})

    async def _send_command(self, changes):
        try:
            await self._device.send_command(changes)
        except PanasonicApiError as err:
            _LOGGER.error("Climate command %s failed: %s", changes, err)
