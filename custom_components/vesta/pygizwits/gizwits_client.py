import asyncio
from dataclasses import dataclass
from enum import Enum
from time import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urljoin

from aiohttp import ClientError, ClientSession

if TYPE_CHECKING:
    from .device_manager import DeviceManager

from .exceptions import (
    GizwitsDeviceNotBound,
    GizwitsException,
    raise_for_status,
)
from .gizwits_device import GizwitsDevice
from .logger import logger


@dataclass
class GizwitsUserToken:
    """User authentication token, obtained following a successful login."""

    user_id: str
    user_token: str
    expiry: int


class GizwitsClient:
    """Gizwits client representing a connection to the Gizwits server."""

    class Region(Enum):
        """Gizwits region."""

        US = "us"
        EU = "eu"
        DEFAULT = "default"

    def __init__(
        self,
        session: ClientSession,
        device_manager: 'DeviceManager',
        app_id: str,
        region: Region = Region.DEFAULT,
    ):
        self.base_url = self.get_base_url(region)
        self.region = region
        self.app_id = app_id
        self.token: str = ""
        self.uid: str = ""
        self.session = session
        self.device_manager = device_manager
        self.task = None

    @staticmethod
    def get_base_url(region: Region) -> str:
        """
        Retrieves the base URL for the given region.
        Args:
            region (Region): The region for which to retrieve the base URL.
        Returns:
            str: The base URL corresponding to the given region.
        """
        if region == GizwitsClient.Region.US:
            return "https://usapi.gizwits.com"
        if region == GizwitsClient.Region.EU:
            return "https://euapi.gizwits.com"
        return "https://api.gizwits.com"

    def token_expired(self):
        """
        Emits a 'token_expired' event.

        Returns:
            None
        """
        self.device_manager.emit('token_expired')

    async def get_token(self, username: str, password: str) -> GizwitsUserToken:
        """
        Retrieves the user token using the provided username and password.

        Args:
            username (str): The username for the login request.
            password (str): The password for the login request.
        Returns:
            GizwitsUserToken: An instance of GizwitsUserToken.
        Raises:
            GizwitsException: If an error occurs during the token retrieval process.
        """
        # Set the URL and headers
        url = urljoin(self.base_url, "/app/login")
        headers = {"X-Gizwits-Application-Id": self.app_id}

        # Set the payload
        payload = {"username": username, "password": password[0:16], "lang": "en"}

        # Send a POST request and get the response
        async with self.session.post(url, headers=headers, json=payload) as response:
            await raise_for_status(response)

            # Extract the token and uid from the response
            data = await response.json()

        # Return the uid and token
        return GizwitsUserToken(data["uid"], data["token"], data["expire_at"])

    async def login(self, username: str, password: str) -> None:
        """
        Login to the Gizwits OpenAPI.

        Sends a POST request to the login endpoint with the given username and password.
        The X-Gizwits-Application-Id header is set to the app_id stored in the class.
        The payload contains the given username, password, and language code.
        If the request is successful, the response json is extracted to set the token
        and uid class variables. Finally, the uid and token are returned as a tuple.

        Args:
            username (str): The username for the login request.
            password (str): The password for the login request.
        Returns:
            None
        Raises:
            GizwitsException: If an error occurs during the login process.
        """
        login_data = await self.get_token(username, password)
        self.token = login_data.user_token
        self.uid = login_data.user_id
        # Schedule the token refresh
        expiry_time = login_data.expiry - int(time())  # Calculate time remaining until expiry
        self.task = asyncio.create_task(self.refresh_token(expiry_time, username, password))

    async def refresh_token(self, expiry_time, username, password):
        """
        Handle token expiry.

        Asynchronously refreshes the token by sleeping until the token expiry time,
        then calling the token_expired() method and refreshing the token by calling
        the login method with the provided username and password.

        Args:
            expiry_time (int): An integer representing the duration
            in seconds until the token expires.
            username (str): A string representing the username.
            password (str): A string representing the password.
        Returns:
            None
        """
        # Sleep until the token expiry time
        await asyncio.sleep(expiry_time)
        self.token_expired()

        # Refresh the token
        await self.login(username, password)

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        """
        An async function that retrieves data from a specific API endpoint.

        Args:
            endpoint (str): The API endpoint to retrieve data from.
        Returns:
            Dict[str, Any]: A dictionary containing the response data.
        """
        url = urljoin(self.base_url, endpoint)
        headers = {
            "X-Gizwits-Application-Id": self.app_id,
            "X-Gizwits-User-Token": self.token,
        }

        async with self.session.get(url, headers=headers) as response:
            await raise_for_status(response)
            # Needed as the api does not always set the correct content type
            response_json: Dict[str, Any] = await response.json(content_type=None)
            return response_json

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously sends a POST request to the specified endpoint with data.

        Args:
            endpoint (str): The endpoint to send the request to.
            data (Dict[str, Any]): The data to send with the request.

        Returns:
            Dict[str, Any]: A dictionary representing the JSON data
            returned by the response.
        """
        url = urljoin(self.base_url, endpoint)
        headers = {
            "X-Gizwits-Application-Id": self.app_id,
            "X-Gizwits-User-Token": self.token,
        }
        headers = {k: v if v is not None else "" for k, v in headers.items()}
        post = self.session.post(url, headers=headers, json=data)
        async with post as response:
            await raise_for_status(response)
            # Needed as the api does not always set the correct content type
            response_json: Dict[str, Any] = await response.json(content_type=None)
            return response_json

    async def get_bindings(
        self, device_manager: 'DeviceManager', device_types: Optional[List[str]] = None
    ) -> Dict[str, GizwitsDevice]:
        """
        Asynchronously retrieves device bindings from Gizwits.

        Using the '/app/bindings' endpoint

        Args:
            device_manager (DeviceManager): The device manager.
            device_types (Optional[List[str]]): A list of device types to retrieve
        Returns:
            A dictionary of GizwitsDevice objects, where the key is the device ID.

        Raises:
            GizwitsException: if an error occurs while retrieving the device bindings.
        """
        bound_devices: Dict[str, GizwitsDevice] = {}
        limit = 20
        skip = 0
        more = True
        url = "/app/bindings"
        while more:
            query = f"?show_disabled=0&limit={limit}&skip={skip}"
            endpoint = url + query
            try:
                response_data = await self._get(endpoint)
                devices = response_data.get('devices', [])
                for device in devices:
                    did = device["did"]
                    bound_devices[did] = GizwitsDevice(
                        device["did"],
                        device["dev_alias"],
                        device["product_name"],
                        device['mac'],
                        device['ws_port'],
                        device['host'],
                        device['wss_port'],
                        device['protoc'],
                        device["mcu_soft_version"],
                        device["mcu_hard_version"],
                        device["wifi_soft_version"],
                        device["is_online"],
                        self,
                        device_manager,
                    )
                if len(devices) == limit:
                    skip += limit
                else:
                    more = False
            except ClientError as e:
                logger.error("Request error: %s", e)
                raise GizwitsException(
                    "Error occurred while retrieving device bindings."
                ) from e
            except Exception as e:
                logger.error("Error: %s", e)
                raise GizwitsException(
                    "Unknown error occurred while retrieving device bindings."
                ) from e
        if device_types is not None:
            filtered_devices = {
                did: device
                for did, device in bound_devices.items()
                if device.product_name in device_types
            }
            device_manager.devices = filtered_devices
            return filtered_devices

        device_manager.devices = bound_devices
        return bound_devices

    async def refresh_bindings(self, device_manager: 'DeviceManager') -> None:
        """
        Asynchronously refreshes the bindings of the current session

        Returns:
            None
        """
        self.device_manager.devices = await self.get_bindings(device_manager)
        self.device_manager.emit('bindings_refreshed', self.device_manager.devices)

    async def fetch_device(self, device_id: str) -> GizwitsDevice:
        """
        Asynchronously fetches the latest data for a specific device.

        Args:
            device_id (str): The ID of the device to fetch.
        Returns:
            GizwitsDevice: The latest data for the device.
        Raises:
            GizwitsDeviceNotBound: if the device is not bound.
        """
        if device_id not in self.device_manager.devices:
            raise GizwitsDeviceNotBound()
        device_info = self.device_manager.devices[device_id]
        logger.debug("Fetching device %s", device_id)
        latest_data = await self._get(f"/app/devdata/{device_id}/latest")
        # Get the age of the data according to the API
        api_update_timestamp = latest_data["updated_at"]

        # Zero indicates the device is offline
        # This has been observed after a device was offline for a few months
        if api_update_timestamp == 0:
            # In testing, the 'attrs' dictionary has been observed to be empty
            device_info.is_online = False
            device_info.attributes = {}
            return device_info

        device_info.attributes = latest_data
        return device_info

    async def fetch_devices(self) -> dict[str, GizwitsDevice]:
        """
        Asynchronously fetches the latest data for all currently bound devices.

        Only devices that are currently bound will be included in the results.

        Returns:
            A dictionary where each key is a device ID and each value is a
            `GizwitsDevice` object containing the latest data for that
            device.
        """
        results: dict[str, GizwitsDevice] = {}

        if not self.device_manager.devices:
            return results

        for did, device_info in self.device_manager.devices.items():
            logger.debug("Fetching device %s", did)
            latest_data = await self._get(f"/app/devdata/{did}/latest")
            # Get the age of the data according to the API
            api_update_timestamp = latest_data["updated_at"]

            # Zero indicates the device is offline
            # This has been observed after a device was offline for a few
            # months
            if api_update_timestamp == 0:
                # In testing, the 'attrs' dictionary has been observed to be
                # empty
                device_info.is_online = False
                device_info.attributes = {}
                continue

            device_info.attributes = latest_data
            results[did] = device_info
        return results

    async def set_device_attribute(
        self, device_id: str, attribute: str, value: Any
    ) -> None:
        """
        Asynchronously sets the value of a device attribute.

        Args:
            device_id (str): The ID of the device.
            attribute (str): The name of the attribute.
            value (Any): The value to set.
        Returns:
            Coroutine
        """
        await self.set_device_attributes(device_id, {attribute: value})
        return

    async def set_device_attributes(
        self, device_id: str, attributes: dict[str, Any]
    ) -> None:
        """
        Asynchronously sets the value of multiple device attributes.

        Args:
            device_id (str): The ID of the device.
            attributes (dict[str, Any]): The attributes to set.
        Returns:
            None
        """
        if device_id not in self.device_manager.devices:
            raise GizwitsDeviceNotBound()
        payload: Dict[str, Any] = {"attrs": dict(attributes)}
        try:
            await self._post(f"/app/control/{device_id}", payload)
        except Exception as e:
            logger.error("Error: %s", e)
            raise GizwitsException(
                "Unknown error occurred while setting device attributes."
            ) from e
        return
