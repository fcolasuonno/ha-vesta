"""Vesta API."""

import asyncio
from dataclasses import dataclass
import json
from logging import getLogger
from time import time

from typing import Any

from aiohttp import ClientResponse, ClientSession

from .model import (
    AIRJET_V01_BUBBLES_MAP,
    HYDROJET_BUBBLES_MAP,
    VestaDevice,
    VestaDeviceStatus,
    VestaDeviceType,
    VestaUserToken,
    BubblesLevel,
    HydrojetFilter,
    HydrojetHeat,
)

_LOGGER = getLogger(__name__)
_HEADERS = {
    "Content-type": "application/json",
    "X-Gizwits-Application-Id": "9a6d8b3d46a246fca38dea306f98e19e",
    "User-Agent": "GizWifiSDK (v18.21071915)",
    "language": "zh-CN"
}
_TIMEOUT = 10


@dataclass
class VestaApiResults:
    """A snapshot of device status reports returned from the API."""

    devices: dict[str, VestaDeviceStatus]


class VestaException(Exception):
    """An exception while using the API."""


class VestaOfflineException(VestaException):
    """Device is offline."""

    def __init__(self) -> None:
        """Construct the exception."""
        super().__init__("Device is offline")


class VestaAuthException(VestaException):
    """An authentication error."""


class VestaTokenInvalidException(VestaAuthException):
    """Auth token is invalid or expired."""


class VestaUserDoesNotExistException(VestaAuthException):
    """User does not exist."""


class VestaIncorrectPasswordException(VestaAuthException):
    """Password is incorrect."""


async def _raise_for_status(response: ClientResponse) -> None:
    """Raise an exception based on the response."""
    if response.ok:
        return

    # Try to parse out the Vesta error code
    try:
        api_error = await response.json()
    except Exception:  # pylint: disable=broad-except
        response.raise_for_status()

    error_code = api_error.get("error_code", 0)
    if error_code == 9004:
        raise VestaTokenInvalidException()
    if error_code == 9005:
        raise VestaUserDoesNotExistException()
    if error_code == 9042:
        raise VestaOfflineException()
    if error_code == 9020:
        raise VestaIncorrectPasswordException()

    # If we don't understand the error code, provide more detail for debugging
    response.raise_for_status()


class VestaApi:
    """Vesta API."""

    def __init__(self, session: ClientSession, user_token: str, api_root: str) -> None:
        """Initialize the API with a user token."""
        self._session = session
        self._user_token = user_token
        self._api_root = api_root

        # Maps device IDs to device info
        self.devices: dict[str, VestaDevice] = {}

        # Cache containing state information for each device received from the API
        # This is used to work around an annoyance where changes to settings via
        # a POST request are not immediately reflected in a subsequent GET request.
        #
        # When updating state via HA, we update the cache and return this value
        # until the API can provide us with a response containing a timestamp
        # more recent than the local update.
        self._state_cache: dict[str, VestaDeviceStatus] = {}

    @staticmethod
    async def get_user_token(
            session: ClientSession, username: str, password: str, api_root: str
    ) -> VestaUserToken:
        """
        Login and obtain a user token.

        The server rate-limits requests for this fairly aggressively.
        """
        body = {"username": username, "password": password, "lang": "en"}

        async with asyncio.timeout(_TIMEOUT):
            response = await session.post(
                f"{api_root}/app/login", headers=_HEADERS, json=body
            )
            await _raise_for_status(response)
            api_data = await response.json()

        return VestaUserToken(
            api_data["uid"], api_data["token"], api_data["expire_at"]
        )

    async def refresh_bindings(self) -> None:
        """Refresh and store the list of devices available in the account."""
        self.devices = {
            device.device_id: device for device in await self._get_devices()
        }

    async def _get_devices(self) -> list[VestaDevice]:
        """Get the list of devices available in the account."""
        api_data = await self._do_get(f"{self._api_root}/app/bindings")
        # {'protoc': 3,
        # 'ws_port': 8080,
        # 'port_s': 8883,
        # 'gw_did': None,
        # 'host': 'ussandbox.gizwits.com',
        # 'sleep_duration': 0,
        # 'port': 1883,
        # 'product_key': '3db0c479df0a4df78948a1771489f493',
        # 'state_last_timestamp': 1713558391,
        # 'role': 'special',
        # 'is_sandbox': True,
        # 'type': 'normal',
        # 'product_name': 'SousVideCooker',
        # 'is_disabled': False,
        #            'dev_alias': 'Souuuuus vide ',
        # 'mesh_id': None,
        # 'is_online': False,
        # 'dev_label': [],
        # 'wss_port': 8880,
        # 'remark': '',
        #             'did': 'hfVgPNuSnBkZhdpM4JeyM6',
        # 'mac': 'f0fe6bf91480',
        # 'passcode': 'PFDBGXHUYW',
        # 'is_low_power': False}
        return [
            VestaDevice(
                protocol_version=raw["protoc"],
                device_id=raw["did"],
                product_name=raw["product_name"],
                alias=raw["dev_alias"],
                mcu_soft_version=raw["mcu_soft_version"],
                mcu_hard_version=raw["mcu_hard_version"],
                wifi_soft_version=raw["wifi_soft_version"],
                wifi_hard_version=raw["wifi_hard_version"],
                is_online=raw["is_online"],
            )
            for raw in api_data["devices"]
        ]

    async def fetch_data(self) -> VestaApiResults:
        """Fetch the latest data for all devices."""
        for did, device_info in self.devices.items():
            latest_data = await self._do_get(
                f"{self._api_root}/app/devdata/{did}/latest"
            )

            # Get the age of the data according to the API
            api_update_timestamp = latest_data["updated_at"]

            # Zero indicates the device is offline
            # This has been observed after a device was offline for a few months
            if api_update_timestamp == 0:
                # In testing, the 'attrs' dictionary has been observed to be empty
                _LOGGER.debug("No data available for device %s", did)
                continue

            # Work out whether the received API update is more recent than the
            # locally cached state
            local_update_timestamp = 0
            cached_state: VestaDeviceStatus | None
            if cached_state := self._state_cache.get(did):
                local_update_timestamp = cached_state.timestamp

            # If the API timestamp is more recent, update the cache
            if api_update_timestamp < local_update_timestamp:
                _LOGGER.debug(
                    "Ignoring update for device %s as local data is newer", did
                )
                continue

            _LOGGER.debug("New data received for device %s", did)
            device_attrs = latest_data["attr"]
            self._state_cache[did] = VestaDeviceStatus(
                latest_data["updated_at"], device_attrs
            )

            attr_dump = json.dumps(device_attrs)

            if device_info.device_type == VestaDeviceType.UNKNOWN:
                _LOGGER.warning(
                    "Status for unknown device type '%s' returned: %s",
                    device_info.product_name,
                    attr_dump,
                )
            else:
                _LOGGER.debug(
                    "Status for device type '%s' returned: %s",
                    device_info.product_name,
                    attr_dump,
                )

        return VestaApiResults(self._state_cache)

    async def airjet_spa_set_power(self, device_id: str, power: bool) -> None:
        """Turn the spa on/off."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = 1 if power else 0
        _LOGGER.debug("Setting power to %s", "ON" if power else "OFF")
        await self._do_control_post(device_id, power=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["spa_power"] = api_value
        if not power:
            # When powering off, all other functions also turn off
            cached_state.attrs["filter_power"] = 0
            cached_state.attrs["heat_power"] = 0
            cached_state.attrs["wave_power"] = 0

    async def airjet_spa_set_filter(self, device_id: str, filtering: bool) -> None:
        """Turn the filter pump on/off on a spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = 1 if filtering else 0
        _LOGGER.debug("Setting filter mode to %s", "ON" if filtering else "OFF")
        await self._do_control_post(device_id, filter_power=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["filter_power"] = api_value
        if filtering:
            cached_state.attrs["spa_power"] = 1
        else:
            cached_state.attrs["wave_power"] = 0
            cached_state.attrs["heat_power"] = 0

    async def airjet_spa_set_heat(self, device_id: str, heat: bool) -> None:
        """
        Turn the heater on/off on a spa device.

        Turning the heater on will also turn on the filter pump.
        """
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = 1 if heat else 0
        _LOGGER.debug("Setting heater mode to %s", "ON" if heat else "OFF")
        await self._do_control_post(device_id, heat_power=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["heat_power"] = api_value
        if heat:
            cached_state.attrs["spa_power"] = 1
            cached_state.attrs["filter_power"] = 1

    async def airjet_spa_set_target_temp(
            self, device_id: str, target_temp: int
    ) -> None:
        """Set the target temperature on a spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        target_temp = int(target_temp)
        _LOGGER.debug("Setting target temperature to %d", target_temp)
        await self._do_control_post(device_id, temp_set=target_temp)
        cached_state.timestamp = int(time())
        cached_state.attrs["temp_set"] = target_temp

    async def airjet_spa_set_locked(self, device_id: str, locked: bool) -> None:
        """Lock or unlock the physical control panel on a spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = 1 if locked else 0
        _LOGGER.debug("Setting lock state to %s", "ON" if locked else "OFF")
        await self._do_control_post(device_id, locked=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["locked"] = api_value

    async def airjet_spa_set_bubbles(self, device_id: str, bubbles: bool) -> None:
        """Turn the bubbles on/off on an Airjet spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        _LOGGER.debug("Setting bubbles mode to %s", "ON" if bubbles else "OFF")
        await self._do_control_post(device_id, wave_power=1 if bubbles else 0)
        cached_state.timestamp = int(time())
        cached_state.attrs["wave_power"] = bubbles
        if bubbles:
            cached_state.attrs["spa_power"] = 1

    async def airjet_v01_spa_set_bubbles(
            self, device_id: str, bubbles: BubblesLevel
    ) -> None:
        """Control the bubbles on an Airjet V01 spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = AIRJET_V01_BUBBLES_MAP.to_api_value(bubbles)
        _LOGGER.debug("Setting bubbles mode to %d", api_value)
        await self._do_control_post(device_id, wave=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["wave"] = api_value
        if bubbles != BubblesLevel.OFF:
            cached_state.attrs["power"] = 1

    async def hydrojet_spa_set_power(self, device_id: str, power: bool) -> None:
        """Turn the spa on/off."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        _LOGGER.debug("Setting power to %s", "ON" if power else "OFF")
        await self._do_control_post(device_id, power=1 if power else 0)
        cached_state.timestamp = int(time())
        cached_state.attrs["power"] = power
        if not power:
            # When powering off, all other functions also turn off
            cached_state.attrs["filter"] = 0
            cached_state.attrs["heat"] = 0
            cached_state.attrs["wave"] = HYDROJET_BUBBLES_MAP.off_val

    async def hydrojet_spa_set_filter(
            self, device_id: str, filtering: HydrojetFilter
    ) -> None:
        """Turn the filter pump on/off on a spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        _LOGGER.debug("Setting filter mode to %s", "ON" if filtering else "OFF")
        await self._do_control_post(device_id, filter=filtering)
        cached_state.timestamp = int(time())
        cached_state.attrs["filter"] = filtering
        if filtering == HydrojetFilter.ON:
            cached_state.attrs["power"] = 1
        else:
            cached_state.attrs["wave"] = HYDROJET_BUBBLES_MAP.off_val
            cached_state.attrs["heat"] = 0

    async def hydrojet_spa_set_heat(self, device_id: str, heat: HydrojetHeat) -> None:
        """
        Turn the heater on/off on a Hydrojet spa device.

        Turning the heater on will also turn on the filter pump.
        """
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        _LOGGER.debug("Setting heater mode to %s", "ON" if heat else "OFF")
        await self._do_control_post(device_id, heat=heat)
        cached_state.timestamp = int(time())
        cached_state.attrs["heat"] = heat
        if heat == HydrojetHeat.ON:
            cached_state.attrs["power"] = 1
            cached_state.attrs["filter"] = HydrojetFilter.ON

    async def hydrojet_spa_set_target_temp(
            self, device_id: str, target_temp: int
    ) -> None:
        """Set the target temperature on a Hydrojet spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        target_temp = int(target_temp)
        _LOGGER.debug("Setting target temperature to %d", target_temp)
        await self._do_control_post(device_id, Tset=target_temp)
        cached_state.timestamp = int(time())
        cached_state.attrs["Tset"] = target_temp

    async def hydrojet_spa_set_bubbles(
            self, device_id: str, bubbles: BubblesLevel
    ) -> None:
        """Control the bubbles on a Hydrojet spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = HYDROJET_BUBBLES_MAP.to_api_value(bubbles)
        _LOGGER.debug("Setting bubbles mode to %d", api_value)
        await self._do_control_post(device_id, wave=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["wave"] = api_value
        if bubbles != BubblesLevel.OFF:
            cached_state.attrs["power"] = 1

    async def hydrojet_spa_set_jets(self, device_id: str, jets: bool) -> None:
        """Control the jets on a Hydrojet spa device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        api_value = 1 if jets else 0
        _LOGGER.debug("Setting jets to %s", "ON" if jets else "OFF")
        await self._do_control_post(device_id, jet=api_value)
        cached_state.timestamp = int(time())
        cached_state.attrs["jet"] = api_value
        if jets:
            cached_state.attrs["power"] = 1

    async def pool_filter_set_power(self, device_id: str, power: bool) -> None:
        """Control power to a pump device."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        _LOGGER.debug("Setting power to %s", "ON" if power else "OFF")
        await self._do_control_post(device_id, power=1 if power else 0)
        cached_state.timestamp = int(time())
        cached_state.attrs["power"] = power

    async def pool_filter_set_time(self, device_id: str, hours: int) -> None:
        """Set filter timeout for for pool devices."""
        if (cached_state := self._state_cache.get(device_id)) is None:
            raise VestaException(f"Device '{device_id}' is not recognised")

        _LOGGER.debug("Setting filter timeout to %d hours", hours)
        await self._do_control_post(device_id, time=hours)
        cached_state.timestamp = int(time())
        cached_state.attrs["time"] = hours

    async def _do_get(self, url: str) -> dict[str, Any]:
        """Make an API call to the specified URL, returning the response as a JSON object."""
        headers = dict(_HEADERS)
        headers["X-Gizwits-User-token"] = self._user_token
        async with asyncio.timeout(_TIMEOUT):
            response = await self._session.get(url, headers=headers)
            await _raise_for_status(response)

            # All API responses are encoded using JSON, however the headers often incorrectly
            # state 'text/html' as the content type.
            # We have to disable the check to avoid an exception.
            response_json: dict[str, Any] = await response.json(content_type=None)
            return response_json

    async def _do_control_post(
            self, device_id: str, **kwargs: int | str
    ) -> dict[str, Any]:
        return await self._do_post(
            f"{self._api_root}/app/control/{device_id}",
            {"attrs": kwargs},
        )

    async def _do_post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        """Make an API call to the specified URL, returning the response as a JSON object."""
        headers = dict(_HEADERS)
        headers["X-Gizwits-User-token"] = self._user_token
        async with asyncio.timeout(_TIMEOUT):
            response = await self._session.post(url, headers=headers, json=body)
            await _raise_for_status(response)

            # All API responses are encoded using JSON, however the headers often incorrectly
            # state 'text/html' as the content type.
            # We have to disable the check to avoid an exception.
            response_json: dict[str, Any] = await response.json(content_type=None)
            return response_json
