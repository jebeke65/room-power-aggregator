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

from .const import DOMAIN, CONF_SUPPLY_ENTITIES, CONF_CONSUME_ENTITIES, CONF_HIDE_DEVICES_COLUMN
from .coordinator import RoomPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RoomPowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: List[SensorEntity] = []

    for area_name in coordinator.data.keys():
        sensors.append(RoomPowerSensor(coordinator, area_name))

    total_sensor = TotalPowerSensor(coordinator)
    sensors.append(total_sensor)

    unaccounted_sensor = UnaccountedPowerSensor(coordinator)
    sensors.append(unaccounted_sensor)

    sankey_tree_sensor = RoomPowerSankeyTreeSensor(coordinator)
    sensors.append(sankey_tree_sensor)

    async_add_entities(sensors)

    @callback
    def _update_sensors() -> None:
        current_rooms = {s.area_name: s for s in sensors if isinstance(s, RoomPowerSensor)}
        new_rooms = set(coordinator.data.keys())
        old_rooms = set(current_rooms.keys())

        for removed in old_rooms - new_rooms:
            s = current_rooms[removed]
            s.async_remove()
            sensors.remove(s)

        new_entities: List[SensorEntity] = []
        for added in new_rooms - old_rooms:
            ns = RoomPowerSensor(coordinator, added)
            sensors.append(ns)
            new_entities.append(ns)

        if new_entities:
            async_add_entities(new_entities)

        for name in new_rooms & old_rooms:
            current_rooms[name].async_write_ha_state()

        total_sensor.async_write_ha_state()
        unaccounted_sensor.async_write_ha_state()
        sankey_tree_sensor.async_write_ha_state()

    coordinator.async_add_listener(_update_sensors)


class _BaseAggregatorSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, coordinator: RoomPowerCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Room Power Aggregator ({entry.title})",
            manufacturer="Custom Integration",
            model="Power Aggregation Engine",
        )

    def _state_to_watts(self, entity_id: str) -> float | None:
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
    _unrecorded_attributes = frozenset({
        "entities",
        "powers_w",
        "entities_count",
        "label_used",
        "filtered_by_label",
    })
    def __init__(self, coordinator: RoomPowerCoordinator, area_name: str) -> None:
        super().__init__(coordinator)
        self.area_name = area_name
        self._attr_name = f"{area_name} Power Total"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_{area_name}"

    @property
    def suggested_area(self) -> str | None:
        return self.area_name

    @property
    def native_value(self) -> float:
        entity_ids = self.coordinator.data.get(self.area_name, [])
        total = 0.0
        for entity_id in entity_ids:
            watts = self._state_to_watts(entity_id)
            if watts is None:
                continue
            total += watts
        return round(total, 1)

    @property
    def extra_state_attributes(self) -> dict | None:
        src = self.coordinator.data.get(self.area_name, [])
        if not src:
            return None
        power_values: Dict[str, float | None] = {eid: self._state_to_watts(eid) for eid in src}
        return {"source_entities": list(src), "source_entity_power_w": power_values}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        area_reg = ar.async_get(self.hass)
        entity_reg = er.async_get(self.hass)

        target_area = next((a for a in area_reg.areas.values() if a.name == self.area_name), None)
        if not target_area:
            return

        ent_entry = entity_reg.async_get(self.entity_id)
        if ent_entry and ent_entry.area_id != target_area.id:
            entity_reg.async_update_entity(ent_entry.entity_id, area_id=target_area.id)


class TotalPowerSensor(_BaseAggregatorSensor):
    def __init__(self, coordinator: RoomPowerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "All Rooms Power Total"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_all_rooms"

    @property
    def native_value(self) -> float:
        all_entities: Set[str] = set()
        for entity_ids in self.coordinator.data.values():
            all_entities.update(entity_ids)
        total = 0.0
        for entity_id in all_entities:
            watts = self._state_to_watts(entity_id)
            if watts is None:
                continue
            total += watts
        return round(total, 1)

    @property
    def extra_state_attributes(self) -> dict | None:
        all_entities: Set[str] = set()
        for entity_ids in self.coordinator.data.values():
            all_entities.update(entity_ids)
        if not all_entities:
            return None
        power_values: Dict[str, float | None] = {eid: self._state_to_watts(eid) for eid in sorted(all_entities)}
        return {"source_entities": sorted(all_entities), "source_entity_power_w": power_values}



class UnaccountedPowerSensor(_BaseAggregatorSensor):
    def __init__(self, coordinator: RoomPowerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Unaccounted Power"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_unaccounted"

    @property
    def native_value(self) -> float:
        cfg = {**self.coordinator.entry.data, **self.coordinator.entry.options}
        supply = cfg.get(CONF_SUPPLY_ENTITIES, []) or []
        consume = cfg.get(CONF_CONSUME_ENTITIES, []) or []

        supply_total = 0.0
        for eid in supply:
            w = self._state_to_watts(eid)
            if w is None:
                continue
            supply_total += w

        consume_total = 0.0
        for eid in consume:
            w = self._state_to_watts(eid)
            if w is None:
                continue
            consume_total += w

        house = float(TotalPowerSensor(self.coordinator).native_value)
        unacc = supply_total - house - consume_total
        if unacc < 0:
            unacc = 0.0
        return round(unacc, 1)

    @property
    def extra_state_attributes(self) -> dict | None:
        cfg = {**self.coordinator.entry.data, **self.coordinator.entry.options}
        return {
            "supply_entities": cfg.get(CONF_SUPPLY_ENTITIES, []) or [],
            "consume_entities": cfg.get(CONF_CONSUME_ENTITIES, []) or [],
        }



class RoomPowerSankeyTreeSensor(_BaseAggregatorSensor):
    _unrecorded_attributes = frozenset({"graph"})
    """Exposes a tree/graph attribute used by the Sankey Tree cards."""

    def __init__(self, coordinator: RoomPowerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Room Power Sankey Tree"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_sankey_tree"
        self._attr_entity_category = None

    @property
    def native_value(self) -> float:
        # Show house total as the state
        # (keeps something useful in the UI; the card reads the attributes)
        all_entities: Set[str] = set()
        for entity_ids in self.coordinator.data.values():
            all_entities.update(entity_ids)
        total = 0.0
        for eid in all_entities:
            w = self._state_to_watts(eid)
            if w is None:
                continue
            total += w
        return round(total, 1)

    def _room_sensor_entity_id(self, room_name: str) -> str:
        ent_reg = er.async_get(self.hass)
        unique = f"{DOMAIN}_{self.coordinator.entry.entry_id}_{room_name}"
        for e in ent_reg.entities.values():
            if e.unique_id == unique:
                return e.entity_id
        # fallback: best effort slug, but entity_id can be renamed by user
        return f"sensor.{room_name.lower().replace(' ', '_')}_power_total"
    def _special_sensor_entity_id(self, suffix: str, fallback: str) -> str:
        """Find our own sensor entity_id by unique_id suffix."""
        ent_reg = er.async_get(self.hass)
        unique = f"{DOMAIN}_{self.coordinator.entry.entry_id}_{suffix}"
        for e in ent_reg.entities.values():
            if e.unique_id == unique:
                return e.entity_id
        return fallback

    def _house_total_entity_id(self) -> str:
        # TotalPowerSensor unique_id uses suffix "all_rooms"
        return self._special_sensor_entity_id("all_rooms", "sensor.all_rooms_power_total")

    def _unaccounted_entity_id(self) -> str:
        # UnaccountedPowerSensor unique_id uses suffix "unaccounted"
        return self._special_sensor_entity_id("unaccounted", "sensor.unaccounted_power")


    @property
    def extra_state_attributes(self) -> dict | None:
        cfg = {**self.coordinator.entry.data, **self.coordinator.entry.options}
        hide_devices = bool(cfg.get(CONF_HIDE_DEVICES_COLUMN, False))

        room_names = sorted(self.coordinator.data.keys())
        # simple deterministic palette
        palette = ["#00BCD4", "#8BC34A", "#FF9800", "#9C27B0", "#03A9F4", "#CDDC39", "#FF5722", "#607D8B"]
        rooms = {}
        devices = {}

        for idx, rn in enumerate(room_names):
            color = palette[idx % len(palette)]
            devs = list(self.coordinator.data.get(rn, []))
            room_eid = self._room_sensor_entity_id(rn)
            rooms[rn] = {
                "entity_id": room_eid,
                "devices": devs,
                "color": color,
            }
            for deid in devs:
                st = self.hass.states.get(deid)
                devices[deid] = {
                    "name": st.attributes.get("friendly_name") if st else None,
                    "color": color,
                    "room": rn,
                }

        # expose supply/consume defaults so user can omit them in card YAML
        supply = cfg.get(CONF_SUPPLY_ENTITIES, []) or []
        consume = cfg.get(CONF_CONSUME_ENTITIES, []) or []

        return {
            "rooms": rooms,
            "devices": devices,
            "hide_devices_column": hide_devices,

            # Defaults for the Sankey Tree 4col card; user can still override via card YAML.
            "supply": [{"entity_id": e} for e in supply],
            "consume": [{"entity_id": e} for e in consume],

            # Always expose our own computed sensors so the card can build column 2 correctly
            # without requiring the user to hardcode entity_ids.
            "house": {
                "entity_id": self._house_total_entity_id(),
                "name": "House",
            },
            "unaccounted": {
                "entity_id": self._unaccounted_entity_id(),
                "name": "Unaccounted",
            },
        }

