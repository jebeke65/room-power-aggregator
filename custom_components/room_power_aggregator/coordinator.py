from __future__ import annotations

from datetime import timedelta
import logging
from typing import Dict, List

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)

from .yaml_exporter import build_sankey_yaml, export_sankey_yaml_if_changed

from .const import (
    DOMAIN,
    UPDATE_INTERVAL,
    CONF_LABEL_NAME,
    CONF_ONLY_POWER_DEVICE_CLASS,
    CONF_INCLUDE_KW,
    CONF_DEBUG,
)


class RoomPowerCoordinator(DataUpdateCoordinator):
    """Scans all rooms and determines which sensors should exist."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="Room Power Aggregator Coordinator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.entry = entry

    async def _async_update_data(self) -> Dict[str, List[str]]:
        data = {**self.entry.data, **self.entry.options}
        label_name = (data.get(CONF_LABEL_NAME) or "").strip()
        only_power = data.get(CONF_ONLY_POWER_DEVICE_CLASS, True)
        include_kw = data.get(CONF_INCLUDE_KW, True)
        debug = data.get(CONF_DEBUG, False)

        er_reg = er.async_get(self.hass)
        ar_reg = ar.async_get(self.hass)
        dr_reg = dr.async_get(self.hass)
        lr_reg = lr.async_get(self.hass)

        target_label_ids = None
        if label_name:
            target_label_ids = {
                label.label_id
                for label in lr_reg.labels.values()
                if label.name == label_name
            }

        rooms: Dict[str, List[str]] = {}

        for ent in er_reg.entities.values():
            if not ent.entity_id.startswith("sensor."):
                continue

            # avoid loops: don't include our own sensors
            if getattr(ent, "platform", None) == DOMAIN:
                continue
            if getattr(ent, "config_entry_id", None) == self.entry.entry_id:
                continue

            state = self.hass.states.get(ent.entity_id)
            if not state:
                continue

            device_class = state.attributes.get("device_class")
            unit = state.attributes.get("unit_of_measurement")

            if unit not in ("W", "kW"):
                continue
            if unit == "kW" and not include_kw:
                continue

            if only_power and device_class is not None and device_class != "power":
                continue

            if target_label_ids:
                if not ent.labels or not (ent.labels & target_label_ids):
                    continue

            area_id = ent.area_id
            if not area_id and ent.device_id:
                dev = dr_reg.devices.get(ent.device_id)
                area_id = dev.area_id if dev else None

            if not area_id:
                continue

            area = ar_reg.areas.get(area_id)
            area_name = area.name if area else area_id

            rooms.setdefault(area_name, []).append(ent.entity_id)

        if debug:
            self.logger.warning("ROOM POWER SCAN RESULT: %s", rooms)
        # Generate Sankey YAML export (rooms/devices + supply/consume/unaccounted) and notify on changes.
        try:
            cfg = {**self.entry.data, **self.entry.options}

            supply_entities = list(cfg.get("supply_entities", []) or [])
            consume_entities = list(cfg.get("consume_entities", []) or [])
            hide_devices_column = bool(cfg.get("hide_devices_column", False))

            # Resolve OUR sensor entity_ids (they can get suffixed if conflicts exist)
            def _resolve_by_unique_id(unique_id: str, fallback: str) -> str:
                for e in er_reg.entities.values():
                    if getattr(e, "platform", None) != DOMAIN:
                        continue
                    if getattr(e, "unique_id", None) == unique_id:
                        return e.entity_id
                return fallback

            house_total_entity_id = _resolve_by_unique_id(
                f"{DOMAIN}_{self.entry.entry_id}_all_rooms",
                "sensor.all_rooms_power_total",
            )
            unaccounted_entity_id = _resolve_by_unique_id(
                f"{DOMAIN}_{self.entry.entry_id}_unaccounted",
                "sensor.unaccounted_power",
            )

            room_totals: Dict[str, str] = {}
            for area_name in rooms.keys():
                room_totals[area_name] = _resolve_by_unique_id(
                    f"{DOMAIN}_{self.entry.entry_id}_{area_name}",
                    f"sensor.{area_name.lower().replace(' ', '_')}_power_total",
                )

            yaml_text = build_sankey_yaml(
                house_total_entity_id=house_total_entity_id,
                unaccounted_entity_id=unaccounted_entity_id,
                supply_entities=supply_entities,
                consume_entities=consume_entities,
                room_totals=room_totals,
                rooms_to_device_entities=rooms,
                hide_devices_column=hide_devices_column,
            )
            await export_sankey_yaml_if_changed(self.hass, self.entry.entry_id, yaml_text)
        except Exception as err:  # noqa: BLE001
            self.logger.exception("Failed to export Sankey YAML: %s", err)

        return rooms
