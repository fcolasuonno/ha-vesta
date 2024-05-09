from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription, ButtonDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VestaCoordinator
from .const import DOMAIN
from .entity import VestaEntity
from .pygizwits import GizwitsDevice


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VestaCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[VestaEntity] = []

    for device in coordinator.device_manager.devices.values():
        entities.extend(
            [
                VestaStartTimerButton(coordinator, config_entry, device),
            ]
        )
    async_add_entities(entities)


class VestaStartTimerButton(VestaEntity, ButtonEntity):
    """Event for finished cooking."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        super().__init__(coordinator, config_entry, device, ButtonEntityDescription(
            key="res1",
            name="Start timer",
            device_class=ButtonDeviceClass.UPDATE
        ))

    async def async_press(self) -> None:
        await self.device.set_device_attribute("res1", 0)
