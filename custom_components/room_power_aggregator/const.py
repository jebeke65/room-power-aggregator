DOMAIN = "room_power_aggregator"

CONF_LABEL_NAME = "label_name"
CONF_ONLY_POWER_DEVICE_CLASS = "only_power_device_class"
CONF_INCLUDE_KW = "include_kw"
CONF_DEBUG = "debug"

PLATFORMS = ["sensor"]
UPDATE_INTERVAL = 5  # seconds

# Frontend (bundled Lovelace cards)
FRONTEND_URL_PATH = f"/{DOMAIN}"
FRONTEND_BUNDLE_FILENAME = "room-power-aggregator-sankey.js"
