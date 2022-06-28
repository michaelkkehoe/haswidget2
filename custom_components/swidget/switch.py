"""Support for TPLink lights."""
from __future__ import annotations

from collections.abc import Sequence
import logging
from typing import Any, Final, cast

from .swidgetclient.swidgetdimmer import SwidgetDimmer
from .swidgetclient.swidgetoutlet import SwidgetOutlet
from .swidgetclient.swidgetswitch import SwidgetSwitch



import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SwidgetDataUpdateCoordinator
from .entity import CoordinatedSwidgetEntity, async_refresh_after

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if coordinator.device.is_dimmer:
        entities.append(SwidgetPlugSwitch(cast(SwidgetDimmer, coordinator.device), coordinator))

    if coordinator.device.insert_type == "USB":
        entities.append(SwidgetUSBSwitch(cast(SwidgetOutlet, coordinator.device), coordinator))

    async_add_entities(entities)


class SwidgetPlugSwitch(CoordinatedSwidgetEntity, SwitchEntity):
    """Representation of a swidget switch."""

    def __init__(
        self,
        device: SwidgetDevice,
        coordinator: SwidgetDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device, coordinator)
        self._attr_name = "Controlled Switch"
        self._attr_unique_id = (
            f"{self.device}_controlled"
        )

    @async_refresh_after
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.device.turn_on()

    @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.device.turn_off()

    @property
    def is_on(self) -> bool:
        return self.device.is_on

class SwidgetUSBSwitch(CoordinatedSwidgetEntity, SwitchEntity):
    """Representation of a swidget USB witch."""

    def __init__(
        self,
        device: SwidgetDevice,
        coordinator: SwidgetDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device, coordinator)
        self._attr_name = "USB Outlet"
        self._attr_unique_id = (
            f"{self.device}_usb_outlet"
        )

    @async_refresh_after
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.device.turn_on_usb_insert()

    @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.device.turn_off_usb_insert()

    @property
    def is_on(self) -> bool:
        return self.device.usb_is_on