/* room-power-aggregator-sankey.js
 * Auto-registered by the integration.
 * - Adds entries to the Lovelace card picker (window.customCards)
 * - Best-effort loads dependent modules if missing
 */

function ensureCustomCards() {
  if (!window.customCards) window.customCards = [];
  return window.customCards;
}

function registerCard(type, name, description) {
  const reg = ensureCustomCards();
  if (!reg.some((c) => c.type === type)) {
    reg.push({ type, name, description, preview: true });
  }
}

async function tryImport(url) {
  try {
    await import(url);
  } catch (e) {
    console.debug("[room_power_aggregator] optional import failed", url, e);
  }
}

(() => {
  registerCard(
    "custom:sankey-chart-tree",
    "Sankey Tree (Room Power Aggregator)",
    "Visualise a hierarchy from a root entity and its graph/tree attributes."
  );
  registerCard(
    "custom:sankey-chart-tree-4col",
    "Sankey Tree 4-col (Room Power Aggregator)",
    "4 columns: supply → house → rooms → devices"
  );

  const base = new URL(import.meta.url);
  base.pathname = base.pathname.substring(0, base.pathname.lastIndexOf("/") + 1);

  if (!customElements.get("sankey-chart-tree")) {
    tryImport(new URL("sankey-chart-tree.js", base).toString());
  }
  if (!customElements.get("sankey-chart-tree-4col")) {
    tryImport(new URL("sankey-chart-tree-4col.js", base).toString());
  }
})();
