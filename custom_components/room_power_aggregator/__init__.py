from __future__ import annotations

import logging
from pathlib import Path
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, PLATFORMS, FRONTEND_BUNDLE_FILENAME, FRONTEND_URL_PATH
from .coordinator import RoomPowerCoordinator

_LOGGER = logging.getLogger(__name__)


async def _ensure_frontend_registered(hass: HomeAssistant) -> None:
    """Serve frontend assets and auto-load the bundled JS once per HA instance."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("_frontend_registered"):
        return

    try:
        frontend_path = Path(__file__).parent / "frontend"
        if getattr(hass, "http", None) is None or hass.http is None:
            _LOGGER.debug("No hass.http available; skipping frontend registration.")
            return
        if not frontend_path.exists():
            _LOGGER.warning("Frontend folder not found at %s. Skipping.", frontend_path)
            return

        hass.http.register_static_path(FRONTEND_URL_PATH, str(frontend_path), cache_headers=True)

        from homeassistant.components import frontend
        url = f"{FRONTEND_URL_PATH}/{FRONTEND_BUNDLE_FILENAME}?v=1"
        frontend.add_extra_js_url(hass, url)

        domain_data["_frontend_registered"] = True
        _LOGGER.debug("Registered frontend bundle at %s", url)
    except Exception as err:
        _LOGGER.warning("Failed to register frontend bundle: %s", err)



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""

    coordinator = RoomPowerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Auto-load bundled Lovelace cards (once per HA instance)
    await _ensure_frontend_registered(hass)

    #
    # Auto-reload bij wijzigingen in entity/device/area/label registries
    #
    @callback
    def _trigger_reload(event):
        hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))

    unsub = [
        hass.bus.async_listen("entity_registry_updated", _trigger_reload),
        hass.bus.async_listen("device_registry_updated", _trigger_reload),
        hass.bus.async_listen("area_registry_updated", _trigger_reload),
        hass.bus.async_listen("label_registry_updated", _trigger_reload),
    ]

    for u in unsub:
        entry.async_on_unload(u)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
