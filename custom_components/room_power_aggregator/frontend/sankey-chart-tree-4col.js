class SankeyChartTree4Col extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = null;
    this._inner = null;
    this._busy = false;
  }

setConfig(config) {
  // Clone first: HA may freeze the config object (Safari throws on mutation)
  var cfg = config || {};
  var cloned;

  try {
    // Modern browsers (incl recent Safari)
    cloned = structuredClone(cfg);
  } catch (e) {
    // Fallback
    cloned = JSON.parse(JSON.stringify(cfg || {}));
  }

  this._config = cloned || {};
  this._config.tree_attribute = this._config.tree_attribute || "graph";

  if (!this._config.sources) this._config.sources = {};
  if (!Array.isArray(this._config.sources.supply)) this._config.sources.supply = [];
  if (!Array.isArray(this._config.sources.consume)) this._config.sources.consume = [];

  this._config.room_entity_match = this._config.room_entity_match || "_power_total";
  this._config.exclude_room_entity = this._config.exclude_room_entity || "sensor.all_rooms_power_total";

  this._config.sort_rooms = this._config.sort_rooms !== false;
  this._config.sort_devices = this._config.sort_devices !== false;

  if (!this._config.sankey) this._config.sankey = {};
}

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 10;
  }

  _safeParse(raw) {
    if (!raw) return null;
    if (typeof raw === "object") return raw;
    if (typeof raw !== "string") return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  async _ensureInner() {
    if (this._inner) return;
    if (!customElements.get("sankey-chart")) {
      await customElements.whenDefined("sankey-chart");
    }
    this._inner = document.createElement("sankey-chart");
    this.appendChild(this._inner);
  }

  _hashColor(seed) {
    var h = 0;
    for (var i = 0; i < seed.length; i++) {
      h = (h * 31 + seed.charCodeAt(i)) % 360;
    }
    return "hsl(" + h + " 70% 45%)";
  }

  async _showMessage(title, msg) {
    await this._ensureInner();
    this._inner.setConfig({
      type: "custom:sankey-chart",
      title: title,
      min_state: 0,
      sections: [
        { entities: [{ type: "entity", entity_id: "sensor.none", name: msg }] }
      ]
    });
    this._inner.hass = this._hass;
  }

  _getStateFloat(entityId) {
    var st = this._hass && this._hass.states ? this._hass.states[entityId] : null;
    var v = st ? Number(st.state) : 0;
    return isNaN(v) ? 0 : v;
  }

  async _render() {
    if (this._busy) return;
    if (!this._hass || !this._config) return;

    this._busy = true;
    try {
      await this._ensureInner();

      if (!this._config.tree_entity) {
        await this._showMessage("Auto Sankey (4 cols)", "Missing config: tree_entity");
        return;
      }

      var treeState = this._hass.states[this._config.tree_entity];
      if (!treeState) {
        await this._showMessage("Auto Sankey (4 cols)", "Waiting for " + this._config.tree_entity + " …");
        return;
      }

      var graphRaw = treeState.attributes ? treeState.attributes[this._config.tree_attribute] : null;
      var graph = this._safeParse(graphRaw);
      if (!graph || !graph.nodes) {
        await this._showMessage("Auto Sankey (4 cols)", "Waiting for attribute '" + this._config.tree_attribute + "' …");
        return;
      }

      var nodes = graph.nodes;

      // -------- Column 3: Rooms (auto) --------
      var rooms = [];
      for (var name in nodes) {
        if (!Object.prototype.hasOwnProperty.call(nodes, name)) continue;
        var eid = nodes[name] && nodes[name].entity_id;
        if (typeof eid !== "string") continue;
        if (eid === this._config.exclude_room_entity) continue;
        if (eid.indexOf(this._config.room_entity_match) === -1) continue;
        rooms.push({ name: name, entity_id: eid });
      }

      if (!rooms.length) {
        await this._showMessage("Auto Sankey (4 cols)", "No rooms found (expected *_power_total nodes)");
        return;
      }

      if (this._config.sort_rooms) {
        var self = this;
        rooms.sort(function (a, b) {
          var av = self._getStateFloat(a.entity_id);
          var bv = self._getStateFloat(b.entity_id);
          if (bv !== av) return bv - av;
          return a.name.localeCompare(b.name);
        });
      }

      // -------- Column 4: Devices (auto from room.source_entities) --------
      var deviceMap = {};      // devEid -> friendly name
      var deviceRoom = {};     // devEid -> roomEid
      var roomChildren = {};   // roomEid -> [devEid]

      for (var r = 0; r < rooms.length; r++) {
        var roomEid = rooms[r].entity_id;
        var roomState = this._hass.states[roomEid];
        var src = roomState && roomState.attributes ? roomState.attributes.source_entities : null;

        var children = [];
        if (Array.isArray(src)) {
          for (var j = 0; j < src.length; j++) {
            var devEid = src[j];
            if (typeof devEid !== "string" || devEid.indexOf(".") === -1) continue;

            children.push(devEid);

            if (!deviceRoom[devEid]) deviceRoom[devEid] = roomEid;

            var devState = this._hass.states[devEid];
            var devName = (devState && devState.attributes && devState.attributes.friendly_name) ? devState.attributes.friendly_name : devEid;
            deviceMap[devEid] = devName;
          }
        }
        if (children.length) roomChildren[roomEid] = children;
      }

      var deviceEntries = [];
      for (var dEid in deviceMap) {
        if (!Object.prototype.hasOwnProperty.call(deviceMap, dEid)) continue;
        deviceEntries.push({ eid: dEid, name: deviceMap[dEid] });
      }

      if (this._config.sort_devices) {
        var roomIndex = {};
        for (var i = 0; i < rooms.length; i++) roomIndex[rooms[i].entity_id] = i;

        var self2 = this;
        deviceEntries.sort(function (a, b) {
          var ra = (deviceRoom[a.eid] && roomIndex[deviceRoom[a.eid]] !== undefined) ? roomIndex[deviceRoom[a.eid]] : 9999;
          var rb = (deviceRoom[b.eid] && roomIndex[deviceRoom[b.eid]] !== undefined) ? roomIndex[deviceRoom[b.eid]] : 9999;
          if (ra !== rb) return ra - rb;

          var av = self2._getStateFloat(a.eid);
          var bv = self2._getStateFloat(b.eid);
          if (bv !== av) return bv - av;

          return a.name.localeCompare(b.name);
        });
      } else {
        deviceEntries.sort(function (a, b) { return a.name.localeCompare(b.name); });
      }

      // -------- Column 2: Consume (manual) --------
      // Any consume item with is_house: true OR entity_id == sensor.all_rooms_power_total will feed rooms.
      var consumeEntities = [];
      var consumeIds = [];

      for (var c = 0; c < this._config.sources.consume.length; c++) {
        var ce = this._config.sources.consume[c];
        if (!ce || typeof ce.entity_id !== "string") continue;

        var isHouse = (ce.is_house === true) || (ce.entity_id === "sensor.all_rooms_power_total");

        var objC = {
          type: "entity",
          entity_id: ce.entity_id,
          name: ce.name || ce.entity_id
        };
        if (ce.color) objC.color = ce.color;

        if (isHouse) {
          var roomIds = [];
          for (var rr = 0; rr < rooms.length; rr++) roomIds.push(rooms[rr].entity_id);
          objC.children = roomIds;
        }

        consumeEntities.push(objC);
        consumeIds.push(ce.entity_id);
      }

      // Fallback: ensure at least one house node exists
      var hasHouseNode = false;
      for (var hc = 0; hc < consumeEntities.length; hc++) {
        if (consumeEntities[hc].children && consumeEntities[hc].children.length) { hasHouseNode = true; break; }
      }
      if (!hasHouseNode) {
        var roomIds2 = [];
        for (var rr2 = 0; rr2 < rooms.length; rr2++) roomIds2.push(rooms[rr2].entity_id);

        consumeEntities.push({
          type: "entity",
          entity_id: "sensor.all_rooms_power_total",
          name: "House consumption",
          children: roomIds2
        });
        consumeIds.push("sensor.all_rooms_power_total");
      }

      // -------- Column 1: Supply (manual) -> children = all consume nodes --------
      var supplyEntities = [];
      for (var s = 0; s < this._config.sources.supply.length; s++) {
        var se = this._config.sources.supply[s];
        if (!se || typeof se.entity_id !== "string") continue;

        var objS = {
          type: "entity",
          entity_id: se.entity_id,
          name: se.name || se.entity_id,
          children: consumeIds.slice()
        };
        if (se.color) objS.color = se.color;

        supplyEntities.push(objS);
      }

      // -------- Column 3 nodes + room colors --------
      var roomColorById = {};
      var roomSectionEntities = [];

      for (var r3 = 0; r3 < rooms.length; r3++) {
        var reid = rooms[r3].entity_id;
        var col = this._hashColor(reid);
        roomColorById[reid] = col;

        var objR = {
          type: "entity",
          entity_id: reid,
          name: rooms[r3].name,
          color: col
        };

        var chList = roomChildren[reid];
        if (chList && chList.length) objR.children = chList;

        roomSectionEntities.push(objR);
      }

      // -------- Column 4 devices, color = room color --------
      var deviceSectionEntities = [];
      for (var k = 0; k < deviceEntries.length; k++) {
        var devId = deviceEntries[k].eid;
        var rId = deviceRoom[devId];
        var devColor = rId ? roomColorById[rId] : undefined;

        var objD = {
          type: "entity",
          entity_id: devId,
          name: deviceEntries[k].name
        };
        if (devColor) objD.color = devColor;

        deviceSectionEntities.push(objD);
      }

      // -------- Build sankey config --------
      var baseConfig = {
        type: "custom:sankey-chart",
        min_state: 0,
        sections: [
          { entities: supplyEntities },        // col 1
          { entities: consumeEntities },       // col 2
          { entities: roomSectionEntities },   // col 3
          { entities: deviceSectionEntities }  // col 4
        ]
      };

      // Only set a title if user provided one (and it's not empty/whitespace)
      const t = (this._config && typeof this._config.title === "string") ? this._config.title.trim() : "";
      if (t) {
        baseConfig.title = t;
      }

      // Merge user sankey options (but never allow user to override sections)
      var merged = {};
      Object.assign(merged, baseConfig);
      Object.assign(merged, this._config.sankey || {});
      merged.sections = baseConfig.sections;

      this._inner.setConfig(merged);
      this._inner.hass = this._hass;
    } catch (e) {
      await this._showMessage("Auto Sankey (4 cols)", "JS error: " + (e && e.message ? e.message : String(e)));
    } finally {
      this._busy = false;
    }
  }
}

customElements.define("sankey-chart-tree-4col", SankeyChartTree4Col);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "sankey-chart-tree-4col",
  name: "Sankey Tree (4 columns, auto)",
  description: "Supply → Consume → Rooms → Devices (auto from Room Power Aggregator)"
});