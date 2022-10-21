from .device import (
    DeviceType,
)
from .swidgetswitch import SwidgetSwitch

class SwidgetTimerSwitch(SwidgetSwitch):

    def __init__(self, host,  secret_key: str, ssl: bool) -> None:
        super().__init__(host=host, secret_key=secret_key, ssl=ssl)
        self._device_type = DeviceType.TimerSwitch

    async def set_timer(self, seconds):
        """Set the brightness of the device."""
        await self.send_command(
            assembly="host", component="0", function="timer", command={"duration": seconds}
        )