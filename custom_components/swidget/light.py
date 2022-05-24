"""Support for TPLink lights."""
from __future__ import annotations

from collections.abc import Sequence
import logging
from typing import Any, Final, cast

from .swidgetdimmer import SwidgetDimmer
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SwidgetDataUpdateCoordinator
from .entity import CoordinatedSwidgetEntity, async_refresh_after

_LOGGER = logging.getLogger(__name__)

SERVICE_RANDOM_EFFECT = "random_effect"
SERVICE_SEQUENCE_EFFECT = "sequence_effect"


VAL = vol.Range(min=0, max=100)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [SwidgetSmartDimmer(cast(SwidgetDimmer, coordinator.device), coordinator)]
    )


class SwidgetSmartDimmer(CoordinatedSwidgetEntity, LightEntity):
    """Representation of a TPLink Smart Bulb."""

    device: SwidgetDimmer

    def __init__(
        self,
        device: SwidgetDimmer,
        coordinator: SwidgetDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device, coordinator)
        # For backwards compat with pyHS100
        self._attr_unique_id = device.mac_address.replace(":", "").upper()

    @async_refresh_after
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness, transition = self._async_extract_brightness_transition(**kwargs)
        await self._async_turn_on_with_brightness(brightness, transition)

    async def _async_turn_on_with_brightness(
        self, brightness: int | None, transition: int | None
    ) -> None:
        # Fallback to adjusting brightness or turning the bulb on
        if brightness is not None:
            await self.device.set_brightness(brightness, transition=transition)
            return
        await self.device.turn_on(transition=transition)  # type: ignore[arg-type]

    @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.device.turn_off()

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return round((self.device.brightness * 255.0) / 100.0)

