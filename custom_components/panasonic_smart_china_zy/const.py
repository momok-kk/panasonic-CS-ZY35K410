"""Constants and device profiles for the Panasonic Smart China ZY integration.

The CS-ZY35K410 uses the 2024 "AirconCommon" new protocol, reverse engineered
from the official web panel at:

    https://app.psmartcloud.com/ca/cn/0900/AirconCommon/

Its control endpoint is ACDevSetStatusNewProtocol.  Status is still read from
ACDevGetStatusInfoAW.  Feature availability is gated by "*Ex" capability flags
in the status bean, exactly as the official web app does.
"""

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

CONF_USR_ID = "usrId"
CONF_DEVICE_ID = "deviceId"
CONF_TOKEN = "token"
CONF_SSID = "SSID"
CONF_SENSOR_ID = "sensor_entity_id"
CONF_CONTROLLER_MODEL = "controller_model"

NO_EXTERNAL_SENSOR = ""

URL_BASE = "https://app.psmartcloud.com/App"
URL_SET = f"{URL_BASE}/ACDevSetStatusInfoAW"
URL_GET = f"{URL_BASE}/ACDevGetStatusInfoAW"

# Read-only auxiliary endpoints (official AirconCommon web app).
ENDPOINT_ELEC_TODAY = "ACGetElectricChargeTodayInfo"
ENDPOINT_ELEC_MONTH = "ACGetElectricChargeDaylyInfo"
ENDPOINT_ELEC_YEAR = "ACGetAirconYearGraphInfo"
ENDPOINT_MODE_TEMP = "ACGetModeTempInfo"

# Business error codes that mean "session expired / re-authenticate".
# Note: the cloud returns either a top-level errorCode or a nested
# {"error": {"code": 4102}} object.  Both shapes are handled in api.py.
AUTH_ERROR_CODES = {"3003", "3004", "403", "4102"}
SUCCESS_ERROR_CODES = {None, "", 0, "0", "0000"}

FAN_MIN = "Min"
FAN_MAX = "Max"
FAN_MUTE = "Quiet"

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

# Writable fields of the old CZ-RD501DW2 ducted-controller protocol.
# Kept verbatim so the legacy profile keeps working.
LEGACY_SAFE_KEYS = [
    "runMode", "forceRunning", "runStatus", "remoteForbidMode", "remoteMode",
    "setTemperature", "setHumidity", "windSet", "exchangeWindSet",
    "portraitWindSet", "orientationWindSet", "nanoeG", "nanoe", "ecoMode",
    "muteMode", "filterReset", "powerful", "powerfulMode", "thermoMode",
    "buzzer", "autoRunMode", "unusualPresent", "runForbidden",
    "inhaleTemperature", "outsideTemperature", "insideHumidity", "alarmCode",
    "nanoeModule", "TDWindModule", "airSupply", "autoAi", "cleanMode",
    "debugMode", "defrost", "detectMode", "displaySet", "douleTemperature",
    "errorStatus", "eClean", "eeconfirm", "electricCurrent", "energySaving",
    "enventSet", "errorCode", "errorCodeW", "feelMode", "functionMode",
    "gasValue", "hcount", "heatExchange", "heatPump", "heatup", "humidClean",
    "humiditySet", "insideTemperature", "ionMode", "lamp", "mcount", "mildew",
    "newair", "notice", "pm2p5Clean", "preMode", "preTemperature", "quickMode",
    "rader", "ratedPower", "selfClean", "selfNanoe", "selfNanoeMode",
    "selfcleanReset", "showMode", "sleep", "sleepCurve", "sleepMode",
    "temperature", "temperatureSet", "temperatureUnit", "tempMode",
    "timerSetting", "totalElectricity", "waterClean", "windDirection",
    "windMethod", "windMode", "windSwing",
]

# Backwards-compatible name; api.py now uses the per-profile "safe_keys".
SAFE_KEYS = LEGACY_SAFE_KEYS

# Exactly the PARAMS bean the AirconCommon web app posts to
# ACDevSetStatusNewProtocol.  Capability-only fields and read-only values are
# deliberately excluded so read-modify-write never echoes them back.
AIRCONCOMMON_SAFE_KEYS = [
    "buzzer", "runStatus", "setTemperature", "runMode", "windSet",
    "portraitWindSet", "orientationWindSet", "cleanSet", "ervWind",
    "ervMode", "scene", "cool", "highCool", "elecHeat", "lamp", "uvc",
    "voiceSet", "spaceClean",
]

# Status-bean sensors (15s coordinator).
STATUS_SENSORS = [
    {
        "key": "inhale_temperature",
        "name": "回风温度",
        "field": "inhaleTemperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "temperature": True,
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
]

BINARY_SENSORS = [
    {
        "key": "alarm", "name": "故障", "field": "alarmCode", "nonzero": True,
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    {
        "key": "filter_due", "name": "滤网需更换", "field": "filterReset",
        "equals": 1,
    },
    {
        "key": "fresh_air_running", "name": "新风运行", "field": "ervMode",
        "equals": 66, "erv_running": True,
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
]

# Known alarm codes reported by the cloud (official web app).
ERROR_TEXT = {
    "0000": "正常",
    "OFFLINE": "本体离线",
    "07DF": "碰撞开关不工作，请确认",
}

SUPPORTED_CONTROLLERS = {
    "CZ-RD501DW2": {
        "name": "Panasonic ducted controller CZ-RD501DW2",
        "safe_keys": LEGACY_SAFE_KEYS,
        "temp_scale": 2,
        "temperature_keys": ["setTemperature"],
        "current_temperature_keys": [
            "inhaleTemperature", "insideTemperature", "preTemperature",
        ],
        "power_on_value": 1,
        "power_off_value": 0,
        "hvac_mapping": {
            HVACMode.COOL: 3,
            HVACMode.HEAT: 4,
            HVACMode.DRY: 2,
            HVACMode.AUTO: 0,
        },
        "fan_mapping": {
            FAN_AUTO: 10,
            FAN_MIN: 3,
            FAN_LOW: 4,
            FAN_MEDIUM: 5,
            FAN_HIGH: 6,
            FAN_MAX: 7,
        },
        "fan_payload_overrides": {
            FAN_MUTE: {"windSet": 10, "muteMode": 1}
        },
        "vertical_swing_mapping": {SWING_AUTO: 15},
        "horizontal_swing_mapping": {SWING_AUTO: 13},
        "remote_switches": [
            {"key": "runStatus", "name": "Power", "on": 1, "off": 0},
            {"key": "muteMode", "name": "Quiet", "on": 1, "off": 0},
            {"key": "powerful", "name": "Powerful", "on": 1, "off": 0},
            {"key": "ecoMode", "name": "Eco", "on": 1, "off": 0},
            {"key": "nanoe", "name": "Nanoe", "on": 1, "off": 0},
            {"key": "nanoeG", "name": "Nanoe-G", "on": 1, "off": 0},
            {"key": "buzzer", "name": "Buzzer", "on": 1, "off": 0},
        ],
        "remote_buttons": [
            {"key": "runStatus", "name": "Power Toggle", "toggle": True},
            {"key": "filterReset", "name": "Filter Reset", "press": 1},
        ],
        "remote_selects": [],
        "status_sensors": [],
        "aux_sensors": [],
        "binary_sensors": [],
    },
    "CS-ZY35K410": {
        "name": "Panasonic CS-ZY35K410 (AirconCommon)",
        "set_url": f"{URL_BASE}/ACDevSetStatusNewProtocol",
        "safe_keys": AIRCONCOMMON_SAFE_KEYS,
        # Community reports disagree on the temperature scale (1 vs 2).
        # api.py auto-detects from the live value; this is the default.
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
        "fan_payload_overrides": {},
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
                "capability": "highCoolEx", "name": "强劲制冷",
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
            # lamp is inverted by the AirconCommon protocol: 0 = light ON.
            {
                "key": "lamp", "capability": "lampEx", "name": "显示灯",
                "on": 0, "off": 1,
            },
            {
                "key": "spaceClean", "capability": "spaceCleanEx",
                "name": "空间净化", "on": 1, "off": 0,
            },
            {"key": "buzzer", "name": "蜂鸣提示音", "on": 1, "off": 0},
            {
                "key": "uvc", "capability": "uvcEx", "name": "UVC 除菌",
                "on": 1, "off": 0,
            },
            {
                "key": "voiceSet", "capability": "voiceSetEx",
                "name": "语音提示", "on": 1, "off": 0,
            },
        ],
        "remote_buttons": [
            {"key": "runStatus", "name": "电源切换", "toggle": True},
            {"key": "filterReset", "name": "滤网复位", "press": 1},
            {"key": "selfcleanReset", "name": "自清洁复位", "press": 1},
        ],
        "remote_selects": [
            {
                "key": "scene", "name": "场景",
                "options": {"关闭": 64, "怡静风": 65, "超远风": 66, "环抱风": 67},
            },
            {
                "key": "portraitWindSet", "name": "上下扫风位置",
                "options": {
                    "自动": 70, "方向1": 65, "方向2": 68, "方向3": 67,
                    "方向4": 69, "方向5": 66,
                },
            },
            {
                "key": "orientationWindSet", "name": "左右扫风位置",
                "capability": "leftType",
                "options": {
                    "自动": 64, "最左": 66, "偏左": 108, "正对": 67,
                    "偏右": 87, "最右": 65,
                },
            },
            {
                "key": "displaySet", "aliases": ["lamp"], "name": "显示灯模式",
                "options": {"关": 1, "开": 0},
            },
            {
                "key": "sleepMode", "name": "睡眠模式",
                "options": {"关闭": 0, "模式 1": 1, "模式 2": 2, "模式 3": 3},
            },
            {
                "key": "powerfulMode", "name": "强劲模式",
                "options": {"关闭": 0, "模式 1": 1, "模式 2": 2},
            },
            {
                "key": "cleanMode", "name": "清洁模式",
                "options": {"关闭": 0, "模式 1": 1, "模式 2": 2, "模式 3": 3},
            },
        ],
        "status_sensors": STATUS_SENSORS,
        "aux_sensors": AUX_SENSORS,
        "binary_sensors": BINARY_SENSORS,
    },
}
