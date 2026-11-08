"""Sensors from the status bean and the electricity-statistics endpoints."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ERROR_TEXT,
    TIMER_ACTIONS,
    TIMER_RUN_MODES,
    TIMER_WEEK_NAMES,
    icon_for,
)
from .helpers import as_int, device_info, sum_array


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
        timer_description = device.profile.get("timer_sensor")
        if timer_description:
            entities.append(
                PanasonicTimerSensor(aux, device, entry, timer_description)
            )
        for key, entity_class in (
            ("hourly_sensor", PanasonicHourlyEnergySensor),
            ("device_info_sensor", PanasonicDeviceInfoSensor),
        ):
            description = device.profile.get(key)
            if description:
                entities.append(entity_class(aux, device, entry, description))
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
        self._attr_suggested_display_precision = description.get(
            "suggested_display_precision"
        )
        self._attr_icon = icon_for("sensor", description["key"])
        self._attr_entity_registry_enabled_default = description.get(
            "enabled_default", True
        )


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

    @property
    def extra_state_attributes(self):
        """Attach related read-only fields without creating more entities."""
        attributes = self._description.get("attributes")
        if not attributes:
            return None
        data = self.coordinator.data or {}
        result = {}
        for item in attributes:
            section = data.get(item["source"])
            if isinstance(section, dict) and item["field"] in section:
                result[item["name"]] = section[item["field"]]
        return result or None


class PanasonicHourlyEnergySensor(_BaseSensor):
    """24-hour power/cost curve from ACGetAirconDayGraphInfo.

    State is the current clock hour's consumption; the full curve is exposed
    as attributes.  255 in setTemperature means "no reading".
    """

    @property
    def _section(self):
        section = (self.coordinator.data or {}).get(self._description["source"])
        return section if isinstance(section, dict) else {}

    @property
    def available(self):
        power = self._section.get("power")
        return (
            self.coordinator.last_update_success
            and isinstance(power, list)
            and len(power) >= 24
        )

    @property
    def native_value(self):
        power = self._section.get("power")
        hour = dt_util.now().hour
        if not isinstance(power, list) or hour >= len(power):
            return None
        try:
            return float(power[hour])
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self):
        section = self._section
        power = section.get("power")
        if not isinstance(power, list) or not power:
            return None
        attributes = {
            "date": dt_util.now().strftime("%Y-%m-%d"),
            "hourly_power_kwh": power,
            "hourly_cost_cny": section.get("cost"),
            "hourly_set_temperature": section.get("setTemperature"),
            "today_total_kwh": sum_array(power),
        }
        numerics = [
            (index, float(value))
            for index, value in enumerate(power)
            if isinstance(value, (int, float))
        ]
        if numerics:
            peak_index, peak_value = max(numerics, key=lambda pair: pair[1])
            if peak_value > 0:
                attributes["peak_hour"] = f"{peak_index:02d}:00"
                attributes["peak_kwh"] = peak_value
        return attributes


class PanasonicDeviceInfoSensor(_BaseSensor):
    """Firmware version plus cached device metadata and official help links."""

    @property
    def _section(self):
        section = (self.coordinator.data or {}).get(self._description["source"])
        return section if isinstance(section, dict) else {}

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            and "version" in self._section
        )

    @property
    def native_value(self):
        return self._section.get("version")

    @property
    def extra_state_attributes(self):
        section = self._section
        if not section:
            return None
        return {
            key: value for key, value in section.items() if key != "version"
        } or None


class PanasonicTimerSensor(_BaseSensor):
    """Read-only view of the device's weekly timer schedule.

    State is the number of configured timer entries; the parsed schedule and
    the next upcoming entry are exposed as attributes.  Editing the schedule
    itself is intentionally not offered: ACSetAirconTimerNewProtocol prunes
    fields per capability flag and a malformed write would silently overwrite
    the schedule configured in the official App.
    """

    def _parse(self):
        timer = (self.coordinator.data or {}).get(self._description["source"])
        if not isinstance(timer, dict):
            return None
        week_list = timer.get("weekList")
        if not isinstance(week_list, list):
            return None

        items = []
        for index, day in enumerate(week_list):
            if not isinstance(day, dict):
                continue
            # Use the explicit week number instead of the array position.
            # AirconCommon's weekList carries "week": 1..7; the App's Chinese
            # week starts on Monday, i.e. ISO 1=Monday ... 7=Sunday, matching
            # TIMER_WEEK_NAMES and dt_util.now().isoweekday().  The raw value
            # and its source stay in the attributes so this encoding can be
            # checked against a real schedule if the cloud ever changes it.
            week_raw = as_int(day.get("week"))
            if week_raw is not None and 1 <= week_raw <= 7:
                week_index = week_raw - 1
                week_source = "week_field"
            else:
                week_index = index
                week_source = "list_index"
            week_label = (
                TIMER_WEEK_NAMES[week_index]
                if week_index < len(TIMER_WEEK_NAMES)
                else str(week_raw if week_raw is not None else index + 1)
            )
            for raw in day.get("timerList") or []:
                if not isinstance(raw, dict):
                    continue
                minutes = as_int(raw.get("startTime"))
                if minutes is None or minutes < 0:
                    continue
                items.append({
                    "week": week_raw if week_raw is not None else index + 1,
                    "week_raw": week_raw,
                    "week_source": week_source,
                    "week_label": week_label,
                    "week_index": week_index,
                    "time": f"{minutes // 60:02d}:{minutes % 60:02d}",
                    "minute_of_day": minutes,
                    "action": TIMER_ACTIONS.get(
                        as_int(raw.get("runStatus")), "未知"
                    ),
                    "mode": TIMER_RUN_MODES.get(
                        as_int(raw.get("runMode")), "未知"
                    ),
                    "temperature": as_int(raw.get("setTemperature")),
                    "nanoe": bool(as_int(raw.get("nanoe"))),
                    "wind_set": as_int(raw.get("windSet")),
                })
        items.sort(key=lambda item: (item["week_index"], item["minute_of_day"]))
        return items

    @property
    def available(self):
        return self.coordinator.last_update_success and self._parse() is not None

    @property
    def native_value(self):
        items = self._parse()
        return len(items) if items is not None else None

    @property
    def extra_state_attributes(self):
        items = self._parse()
        if items is None:
            return None
        data = self.coordinator.data or {}
        status = data.get("timer_status")
        enabled = (
            as_int(status.get("fixTimeStatus")) == 1
            if isinstance(status, dict)
            else False
        )

        now = dt_util.now()
        # week_index is 0=Monday, matching the ISO week numbers in weekList.
        today = now.isoweekday() - 1
        now_minutes = now.hour * 60 + now.minute
        next_item = None
        for offset in range(8):
            week_index = (today + offset) % 7
            for item in items:
                if item["week_index"] != week_index:
                    continue
                if offset == 0 and item["minute_of_day"] <= now_minutes:
                    continue
                next_item = dict(item)
                next_item["days_ahead"] = offset
                break
            if next_item:
                break

        return {
            "enabled": enabled,
            "schedule": items,
            "next_timer": next_item,
        }
