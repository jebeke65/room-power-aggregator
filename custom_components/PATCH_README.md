# Patch: bundle the Sankey Lovelace cards inside the integration

This patch adds a **frontend bundle** to `room_power_aggregator` and registers it automatically in the HA UI.

## What you get
- `custom_components/room_power_aggregator/frontend/room-power-aggregator-sankey.js` (bundle; contains both cards)
- also included in the same folder:
  - `sankey-chart-tree.js`
  - `sankey-chart-tree-4col.js`

## How it works
- The integration serves `/room_power_aggregator/*` from the `frontend/` directory
- The integration calls `frontend.add_extra_js_url()` so the bundle is auto-loaded (no manual Resources step)

## How to apply
Copy/merge the contents of this zip into the **root** of your existing GitHub repo.

### IMPORTANT
- If you already have `custom_components/room_power_aggregator/__init__.py` and/or `const.py`,
  **merge** the changes instead of overwriting blindly.
- Specifically, keep your existing `PLATFORMS` and other constants; only ensure:
  - `DOMAIN = "room_power_aggregator"`
  - `PLATFORMS` contains `"sensor"`

## After install
- Restart Home Assistant
- The cards should be available as:
  - `custom:sankey-chart-tree`
  - `custom:sankey-chart-tree-4col`

Prerequisite: MindFreeze `ha-sankey-chart` must still be installed.
