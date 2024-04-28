"""The Vesta integration."""

from __future__ import annotations

from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import VestaCoordinator
from .pygizwits import DeviceManager, GizwitsClient

from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_REGION,
    CONF_APP_ID,
    DOMAIN,
)

_LOGGER = getLogger(__name__)
_PLATFORMS: list[Platform] = [
    # Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.TIME,
    # Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vesta from a config entry."""
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    region = GizwitsClient.Region.from_value(entry.data.get(CONF_REGION))
    app_id = entry.data.get(CONF_APP_ID)

    session = async_get_clientsession(hass)

    # Create a device manager and login
    device_manager = DeviceManager(session, app_id, region)

    try:
        await device_manager.login(username, password)
    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.error("Failed to login: %s", ex)
        raise ConfigEntryNotReady from ex

    coordinator = VestaCoordinator(hass, device_manager)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(
        entry, _PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)