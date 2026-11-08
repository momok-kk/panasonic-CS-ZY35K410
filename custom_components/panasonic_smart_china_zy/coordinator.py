"""Shared polling coordinators for a single Panasonic device.

All entities of a device share these two loops instead of each issuing its
own cloud request.  Status polls every 15s; electricity statistics every 60s.
"""

from __future__ import annotations

from datetime import timedelta
import inspect
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PanasonicAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL = timedelta(seconds=15)
AUX_POLLING_INTERVAL = timedelta(seconds=60)

# config_entry= was added to DataUpdateCoordinator after the minimum HA
# version declared in hacs.json.  Detect it once so the integration still
# loads on older releases (which need the legacy attribute assignment).
_SUPPORTS_CONFIG_ENTRY = (
    "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters
)


class PanasonicStatusCoordinator(DataUpdateCoordinator):
    """Poll the device status bean and cache it for every entity."""

    def __init__(self, hass, device, entry):
        self.device = device
        kwargs = {
            "name": f"{DOMAIN}_status_{device.device_id}",
            "update_interval": POLLING_INTERVAL,
        }
        if _SUPPORTS_CONFIG_ENTRY:
            # Lets DataUpdateCoordinator start the reauth flow on 4102/3003.
            kwargs["config_entry"] = entry
        super().__init__(hass, _LOGGER, **kwargs)
        if not _SUPPORTS_CONFIG_ENTRY:
            self.config_entry = entry

    async def _async_update_data(self):
        try:
            data = await self.device.fetch_status()
        except PanasonicAuthError as err:
            raise ConfigEntryAuthFailed("Panasonic Smart China session expired") from err
        if not data:
            raise UpdateFailed(f"Empty status for {self.device.device_id}")
        return data


class PanasonicAuxCoordinator(DataUpdateCoordinator):
    """Poll slower, read-only auxiliary endpoints (electricity stats).

    Deliberately not bound to the config entry: the status coordinator owns
    reauth, so the two loops cannot start duplicate reauth flows.
    """

    def __init__(self, hass, device, entry):
        self.device = device
        kwargs = {
            "name": f"{DOMAIN}_aux_{device.device_id}",
            "update_interval": AUX_POLLING_INTERVAL,
        }
        if _SUPPORTS_CONFIG_ENTRY:
            kwargs["config_entry"] = None
        super().__init__(hass, _LOGGER, **kwargs)
        self.config_entry = None

    async def _async_update_data(self):
        try:
            return await self.device.fetch_aux()
        except PanasonicAuthError as err:
            raise ConfigEntryAuthFailed("Panasonic Smart China session expired") from err
        except Exception as err:
            raise UpdateFailed(f"Aux fetch failed: {err}") from err
