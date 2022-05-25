"""Support for Elgato button."""
from __future__ import annotations

import logging

from device import SwidgetDevice

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantElgatoData
from .const import DOMAIN
from .entity import ElgatoEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elgato button based on a config entry."""
    # data: HomeAssistantSwidgetData = hass.data[DOMAIN][entry.entry_id]
    #async_add_entities(
    #    [SwidgetIdentifyButton(data.device, device.info, entry.data.get(CONF_MAC))]
    #)
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [SwidgetIdentifyButton(coordinator.device), coordinator)]
    )


class SwidgetIdentifyButton(CoordinatedSwidgetEntity, ButtonEntity):
    """Defines an Elgato identify button."""

    def __init__(
        self,
        device: SwidgetDimmer,
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
        self._attr_unique_id = f"{device.id}_{self.entity_description.key}"

    async def async_press(self) -> None:
        """Identify the light, will make it blink."""
        try:
            await self.device.blink()
        except ElgatoError:
            _LOGGER.exception("An error occurred while identifying the Elgato Light")
