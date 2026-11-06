"""Panasonic Smart China ZY custom integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import PanasonicSmartDevice
from .const import DOMAIN
from .coordinator import PanasonicAuxCoordinator, PanasonicStatusCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "select", "button", "sensor", "binary_sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Initialise global session cache used by the config flow."""
    hass.data.setdefault(DOMAIN, {"session": None})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up one device with two shared coordinators."""
    domain_data = hass.data.setdefault(DOMAIN, {"session": None})

    device = PanasonicSmartDevice(hass, entry.data, entry.title)
    status = PanasonicStatusCoordinator(hass, device, entry)
    aux = PanasonicAuxCoordinator(hass, device, entry)
    device.attach_coordinator(status)

    # async_refresh() (not async_config_entry_first_refresh) keeps the entry
    # loadable while the session is expired: entities show as unavailable and
    # the coordinator starts the reauth flow automatically.
    await status.async_refresh()
    await aux.async_refresh()
    if not status.last_update_success:
        _LOGGER.warning(
            "Initial status fetch failed for %s; entities will be unavailable "
            "until the Panasonic session is renewed.",
            device.device_id,
        )

    domain_data[entry.entry_id] = {
        "device": device,
        "status": status,
        "aux": aux,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload platforms and drop the shared runtime."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
