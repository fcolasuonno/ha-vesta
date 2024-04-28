"""Home Assistant sensor descriptions."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
    """Set up sensor entities."""
    coordinator: VestaCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[VestaEntity] = []

    for device_id, device in coordinator.device_manager.devices.items():
        entities.extend(
            [
                VestaRunningTime(coordinator, config_entry, device),
                VestaRemainingTime(coordinator, config_entry, device),
            ]
        )
    async_add_entities(entities)


class VestaRunningTime(VestaEntity, SensorEntity):
    """A sensor based on device metadata."""
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    should_poll = False

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, SensorEntityDescription(
            key="running_time",
            name="Running time",
            icon="mdi:timeline-clock-outline"
        ))

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.status:
            return None
        return self.device.attributes["runnning_time_hour"] * 60 + self.device.attributes["runnning_time_min"]

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Return the state attributes of the last update."""
        if not self.status:
            return None

        return {
            "runnning_time_hour": self.device.attributes["runnning_time_hour"],
            "runnning_time_min": self.device.attributes["runnning_time_min"]
        }


class VestaRemainingTime(VestaEntity, SensorEntity):
    """A sensor based on device metadata."""
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    should_poll = False

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, SensorEntityDescription(
            key="remaining_time",
            name="Remaining time",
            icon="mdi:progress-clock"
        ))

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.status:
            return None
        return self.device.attributes["remaining_time_hour"] * 60 + self.device.attributes["remaining_time_min"]

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Return the state attributes of the last update."""
        if not self.status:
            return None

        return {
            "remaining_time_hour": self.device.attributes["remaining_time_hour"],
            "remaining_time_min": self.device.attributes["remaining_time_min"]
        }
