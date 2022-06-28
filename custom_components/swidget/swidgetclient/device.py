import json
import logging
import time

from aiohttp import ClientSession, TCPConnector
from enum import auto, Enum
from typing import Any, Dict, List

from .exceptions import SwidgetException
from .websocket import SwidgetWebsocket

_LOGGER = logging.getLogger(__name__)


class DeviceType(Enum):
    """Device type enum."""

    Dimmer = "dimmer"
    Outlet = "outlet"
    Switch = "switch"
    Unknown = -1


class SwidgetDevice:
    def __init__(self, host, secret_key, ssl=False, use_websockets=True):
        self.ip_address = host
        self.ssl = ssl
        self.secret_key = secret_key
        self.use_websockets = use_websockets
        headers = {"x-secret-key": self.secret_key}
        connector = TCPConnector(force_close=True)
        self._session = ClientSession(headers=headers, connector=connector)
        self._last_update = None
        if self.use_websockets:
            self._websocket = SwidgetWebsocket(
                host=self.ip_address,
                secret_key=self.secret_key,
                callback=self.message_callback,
                session=self._session)


    async def stop(self):
        """Stop the websocket."""
        if self._websocket is not None:
            await self._websocket.stop()

    async def message_callback(self, message):
        if message["request_id"] == "summary" or message["request_id"] == "DYNAMIC_UPDATE":
            self.process_summary(message)
        elif message["request_id"] == "state":
            self.process_state(message)

    async def get_summary(self):
        async with self._session.get(
            url=f"https://{self.ip_address}/api/v1/summary", ssl=self.ssl
        ) as response:
            summary = await response.json()
        await self.process_summary(summary)

    async def process_summary(self, summary):
        self.model = summary["model"]
        self.mac_address = summary["mac"]
        self.version = summary["version"]
        self.assemblies = {
            "host": SwidgetAssembly(summary["host"]),
            "insert": SwidgetAssembly(summary["insert"]),
        }
        self.device_type = self.assemblies['host'].type
        self.insert_type = self.assemblies['insert'].type
        self.id = self.assemblies['host'].id
        self._last_update = int(time.time())

    async def get_state(self):
        async with self._session.get(
            url=f"https://{self.ip_address}/api/v1/state", ssl=self.ssl
        ) as response:
            state = await response.json()
        self.process_state(state)

    async def process_state(self, state):
        self.rssi = state["connection"]["rssi"]
        for assembly in self.assemblies:
            for id, component in self.assemblies[assembly].components.items():
                component.functions = state[assembly]["components"][id]
        self._last_update = int(time.time())

    async def update(self):
        if self._last_update is None:
            _LOGGER.debug("Performing the initial update to obtain sysinfo")
        await self.get_summary()
        await self.get_state()

    async def send_command(
        self, assembly: str, component: str, function: str, command: dict
    ):
        data = json.dumps({assembly: {"components": {component: {function: command}}}})

        if self.use_websockets:
            data = json.dumps({"type": "command",
                               "request_id": "command",
                               "payload": data
                               })
            self._websocket.send_str(data)
        else:
            async with self._session.post(
                url=f"https://{self.ip_address}/api/v1/command",
                ssl=self.ssl,
                data=data,
            ) as response:
                state = await response.json()

        function_value = state[assembly]["components"][component][function]
        self.assemblies[assembly].components[component].functions[function] = function_value  # fmt: skip

    async def ping(self):
        """Ping the device to ensure it's devices

        :raises SwidgetException: Raise the exception if there we are unable to connect to the Swidget device
        """
        try:
            async with self._session.get(
                url=f"https://{self.ip_address}/ping",
                ssl=self.ssl
            ) as response:
                return response.text
        except:
            raise SwidgetException

    async def blink(self):
        """Make the device LED blink

        :raises SwidgetException: Raise the exception if there we are unable to connect to the Swidget device
        """
        try:
            async with self._session.get(
                url=f"https://{self.ip_address}/blink?x-user-key=dqMMBX9deuwtkkp784ewTjqo76IYfThV",
                ssl=self.ssl
            ) as response:
                return response.text
        except:
            raise SwidgetException

    @property
    def hw_info(self) -> Dict:
        """
        Return hardware information.

        This returns just a selection of attributes that are related to hardware.
        """
        return {
            "version": self.version,
            "mac_address": self.mac_address,
            "type": self.device_type,
            "id": self.id,
            "model": self.model,
            "insert_type": self.insert_type,
            "features": self.features
        }

    def get_child_consumption(self, plug_id=0):
        """Get the power consumption of a plug in watts."""
        if plug_id == "all":
            return_dict = {}
            for id, properties in self.assemblies['host'].components.items():
                return_dict[f"power_{id}"] = properties.functions['power']['current']
            return return_dict
        return self.assemblies['host'].components[str(plug_id)].functions['power']['current']

    async def total_consumption(self):
        """Get the total power consumption in watts."""
        await self.get_state()
        total_consumption = 0
        for id, properties in self.assemblies['host'].components.items():
            print(vars(properties))
            total_consumption += properties.functions['power']['current']
        return total_consumption

    @property
    def realtime_values(self):
        """Get a dict of realtime value attributes from the insert and host

        :return: A dictionary of insert sensor values and power consumption values
        :rtype: dict
        """
        return_dict = {}
        for feature in self.features:
            return_dict.update(self.get_function_values(feature))
        power_values = self.get_child_consumption("all")
        return_dict.update(power_values)
        return return_dict

    @property
    def features(self) -> List[str]:
        """Return a set of features that the device supports."""
        try:
            return list(self.assemblies['insert'].components.keys())
        except KeyError:
            _LOGGER.debug("Device does not have feature information")
            return set()

    def get_function_values(self, function: str):
        """Return the values of an insert function."""
        return_values = dict()
        for function, data in self.assemblies['insert'].components[function].functions.items():
            if function == "occupied":
                return_values[function] = data['state']
            elif function == "toggle":
                pass
            else:
                return_values[function] = data['now']
        return return_values

    def get_sensor_value(self, function, sensor):
        """Return the value of a sensor."""
        if sensor == "occupied":
            return self.assemblies['insert'].components[function].functions['occupied']['state']
        else:
            return self.assemblies['insert'].components[function].functions[sensor]['now']

    @property
    def is_outlet(self) -> bool:
        """Return True if the device is an outlet."""
        return self.device_type == "outlet"

    @property
    def is_switch(self) -> bool:
        """Return True if the device is a switch"""
        return self.device_type == "switch"

    @property
    def is_dimmer(self) -> bool:
        """Return True if the device is a dimmer"""
        return self.device_type == "dimmer"

    @property
    def friendly_name(self) -> str:
        """Return a friendly description of the device"""
        return f"Swidget {self.device_type} w/{self.insert_type} insert"

    def __repr__(self):
        if self._last_update is None:
            return f"<{self.device_type} at {self.ip_address} - update() needed>"
        return f"<{self.device_type} model {self.model} at {self.ip_address}>"


class SwidgetAssembly:
    def __init__(self, summary: dict):
        self.type = summary["type"]
        self.components = {
            c["id"]: SwidgetComponent(c["functions"]) for c in summary["components"]
        }
        self.id = summary.get("id")
        self.error = summary.get("error")


class SwidgetComponent:
    def __init__(self, functions):
        self.functions = {f: None for f in functions}


class SwidgetException(Exception):
    """Base exception for device errors."""
