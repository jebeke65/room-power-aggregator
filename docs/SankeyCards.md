# Sankey cards (optional)

These cards build **automatic Sankey diagrams** from the sensors created by **Room Power Aggregator**.

They work with the **MindFreeze ha-sankey-chart** Lovelace card:
- Install it via HACS: search for **"Sankey Chart"** (MindFreeze/ha-sankey-chart)
- Add its resource (HACS does this automatically for most installs)

## Option 1 (recommended): install as a HACS *plugin*
Use the separate plugin repository **room-power-aggregator-sankey** (generated in this deliverable set).
Then add **one** Lovelace resource from `/hacsfiles/...`.

## Option 2: manual install (copy to /config/www)
Copy the JS files from this repository into Home Assistant:

- `www/sankey-chart-tree.js` → `/config/www/sankey-chart-tree.js`
- `www/sankey-chart-tree-4col.js` → `/config/www/sankey-chart-tree-4col.js`

Then add Resources (Settings → Dashboards → Resources), type **JavaScript module**:

- `/local/sankey-chart-tree.js?v=1`
- `/local/sankey-chart-tree-4col.js?v=1`

Safari tip: bump the `?v=` number when you change the file to avoid caching.

## Example: 4 columns (Supply → Consume → Rooms → Devices)

See `lovelace/sankey-4col-example.yaml`.
