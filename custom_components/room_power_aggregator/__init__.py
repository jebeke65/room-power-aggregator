from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, PLATFORMS
from .coordinator import RoomPowerCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""

    coordinator = RoomPowerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
