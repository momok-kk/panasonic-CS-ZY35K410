"""Cloud API client for Panasonic Smart China (ZY / AirconCommon)."""

from __future__ import annotations

import logging
import time

import async_timeout

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AUTH_ERROR_CODES,
    COMMAND_BUZZER,
    CONF_CONTROLLER_MODEL,
    CONF_DEVICE_ID,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    ENDPOINT_CHARGE_GET,
    ENDPOINT_CHARGE_SET,
    ENDPOINT_ELEC_MONTH,
    ENDPOINT_ELEC_TODAY,
    ENDPOINT_ELEC_YEAR,
    ENDPOINT_MODE_TEMP,
    SAFE_KEYS,
    SUCCESS_ERROR_CODES,
    SUPPORTED_CONTROLLERS,
    URL_BASE,
    URL_GET,
    URL_SET,
)
from .helpers import business_error_code, error_message

_LOGGER = logging.getLogger(__name__)

AUX_ENDPOINTS = {
    "electricity_today": (ENDPOINT_ELEC_TODAY, None),
    "electricity_month": (
        ENDPOINT_ELEC_MONTH,
        lambda: {"time": time.strftime("%Y%m%d")},
    ),
    "electricity_year": (
        ENDPOINT_ELEC_YEAR,
        lambda: {"time": time.strftime("%Y-%m-%d")},
    ),
    "electricity_charge": (ENDPOINT_CHARGE_GET, None),
    "mode_temp": (ENDPOINT_MODE_TEMP, None),
}
# Live responses (2026-11-06):
#   today  -> {powerToday, costToday, durationToday}
#   month  -> {powerSelectMonth[], costSelectMonth[], durationSelectMonth[]}
#   year   -> {power[12], cost[12], setTemperature[12], outsideTemperature[12]}
#   charge -> {charge: 0.6}
#   mode_temp -> {coldModeTemp, warmModeTemp, wetModeTemp, *ModeWind}


class PanasonicApiError(Exception):
    """Base class for cloud API failures."""


class PanasonicAuthError(PanasonicApiError):
    """Session expired or invalid; triggers HA reauthentication."""


class PanasonicSmartDevice:
    """One device: a single shared client for all of its entities."""

    def __init__(self, hass, config, name):
        self.hass = hass
        self.usr_id = config[CONF_USR_ID]
        self.device_id = config[CONF_DEVICE_ID]
        self.token = config[CONF_TOKEN]
        self.ssid = config[CONF_SSID]
        self.name = name

        model = config.get(CONF_CONTROLLER_MODEL, "CZ-RD501DW2")
        # Fall back to the device id suffix; the device name does not
        # necessarily contain the model number (e.g. "卧室空调").
        if model == "CZ-RD501DW2":
            if "CS-ZY35K410" in name.upper() or "CS-ZY35K410" in self.device_id.upper():
                model = "CS-ZY35K410"

        self.model = model
        self.profile = SUPPORTED_CONTROLLERS.get(model)
        if not self.profile:
            _LOGGER.error("Controller model %s not found, using default.", model)
            self.profile = SUPPORTED_CONTROLLERS["CZ-RD501DW2"]

        self.safe_keys = set(self.profile.get("safe_keys", SAFE_KEYS))
        self.url_get = self.profile.get("get_url", URL_GET)
        self.url_set = self.profile.get("set_url", URL_SET)
        self.last_params = {}
        self._coordinator = None
        # Set from the live setTemperature value; shared with temperature sensors.
        self.detected_temp_scale = None

    def attach_coordinator(self, coordinator):
        """Bind the shared status coordinator for push updates."""
        self._coordinator = coordinator

    @property
    def power_on_value(self):
        return self.profile.get("power_on_value", 1)

    @property
    def power_off_value(self):
        return self.profile.get("power_off_value", 0)

    @property
    def temp_scale(self):
        return self.profile.get("temp_scale", 2)

    @property
    def temperature_keys(self):
        return self.profile.get("temperature_keys", ["setTemperature"])

    @property
    def current_temperature_keys(self):
        return self.profile.get(
            "current_temperature_keys",
            ["inhaleTemperature", "insideTemperature", "preTemperature"],
        )

    def is_on(self, params):
        return params.get("runStatus") == self.power_on_value

    def read_target_temperature(self, params, fallback=26.0):
        """Read set temperature, tolerating both x1 and x2 firmware.

        Community reports disagree on the scale used by CS-ZY35K410.  A raw
        value above 45 cannot be a Celsius setpoint (max 30), so it is treated
        as x2 encoded.  The same inference is applied to writes.
        """
        for key in self.temperature_keys:
            value = params.get(key)
            if value is None:
                continue
            raw = self._as_float(value)
            if raw is None:
                continue
            scale = 2 if raw > 45 else 1
            self.detected_temp_scale = scale
            temperature = raw / scale
            if 10 <= temperature <= 40:
                return temperature
        return fallback

    def build_temperature_payload(self, temperature):
        """Write a setpoint using the scale observed in the last status read."""
        raw = self.last_params.get(self.temperature_keys[0])
        scale = 2 if raw is not None and (self._as_float(raw) or 0) > 45 else 1
        return {self.temperature_keys[0]: int(round(temperature * scale))}

    @staticmethod
    def _as_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def read_current_temperature(self, params):
        for key in self.current_temperature_keys:
            value = params.get(key)
            if value is None:
                continue
            temperature = self._as_float(value)
            if temperature is None:
                continue
            # Protocol sentinels for "no reading".
            if temperature in (127, 128, 255, 65535):
                continue
            if temperature > 80:
                temperature = temperature / 2
            if -40 <= temperature <= 80:
                return temperature
        return None

    async def _post(self, url, payload):
        """POST with the control headers, raising on business errors."""
        session = async_get_clientsession(self.hass)
        async with async_timeout.timeout(10):
            response = await session.post(
                url, json=payload, headers=self._get_headers(), ssl=False
            )
            if response.status != 200:
                text = await response.text()
                raise PanasonicApiError(f"HTTP {response.status} from {url}: {text[:200]}")
            try:
                data = await response.json()
            except Exception as err:
                text = await response.text()
                raise PanasonicApiError(f"Invalid JSON from {url}: {text[:200]}") from err

        if not isinstance(data, dict):
            raise PanasonicApiError(f"Unexpected response from {url}")

        code = business_error_code(data)
        if code not in SUCCESS_ERROR_CODES:
            code_text = str(code)
            message = error_message(data)
            if code_text in AUTH_ERROR_CODES:
                raise PanasonicAuthError(f"{message} (errorCode: {code_text})")
            raise PanasonicApiError(f"{message} (errorCode: {code_text})")
        return data

    async def fetch_status(self):
        """Fetch and cache the full status bean."""
        payload = {
            "id": 100,
            "usrId": self.usr_id,
            "deviceId": self.device_id,
            "token": self.token,
        }
        try:
            data = await self._post(self.url_get, payload)
            results = data.get("results")
            if not isinstance(results, dict) or "runStatus" not in results:
                raise PanasonicApiError("Status response missing runStatus")
            self.last_params = results
            return results
        except PanasonicAuthError:
            raise
        except Exception as err:
            _LOGGER.debug("Fetch status failed: %s", err)
            return None

    async def fetch_aux(self):
        """Fetch read-only electricity statistics (one request per section)."""
        result = {}
        for section, (path, params_builder) in AUX_ENDPOINTS.items():
            payload = {
                "id": 100,
                "usrId": self.usr_id,
                "deviceId": self.device_id,
                "token": self.token,
            }
            if params_builder:
                payload["params"] = params_builder()
            try:
                data = await self._post(f"{URL_BASE}/{path}", payload)
                section_data = data.get("results")
                result[section] = section_data if isinstance(section_data, dict) else {}
            except PanasonicAuthError:
                raise
            except Exception as err:
                _LOGGER.debug("Aux endpoint %s failed: %s", path, err)
                result[section] = {}
        return result

    async def set_charge(self, value):
        """Write the electricity price used by the App's cost charts."""
        payload = {
            "id": 200,
            "usrId": self.usr_id,
            "deviceId": self.device_id,
            "token": self.token,
            "params": {"charge": round(float(value), 2)},
        }
        return await self._post(f"{URL_BASE}/{ENDPOINT_CHARGE_SET}", payload)

    async def send_command(self, changes):
        """Read-modify-write against the freshest status, then push the update.

        Only the profile's safe writable keys are sent.  When the status read
        fails we refuse to write instead of replaying a stale cached state.
        """
        latest = await self.fetch_status()
        if not latest and self._coordinator is not None:
            latest = self._coordinator.data
        if not latest:
            raise PanasonicApiError("Cannot read current status; command refused")

        current_params = dict(latest)
        current_params.update(changes)
        params = {
            key: value
            for key, value in current_params.items()
            if key in self.safe_keys
        }
        # Explicit commands (e.g. filterReset, scene presets) are always
        # forwarded even when they are not part of the status bean whitelist.
        params.update(changes)
        # The official App stamps buzzer=65 on every NewProtocol command.
        # It is a per-command beep marker, not a persistent state to echo.
        if "NewProtocol" in self.url_set:
            params["buzzer"] = COMMAND_BUZZER

        await self._post(
            self.url_set,
            {
                "id": 200,
                "usrId": self.usr_id,
                "deviceId": self.device_id,
                "token": self.token,
                "params": params,
            },
        )

        self.last_params = current_params
        if self._coordinator is not None:
            self._coordinator.async_set_updated_data(current_params)
        return current_params

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X)",
            "xtoken": f"SSID={self.ssid}",
            "Cookie": f"SSID={self.ssid}",
            "DNT": "1",
            "Origin": "https://app.psmartcloud.com",
            "X-Requested-With": "XMLHttpRequest",
        }
