"""Panasonic Smart China ZY custom integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import PanasonicSmartDevice
from .const import DOMAIN
from .coordinator import PanasonicAuxCoordinator, PanasonicStatusCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "climate", "switch", "select", "button", "sensor", "binary_sensor", "number",
]

_COMPONENT_DIR = Path(__file__).parent
_ICONSET_FILE = str(_COMPONENT_DIR / "frontend" / "panasonic_icons.js")
_ICONSET_URL = f"/{DOMAIN}/panasonic_icons.js"


async def _async_register_iconset(hass: HomeAssistant, domain_data: dict) -> None:
    """Serve the `panasonic:` icon set and inject it into the frontend.

    MDI has no nanoe glyph, and any non-MDI prefix that is not registered in
    window.customIcons makes ha-icon fall back to the removed <iron-icon>,
    which renders as an empty box.  Registering a real icon set makes
    `panasonic:nanoe` selectable in the icon picker and renderable anywhere.

    The version for the cache buster comes from the loader (already cached, and
    safe to read off the event loop) rather than from a direct manifest read,
    which the loop-protection detector flags as a blocking call.
    """
    if domain_data.get("iconset_registered"):
        return
    if hass.http is None:
        # HTTP may not be ready during async_setup; the entry setup retries.
        _LOGGER.debug("HTTP not ready yet; deferring panasonic icon set")
        return
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig
        from homeassistant.loader import async_get_integration

        version = "0"
        try:
            integration = await async_get_integration(hass, DOMAIN)
            version = integration.version or "0"
        except Exception:  # noqa: BLE001 - cosmetic cache buster only
            pass

        await hass.http.async_register_static_paths(
            [StaticPathConfig(_ICONSET_URL, _ICONSET_FILE, True)]
        )
        add_extra_js_url(hass, f"{_ICONSET_URL}?v={version}")
        # Only mark as done once both steps succeed, so a reload can retry.
        domain_data["iconset_registered"] = True
        _LOGGER.debug("Registered panasonic icon set at %s", _ICONSET_URL)
    except Exception:  # noqa: BLE001 - cosmetic feature, never block setup
        _LOGGER.warning(
            "Unable to register the panasonic icon set; panasonic:nanoe "
            "will render blank until the integration is reloaded",
            exc_info=True,
        )


async def async_setup(hass: HomeAssistant, config: dict):
    """Initialise global session cache used by the config flow."""
    domain_data = hass.data.setdefault(DOMAIN, {"session": None})
    await _async_register_iconset(hass, domain_data)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up one device with two shared coordinators."""
    domain_data = hass.data.setdefault(DOMAIN, {"session": None})
    # Idempotent: retries icon registration if HTTP was not ready at startup.
    await _async_register_iconset(hass, domain_data)

    device = PanasonicSmartDevice(hass, entry.data, entry.title, entry)
    status = PanasonicStatusCoordinator(hass, device, entry)
    aux = PanasonicAuxCoordinator(hass, device, entry)
    device.attach_coordinator(status, aux)

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
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None) or {}
        device = runtime.get("device")
        if device is not None:
            device.cancel_pending_refreshes()
    return unload_ok
