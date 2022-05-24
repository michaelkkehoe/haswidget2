import json
import logging
import time

from aiohttp import ClientSession, TCPConnector
from enum import auto, Enum
from typing import Any, Dict, List

from pyswidget.exceptions import SwidgetException

_LOGGER = logging.getLogger(__name__)


class DeviceType(Enum):
    """Device type enum."""

    Dimmer = auto()
    Outlet = auto()
    Switch = auto()
    Unknown = -1


class SwidgetDevice:
    def __init__(self, host, secret_key, ssl):
        self.ip_address = host
        self.ssl = ssl
        self.secret_key = secret_key
        headers = {"x-secret-key": self.secret_key}
        connector = TCPConnector(force_close=True)
        self._session = ClientSession(headers=headers, connector=connector)
        self._last_update = None

    async def get_summary(self):
        async with self._session.get(
            url=f"https://{self.ip_address}/api/v1/summary", ssl=self.ssl
        ) as response:
            summary = await response.json()

        self.model = summary["model"]
        self.version = summary["version"]
        self.assemblies = {
            "host": SwidgetAssembly(summary["host"]),
            "insert": SwidgetAssembly(summary["insert"]),
        }
        self.device_type = self.assemblies['host'].type
        self.id = self.assemblies['host'].id
        self._last_update = int(time.time())

    async def get_state(self):
        async with self._session.get(
            url=f"https://{self.ip_address}/api/v1/state", ssl=self.ssl
        ) as response:
            state = await response.json()

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

        async with self._session.post(
            url=f"https://{self.ip_address}/api/v1/command",
            ssl=self.ssl,
            data=data,
        ) as response:
            state = await response.json()

        function_value = state[assembly]["components"][component][function]
        self.assemblies[assembly].components[component].functions[function] = function_value  # fmt: skip

    async def ping(self):
        try:
            async with self._session.get(
                url=f"https://{self.ip_address}/ping?x-secret-key={self.secret_key}",
                ssl=self.ssl
            ) as response:
                return response.text
        except:
            raise SwidgetException

    async def turn_on(self):
        """Turn the device on."""
        await self.send_command(
            assembly="host", component="0", function="toggle", command={"state": "on"}
        )

    async def turn_off(self):
        """Turn the device off."""
        await self.send_command(
            assembly="host", component="0", function="toggle", command={"state": "off"}
        )

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
            "model": self.model
        }

    async def get_child_comsumption(self, plug_id=0):
        """Get the power consumption of a plug in watts."""
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
            if function == "motion":
                return_values[function] = data['state']
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
        """Return True if the device is a plug."""
        return self.device_type == DeviceType.Outlet

    @property
    def is_switch(self) -> bool:
        """Return True if the device is a plug."""
        return self.device_type == DeviceType.Switch

    @property
    def is_dimmer(self) -> bool:
        """Return True if the device is a Dimmer"""
        return self.device_type == DeviceType.Dimmer

    def __repr__(self):
        if self._last_update is None:
            return f"<{self._device_type} at {self.ip_address} - update() needed>"
        return f"<{self._device_type} model {self.model} at {self.ip_address} , is_on: {self.is_on} - dev specific: {self.state_information}>"


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
