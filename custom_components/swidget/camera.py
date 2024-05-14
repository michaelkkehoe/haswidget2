
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.components import ffmpeg
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.components.ffmpeg import CONF_EXTRA_ARGUMENTS, get_ffmpeg_manager
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SwidgetDataUpdateCoordinator
from .entity import CoordinatedSwidgetEntity

from swidgetclient.device import SwidgetDevice


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camera."""
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    if "video" in coordinator.device.insert_type:
        async_add_entities(
            [SwidgetCameraEntity(coordinator.device, coordinator)]
        )


class SwidgetCameraEntity(CoordinatedSwidgetEntity, Camera):
    """Representation of a Swidget camera."""

    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_name = None

    def __init__(
        self,
        device: SwidgetDevice,
        coordinator: SwidgetDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device, coordinator)
        Camera.__init__(self)
        self._extra_arguments: str = "-pred 1"

    @property
    def use_stream_for_stills(self) -> bool:
        return True

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        # return self.device.stream_source
        return f"rtsp://{self.device.ip_address}:8554/ph254"

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        return await ffmpeg.async_get_image(
            self.hass,
            f"rtsp://{self.device.ip_address}:8554/ph254",
            extra_cmd="-pred 1",
            width=width,
            height=height,
        )