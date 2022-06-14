"""Support for Elgato button."""
from __future__ import annotations

import logging

from .device import SwidgetDevice

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SwidgetDataUpdateCoordinator
from .exceptions import SwidgetException
from .entity import CoordinatedSwidgetEntity, async_refresh_after

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elgato button based on a config entry."""

    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [SwidgetIdentifyButton(coordinator.device, coordinator)]
    )


class SwidgetIdentifyButton(CoordinatedSwidgetEntity, ButtonEntity):
    """Defines an Swidget identify button."""

    def __init__(
        self,
        device: Swidgetevice,
        coordinator: SwidgetDataUpdateCoordinator,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(device, coordinator)
        self.entity_description = ButtonEntityDescription(
            key="identify",
            name="Identify",
            icon="mdi:help",
            entity_category=EntityCategory.CONFIG,
        )
        self._attr_name = "Identify"
        self._attr_unique_id = f"{device.id}_{self.entity_description.key}"

    async def async_press(self) -> None:
        """Identify the device by making it blink."""
        try:
            await self.device.blink()
        except SwidgetException:
            _LOGGER.exception("An error occurred while identifying the Swidget device")
