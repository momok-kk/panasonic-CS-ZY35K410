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
_FRONTEND_DIR = _COMPONENT_DIR / "frontend"
# Bundled frontend modules.  They are injected as extra JS URLs so the custom
# card and the `panasonic:` icon set work out of the box: no /config/www copy
# and no lovelace.resources entry is needed, in UI or YAML dashboards.
_FRONTEND_FILES = (
    ("panasonic_icons.js", "panasonic_icons.js"),
    ("panasonic-climate-card.js", "panasonic-climate-card.js"),
)


async def _async_register_frontend(hass: HomeAssistant, domain_data: dict) -> None:
    """Serve the bundled frontend modules and inject them into the frontend.

    MDI has no nanoe glyph, and any non-MDI prefix that is not registered in
    window.customIcons makes ha-icon fall back to the removed <iron-icon>,
    which renders as an empty box.  The card registers itself through
    window.customCards and customElements, so it appears in the card picker
    and resolves `custom:panasonic-climate-card` without extra resources.

    The version for the cache buster comes from the loader (already cached, and
    safe to read off the event loop) rather than from a direct manifest read,
    which the loop-protection detector flags as a blocking call.
    """
    if domain_data.get("frontend_registered"):
        return
    if hass.http is None:
        # HTTP may not be ready during async_setup; the entry setup retries.
        _LOGGER.debug("HTTP not ready yet; deferring panasonic frontend files")
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

        # No filesystem check here: Path.is_file() is blocking I/O and would
        # trip HA's event-loop protection.  The files ship with the component.
        paths = [
            StaticPathConfig(
                f"/{DOMAIN}/{url_name}", str(_FRONTEND_DIR / file_name), True
            )
            for url_name, file_name in _FRONTEND_FILES
        ]
        urls = [f"/{DOMAIN}/{url_name}" for url_name, _ in _FRONTEND_FILES]
        await hass.http.async_register_static_paths(paths)
        for url in urls:
            add_extra_js_url(hass, f"{url}?v={version}")
        # Only mark as done once every step succeeds, so a reload can retry.
        domain_data["frontend_registered"] = True
        _LOGGER.debug("Registered %d panasonic frontend modules", len(paths))
    except Exception:  # noqa: BLE001 - cosmetic feature, never block setup
        _LOGGER.warning(
            "Unable to register bundled frontend files; the custom card and "
            "panasonic:nanoe may be unavailable until the integration is reloaded",
            exc_info=True,
        )


def _build_entity_map(hass: HomeAssistant, entry: ConfigEntry, device) -> dict:
    """Map stable profile keys to the entity_ids HA actually generated.

    Entity IDs depend on the device name in the Panasonic app (and on how many
    devices the user owns), so nothing outside the integration may hardcode
    them.  The climate entity publishes this map as an attribute; the bundled
    card resolves every switch/sensor/button from it, and the map is scoped to
    a single config entry, so multiple CS-ZY35K410 units stay independent.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    prefix = f"panasonic_{device.device_id}_"
    # binary_sensor must be tested before sensor: "_binary_sensor" also ends
    # with "_sensor" and would otherwise produce a wrong key.
    platforms = (
        "binary_sensor", "switch", "sensor", "button", "number", "select",
    )
    mapping: dict[str, str] = {}
    for reg_entry in registry.entities.values():
        if reg_entry.config_entry_id != entry.entry_id:
            continue
        unique_id = reg_entry.unique_id or ""
        if unique_id == f"panasonic_{device.device_id}":
            mapping["climate"] = reg_entry.entity_id
        elif unique_id.startswith(prefix):
            rest = unique_id[len(prefix):]
            for platform in platforms:
                suffix = f"_{platform}"
                if rest.endswith(suffix):
                    mapping[rest[: -len(suffix)]] = reg_entry.entity_id
                    break
    return mapping


async def async_setup(hass: HomeAssistant, config: dict):
    """Initialise global session cache used by the config flow."""
    domain_data = hass.data.setdefault(DOMAIN, {"session": None})
    await _async_register_frontend(hass, domain_data)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up one device with two shared coordinators."""
    domain_data = hass.data.setdefault(DOMAIN, {"session": None})
    # Idempotent: retries frontend registration if HTTP was not ready at startup.
    await _async_register_frontend(hass, domain_data)

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
    # Platforms have registered their entities by now; publish the map so the
    # bundled card can discover them regardless of naming or device count.
    try:
        device.entity_map = _build_entity_map(hass, entry, device)
    except Exception:  # noqa: BLE001 - diagnostics only, never break setup
        _LOGGER.debug("Unable to build the entity map", exc_info=True)
        device.entity_map = {}
    # Push the current status again so the climate entity publishes the map
    # immediately instead of only on the next 15s poll.
    if status.data is not None:
        status.async_set_updated_data(dict(status.data))
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
