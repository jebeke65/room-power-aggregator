from __future__ import annotations

from typing import Dict, List, Set

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RoomPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Room Power Aggregator sensors from a config entry."""
    coordinator: RoomPowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: List[SensorEntity] = []

    # Per-room sensors
    for area_name in coordinator.data.keys():
        sensors.append(RoomPowerSensor(coordinator, area_name))

    # Global total sensor (not tied to any room)
    total_sensor = TotalPowerSensor(coordinator)
    sensors.append(total_sensor)

    async_add_entities(sensors)

    @callback
    def _update_sensors() -> None:
        """Create/remove/update room sensors dynamically and refresh total sensor."""
        current_rooms = {
            s.area_name: s for s in sensors if isinstance(s, RoomPowerSensor)
        }

        new_rooms = set(coordinator.data.keys())
        old_rooms = set(current_rooms.keys())

        # Rooms removed -> remove sensor
        for removed in old_rooms - new_rooms:
            s = current_rooms[removed]
            s.async_remove()
            sensors.remove(s)

        # Rooms added -> create sensor
        new_entities: List[SensorEntity] = []
        for added in new_rooms - old_rooms:
            new_sensor = RoomPowerSensor(coordinator, added)
            sensors.append(new_sensor)
            new_entities.append(new_sensor)

        if new_entities:
            async_add_entities(new_entities)

        # Existing rooms -> update state
        for name in new_rooms & old_rooms:
            current_rooms[name].async_write_ha_state()

        # Always refresh the global total sensor
        total_sensor.async_write_ha_state()

    coordinator.async_add_listener(_update_sensors)


class _BaseAggregatorSensor(SensorEntity):
    """Common helpers for aggregator sensors."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, coordinator: RoomPowerCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        """Create ONE device per config entry so each entry shows its own entities."""
        # Unique per entry to avoid mixing entities across entries
        entry = self.coordinator.entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Room Power Aggregator ({entry.title})",
            manufacturer="Custom Integration",
            model="Power Aggregation Engine",
        )

    def _state_to_watts(self, entity_id: str) -> float | None:
        """Return the entity's current power in W (supports W and kW)."""
        state = self.coordinator.hass.states.get(entity_id)
        if state is None:
            return None

        try:
            val = float(state.state)
        except (ValueError, TypeError):
            return None

        unit = state.attributes.get("unit_of_measurement")
        if unit == "kW":
            val *= 1000.0

        return val


class RoomPowerSensor(_BaseAggregatorSensor):
    """Room-level total power sensor."""

    def __init__(self, coordinator: RoomPowerCoordinator, area_name: str) -> None:
        super().__init__(coordinator)
        self.area_name = area_name
        self._attr_name = f"{area_name} Power Total"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_{area_name}"

    @property
    def suggested_area(self) -> str | None:
        """Suggest the Home Assistant area for this sensor."""
        return self.area_name

    @property
    def native_value(self) -> float | None:
        """Sum of all contributing entities for this room."""
        entity_ids = self.coordinator.data.get(self.area_name, [])
        total = 0.0
        found = False

        for entity_id in entity_ids:
            watts = self._state_to_watts(entity_id)
            if watts is None:
                continue
            total += watts
            found = True

        return round(total, 1) if found else None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Entities included + their current W values."""
        source_entities = self.coordinator.data.get(self.area_name, [])
        if not source_entities:
            return None

        power_values: Dict[str, float | None] = {}
        for entity_id in source_entities:
            power_values[entity_id] = self._state_to_watts(entity_id)

        return {
            "source_entities": list(source_entities),
            "source_entity_power_w": power_values,
        }

    async def async_added_to_hass(self) -> None:
        """Force-link this room sensor to the correct area (not the device area)."""
        await super().async_added_to_hass()

        area_reg = ar.async_get(self.hass)
        entity_reg = er.async_get(self.hass)

        # Find the area by name
        target_area = next(
            (a for a in area_reg.areas.values() if a.name == self.area_name),
            None,
        )
        if not target_area:
            return

        ent_entry = entity_reg.async_get(self.entity_id)
        if ent_entry is None:
            return

        if ent_entry.area_id != target_area.id:
            entity_reg.async_update_entity(ent_entry.entity_id, area_id=target_area.id)


class TotalPowerSensor(_BaseAggregatorSensor):
    """Total power over all rooms."""

    def __init__(self, coordinator: RoomPowerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "All Rooms Power Total"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_all_rooms"

    @property
    def native_value(self) -> float | None:
        """Sum of all unique contributing entities across all rooms."""
        all_entities: Set[str] = set()
        for entity_ids in self.coordinator.data.values():
            all_entities.update(entity_ids)

        total = 0.0
        found = False

        for entity_id in all_entities:
            watts = self._state_to_watts(entity_id)
            if watts is None:
                continue
            total += watts
            found = True

        return round(total, 1) if found else None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Entities included + their current W values."""
        all_entities: Set[str] = set()
        for entity_ids in self.coordinator.data.values():
            all_entities.update(entity_ids)

        if not all_entities:
            return None

        power_values: Dict[str, float | None] = {}
        for entity_id in sorted(all_entities):
            power_values[entity_id] = self._state_to_watts(entity_id)

        return {
            "source_entities": sorted(all_entities),
            "source_entity_power_w": power_values,
        }
