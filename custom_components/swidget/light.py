"""Support for TPLink lights."""
from __future__ import annotations

from collections.abc import Sequence
import logging
from typing import Any, Final, cast

from .swidgetdimmer import SwidgetDimmer
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
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
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    if coordinator.device.is_dimmer:
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
        self._attr_unique_id = device.id

    @async_refresh_after
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if (brightness := kwargs.get(ATTR_BRIGHTNESS)) is not None:
            brightness = round((brightness * 100.0) / 255.0)
        await self._async_turn_on_with_brightness(brightness)

    @async_refresh_after
    async def _async_turn_on_with_brightness(
        self, brightness: int | None) -> None:
        # Fallback to adjusting brightness or turning the bulb on
        if brightness is not None:
            await self.device.set_brightness(brightness)
            return
        await self.device.turn_on()  # type: ignore[arg-type]

    @property
    def supported_color_modes(self) -> set[ColorMode | str] | None:
        """Return list of available color modes."""
        modes: set[ColorMode | str] = set()
        modes.add(ColorMode.BRIGHTNESS)
        return modes

    @property
    def color_mode(self) -> ColorMode:
        """Return the active color mode."""
        return ColorMode.BRIGHTNESS

    @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.device.turn_off()

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return round((self.device.brightness * 255.0) / 100.0)
