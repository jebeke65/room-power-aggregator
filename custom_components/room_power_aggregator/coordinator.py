from __future__ import annotations

from datetime import timedelta
import logging
from typing import Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)

from .const import (
    UPDATE_INTERVAL,
    CONF_LABEL_NAME,
    CONF_ONLY_POWER_DEVICE_CLASS,
    CONF_INCLUDE_KW,
    CONF_DEBUG,
)


class RoomPowerCoordinator(DataUpdateCoordinator):
    """Scans all rooms and determines which sensors should exist."""

    def __init__(self, hass: HomeAssistant, entry):
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="Room Power Aggregator Coordinator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.entry = entry

    async def _async_update_data(self):
        """Compute which room totals should exist and with which members."""

        data = {**self.entry.data, **self.entry.options}
        label_name = data.get(CONF_LABEL_NAME)
        only_power = data.get(CONF_ONLY_POWER_DEVICE_CLASS, True)
        include_kw = data.get(CONF_INCLUDE_KW, True)
        debug = data.get(CONF_DEBUG, False)

        er_reg = er.async_get(self.hass)
        ar_reg = ar.async_get(self.hass)
        dr_reg = dr.async_get(self.hass)
        lr_reg = lr.async_get(self.hass)

        #
        # Resolve label IDs for filtering
        #
        target_label_ids = None
        if label_name:
            target_label_ids = {
                label.label_id
                for label in lr_reg.labels.values()
                if label.name == label_name
            }

        #
        # Scan all sensor entities
        #
        rooms: Dict[str, List[str]] = {}

        for ent in er_reg.entities.values():
            if not ent.entity_id.startswith("sensor."):
                continue

            state = self.hass.states.get(ent.entity_id)
            if not state:
                continue

            device_class = state.attributes.get("device_class")
            unit = state.attributes.get("unit_of_measurement")

            # filters
            if only_power and device_class != "power":
                continue

            if unit not in ("W", "kW"):
                continue

            if unit == "kW" and not include_kw:
                continue

            # label filtering
            if target_label_ids:
                if not ent.labels or not (ent.labels & target_label_ids):
                    continue

            # area detection
            area_id = ent.area_id
            if not area_id and ent.device_id:
                dev = dr_reg.devices.get(ent.device_id)
                area_id = dev.area_id if dev else None

            if not area_id:
                continue

            area = ar_reg.areas.get(area_id)
            area_name = area.name if area else area_id

            rooms.setdefault(area_name, [])
            rooms[area_name].append(ent.entity_id)

        if debug:
            self.logger.warning("ROOM POWER SCAN RESULT: %s", rooms)

        return rooms
