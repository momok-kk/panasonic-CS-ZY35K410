"""Constants and the device profile for the Panasonic CS-ZY35K410 integration.

This integration supports exactly ONE model: the CS-ZY35K410 (2024
"AirconCommon" protocol), reverse engineered from the official web panel at:

    https://app.psmartcloud.com/ca/cn/0900/AirconCommon/

Status: ACDevGetStatusInfoAW; control: ACDevSetStatusNewProtocol (incremental).
Feature availability is gated by "*Ex" capability flags in the status bean,
exactly as the official web app does.  No other controller model, protocol or
device category is supported.
"""

import base64

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfTime

DOMAIN = "panasonic_smart_china_zy"

DEVICE_MODEL = "CS-ZY35K410"
# deviceId is MAC_CATEGORY_MODEL, e.g. B812DAC81168_0900_CS-ZY35K410.
DEVICE_CATEGORY = "0900"

CONF_USR_ID = "usrId"
CONF_DEVICE_ID = "deviceId"
CONF_TOKEN = "token"
CONF_SSID = "SSID"
CONF_SENSOR_ID = "sensor_entity_id"

NO_EXTERNAL_SENSOR = ""

URL_BASE = "https://app.psmartcloud.com/App"
URL_SET = f"{URL_BASE}/ACDevSetStatusNewProtocol"
URL_GET = f"{URL_BASE}/ACDevGetStatusInfoAW"

# Read-only auxiliary endpoints (official AirconCommon web app).
ENDPOINT_ELEC_TODAY = "ACGetElectricChargeTodayInfo"
ENDPOINT_ELEC_MONTH = "ACGetElectricChargeDaylyInfo"
ENDPOINT_ELEC_YEAR = "ACGetAirconYearGraphInfo"
ENDPOINT_MODE_TEMP = "ACGetModeTempInfo"
ENDPOINT_CHARGE_GET = "ACGetAirconElectricChargeInfo"
ENDPOINT_CHARGE_SET = "ACSetAirconElectricChargeInfo"

# Weekly timer ("fix time") endpoints from the official AirconCommon web app.
# ACSetAirconTimerNewProtocol (schedule editing) is deliberately NOT called.
ENDPOINT_TIMER_GET = "ACGetAirconTimerNewProtocol"
ENDPOINT_FIX_STATUS_GET = "ACGetAirconFixTimeStatusInfo"
ENDPOINT_FIX_STATUS_SET = "ACSetAirconFixTimeStatusInfo"

# Additional read-only endpoints found in the official AirconCommon bundles
# and verified against a live CS-ZY35K410 (2026-11-06).  These feed the
# 60s auxiliary coordinator, except the slow-changing device_meta group.
ENDPOINT_DAY_GRAPH = "ACGetAirconDayGraphInfo"
ENDPOINT_MONTH_GRAPH = "ACGetAirconMonthGraphInfo"
ENDPOINT_FW_VERSION = "ACDevGetFwVersion"
ENDPOINT_OTA_PERCENT = "ACDevGetOTAPercent"
ENDPOINT_HELP_ERROR = "ACDevGetHelpAndErrorInfo"
ENDPOINT_MASTER_USER = "ACDevGetMasterUser"
ENDPOINT_DEV_NAME = "DevGetName"

# Firmware/help/master-user data barely changes; cache it instead of hitting
# five extra cloud endpoints on every 60s auxiliary poll.
DEVICE_META_TTL = 1800

# The official web app sends buzzer=65 with EVERY command (BUZZER:{ON:65}).
# It is a "beep on this command" marker, not a persistent toggle; the status
# bean merely echoes a sticky value.  Do not expose it as a switch.
COMMAND_BUZZER = 65

# One-shot command markers, not persistent device state.  Never merge these
# into the optimistic status cache: filterReset=1 would briefly make the
# "filter due" binary sensor read as on until the next 15s poll.
TRANSIENT_COMMAND_KEYS = {"filter", "filterReset"}

# Business error codes that mean "session expired / re-authenticate".
# Note: the cloud returns either a top-level errorCode or a nested
# {"error": {"code": 4102}} object.  Both shapes are handled in api.py.
AUTH_ERROR_CODES = {"3003", "3004", "403", "4102"}
SUCCESS_ERROR_CODES = {None, "", 0, "0", "0000"}

FAN_MIN = "Min"
FAN_MAX = "Max"

SWING_AUTO = "Auto"
SWING_UP = "Up"
SWING_UP_MIDDLE = "Up Middle"
SWING_MIDDLE = "Middle"
SWING_DOWN_MIDDLE = "Down Middle"
SWING_DOWN = "Down"
SWING_LEFT = "Left"
SWING_LEFT_MIDDLE = "Left Middle"
SWING_CENTER = "Center"
SWING_RIGHT_MIDDLE = "Right Middle"
SWING_RIGHT = "Right"

# ACDevSetStatusNewProtocol is incremental: a command carries only the
# changed fields.  No read-modify-write whitelist is needed.

# Status-bean sensors (15s coordinator).
# inhaleTemperature is a sentinel (128) on the CS-ZY35K410: the unit never
# reports a real return-air temperature, so the sensor would stay "unknown"
# forever.  The definition is kept but disabled by default; it can be
# re-enabled from the HA entity registry if needed.
STATUS_SENSORS = [
    {
        "key": "inhale_temperature",
        "name": "回风温度",
        "field": "inhaleTemperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "temperature": True,
        "enabled_default": False,
    },
    {
        "key": "alarm_code",
        "name": "故障码",
        "field": "alarmCode",
        "kind": "text",
    },
]

# Electricity / cost sensors (60s auxiliary coordinator).
AUX_SENSORS = [
    {
        "key": "energy_today", "name": "今日用电量", "field": "powerToday",
        "source": "electricity_today", "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    {
        "key": "duration_today", "name": "今日运行时长", "field": "durationToday",
        "source": "electricity_today", "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "cost_today", "name": "今日费用", "field": "costToday",
        "source": "electricity_today", "unit": "CNY",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.TOTAL,
    },
    {
        "key": "energy_month", "name": "本月用电量",
        "field": "powerSelectMonth", "source": "electricity_month",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "sum_array": True,
        "attributes": [
            {"name": "daily_power_kwh", "source": "month_graph",
             "field": "power"},
            {"name": "daily_cost_cny", "source": "month_graph",
             "field": "cost"},
        ],
    },
    {
        "key": "duration_month", "name": "本月运行时长",
        "field": "durationSelectMonth", "source": "electricity_month",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.MEASUREMENT,
        "sum_array": True,
    },
    {
        "key": "cost_month", "name": "本月费用", "field": "costSelectMonth",
        "source": "electricity_month", "unit": "CNY",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.TOTAL,
        "sum_array": True,
    },
    {
        "key": "energy_year", "name": "本年用电量", "field": "power",
        "source": "electricity_year", "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "sum_array": True,
    },
    {
        "key": "cost_year", "name": "本年费用", "field": "cost",
        "source": "electricity_year", "unit": "CNY",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.TOTAL,
        "sum_array": True,
    },
    {
        "key": "mode_temp_cool", "name": "制冷记忆温度",
        "field": "coldModeTemp", "source": "mode_temp",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        # ACGetModeTempInfo also returns remembered fan speeds.  Expose them
        # as attributes instead of four more entities.
        "attributes": [
            {"name": "wind_set", "source": "mode_temp",
             "field": "coldModeWind"},
            {"name": "nanoe_wind_set", "source": "mode_temp",
             "field": "nanoeModeWind"},
        ],
    },
    {
        "key": "mode_temp_heat", "name": "制暖记忆温度",
        "field": "warmModeTemp", "source": "mode_temp",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "attributes": [
            {"name": "wind_set", "source": "mode_temp",
             "field": "warmModeWind"},
        ],
    },
    {
        "key": "mode_temp_dry", "name": "抽湿记忆温度",
        "field": "wetModeTemp", "source": "mode_temp",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "attributes": [
            {"name": "wind_set", "source": "mode_temp",
             "field": "wetModeWind"},
        ],
    },
]

# Two new read-only entities for the extra cloud data.  Everything else from
# the probe is attached as attributes to existing entities so the entity
# count stays low.
HOURLY_ENERGY_SENSOR = {
    "key": "hourly_energy",
    "name": "逐时用电",
    "source": "hourly",
    "unit": UnitOfEnergy.KILO_WATT_HOUR,
    "device_class": SensorDeviceClass.ENERGY,
    # State is the current clock hour's consumption - an interval delta, not a
    # running total - so it must not declare a statistics state class.  HA
    # rejects energy + state_class=measurement at runtime ("impossible
    # considering device class"), and total/total_increasing would fabricate a
    # cumulative series out of per-hour values.  Today/month/year totals are
    # separate sensors and do carry total_increasing.
}

DEVICE_INFO_SENSOR = {
    "key": "device_info",
    "name": "设备信息",
    "source": "device_meta",
    "field": "version",
    "kind": "text",
}

# Writable electricity price (yuan/kWh) from ACGet/SetAirconElectricChargeInfo.
CHARGE_NUMBER = {
    "key": "electricity_charge",
    "name": "电价",
    "source": "electricity_charge",
    "field": "charge",
    "unit": "CNY/kWh",
    "min": 0.0,
    "max": 5.0,
    "step": 0.01,
}

# Weekly timer, verified against a live CS-ZY35K410 (2026-11-06).
#   ACGetAirconTimerNewProtocol -> {"weekList": [{"week": 1..7,
#       "timerList": [{startTime, runStatus, runMode, setTemperature,
#                      windSet, portraitWindSet, orientationWindSet, nanoe}]}]}
#   startTime = 60 * hour + minute (official formatHM / getDiffTimeset).
#   ACGetAirconFixTimeStatusInfo -> {"fixTimeStatus": 0 | 1}; the official
#   TimingSettingPage onShow treats 1 as enabled and anything else as off.
# The timer lists themselves are deliberately READ-ONLY here: editing them
# requires ACSetAirconTimerNewProtocol with per-capability field pruning, and
# a wrong write would silently change the user's App schedule.
TIMER_WEEK_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
TIMER_RUN_MODES = {
    65: "自动", 66: "制冷", 67: "制暖", 68: "抽湿", 69: "送风",
}
TIMER_ACTIONS = {48: "开机", 49: "关机"}

TIMER_SWITCH = {
    "key": "fix_time_status",
    "name": "定时开关",
    "source": "timer_status",
    "field": "fixTimeStatus",
    "on": 1,
    "off": 0,
}

TIMER_SENSOR = {
    "key": "timer_schedule",
    "name": "定时计划",
    "source": "timer",
}

BINARY_SENSORS = [
    {
        "key": "alarm", "name": "故障", "field": "alarmCode", "nonzero": True,
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    {
        # "filterReset" is a one-shot reset COMMAND in the official protocol,
        # not a filter-due status bit.  The App shows its filter reminder via
        # a local timer and only for airconType==2 (this unit is 0), so this
        # flag can never become "on".  Hidden by default; re-enable manually.
        "key": "filter_due", "name": "滤网需更换", "field": "filterReset",
        "equals": 1,
        "enabled_default": False,
    },
    # "fresh_air_running" deliberately removed: live ervType=0 means this
    # CS-ZY35K410 has no fresh-air module at all.
]

# Known alarm codes reported by the cloud (official web app).
ERROR_TEXT = {
    "0000": "正常",
    "OFFLINE": "本体离线",
    "07DF": "碰撞开关不工作，请确认",
}

# Official AirconCommon RUN_MODE_COLOR table from the web app.  These are UI
# colours derived from runMode, NOT values reported by the device.  Exposed as
# climate attributes so HA cards can tint themselves like the official App.
MODE_COLOR_OFF = "#DDD"
RUN_MODE_COLORS = {
    65: ("#DDD", "灰色", "自动"),
    66: ("#4097DC", "蓝色", "制冷"),
    67: ("#FF9E18", "橙色", "制暖"),
    68: ("#00C101", "绿色", "抽湿"),
    69: ("#7056DC", "紫色", "送风"),
}

# ---------------------------------------------------------------------------
# Entity icons.  Without these HA falls back to the platform default (every
# switch shows the same generic toggle glyph).  All names below were checked
# against Material Design Icons 7.4.47, the set shipped with current HA.
# ---------------------------------------------------------------------------

# nanoe brand mark reconstructed from the official App asset: a large disc
# with a straight right edge plus a small satellite dot, in Panasonic blue.
# Embedded as a data URI so no static-path registration or external resource
# is needed; HA renders it through the entity_picture attribute.  The MDI
# molecule icon below is the fallback for third-party cards that ignore it.
#
# Canvas is 44x44 while the artwork itself is 31.6x22.  HA draws an
# entity_picture edge-to-edge inside the icon slot, so a tight canvas made the
# mark look oversized next to the 24px MDI glyphs; the surrounding padding
# brings the disc down to ~18px in a 36px tile, i.e. the same optical size as a
# neighbouring icon.  NANOE_CANVAS / NANOE_OFFSET are the tuning knobs.
NANOE_CANVAS = 44
NANOE_OFFSET = (4.2, 6)
NANOE_SVG = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {NANOE_CANVAS} {NANOE_CANVAS}"'
    f' width="{NANOE_CANVAS}" height="{NANOE_CANVAS}">'
    '<defs><clipPath id="c"><rect width="22.6" height="32"/></clipPath></defs>'
    f'<g transform="translate({NANOE_OFFSET[0]},{NANOE_OFFSET[1]})">'
    '<circle cx="13" cy="16" r="11" fill="#2C4198" clip-path="url(#c)"/>'
    '<circle cx="29" cy="16" r="4.6" fill="#2C4198"/>'
    "</g></svg>"
)
NANOE_ENTITY_PICTURE = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(NANOE_SVG.encode("utf-8")).decode("ascii")
)

ENTITY_ICONS = {
    "climate": "mdi:air-conditioner",
    "switch": {
        "runStatus": "mdi:power",
        "powerful": "mdi:fan-plus",
        "selfClean": "mdi:shimmer",
        "cool": "mdi:water-percent",
        "elecHeat": "mdi:heat-wave",
        "nanoe": "mdi:molecule",
        "sleep": "mdi:sleep",
        "lamp": "mdi:led-on",
        "spaceClean": "mdi:air-purifier",
        "fix_time_status": "mdi:timer-outline",
    },
    "button": {
        "runStatus": "mdi:power-cycle",
        "filterReset": "mdi:air-filter",
    },
    "sensor": {
        "inhale_temperature": "mdi:thermometer",
        "alarm_code": "mdi:alert-circle-outline",
        "energy_today": "mdi:flash",
        "duration_today": "mdi:clock-outline",
        "cost_today": "mdi:currency-cny",
        "energy_month": "mdi:flash",
        "duration_month": "mdi:clock-outline",
        "cost_month": "mdi:currency-cny",
        "energy_year": "mdi:flash",
        "cost_year": "mdi:currency-cny",
        "mode_temp_cool": "mdi:snowflake",
        "mode_temp_heat": "mdi:fire",
        "mode_temp_dry": "mdi:water-percent",
        "hourly_energy": "mdi:chart-timeline-variant",
        "device_info": "mdi:information-outline",
        "timer_schedule": "mdi:calendar-clock",
    },
    "binary_sensor": {
        "alarm": "mdi:alert-circle",
        "filter_due": "mdi:air-filter",
    },
    "number": {
        "electricity_charge": "mdi:currency-cny",
    },
    "select": {
        "portraitWindSet": "mdi:arrow-up-down",
        "orientationWindSet": "mdi:arrow-left-right",
    },
}

ENTITY_PICTURES = {
    "switch": {"nanoe": NANOE_ENTITY_PICTURE},
}


def icon_for(platform, key=None):
    """Return the MDI icon for an entity, or None to use the HA default."""
    section = ENTITY_ICONS.get(platform)
    return section.get(key) if isinstance(section, dict) else section


def picture_for(platform, key):
    """Return an optional entity_picture URL (currently only nanoe)."""
    return ENTITY_PICTURES.get(platform, {}).get(key)


# Feature availability is gated by the matching "*Ex" capability flag in
# commonStatus, exactly as the official web app's MorePage does.

# The one and only supported device profile.  Kept as a plain dict so all
# entity platforms stay data-driven; there is no model selection or fallback.
DEVICE_PROFILE = {
    "name": "Panasonic CS-ZY35K410 (AirconCommon)",
    # Verified live 2026-11-06: tempType=0 -> x1, 1.0 C steps.
    "temp_scale": 1,
    "temperature_keys": ["setTemperature", "temperatureSet", "temperature"],
    "current_temperature_keys": [
        "inhaleTemperature", "insideTemperature", "preTemperature",
        "douleTemperature",
    ],
    "power_on_value": 48,
    "power_off_value": 49,
    "hvac_mapping": {
        HVACMode.AUTO: 65,
        HVACMode.COOL: 66,
        HVACMode.HEAT: 67,
        HVACMode.DRY: 68,
        HVACMode.FAN_ONLY: 69,
    },
    "fan_mapping": {
        FAN_AUTO: 65,
        FAN_MIN: 49,
        FAN_LOW: 50,
        FAN_MEDIUM: 52,
        FAN_HIGH: 54,
        FAN_MAX: 55,
    },
    "horizontal_swing_mapping": {
        SWING_AUTO: 64,
        SWING_LEFT: 66,
        SWING_LEFT_MIDDLE: 108,
        SWING_CENTER: 67,
        SWING_RIGHT_MIDDLE: 87,
        SWING_RIGHT: 65,
    },
    "vertical_swing_mapping": {
        SWING_AUTO: 70,
        SWING_UP: 65,
        SWING_UP_MIDDLE: 68,
        SWING_MIDDLE: 67,
        SWING_DOWN_MIDDLE: 69,
        SWING_DOWN: 66,
    },
    # "key" is kept stable for entity unique_id compatibility; "aliases"
    # point at the real AirconCommon field when the legacy name differs.
    # "capability" is the official *Ex flag gating the feature.
    "remote_switches": [
        {"key": "runStatus", "name": "电源", "on": 48, "off": 49},
        {
            "key": "powerful", "aliases": ["highCool"],
            "capability": "highCoolEx", "name": "强劲运转",
            "on": 1, "off": 0,
        },
        {
            "key": "selfClean", "aliases": ["cleanSet"],
            "capability": "cleanSetEx", "name": "自清洁",
            "on": 1, "off": 0,
        },
        {
            "key": "cool", "capability": "coolEx", "name": "柔湿制冷",
            "on": 1, "off": 0,
        },
        {
            "key": "elecHeat", "capability": "elecHeatEx", "name": "辅热",
            "on": 1, "off": 0,
        },
        {
            "key": "nanoe", "capability": "nanoeEx", "name": "纳诺怡",
            "on": 1, "off": 0,
        },
        {
            "key": "sleep", "capability": "sleepEx", "name": "睡眠",
            "on": 1, "off": 0,
        },
    # lamp is inverted (0 = light ON), confirmed on the live unit 2026-11-06.
        {
            "key": "lamp", "capability": "lampEx", "name": "显示灯",
            "on": 0, "off": 1,
        },
        {
            "key": "spaceClean", "capability": "spaceCleanEx",
            "name": "空间净化", "on": 1, "off": 0,
        },
        # uvc / voiceSet deliberately removed: the live status bean of
        # this CS-ZY35K410 reports uvcEx=0 and voiceSetEx=0, and neither
        # "uvc" nor "voiceSet" field is present.  spaceClean IS supported
        # (spaceCleanEx=1) and stays.
        # buzzer is intentionally absent: the App sends a fixed
        # buzzer=65 on every command (COMMAND_BUZZER), it is not a toggle.
    ],
    "remote_buttons": [
        {"key": "runStatus", "name": "电源切换", "toggle": True},
        # The AirconCommon H5 resets the filter with {"filter": 1};
        # filterReset is the older field name still present in the status
        # bean.  Send both so the command is not ignored.
        {
            "key": "filterReset", "name": "滤网复位", "press": 1,
            "payload": {"filter": 1, "filterReset": 1},
        },
    ],
    # Swing position selects (restored in 2.5.1) duplicate the climate
    # entity's swing_mode / swing_horizontal_mode on the same two fields.
    # They are kept as a fallback entry point but disabled by default, so a
    # fresh install registers them in the registry without cluttering the UI.
    # `scene` stays deleted: the live status bean has neither `scene` nor a
    # `sceneEx` capability flag, so that entity was permanently unavailable.
    # displaySet / sleepMode / powerfulMode / cleanMode were removed in 2.1.0.
    "remote_selects": [
        {
            "key": "portraitWindSet", "name": "上下扫风位置",
            "enabled_default": False,
            "options": {
                "自动": 70, "方向1": 65, "方向2": 68, "方向3": 67,
                "方向4": 69, "方向5": 66,
            },
        },
        {
            "key": "orientationWindSet", "name": "左右扫风位置",
            "enabled_default": False,
            "capability": "leftType",
            "options": {
                "自动": 64, "最左": 66, "偏左": 108, "正对": 67,
                "偏右": 87, "最右": 65,
            },
        },
    ],
    "status_sensors": STATUS_SENSORS,
    "aux_sensors": AUX_SENSORS,
    "binary_sensors": BINARY_SENSORS,
    "charge_number": CHARGE_NUMBER,
    "timer_switch": TIMER_SWITCH,
    "timer_sensor": TIMER_SENSOR,
    "hourly_sensor": HOURLY_ENERGY_SENSOR,
    "device_info_sensor": DEVICE_INFO_SENSOR,
}
