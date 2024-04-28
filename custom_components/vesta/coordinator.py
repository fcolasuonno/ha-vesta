"""Data update coordinator for the Vesta API."""

import asyncio
from logging import getLogger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .pygizwits import DeviceManager, GizwitsDevice

_LOGGER = getLogger(__name__)


class VestaCoordinator(DataUpdateCoordinator[dict[str, GizwitsDevice]]):
    """Update coordinator that polls the device status for all devices in an account."""

    def __init__(self, hass: HomeAssistant, device_manager: DeviceManager) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Vesta Device Manager",
        )
        self.device_manager = device_manager
        self.devices:dict[str, GizwitsDevice]= {}

    def status_update(self, device: GizwitsDevice):
        self.devices[device.device_id] = device
        self.async_set_updated_data(self.devices)

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data for the first time when a config entry is setup."""
        try:
            async with asyncio.timeout(10):
                self.device_manager.on("device_status_update", self.status_update)
                self.devices = await self.device_manager.get_devices()
                for device_id, device in self.devices.items():
                    await device.subscribe_to_device_updates()
        except Exception as err:
            _LOGGER.exception("Data update failed")
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, GizwitsDevice]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        return self.devices

