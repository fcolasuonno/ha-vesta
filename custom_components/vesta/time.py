from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
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
                VestaTimer(coordinator, config_entry, device),
            ]
        )
    async_add_entities(entities)


class VestaTimer(VestaEntity, TimeEntity):
    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        super().__init__(coordinator, config_entry, device, TimeEntityDescription(
            key="cooking_time",
            name="Cooking Time",
            icon="mdi:timer-edit-outline",
        ))

    @property
    def native_value(self) -> time | None:
        if not self.status:
            return None
        return time(hour=self.device.attributes["set_time_hour"], minute=self.device.attributes["set_time_min"])

    async def async_set_value(self, value: time) -> None:
        if value is None:
            return
        hour = value.hour
        minute = value.minute
        await self.device.set_device_attributes({"set_time_hour": hour, "set_time_min": minute})
        await self.coordinator.async_refresh()
