from pyswidget.device import (
    DeviceType,
    SwidgetDevice
)


class SwidgetOutlet(SwidgetDevice):

    def __init__(self, host,  secret_key: str, ssl: bool) -> None:
        super().__init__(host=host, secret_key=secret_key, ssl=ssl)
        self._device_type = DeviceType.Outlet

    async def current_consumption(self) -> float:
        """Get the current power consumption in watts."""
        return sum([await plug.current_consumption() for plug in self.children])

    async def get_plug_comsumption(self, plug_id):
        """Get the power consumption of a plug in watts."""
        return self.get_child_comsumption(plug_id)
