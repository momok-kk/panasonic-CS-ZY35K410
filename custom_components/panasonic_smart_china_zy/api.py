"""Cloud API client for the Panasonic CS-ZY35K410 (AirconCommon)."""

from __future__ import annotations

import logging
import time

import async_timeout

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    AUTH_ERROR_CODES,
    COMMAND_BUZZER,
    CONF_DEVICE_ID,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_META_TTL,
    DEVICE_MODEL,
    DEVICE_PROFILE,
    ENDPOINT_CHARGE_GET,
    ENDPOINT_CHARGE_SET,
    ENDPOINT_DAY_GRAPH,
    ENDPOINT_DEV_NAME,
    ENDPOINT_ELEC_MONTH,
    ENDPOINT_ELEC_TODAY,
    ENDPOINT_ELEC_YEAR,
    ENDPOINT_FIX_STATUS_GET,
    ENDPOINT_FIX_STATUS_SET,
    ENDPOINT_FW_VERSION,
    ENDPOINT_HELP_ERROR,
    ENDPOINT_MASTER_USER,
    ENDPOINT_MODE_TEMP,
    ENDPOINT_MONTH_GRAPH,
    ENDPOINT_OTA_PERCENT,
    ENDPOINT_TIMER_GET,
    SUCCESS_ERROR_CODES,
    TRANSIENT_COMMAND_KEYS,
    URL_BASE,
    URL_GET,
    URL_SET,
)
from .helpers import as_int, business_error_code, error_message

_LOGGER = logging.getLogger(__name__)

# Date parameters must follow the timezone configured in Home Assistant, not
# the container clock (which is often UTC).  The cloud reports Beijing time.
AUX_ENDPOINTS = {
    "electricity_today": (ENDPOINT_ELEC_TODAY, None),
    "electricity_month": (
        ENDPOINT_ELEC_MONTH,
        lambda: {"time": dt_util.now().strftime("%Y%m%d")},
    ),
    "electricity_year": (
        ENDPOINT_ELEC_YEAR,
        lambda: {"time": dt_util.now().strftime("%Y-%m-%d")},
    ),
    "electricity_charge": (ENDPOINT_CHARGE_GET, None),
    "mode_temp": (ENDPOINT_MODE_TEMP, None),
    "timer": (ENDPOINT_TIMER_GET, None),
    "timer_status": (ENDPOINT_FIX_STATUS_GET, None),
    "hourly": (
        ENDPOINT_DAY_GRAPH,
        lambda: {"time": dt_util.now().strftime("%Y%m%d")},
    ),
    "month_graph": (
        ENDPOINT_MONTH_GRAPH,
        lambda: {"time": dt_util.now().strftime("%Y%m")},
    ),
}
# Live responses (2026-11-06):
#   today  -> {powerToday, costToday, durationToday}
#   month  -> {powerSelectMonth[], costSelectMonth[], durationSelectMonth[]}
#   year   -> {power[12], cost[12], setTemperature[12], outsideTemperature[12]}
#   charge -> {charge: 0.6}
#   mode_temp -> {coldModeTemp, warmModeTemp, wetModeTemp, *ModeWind}
#   timer  -> {weekList: [{week: 1..7, timerList: [timer, ...]}]}
#   timer_status -> {fixTimeStatus: 0 | 1}
#   hourly -> {power[24], cost[24], setTemperature[24], outsideTemperature[24]}
#   month_graph -> {power[30], cost[30], setTemperature[30], ...}

# Slow-changing, read-only device metadata.  Fetched at most every
# DEVICE_META_TTL seconds rather than on every 60s auxiliary poll.
STATIC_ENDPOINTS = {
    "fw_version": (ENDPOINT_FW_VERSION, None),
    "ota": (ENDPOINT_OTA_PERCENT, None),
    "help": (ENDPOINT_HELP_ERROR, None),
    "master_user": (ENDPOINT_MASTER_USER, None),
    "dev_name": (ENDPOINT_DEV_NAME, None),
}


class PanasonicApiError(Exception):
    """Base class for cloud API failures."""


class PanasonicAuthError(PanasonicApiError):
    """Session expired or invalid; triggers HA reauthentication."""


async def async_run_command(device, awaitable, action):
    """Run a cloud write and surface failures to the HA service caller.

    Entity service calls used to swallow errors, so a rejected command looked
    successful in the UI.  Auth failures additionally start the reauth flow
    right away instead of waiting for the next status poll to notice the
    stale session.
    """
    try:
        return await awaitable
    except PanasonicAuthError as err:
        device.request_reauth()
        raise HomeAssistantError(
            f"{action}失败：松下账号会话已过期，请重新登录"
        ) from err
    except PanasonicApiError as err:
        raise HomeAssistantError(f"{action}失败：{err}") from err


class PanasonicSmartDevice:
    """One device: a single shared client for all of its entities."""

    def __init__(self, hass, config, name, entry=None):
        self.hass = hass
        self.entry = entry
        self.usr_id = config[CONF_USR_ID]
        self.device_id = config[CONF_DEVICE_ID]
        self.token = config[CONF_TOKEN]
        self.ssid = config[CONF_SSID]
        self.name = name

        # Only the CS-ZY35K410 is supported: no model detection or fallback.
        self.model = DEVICE_MODEL
        self.profile = DEVICE_PROFILE
        self.url_get = URL_GET
        self.url_set = URL_SET
        self.last_params = {}
        self._coordinator = None
        # Set from the live setTemperature value; shared with temperature sensors.
        self.detected_temp_scale = None
        self._device_meta = {}
        self._device_meta_ts = 0.0
        self._device_meta_fetched = False
        self._read_error_logged = False

    def attach_coordinator(self, coordinator):
        """Bind the shared status coordinator for push updates."""
        self._coordinator = coordinator

    def request_reauth(self):
        """Start the reauth flow when a write reports an expired session.

        Older HA releases expose this on the entry, newer ones may move it;
        the status coordinator still triggers reauth on its next poll, so a
        missing helper must never break the service call.
        """
        if self.entry is None:
            return
        starter = getattr(self.entry, "async_start_reauth", None)
        if callable(starter):
            starter(self.hass)
        else:
            _LOGGER.debug("Reauth will be triggered by the next status poll")

    def _log_read_failure(self, message, *args):
        """Warn once per failure streak, then fall back to debug to avoid spam."""
        if self._read_error_logged:
            _LOGGER.debug(message, *args)
        else:
            _LOGGER.warning(message, *args)
            self._read_error_logged = True

    @property
    def power_on_value(self):
        return DEVICE_PROFILE["power_on_value"]

    @property
    def power_off_value(self):
        return DEVICE_PROFILE["power_off_value"]

    @property
    def temp_scale(self):
        return DEVICE_PROFILE["temp_scale"]

    @property
    def temperature_keys(self):
        return DEVICE_PROFILE["temperature_keys"]

    @property
    def current_temperature_keys(self):
        return DEVICE_PROFILE["current_temperature_keys"]

    def is_on(self, params):
        return as_int(params.get("runStatus")) == as_int(self.power_on_value)

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
        scale = self.detected_temp_scale or 1
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
            self._read_error_logged = False
            return results
        except PanasonicAuthError:
            raise
        except Exception as err:
            self._log_read_failure("Fetch status failed: %s", err)
            return None

    async def fetch_aux(self):
        """Fetch read-only electricity statistics (one request per section)."""
        result = {}
        failures = 0
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
                failures += 1
                self._log_read_failure("Aux endpoint %s failed: %s", path, err)
                result[section] = {}
        if failures == len(AUX_ENDPOINTS):
            # Without this the coordinator would report success with an
            # all-empty dataset and never back off.
            raise PanasonicApiError("All auxiliary endpoints failed")
        result["device_meta"] = await self.fetch_device_meta()
        return result

    async def fetch_device_meta(self):
        """Fetch firmware/OTA/help/owner data, cached for DEVICE_META_TTL.

        All five endpoints were verified on a live CS-ZY35K410.  Note that
        ACDevGetMasterUser returns its payload at the top level instead of
        inside "results", so both response shapes are accepted.
        """
        now = time.monotonic()
        if self._device_meta_fetched and now - self._device_meta_ts < DEVICE_META_TTL:
            return dict(self._device_meta)

        raw = {}
        succeeded = 0
        for label, (path, params_builder) in STATIC_ENDPOINTS.items():
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
                section = data.get("results")
                raw[label] = section if isinstance(section, dict) else data
                succeeded += 1
            except PanasonicAuthError:
                raise
            except Exception as err:
                self._log_read_failure(
                    "Device meta endpoint %s failed: %s", path, err
                )
                raw[label] = {}

        fw = raw.get("fw_version") or {}
        ota = raw.get("ota") or {}
        help_links = raw.get("help") or {}
        name = raw.get("dev_name") or {}
        owner = raw.get("master_user") or {}
        meta = {
            "version": fw.get("version"),
            "ota_percent": ota.get("otaUpgradePer"),
            "device_name": name.get("deviceName"),
            "master_user": owner.get("masterUser"),
            "help_links": help_links.get("help"),
            "error_links": help_links.get("error"),
            "problem_links": help_links.get("problem"),
        }
        meta = {key: value for key, value in meta.items() if value is not None}
        if succeeded:
            # Cache even a partial/empty result: otherwise one failed metadata
            # endpoint makes every 60s poll hammer all five endpoints again.
            self._device_meta = meta
            self._device_meta_ts = now
            self._device_meta_fetched = True
        return meta

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

    async def set_fix_time_status(self, enabled):
        """Enable or disable the device's weekly timer feature.

        The official App posts {"params": {"fixTimeStatus": 1}}; a flat
        payload is rejected by the cloud with error 4099.  Verified by
        writing back the unchanged value on a live device.
        """
        payload = {
            "id": 200,
            "usrId": self.usr_id,
            "deviceId": self.device_id,
            "token": self.token,
            "params": {"fixTimeStatus": 1 if enabled else 0},
        }
        return await self._post(f"{URL_BASE}/{ENDPOINT_FIX_STATUS_SET}", payload)

    async def send_command(self, changes):
        """Push only the changed fields to the cloud.

        ACDevSetStatusNewProtocol is incremental: the official H5 calls
        setStatusInfoAWByOne({"portraitWindSet": 65}) and every other field
        is preserved by the device.  Verified on a live CS-ZY35K410
        (todoId 327/328/329, status diff empty).
        """
        params = dict(changes)
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
        return self._apply_optimistic(changes)

    def _apply_optimistic(self, changes):
        """Reflect a successful command immediately, then let polling verify."""
        current = dict(self.last_params)
        if self._coordinator is not None and self._coordinator.data:
            current = dict(self._coordinator.data)
        current.update(
            (key, value)
            for key, value in changes.items()
            if key not in TRANSIENT_COMMAND_KEYS
        )
        self.last_params = current
        if self._coordinator is not None:
            self._coordinator.async_set_updated_data(current)
        return current

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
