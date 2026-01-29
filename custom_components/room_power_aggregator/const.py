from __future__ import annotations

from pathlib import Path
import json
from typing import Final

DOMAIN: Final[str] = "room_power_aggregator"

CONF_LABEL_NAME: Final[str] = "label_name"
CONF_ONLY_POWER_DEVICE_CLASS: Final[str] = "only_power_device_class"
CONF_INCLUDE_KW: Final[str] = "include_kw"
CONF_DEBUG: Final[str] = "debug"

PLATFORMS: Final[list[str]] = ["sensor"]
UPDATE_INTERVAL: Final[int] = 5  # seconds

# --- Frontend (embedded Lovelace card) ---
_MANIFEST_PATH = Path(__file__).parent / "manifest.json"
with open(_MANIFEST_PATH, encoding="utf-8") as f:
    INTEGRATION_VERSION: Final[str] = json.load(f).get("version", "0.0.0")

# Base URL under which this integration serves its JS resources
URL_BASE: Final[str] = f"/{DOMAIN}"

# JS modules to auto-register in Lovelace resources (storage mode)
JSMODULES: Final[list[dict[str, str]]] = [
    {"name": "Sankey Tree 4col", "filename": "sankey-chart-tree-4col.js", "version": INTEGRATION_VERSION},
    {"name": "Sankey Tree", "filename": "sankey-chart-tree.js", "version": INTEGRATION_VERSION},
    {"name": "Room Power Aggregator Sankey Loader", "filename": "room-power-aggregator-sankey.js", "version": INTEGRATION_VERSION},
]
