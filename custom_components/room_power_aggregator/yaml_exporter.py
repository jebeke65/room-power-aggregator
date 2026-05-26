from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1


def _dedup(seq: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in seq:
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


@dataclass(frozen=True)
class SankeyExportResult:
    yaml_text: str
    file_path: str
    changed: bool


def build_sankey_yaml(
    *,
    house_total_entity_id: str,
    unaccounted_entity_id: str,
    supply_entities: list[str],
    consume_entities: list[str],
    room_totals: dict[str, str],
    rooms_to_device_entities: dict[str, list[str]],
    hide_devices_column: bool,
) -> str:
    """Build Sankey YAML in v4 format (ha-sankey-chart 4.0.0+).

    v4 uses flat nodes[] with section index + separate links[] array.
    """

    def _room_color(room_name: str) -> str:
        h = hashlib.sha1(room_name.casefold().encode("utf-8")).hexdigest()
        return f"#{h[:6]}"

    def _pretty_name(entity_id: str) -> str:
        base = entity_id.split(".")[-1]
        base = base.replace("_", " ").strip()
        return " ".join(w.capitalize() for w in base.split())

    nodes: list[str] = []
    links: list[str] = []

    # Section 0: SUPPLY
    # Section 1: CONSUME + HOUSE + UNACCOUNTED
    # Section 2: ROOMS
    # Section 3: DEVICES (optional)

    # --- SUPPLY nodes (section 0) ---
    for eid in supply_entities:
        nodes += [
            "  - id: " + eid,
            "    section: 0",
            "    name: " + _pretty_name(eid),
        ]

    # --- CONSUME + HOUSE + UNACCOUNTED nodes (section 1) ---
    nodes += [
        "  - id: " + house_total_entity_id,
        "    section: 1",
        "    name: House consumption",
    ]

    for eid in consume_entities:
        nodes += [
            "  - id: " + eid,
            "    section: 1",
            "    name: " + _pretty_name(eid),
        ]

    nodes += [
        "  - id: " + unaccounted_entity_id,
        "    section: 1",
        "    name: Unaccounted",
    ]

    # --- SUPPLY links → section 1 targets ---
    supply_targets = _dedup([house_total_entity_id, *consume_entities, unaccounted_entity_id])
    for eid in supply_entities:
        for target in supply_targets:
            links += [
                "  - source: " + eid,
                "    target: " + target,
            ]

    # --- ROOM nodes (section 2) ---
    for area_name in sorted(room_totals.keys(), key=lambda s: s.casefold()):
        room_eid = room_totals[area_name]
        room_color = _room_color(area_name)
        nodes += [
            "  - id: " + room_eid,
            "    section: 2",
            "    name: " + area_name,
            "    color: '" + room_color + "'",
        ]

    # --- HOUSE → ROOM links ---
    for area_name in sorted(room_totals.keys(), key=lambda s: s.casefold()):
        links += [
            "  - source: " + house_total_entity_id,
            "    target: " + room_totals[area_name],
        ]

    # --- DEVICE nodes + links (section 3, optional) ---
    if not hide_devices_column:
        for area_name in sorted(room_totals.keys(), key=lambda s: s.casefold()):
            room_color = _room_color(area_name)
            room_eid = room_totals[area_name]
            for dev in sorted(rooms_to_device_entities.get(area_name, []), key=lambda s: s.casefold()):
                nodes += [
                    "  - id: " + dev,
                    "    section: 3",
                    "    name: " + _pretty_name(dev),
                    "    color: '" + room_color + "'",
                ]
                links += [
                    "  - source: " + room_eid,
                    "    target: " + dev,
                ]

    # --- Assemble final YAML ---
    lines: list[str] = [
        "type: custom:sankey-chart",
        "layout: horizontal",
        "height: 800",
        'unit_prefix: ""',
        "round: 0",
        "min_state: 0",
        "show_names: true",
        "show_states: true",
        "show_units: true",
        "",
        "nodes:",
    ]
    lines += nodes
    lines += [
        "",
        "links:",
    ]
    lines += links
    lines += [""]

    return "\n".join(lines)


async def export_sankey_yaml_if_changed(hass, entry_id: str, yaml_text: str) -> SankeyExportResult:
    """Write yaml to /config/www/room_configurator/sankey.yaml when it changed.

    Dashboard reads via config_url + cache_bust, so no manual copy needed.
    """
    store = Store(hass, STORAGE_VERSION, f"room_power_aggregator_yaml_{entry_id}")
    data = await store.async_load() or {}

    new_hash = hashlib.sha256(yaml_text.encode("utf-8")).hexdigest()
    old_hash = data.get("hash")

    outdir = Path(hass.config.path("www", "room_configurator"))
    await hass.async_add_executor_job(lambda: outdir.mkdir(parents=True, exist_ok=True))
    outfile = outdir / "sankey.yaml"

    changed = new_hash != old_hash
    if changed:
        await hass.async_add_executor_job(outfile.write_text, yaml_text, "utf-8")
        data["hash"] = new_hash
        await store.async_save(data)

    return SankeyExportResult(yaml_text=yaml_text, file_path=str(outfile), changed=changed)
