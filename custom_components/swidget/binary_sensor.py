from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from .swidgetclient.device import SwidgetDevice

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,

)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
)
from .coordinator import SwidgetDataUpdateCoordinator
from .entity import CoordinatedSwidgetEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class SwidgetBinarySensorEntityDescription(SensorEntityDescription):
    """Describes A Swidget binary sensor entity."""

    emeter_attr: str | None = None
    precision: int | None = None

SWIDGET_SENSORS: tuple[SwidgetBinarySensorEntityDescription, ...] = (
    SwidgetBinarySensorEntityDescription(
        key="Motion",
        device_class=BinarySensorDeviceClass.MOTION,
        name="Motion",
        emeter_attr="occupied",
    ),
)

def async_emeter_from_device(
    device: SwidgetDevice, description: SwidgetBinarySensorEntityDescription
) -> float | None:
    """Map a sensor key to the device attribute."""
    if attr := description.emeter_attr:
        if (val := device.realtime_values.get(attr, None)) is None:
            return None
        if attr == "occupied":
            if val is True:
                return "on"
            return "off"
        return round(cast(float, val), description.precision)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SwidgetBinarySensor] = []
    parent = coordinator.device

    def _async_sensors_for_device(device: SwidgetDevice) -> list[SwidgetBinarySensor]:
        return [
            SwidgetBinarySensor(device, coordinator, description)
            for description in SWIDGET_SENSORS
            if async_emeter_from_device(device, description) is not None
        ]

    entities.extend(_async_sensors_for_device(parent))

    async_add_entities(entities)


class SwidgetBinarySensor(CoordinatedSwidgetEntity, SensorEntity):
    """Representation of a Swidget sensor"""

    entity_description: SwidgetBinarySensorEntityDescription

    def __init__(
        self,
        device: SwidgetDevice,
        coordinator: SwidgetDataUpdateCoordinator,
        description: SwidgetBinarySensorEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{self.device}_{self.entity_description.key}"
        )

    @property
    def name(self) -> str:
        """Return the name of the Smart Plug.

        Overridden to include the description.
        """
        return f"{self.entity_description.name}"

    @property
    def native_value(self) -> float | None:
        """Return the sensors state."""
        return async_emeter_from_device(self.device, self.entity_description)
