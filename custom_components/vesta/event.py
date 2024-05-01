from __future__ import annotations

from homeassistant.components.event import EventEntity, EventEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
                VestaFinishedCookingEvent(coordinator, config_entry, device),
            ]
        )
    async_add_entities(entities)


class VestaFinishedCookingEvent(VestaEntity, EventEntity):
    """Event for finished cooking."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        super().__init__(coordinator, config_entry, device, EventEntityDescription(
            key="cooking_finish",
            name="Finished cooking",
            event_types=["cooking_finish"]
        ))

    @callback
    def _async_handle_event(self) -> None:
        finished = self.device.attributes.get("cooking_finish")
        if finished:
            self._trigger_event(self.event_types[0], {"cooking_finish": finished})
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.coordinator.async_add_listener(self._async_handle_event)
