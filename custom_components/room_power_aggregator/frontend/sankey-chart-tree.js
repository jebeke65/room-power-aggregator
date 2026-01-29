class SankeyChartTree extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = null;
    this._inner = null;
    this._busy = false;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    if (!config || !config.tree_entity) {
      throw new Error("Missing required config: tree_entity");
    }

    this._config = {
      tree_entity: config.tree_entity,
      tree_attribute: config.tree_attribute || "graph",
      sankey: config.sankey || {},
      room_entity_match: config.room_entity_match || "_power_total",
      exclude_room_entity: config.exclude_room_entity || "sensor.all_rooms_power_total",
    };

    this._render();
  }

  getCardSize() {
    return 6;
  }

  async _ensureInner() {
    if (this._inner) return;

    // Wait for MindFreeze element to exist (important in Safari/resource order/caching)
    if (!customElements.get("sankey-chart")) {
      await customElements.whenDefined("sankey-chart");
    }

    this._inner = document.createElement("sankey-chart");
    this.appendChild(this._inner);
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

  async _renderError(msg) {
    await this._ensureInner();
    this._inner.setConfig({
      type: "custom:sankey-chart",
      title: "Sankey Tree (error)",
      min_state: 0,
      sections: [
        {
          entities: [
            {
              type: "entity",
              entity_id: this._config ? this._config.tree_entity : "sensor.none",
              name: msg,
            },
          ],
        },
      ],
    });
    this._inner.hass = this._hass;
  }

  async _render() {
    if (this._busy) return;
    if (!this._hass || !this._config) return;

    this._busy = true;
    try {
      await this._ensureInner();

      const treeState = this._hass.states[this._config.tree_entity];
      if (!treeState) {
        await this._renderError("tree_entity not found");
        return;
      }

      const raw = treeState.attributes[this._config.tree_attribute];
      const graph = this._safeParse(raw);

      if (!graph || !graph.nodes) {
        await this._renderError("graph attribute missing/invalid (expected JSON with nodes)");
        return;
      }

      // nodes: { "RoomName": {entity_id:"sensor.xxx"}, ... }
      const nodes = graph.nodes;
      const roomEntities = [];
      const deviceMap = {}; // eid -> name
      const roomChildren = {}; // room_eid -> [device_eid]

      // Determine rooms = *_power_total (except all_rooms)
      for (const name in nodes) {
        if (!Object.prototype.hasOwnProperty.call(nodes, name)) continue;
        const eid = nodes[name] && nodes[name].entity_id;
        if (typeof eid !== "string") continue;
        if (eid === this._config.exclude_room_entity) continue;
        if (eid.indexOf(this._config.room_entity_match) === -1) continue;
        roomEntities.push({ name: name, entity_id: eid });
      }

      if (!roomEntities.length) {
        await this._renderError("No room entities found (expected *_power_total nodes)");
        return;
      }

      // Build children from each room's source_entities attribute
      for (let i = 0; i < roomEntities.length; i++) {
        const r = roomEntities[i];
        const st = this._hass.states[r.entity_id];
        const sources = st && st.attributes && st.attributes.source_entities;

        const children = [];
        if (Array.isArray(sources)) {
          for (let j = 0; j < sources.length; j++) {
            const devEid = sources[j];
            if (typeof devEid !== "string") continue;
            children.push(devEid);

            const devState = this._hass.states[devEid];
            const devName =
              (devState && devState.attributes && devState.attributes.friendly_name) || devEid;

            deviceMap[devEid] = devName;
          }
        }
        if (children.length) roomChildren[r.entity_id] = children;
      }

      // Sections:
      // 1) rooms with children
      // 2) devices
      roomEntities.sort(function (a, b) {
        return a.name.localeCompare(b.name);
      });

      const section1Entities = [];
      for (let i = 0; i < roomEntities.length; i++) {
        const r = roomEntities[i];
        const obj = { type: "entity", entity_id: r.entity_id, name: r.name };
        const ch = roomChildren[r.entity_id];
        if (ch && ch.length) obj.children = ch;
        section1Entities.push(obj);
      }

      const deviceEntries = [];
      for (const eid in deviceMap) {
        if (!Object.prototype.hasOwnProperty.call(deviceMap, eid)) continue;
        deviceEntries.push({ eid: eid, name: deviceMap[eid] });
      }
      deviceEntries.sort(function (a, b) {
        return a.name.localeCompare(b.name);
      });

      const section2Entities = [];
      for (let i = 0; i < deviceEntries.length; i++) {
        section2Entities.push({
          type: "entity",
          entity_id: deviceEntries[i].eid,
          name: deviceEntries[i].name,
        });
      }

      const sankeyConfig = Object.assign(
        {
          type: "custom:sankey-chart",
          title: "Rooms → Devices (auto)",
          min_state: 0,
          sections: [
            { entities: section1Entities },
            { entities: section2Entities },
          ],
        },
        this._config.sankey || {}
      );

      this._inner.setConfig(sankeyConfig);
      this._inner.hass = this._hass;
    } catch (e) {
      // If anything blows up, show it instead of going blank
      await this._renderError("JS error: " + (e && e.message ? e.message : String(e)));
    } finally {
      this._busy = false;
    }
  }
}

customElements.define("sankey-chart-tree", SankeyChartTree);

// Optional: register so HA can show it as a custom card (not always in picker, but helps)
window.customCards = window.customCards || [];
window.customCards.push({
  type: "sankey-chart-tree",
  name: "Sankey Tree (auto)",
  description: "Auto-generate MindFreeze sankey config from a tree sensor attribute",
});
