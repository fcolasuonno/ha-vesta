"""Config flow for Vesta integration."""

from __future__ import annotations

import asyncio
from logging import getLogger

from typing import Any

from aiohttp import ClientConnectionError
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .vesta.api import (
    VestaApi,
    VestaIncorrectPasswordException,
    VestaUserDoesNotExistException,
)
from .const import (
    CONF_API_ROOT,
    CONF_API_ROOT_EU,
    CONF_API_ROOT_US,
    CONF_PASSWORD,
    CONF_USER_TOKEN,
    CONF_USER_TOKEN_EXPIRY,
    CONF_USERNAME,
    DOMAIN,
)

_LOGGER = getLogger(__name__)
_STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_API_ROOT): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=CONF_API_ROOT_EU, label="EU"),
                    selector.SelectOptionDict(value=CONF_API_ROOT_US, label="US"),
                ]
            )
        ),
    }
)


async def validate_input(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Returns data to be stored in the config entry.
    """
    username = user_input[CONF_USERNAME]
    api_root = user_input[CONF_API_ROOT]
    session = async_get_clientsession(hass)
    async with asyncio.timeout(10):
        token = await VestaApi.get_user_token(
            session, username, user_input[CONF_PASSWORD], api_root
        )

    config_entry_data = dict(user_input)
    config_entry_data[CONF_USER_TOKEN] = token.user_token
    config_entry_data[CONF_USER_TOKEN_EXPIRY] = token.expiry
    return config_entry_data


class VestaConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for vesta."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=_STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            config_entry_data = await validate_input(self.hass, user_input)
        except VestaUserDoesNotExistException:
            errors["base"] = "user_does_not_exist"
        except VestaIncorrectPasswordException:
            errors["base"] = "incorrect_password"
        except ClientConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown_connection_error"
        else:
            return self.async_create_entry(
                title=user_input[CONF_USERNAME], data=config_entry_data
            )

        return self.async_show_form(
            step_id="user", data_schema=_STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
