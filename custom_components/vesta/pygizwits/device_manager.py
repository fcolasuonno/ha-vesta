from typing import Dict, cast

from aiohttp import ClientSession
from pyee.base import EventEmitter

from .exceptions import GizwitsDeviceNotBound
from .gizwits_client import GizwitsClient
from .gizwits_device import GizwitsDevice
from .websocket_connection import WebsocketConnection


class DeviceManager(EventEmitter):
    """Gizwits device manager."""

    def __init__(
        self,
        session: ClientSession,
        app_id: str,
        region: GizwitsClient.Region = GizwitsClient.Region.DEFAULT,
    ):
        super().__init__()
        self.client = GizwitsClient(session, self, app_id, region)
        self.sockets: Dict[str, WebsocketConnection] = {}
        self.devices: Dict[str, GizwitsDevice] = {}

    async def login(self, username: str, password: str) -> bool:
        """
        Login to the Gizwits OpenAPI.

        Args:
            username (str): The username for the login request.
            password (str): The password for the login request.
        Returns:
            bool
        Raises:
            GizwitsException: If an error occurs during the login process.
        """
        await self.client.login(username, password)
        return True

    async def get_devices(self):
        """
        Asynchronously retrieves the devices.

        returns:
            Dict[str, GizwitsDevice]: The bindings obtained from the client.
        """
        return await self.client.get_bindings(self)

    def get_device(self, device_id) -> GizwitsDevice:
        """
        Retrieves a GizwitsDevice object from the devices dictionary
        matching the given device ID.

        Args:
            device_id (str): The ID of the device.
        Returns:
            GizwitsDevice: The device.
        Raises:
            GizwitsDeviceNotBound: If the device ID is not found.
        """
        if device_id not in self.devices:
            raise GizwitsDeviceNotBound(device_id)
        return self.devices[device_id]

    async def sync_devices(self):
        """
        Updates devices with their latest attributes from the server.

        Returns:
            None
        """
        return await self.client.fetch_devices()

    async def got_device_status_update(self, device_update: dict):
        """
        Asynchronously takes in a device update and produces a GizwitsDeviceReport.

        Args:
            device_update (dict): A dictionary containing information about the device.
        Returns:
            None
        """
        did = device_update["did"]
        device_info = cast(GizwitsDevice, self.devices.get(did))
        device_info.attributes = device_update["attrs"]
        self.emit('device_status_update', device_info)
