# Room Power Aggregator

Room Power Aggregator is a Home Assistant integration that automatically creates
**per-room (area)** power total sensors by summing the power values of all
supported power sensors inside that room.

This provides an immediate overview of **total live power consumption per room**,
fully synchronized with your Home Assistant areas.

---

## ✨ Features

✔ Automatically generates one sensor per Home Assistant area  
✔ Aggregates power (W) or kW (converted to W)  
✔ Optional label filtering (include only sensors with a specific label)  
✔ Optional device_class filtering (only sensors with `device_class: power`)  
✔ Automatically updates when:
- new entities appear
- entities disappear
- areas change
- devices move to a different area
- labels are added/removed

✔ Each room sensor includes:
- `source_entities`: list of all sensors used in the calculation  
- `source_entity_power_w`: dictionary with each entity's current power in W  

✔ Sensors are grouped under one device: **Room Power Aggregator**  
✔ Fully UI-configurable (config flow + options flow)  
✔ 100% Home Assistant 2024/2025 compatible  

---

## 📦 Installation via HACS

### **Method 1 — HACS Custom Repository**
1. Open Home Assistant  
2. Go to **HACS → Integrations**  
3. Click the **⋮ menu → Custom repositories**  
4. Add:

```
https://github.com/jebeke65/room-power-aggregator
```

Category: **Integration**

5. Install **Room Power Aggregator**  
6. Restart Home Assistant after installation  

---

## ⚙️ Configuration

After installation:

1. Go to  
   **Settings → Devices & Services → Add Integration**  
2. Search for **Room Power Aggregator**

### You can configure:

| Setting | Description |
|--------|-------------|
| **Label name** | Only include entities with this label (optional) |
| **Only power device_class** | Only sensors with `device_class: power` |
| **Include kW** | Convert kW sensors to W and include them |
| **Debug** | Extra log output for troubleshooting |

Generated sensors look like:

```
sensor.living_room_power_total
sensor.kitchen_power_total
sensor.office_power_total
```

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

The integration:

- Scans HA areas, devices, entities, labels  
- Selects W and kW (converted) power sensors  
- Groups them by area  
- Computes a live total per room  
- Updates automatically when HA updates  
- Exposes results as native HA sensors  

---

## 🔮 Planned Enhancements

- Optional Lovelace dashboard auto-creation  
- Per-room daily/weekly/monthly kWh stats  
- Top-consumer attribution per room  

---

## 🐛 Issues / Feature Requests

https://github.com/jebeke65/room-power-aggregator/issues

---

## 📜 License

MIT License — see LICENSE file.
