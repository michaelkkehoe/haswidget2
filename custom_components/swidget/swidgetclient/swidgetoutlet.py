from .device import (
    DeviceType,
    SwidgetDevice
)


class SwidgetOutlet(SwidgetDevice):

    def __init__(self, host,  secret_key: str, ssl: bool) -> None:
        super().__init__(host=host, secret_key=secret_key, ssl=ssl)
        self._device_type = DeviceType.Outlet

    @property  # type: ignore
    def is_on(self) -> bool:
        """Return whether device is on."""
        dimmer_state = self.assemblies['host'].components["0"].functions['toggle']["state"]
        if dimmer_state == "on":
            return True
        return False

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

    async def turn_on_usb_insert(self):
        """Turn the USB insert on."""
        await self.send_command(
            assembly="insert", component="usb", function="toggle", command={"state": "on"}
        )

    async def turn_off_usb_insert(self):
        """Turn the USB insert off."""
        await self.send_command(
            assembly="insert", component="usb", function="toggle", command={"state": "off"}
        )

    @property  # type: ignore
    def usb_is_on(self) -> bool:
        """Return whether USB is on."""
        usb_state = self.assemblies['insert'].components["usb"].functions['toggle']["state"]
        if usb_state == "on":
            return True
        return False