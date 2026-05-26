DOMAIN = "room_power_aggregator"

CONF_LABEL_NAME = "label_name"
CONF_ONLY_POWER_DEVICE_CLASS = "only_power_device_class"
CONF_INCLUDE_KW = "include_kw"
CONF_DEBUG = "debug"

PLATFORMS = ["sensor"]

# Coordinator refresh interval (seconds)
UPDATE_INTERVAL = 5

# Frontend (served from custom_components/room_power_aggregator/frontend/)
FRONTEND_URL_PATH = f"/{DOMAIN}"
FRONTEND_FILES = [
    "sankey-chart-tree.js",
    "sankey-chart-tree-4col.js",
    "room-power-aggregator-sankey.js",
]

CONF_SUPPLY_ENTITIES = "supply_entities"
CONF_CONSUME_ENTITIES = "consume_entities"
CONF_HIDE_DEVICES_COLUMN = "hide_devices_column"

CONF_TREE_SENSOR = "tree_sensor"
