from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_LABEL_NAME,
    CONF_ONLY_POWER_DEVICE_CLASS,
    CONF_INCLUDE_KW,
    CONF_DEBUG,
)


class RoomPowerAggregatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Room Power Aggregator",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_LABEL_NAME): str,
                vol.Optional(CONF_ONLY_POWER_DEVICE_CLASS, default=True): bool,
                vol.Optional(CONF_INCLUDE_KW, default=True): bool,
                vol.Optional(CONF_DEBUG, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return RoomPowerAggregatorOptionsFlowHandler(entry)


class RoomPowerAggregatorOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        data = {**self.entry.data, **self.entry.options}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_LABEL_NAME, default=data.get(CONF_LABEL_NAME, "")): str,
                vol.Optional(CONF_ONLY_POWER_DEVICE_CLASS,
                             default=data.get(CONF_ONLY_POWER_DEVICE_CLASS, True)): bool,
                vol.Optional(CONF_INCLUDE_KW,
                             default=data.get(CONF_INCLUDE_KW, True)): bool,
                vol.Optional(CONF_DEBUG, default=data.get(CONF_DEBUG, False)): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
