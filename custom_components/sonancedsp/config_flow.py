"""Config flow for the Sonance DSP integration."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import async_read_basic_status
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    try:
        status = await async_read_basic_status(
            data[CONF_HOST],
            data[CONF_PORT],
            async_get_clientsession(hass),
        )
    except (aiohttp.ClientError, TimeoutError, OSError, ValueError) as err:
        raise CannotConnect from err

    serial_number = status.serial_number or data[CONF_HOST]
    amplifier_name = status.amplifier_name or data[CONF_HOST]
    return {
        "title": amplifier_name,
        "serial_number": serial_number,
    }


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sonance DSP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
