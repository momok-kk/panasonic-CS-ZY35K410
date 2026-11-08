import logging
import hashlib
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import (
    DOMAIN, CONF_USR_ID, CONF_DEVICE_ID, CONF_TOKEN,
    CONF_SSID, CONF_SENSOR_ID, DEVICE_CATEGORY, DEVICE_MODEL,
    NO_EXTERNAL_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

URL_LOGIN = "https://app.psmartcloud.com/App/UsrLogin"
URL_GET_DEV = "https://app.psmartcloud.com/App/UsrGetBindDevInfo"
URL_GET_TOKEN = "https://app.psmartcloud.com/App/UsrGetToken"

# The cloud occasionally stalls; without an explicit timeout the config flow
# would hang for aiohttp's default 5-minute total timeout.
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


def _is_supported_device(device_id):
    """Accept only the CS-ZY35K410 (AirconCommon category 0900)."""
    parts = str(device_id).upper().split("_")
    return (
        len(parts) == 3
        and parts[1] == DEVICE_CATEGORY
        and parts[2] == DEVICE_MODEL
    )


class PanasonicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._login_data = {}
        self._devices = {}
        self._temp_login_info = {}

    async def async_step_reauth(self, entry_data):
        """Start reauthentication when the cloud reports 4102/3003."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Refresh the SSID without changing device identity or entity ids."""
        errors = {}
        if user_input is not None:
            try:
                usr_id, ssid, _ = await self._authenticate_full_flow(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except Exception as err:
                _LOGGER.error("Reauthentication failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                entry_id = self.context.get("entry_id")
                entry = self.hass.config_entries.async_get_entry(entry_id)
                if entry:
                    new_data = dict(entry.data)
                    new_data[CONF_USR_ID] = usr_id
                    new_data[CONF_SSID] = ssid
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    # Invalidate the cached session so other devices re-login.
                    self.hass.data.setdefault(DOMAIN, {})["session"] = None
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Step 1: reuse a cached session or sign in."""
        errors = {}

        domain_data = self.hass.data.get(DOMAIN, {})
        cached_session = domain_data.get("session")

        if cached_session:
            _LOGGER.info("Found cached session, verifying validity...")

            valid_devices = await self._get_devices_with_ssid(
                cached_session[CONF_USR_ID], cached_session[CONF_SSID]
            )

            if valid_devices:
                _LOGGER.info("Session valid. Skipping login.")
                self._login_data = {
                    CONF_USR_ID: cached_session[CONF_USR_ID],
                    CONF_SSID: cached_session[CONF_SSID]
                }
                self._devices = valid_devices
                return await self.async_step_device()
            _LOGGER.warning("Cached session expired.")
            if DOMAIN in self.hass.data:
                self.hass.data[DOMAIN]["session"] = None

        if user_input is not None:
            try:
                usr_id, ssid, devices = await self._authenticate_full_flow(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )

                if not devices:
                    return self.async_abort(reason="no_devices_found")

                self._login_data = {CONF_USR_ID: usr_id, CONF_SSID: ssid}
                self._devices = devices

                self.hass.data.setdefault(DOMAIN, {})["session"] = {
                    CONF_USR_ID: usr_id,
                    CONF_SSID: ssid,
                    "devices": devices,
                    "familyId": self._temp_login_info.get('familyId'),
                    "realFamilyId": self._temp_login_info.get('realFamilyId')
                }

                return await self.async_step_device()

            except Exception as err:
                _LOGGER.error("Login failed: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_device(self, user_input=None):
        """Step 2: pick the device."""
        errors = {}

        existing_ids = self._async_current_ids()

        available_devices = {}
        for did, info in self._devices.items():
            if f"panasonic_{did}" not in existing_ids:
                available_devices[did] = f"{info['deviceName']} ({did})"

        if not available_devices:
            return self.async_abort(reason="all_devices_configured")

        if user_input is not None:
            selected_dev_id = user_input[CONF_DEVICE_ID]
            dev_info = self._devices.get(selected_dev_id)
            dev_name = dev_info.get("deviceName", "Panasonic AC")

            token = self._generate_token(selected_dev_id)
            if not token:
                errors["base"] = "token_generation_failed"
            else:
                return self.async_create_entry(
                    title=dev_name,
                    data={
                        CONF_USR_ID: self._login_data[CONF_USR_ID],
                        CONF_SSID: self._login_data[CONF_SSID],
                        CONF_DEVICE_ID: selected_dev_id,
                        CONF_TOKEN: token,
                        CONF_SENSOR_ID: user_input.get(CONF_SENSOR_ID, NO_EXTERNAL_SENSOR),
                    }
                )

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(available_devices),
                vol.Optional(CONF_SENSOR_ID): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
            }),
            errors=errors,
        )

    async def _get_devices_with_ssid(self, usr_id, ssid):
        """Verify a cached session by listing devices with just its SSID."""
        headers = {
            'User-Agent': 'SmartApp',
            'Content-Type': 'application/json',
            'Cookie': f"SSID={ssid}",
        }

        session_cache = self.hass.data.get(DOMAIN, {}).get("session")
        if not session_cache or 'familyId' not in session_cache:
            return None

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(URL_GET_DEV, json={
                "id": 3, "uiVersion": 4.0,
                "params": {
                    "realFamilyId": session_cache['realFamilyId'],
                    "familyId": session_cache['familyId'],
                    "usrId": usr_id
                }
            }, headers=headers, ssl=False, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status != 200:
                    return None
                dev_res = await resp.json()
                if 'results' not in dev_res:
                    return None

                devices = {}
                for dev in dev_res['results']['devList']:
                    if _is_supported_device(dev.get('deviceId', '')):
                        devices[dev['deviceId']] = dev['params']
                return devices
        except Exception as err:
            _LOGGER.warning("Cached Panasonic session could not be verified: %s", err)
            return None

    async def _authenticate_full_flow(self, username, password):
        """Full login: get challenge token, derive password, login, list devices."""
        headers = {'User-Agent': 'SmartApp', 'Content-Type': 'application/json'}
        session = async_get_clientsession(self.hass)

        # 1. GetToken
        async with session.post(URL_GET_TOKEN, json={
            "id": 1, "uiVersion": 4.0, "params": {"usrId": username}
        }, headers=headers, ssl=False, timeout=REQUEST_TIMEOUT) as resp:
            data = await resp.json()
            if 'results' not in data:
                raise RuntimeError("GetToken Failed")
            token_start = data['results']['token']

        # 2. Calc Password
        pwd_md5 = hashlib.md5(password.encode()).hexdigest().upper()
        inter_md5 = hashlib.md5((pwd_md5 + username).encode()).hexdigest().upper()
        final_token = hashlib.md5((inter_md5 + token_start).encode()).hexdigest().upper()

        # 3. Login
        async with session.post(URL_LOGIN, json={
            "id": 2, "uiVersion": 4.0,
            "params": {
                "telId": "00:00:00:00:00:00",
                "checkFailCount": 0,
                "usrId": username,
                "pwd": final_token,
            }
        }, headers=headers, ssl=False, timeout=REQUEST_TIMEOUT) as resp:
            login_res = await resp.json()
            if "results" not in login_res:
                raise RuntimeError("Login Failed")

            res = login_res['results']
            real_usr_id = res['usrId']
            ssid = res['ssId']

            self._temp_login_info = {
                'realFamilyId': res['realFamilyId'],
                'familyId': res['familyId']
            }

        # 4. Get Devices
        headers['Cookie'] = f"SSID={ssid}"
        async with session.post(URL_GET_DEV, json={
            "id": 3, "uiVersion": 4.0,
            "params": {
                "realFamilyId": res['realFamilyId'],
                "familyId": res['familyId'],
                "usrId": real_usr_id
            }
        }, headers=headers, ssl=False, timeout=REQUEST_TIMEOUT) as resp:
            dev_res = await resp.json()
            devices = {}
            skipped = 0
            if 'results' in dev_res and 'devList' in dev_res['results']:
                for dev in dev_res['results']['devList']:
                    did = dev.get('deviceId', '')
                    if _is_supported_device(did):
                        devices[did] = dev.get('params', {})
                    else:
                        skipped += 1
            if skipped:
                _LOGGER.info(
                    "Ignored %d device(s) that are not CS-ZY35K410", skipped
                )
            return real_usr_id, ssid, devices

    def _generate_token(self, device_id):
        """Derive the device token from an AirconCommon deviceId.

        deviceId is MAC_CATEGORY_MODEL, e.g. B812DAC81168_0900_CS-ZY35K410.
        stoken = MAC[6:] + '_' + category + '_' + MAC[:6]
        token  = sha512(sha512(stoken) + '_' + model)
        """
        try:
            did = str(device_id).upper()
            parts = did.split('_')
            if len(parts) != 3:
                _LOGGER.error(
                    "Invalid deviceId format: %s (expected MAC_CATEGORY_MODEL)",
                    device_id,
                )
                return None

            mac_part, category, model = parts
            if len(mac_part) != 12 or any(
                char not in "0123456789ABCDEF" for char in mac_part
            ):
                _LOGGER.error("Invalid 12-character MAC in deviceId: %s", device_id)
                return None
            if category != DEVICE_CATEGORY or model != DEVICE_MODEL:
                _LOGGER.error(
                    "Unsupported device category/model: %s / %s", category, model
                )
                return None

            stoken = mac_part[6:] + '_' + category + '_' + mac_part[:6]
            inner = hashlib.sha512(stoken.encode()).hexdigest()
            return hashlib.sha512((inner + '_' + model).encode()).hexdigest()
        except Exception as err:
            _LOGGER.error("Token generation failed for deviceId %s: %s", device_id, err)
            return None
