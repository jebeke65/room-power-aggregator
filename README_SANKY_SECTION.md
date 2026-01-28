## Sankey charts (automatic topology)

You can visualize your Room Power Aggregator topology as a Sankey diagram (Supply → Consume → Rooms → Devices).

**Recommended:** install the companion HACS plugin repo `room-power-aggregator-sankey` (see docs/SankeyCards.md).

Manual alternative:
1. Copy these files to `/config/www/`:
   - `www/sankey-chart-tree.js`
   - `www/sankey-chart-tree-4col.js`
2. Add Dashboard Resources (JavaScript module):
   - `/local/sankey-chart-tree.js?v=1`
   - `/local/sankey-chart-tree-4col.js?v=1`
3. Use the example in `lovelace/sankey-4col-example.yaml`.

Docs: `docs/SankeyCards.md`
