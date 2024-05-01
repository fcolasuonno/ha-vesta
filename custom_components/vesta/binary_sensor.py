from __future__ import annotations

from collections.abc import Mapping

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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
                VestaConnectivitySensor(coordinator, config_entry, device),
                VestaErrorsSensor(coordinator, config_entry, device),
                VestaRes1Sensor(coordinator, config_entry, device),
                VestaRes2Sensor(coordinator, config_entry, device),
                VestaWordHourSensor(coordinator, config_entry, device),
                VestaWaterReachedTemperatureSensor(coordinator, config_entry, device),
            ]
        )

    async_add_entities(entities)


class VestaConnectivitySensor(VestaEntity, BinarySensorEntity):
    """Sensor to indicate whether a device is currently online."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, BinarySensorEntityDescription(
            key="connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            name="Connected",
        ))

    @property
    def is_on(self) -> bool | None:
        """Return True if online."""
        return self.vesta_device is not None and self.vesta_device.is_online

    @property
    def available(self) -> bool:
        """Return True, as the connectivity sensor is always available."""
        return True


class VestaRes1Sensor(VestaEntity, BinarySensorEntity):
    """Timer started"""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        super().__init__(coordinator, config_entry, device, BinarySensorEntityDescription(
            key="res1",
            device_class=BinarySensorDeviceClass.RUNNING,
            name="Timer started",
        ))

    @property
    def is_on(self) -> bool | None:
        return self.vesta_device is not None and not self.vesta_device.attributes.get("res1")


class VestaRes2Sensor(VestaEntity, BinarySensorEntity):
    """Sensor for res2."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, BinarySensorEntityDescription(
            key="res2",
            entity_category=EntityCategory.DIAGNOSTIC,
            name="Res2",
        ))

    @property
    def is_on(self) -> bool | None:
        return self.vesta_device is not None and self.vesta_device.attributes.get("res2")


class VestaWordHourSensor(VestaEntity, BinarySensorEntity):
    """Sensor for word hour 100 ????."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, BinarySensorEntityDescription(
            key="word_hour",
            entity_category=EntityCategory.DIAGNOSTIC,
            name="Word hour 100?",
        ))

    @property
    def is_on(self) -> bool | None:
        return self.vesta_device is not None and self.vesta_device.attributes.get("word_hour100")


class VestaWaterReachedTemperatureSensor(VestaEntity, BinarySensorEntity):
    """Sensor for water reached temperature."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, BinarySensorEntityDescription(
            key="water_temp_reached",
            device_class=BinarySensorDeviceClass.HEAT,
            name="Water temperature reached",
        ))

    @property
    def is_on(self) -> bool | None:
        return self.vesta_device is not None and self.vesta_device.attributes.get("water_hated")


class VestaErrorsSensor(VestaEntity, BinarySensorEntity):
    """Sensor to indicate an error state."""

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device: GizwitsDevice
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, config_entry, device, BinarySensorEntityDescription(
            key="_has_error",
            name="Errors",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ))

    @property
    def is_on(self) -> bool | None:
        """Return true if reporting an error."""
        if not self.status:
            return None

        errors = []
        for err_num in range(0, 1):
            if self.device.attributes.get("error_code")[err_num] != 0:
                errors.append(err_num)

        return (len(errors) > 0 or
                self.device.attributes.get("low_water_level") or
                self.device.attributes.get("not_working_properly") or
                self.device.attributes.get("loss_power") or
                self.device.attributes.get("no_water") or
                self.device.attributes.get("work_alert"))

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return more detailed error information."""
        if not self.status:
            return None

        return {
            "e00": self.device.attributes.get("error_code")[0],
            "e01": self.device.attributes.get("error_code")[1],
            "low_water_level": self.device.attributes.get("low_water_level"),
            "not_working_properly": self.device.attributes.get("not_working_properly"),
            "loss_power": self.device.attributes.get("loss_power"),
            "no_water": self.device.attributes.get("no_water"),
            "work_alert": self.device.attributes.get("work_alert"),
        }
