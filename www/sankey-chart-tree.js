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
    if (!config || !config.tree_entity) throw new Error("Missing required config: tree_entity");

    this._config = {
      tree_entity: config.tree_entity,
      tree_attribute: config.tree_attribute || "graph",
      root_name: config.root_name || "House",
      max_depth: (config.max_depth === undefined || config.max_depth === null) ? 10 : config.max_depth,
      sankey: config.sankey || {},
    };

    if (!this._inner) {
      this._inner = document.createElement("sankey-chart");
      this.appendChild(this._inner);
    }
  }

  getCardSize() {
    return 6;
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

  _renderError(msg) {
    this._inner.setConfig({
      type: "custom:sankey-chart",
      title: "Sankey Tree",
      sections: [
        {
          entities: [
            {
              type: "entity",
              entity_id: this._config.tree_entity,
              name: msg,
            },
          ],
        },
      ],
    });
    this._inner.hass = this._hass;
  }

  async _ensureInner() {
    if (this._inner) return;
    if (!customElements.get("sankey-chart")) {
      await customElements.whenDefined("sankey-chart");
    }
    this._inner = document.createElement("sankey-chart");
    this.appendChild(this._inner);
  }

  async _render() {
    if (this._busy) return;
    if (!this._hass || !this._config) return;

    this._busy = true;
    try {
      await this._ensureInner();

      const stateObj = this._hass.states[this._config.tree_entity];
      const raw = stateObj && stateObj.attributes ? stateObj.attributes[this._config.tree_attribute] : null;
      const graph = this._safeParse(raw);

      if (!graph || !graph.nodes || !graph.links) {
        this._renderError("Invalid graph attribute (expected JSON with nodes + links)");
        return;
      }

      const nodes = graph.nodes || {};
      const links = graph.links || [];

      const nodeNames = new Set(Object.keys(nodes));
      const nodeEntity = new Map();
      for (const n of nodeNames) {
        const eid = nodes[n] ? nodes[n].entity_id : null;
        if (typeof eid === "string" && eid.indexOf(".") !== -1) nodeEntity.set(n, eid);
      }

      let rootName = this._config.root_name;
      if (!nodeNames.has(rootName)) {
        const it = nodeNames.values().next();
        rootName = it && !it.done ? it.value : rootName;
      }
      if (!nodeEntity.has(rootName)) {
        this._renderError('Root node "' + rootName + '" has no valid entity_id');
        return;
      }

      const out = new Map();
      for (const n of nodeNames) out.set(n, []);
      for (const l of links) {
        const from = l.from;
        const to = l.to;
        if (!nodeEntity.has(from) || !nodeEntity.has(to)) continue;
        out.get(from).push(to);
      }

      const maxDepth = this._config.max_depth;
      const depth = new Map();
      const q = [rootName];
      depth.set(rootName, 0);

      while (q.length) {
        const cur = q.shift();
        const d = depth.get(cur);
        if (d >= maxDepth) continue;

        for (const nxt of (out.get(cur) || [])) {
          if (!depth.has(nxt)) {
            depth.set(nxt, d + 1);
            q.push(nxt);
          }
        }
      }

      const byDepth = new Map();
      for (const ent of depth.entries()) {
        const n = ent[0];
        const d = ent[1];
        if (!byDepth.has(d)) byDepth.set(d, []);
        byDepth.get(d).push(n);
      }
      let maxSeenDepth = 0;
      for (const d of byDepth.keys()) if (d > maxSeenDepth) maxSeenDepth = d;

      const entityIndex = new Map();
      const sections = [];

      for (let d = 0; d <= maxSeenDepth; d++) {
        const names = (byDepth.get(d) || []).slice().sort();
        const ents = [];
        for (const name of names) {
          const eid = nodeEntity.get(name);
          if (!eid) continue;
          const obj = { type: "entity", entity_id: eid, name: name };
          entityIndex.set(name, obj);
          ents.push(obj);
        }
        if (ents.length) sections.push({ entities: ents });
      }

      if (!sections.length) {
        this._renderError("No renderable nodes (missing entity_id mapping)");
        return;
      }

      for (const ent of entityIndex.entries()) {
        const fromName = ent[0];
        const fromObj = ent[1];
        const children = [];
        for (const toName of (out.get(fromName) || [])) {
          const toObj = entityIndex.get(toName);
          if (!toObj) continue;
          children.push(toObj.entity_id);
        }
        if (children.length) fromObj.children = children;
      }

      const sankeyConfig = Object.assign(
        { type: "custom:sankey-chart", sections: sections },
        this._config.sankey || {}
      );
      sankeyConfig.sections = sections;

      this._inner.setConfig(sankeyConfig);
      this._inner.hass = this._hass;
    } catch (e) {
      this._renderError("JS error: " + (e && e.message ? e.message : String(e)));
    } finally {
      this._busy = false;
    }
  }
}

customElements.define("sankey-chart-tree", SankeyChartTree);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "sankey-chart-tree",
  name: "Sankey Tree (auto)",
  description: "Auto-generate MindFreeze sankey config from a tree sensor attribute",
});
