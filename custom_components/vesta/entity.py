"""Home Assistant entity descriptions."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VestaUpdateCoordinator
from .vesta.model import VestaDevice, VestaDeviceStatus
from .const import DOMAIN


class VestaEntity(CoordinatorEntity[VestaUpdateCoordinator]):
    """Vesta base entity type."""

    def __init__(
        self,
        coordinator: VestaUpdateCoordinator,
        config_entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Device information for the spa providing this entity."""

        device_info = self.coordinator.api.devices[self.device_id]

        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=device_info.alias,
            model=device_info.device_type.value,
            manufacturer="Vesta",
        )

    @property
    def vesta_device(self) -> VestaDevice | None:
        """Get status data for the spa providing this entity."""
        device: VestaDevice | None = self.coordinator.api.devices.get(self.device_id)
        return device

    @property
    def status(self) -> VestaDeviceStatus | None:
        """Get status data for the spa providing this entity."""
        status: VestaDeviceStatus | None = self.coordinator.data.devices.get(
            self.device_id
        )
        return status

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.Vesta_device is not None and self.Vesta_device.is_online
