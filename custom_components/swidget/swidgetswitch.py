from .device import (
    DeviceType,
    SwidgetDevice
)

class SwidgetSwitch(SwidgetDevice):

    def __init__(self, host,  secret_key: str, ssl: bool) -> None:
        super().__init__(host=host, secret_key=secret_key, ssl=ssl)
        self._device_type = DeviceType.Switch
