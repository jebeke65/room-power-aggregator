# Room Power Aggregator

Room Power Aggregator is a Home Assistant integration that automatically creates
**per-room (area)** power total sensors by summing the power values of all
supported power sensors inside that room.

This provides an immediate overview of **total live power consumption per room**,
fully synchronized with your Home Assistant areas.

The integration also generates a **Sankey-ready YAML** file that visualizes
the full supply → distribution → consumption tree, ready to drop into
Lovelace via `custom:config-wrapper-card`.

---

## ✨ Features

✔ Automatically generates one sensor per Home Assistant area  
✔ Aggregates power (W) or kW (converted to W)  
✔ Optional label filtering (include only sensors with a specific label)  
✔ Optional device_class filtering (only sensors with `device_class: power`)  
✔ **Sankey tree sensor** with full supply/consume hierarchy  
✔ **Unaccounted-power sensor** (gap between total inflow and tracked rooms)  
✔ **Auto-generated Sankey YAML** at `/config/www/room_configurator/sankey.yaml`  
✔ Automatically updates when:
- new entities appear
- entities disappear
- areas change
- devices move to a different area
- labels are added/removed

✔ Each room sensor includes:
- `source_entities`: list of all sensors used in the calculation  
- `source_entity_power_w`: dictionary with each entity's current power in W  

✔ Sensors grouped under one device: **Room Power Aggregator**  
✔ Fully UI-configurable (config flow + options flow)  

---

## 📦 Installation

### Via HACS (recommended)

1. Open **HACS → Integrations**
2. **⋮ → Custom repositories**, add:
   ```
   https://github.com/jebeke65/room-power-aggregator
   ```
   Category: **Integration**
3. Install **Room Power Aggregator** and restart Home Assistant.

### Required companion cards (HACS)

For the Sankey visualization, install these as Lovelace plugins:

- [`ha-sankey-chart`](https://github.com/MindFreeze/ha-sankey-chart) — renders the Sankey
- [`config-wrapper-card`](https://github.com/custom-cards/config-template-card) (or equivalent) — loads the generated YAML

---

## ⚙️ Configuration

After installation:

1. **Settings → Devices & Services → Add Integration**
2. Search for **Room Power Aggregator**

| Setting | Description |
|---|---|
| `label_name` | Only include entities with this label (optional) |
| `only_power_device_class` | Only sensors with `device_class: power` |
| `include_kw` | Convert kW sensors to W and include them |
| `supply_entities` | Entities representing power sources (solar, battery discharge, grid import) |
| `consume_entities` | Entities representing power sinks (grid export, battery charge) |
| `tree_sensor` | Expose the Sankey tree sensor |
| `hide_devices_column` | Hide the per-device column in the generated Sankey |
| `debug` | Extra log output for troubleshooting |

Room sensors are exposed as:

```
sensor.living_room_power_total
sensor.kitchen_power_total
sensor.office_power_total
```

---

## 🌊 Sankey YAML export

On every coordinator refresh, the integration writes a fully-formed Sankey
configuration to:

```
/config/www/room_configurator/sankey.yaml
```

The folder is created automatically — no manual setup needed.

### Use it in Lovelace

```yaml
type: custom:config-wrapper-card
config_url: /local/room_configurator/sankey.yaml
cache_bust: true
```

That's it — the card stays in sync with your live area/device topology.

---

## 📊 Sensor Attributes

Room sensors include:

```yaml
source_entities:
  - sensor.pc_power
  - sensor.monitor_power

source_entity_power_w:
  sensor.pc_power: 42.3
  sensor.monitor_power: 27.1
```

---

## 🧠 How it works

- Scans HA areas, devices, entities, labels
- Selects W and kW (converted) power sensors
- Groups them by area, builds a supply/consume tree
- Computes live per-room totals and unaccounted power
- Exports the tree as a Sankey-ready YAML on every change
- Exposes everything as native HA sensors

---

## 🐛 Issues / Feature Requests

https://github.com/jebeke65/room-power-aggregator/issues

---

## 📜 License

MIT License — see LICENSE file.
