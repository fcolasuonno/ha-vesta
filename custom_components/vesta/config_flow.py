"""Config flow for Vesta integration."""

from __future__ import annotations

from logging import getLogger

from typing import Any

from aiohttp import ClientConnectionError
from homeassistant.config_entries import ConfigFlow
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .pygizwits import GizwitsClient, DeviceManager, GizwitsUserDoesNotExistException, GizwitsIncorrectPasswordException

from .const import (
    CONF_REGION,
    CONF_APP_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

_LOGGER = getLogger(__name__)
_STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="password")
        ),
        vol.Required(CONF_APP_ID, description={"suggested_value": "9a6d8b3d46a246fca38dea306f98e19e"}): str,
        vol.Required(CONF_REGION): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=GizwitsClient.Region.US.value, label="US"),
                    selector.SelectOptionDict(value=GizwitsClient.Region.EU.value, label="EU"),
                ]
            )
        ),
    }
)


async def validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    username = user_input[CONF_USERNAME]
    password = user_input[CONF_PASSWORD]
    region = GizwitsClient.Region.from_value(user_input[CONF_REGION])
    app_id = user_input[CONF_APP_ID]
    session = async_get_clientsession(hass)

    # Create a device manager and login
    device_manager = DeviceManager(session, app_id, region)

    await device_manager.login(username, password)

    return {"title": username}


class VestaConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for vesta."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def async_step_user(self, user_input: dict[str, str] | None = None):
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except GizwitsUserDoesNotExistException:
                errors["base"] = "user_does_not_exist"
            except GizwitsIncorrectPasswordException:
                errors["base"] = "incorrect_password"
            except ClientConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown_connection_error"

        return self.async_show_form(
            step_id="user", data_schema=_STEP_USER_DATA_SCHEMA, errors=errors
        )
