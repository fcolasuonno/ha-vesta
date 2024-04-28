"""Home Assistant entity descriptions."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import VestaCoordinator
from .pygizwits import GizwitsDevice
from .const import DOMAIN


class VestaEntity(CoordinatorEntity[VestaCoordinator]):
    """Vesta base entity type."""

    def __init__(
        self,
        coordinator: VestaCoordinator,
        config_entry: ConfigEntry,
        device: GizwitsDevice,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.device = device

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.device_id)},
            name=self.device.alias,
            model=self.device.product_name,
            manufacturer="Vesta",
        )

    @property
    def vesta_device(self) -> GizwitsDevice | None:
        return self.device

    @property
    def status(self) -> bool | None:
        """Get status data for the cooker providing this entity."""
        return self.device.is_online and bool(self.device.attributes)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.device.is_online

    @property
    def name(self):
        """Name of the entity."""
        return self.vesta_device.alias