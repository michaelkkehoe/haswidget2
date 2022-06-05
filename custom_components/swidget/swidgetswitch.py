from .device import (
    DeviceType,
    SwidgetDevice
)

class SwidgetSwitch(SwidgetDevice):

    def __init__(self, host,  secret_key: str, ssl: bool) -> None:
        super().__init__(host=host, secret_key=secret_key, ssl=ssl)
        self._device_type = DeviceType.Switch

    async def current_consumption(self) -> float:
        """Get the current power consumption in watts."""
        return sum([await plug.current_consumption() for plug in self.children])


    @property  # type: ignore
    def is_on(self) -> bool:
        """Return whether device is on."""
        dimmer_state = self.assemblies['host'].components["0"].functions['toggle']["state"]
        if dimmer_state == "on":
            return True
        return False
