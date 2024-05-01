"""Select platform support."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
                VestaTempUnitSelect(coordinator, config_entry, device),
            ]
        )
    async_add_entities(entities)


class VestaTempUnitSelect(VestaEntity, SelectEntity):
    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize toggle."""
        super().__init__(coordinator, config_entry, device, SelectEntityDescription(
            key="temp_unit",
            name="Unit",
            options=["C", "F"],
            entity_category=EntityCategory.CONFIG,
        ))

    @property
    def current_option(self) -> str | None:
        if not self.status:
            return None
        t = self.device.attributes.get("temp_unit")
        if t is None:
            return None
        return self.options[t]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.device.set_device_attribute("temp_unit", self.options.index(option))
        await self.coordinator.async_refresh()
