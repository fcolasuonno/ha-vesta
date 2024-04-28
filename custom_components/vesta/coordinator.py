"""Data update coordinator for the Vesta API."""

import asyncio
from datetime import timedelta
from logging import getLogger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .vesta.api import VestaApi, VestaApiResults

_LOGGER = getLogger(__name__)


class VestaUpdateCoordinator(DataUpdateCoordinator[VestaApiResults]):
    """Update coordinator that polls the device status for all devices in an account."""

    def __init__(self, hass: HomeAssistant, api: VestaApi) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Vesta API",
            update_interval=timedelta(seconds=30),
        )
        self.api = api

    async def _async_update_data(self) -> VestaApiResults:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with asyncio.timeout(10):
                await self.api.refresh_bindings()
                return await self.api.fetch_data()
        except Exception as err:
            _LOGGER.exception("Data update failed")
            raise UpdateFailed(f"Error communicating with API: {err}") from err
