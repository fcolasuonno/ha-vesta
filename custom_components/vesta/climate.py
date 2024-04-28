"""Climate platform support."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import ATTR_HVAC_MODE, HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature, PRECISION_TENTHS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VestaCoordinator
from .const import DOMAIN
from .entity import VestaEntity
from .pygizwits import GizwitsDevice

_MIN_TEMP_C = 5
_MIN_TEMP_F = 41
_MAX_TEMP_C = 95
_MAX_TEMP_F = 203


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities."""
    coordinator: VestaCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[VestaEntity] = []

    for device_id, device in coordinator.device_manager.devices.items():
        entities.extend(
            [
                VestaClimate(coordinator, config_entry, device_id, device),
            ]
        )
    async_add_entities(entities)


class VestaClimate(VestaEntity, ClimateEntity):
    """A vesta cooking device."""

    _attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = PRECISION_TENTHS
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
            self,
            coordinator: VestaCoordinator,
            config_entry: ConfigEntry,
            device_id: str,
            device: GizwitsDevice
    ) -> None:
        """Initialize cooker."""
        super().__init__(coordinator, config_entry, device)
        self._attr_unique_id = f"{device_id}_cooker"

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return the current mode (HEAT or OFF)."""
        if not self.status:
            return None
        return HVACMode.HEAT if self.device.attributes["onoff"] else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | str | None:
        """Return the current running action (HEATING or IDLE)."""
        if not self.status:
            return None
        heat_on = self.device.attributes["onoff"]
        target_reached = self.device.attributes["water_hated"]
        return (
            HVACAction.HEATING if (heat_on and not target_reached) else HVACAction.IDLE
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self.status:
            return None
        return self.device.attributes["real_temp_integer"] + self.device.attributes["real_temp_decimal"] / 10.0

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if not self.status:
            return None
        return self.device.attributes["set_temp_integer"] + self.device.attributes["set_temp_decimal"] / 10.0

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        if not self.status or self.device.attributes["temp_unit"] == 0:
            return str(UnitOfTemperature.CELSIUS)
        else:
            return str(UnitOfTemperature.FAHRENHEIT)

    @property
    def min_temp(self) -> float:
        """
        Get the minimum temperature that a user can set.

        As the cooker can be switched between temperature units, this needs to be dynamic.
        """
        return (
            _MIN_TEMP_C
            if self.temperature_unit == UnitOfTemperature.CELSIUS
            else _MIN_TEMP_F
        )

    @property
    def max_temp(self) -> float:
        """
        Get the maximum temperature that a user can set.

        As the cooker can be switched between temperature units, this needs to be dynamic.
        """
        return (
            _MAX_TEMP_C
            if self.temperature_unit == UnitOfTemperature.CELSIUS
            else _MAX_TEMP_F
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        should_heat = hvac_mode == HVACMode.HEAT
        await self.device.set_device_attribute("onoff", should_heat)
        await self.coordinator.async_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if target_temperature is None:
            return

        if hvac_mode := kwargs.get(ATTR_HVAC_MODE):
            should_heat = hvac_mode == HVACMode.HEAT
            await self.deviceset_device_attributes("onoff", should_heat)

        temp_int = int(target_temperature)
        temp_decimal = int((target_temperature - temp_int)*10)
        await self.device.set_device_attributes({"set_temp_integer": temp_int, "set_temp_decimal": temp_decimal})

        await self.coordinator.async_refresh()
