from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import area_registry as ar, entity_registry as er


from .const import DOMAIN
from .coordinator import RoomPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    coordinator: RoomPowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    for area_name in coordinator.data.keys():
        sensors.append(RoomPowerSensor(coordinator, area_name))

    async_add_entities(sensors)

    @callback
    def _update_sensors():
        """Create/remove/update sensors dynamically if rooms change."""
        current = {s.area_name: s for s in sensors}
        new_rooms = set(coordinator.data.keys())
        old_rooms = set(current.keys())

        # rooms removed → remove sensor
        for removed in old_rooms - new_rooms:
            s = current[removed]
            s.async_remove()
            sensors.remove(s)

        # rooms added → add sensor
        for added in new_rooms - old_rooms:
            new_sensor = RoomPowerSensor(coordinator, added)
            sensors.append(new_sensor)
            async_add_entities([new_sensor])

        # existing rooms → update
        for name in new_rooms & old_rooms:
            current[name].async_write_ha_state()

    coordinator.async_add_listener(_update_sensors)


class RoomPowerSensor(SensorEntity):

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, coordinator: RoomPowerCoordinator, area_name: str):
        self.coordinator = coordinator
        self.area_name = area_name
        self._attr_name = f"{area_name} Power Total"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_{area_name}"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Welke entiteiten dragen bij, en met welke W-waardes?"""
        source_entities = self.coordinator.data.get(self.area_name, [])
        if not source_entities:
            return None

        # lijst van instantene W waarden voor grafieken/debugging
        power_values = {}

        for entity_id in source_entities:
            state = self.coordinator.hass.states.get(entity_id)
            if state is None:
                power_values[entity_id] = None
                continue

            try:
                val = float(state.state)
            except (ValueError, TypeError):
                power_values[entity_id] = None
                continue

            unit = state.attributes.get("unit_of_measurement")
            if unit == "kW":
                val = val * 1000.0

            power_values[entity_id] = val

        return {
            "source_entities": list(source_entities),
            "source_entity_power_w": power_values,
        }
        
    @property
    def suggested_area(self) -> str | None:
        """Suggest the Home Assistant area for this sensor."""
        return self.area_name
        
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="Room Power Aggregator",
            manufacturer="Custom Integration",
        )

    @property
    def native_value(self) -> float | None:
        sensors = self.coordinator.data.get(self.area_name, [])

        total = 0.0
        found = False

        for entity_id in sensors:
            state = self.coordinator.hass.states.get(entity_id)
            if not state:
                continue
            try:
                value = float(state.state)
            except:
                continue

            unit = state.attributes.get("unit_of_measurement")
            if unit == "kW":
                value *= 1000

            total += value
            found = True

        return round(total, 1) if found else None

    async def async_added_to_hass(self) -> None:
        """Zorg dat de entiteit aan de juiste area (room) hangt."""
        await super().async_added_to_hass()

        # Zoek de area-id op basis van de area-naam
        area_reg = ar.async_get(self.hass)
        entity_reg = er.async_get(self.hass)

        target_area = next(
            (a for a in area_reg.areas.values() if a.name == self.area_name),
            None,
        )
        if not target_area:
            return  # area bestaat (nog) niet

        entry = entity_reg.async_get(self.entity_id)
        if entry is None:
            return

        # Alleen updaten als het nog geen eigen area heeft
        if entry.area_id != target_area.id:
            entity_reg.async_update_entity(entry.entity_id, area_id=target_area.id)
