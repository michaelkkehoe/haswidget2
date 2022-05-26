from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from pyswidget.device import SwidgetDevice

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
    PERCENTAGE,
    POWER_WATT,
    PRESSURE_KPA,
    TEMP_CELSIUS,

)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
)
from .coordinator import SwidgetDataUpdateCoordinator
from .entity import CoordinatedSwidgetEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class SwidgetSensorEntityDescription(SensorEntityDescription):
    """Describes TPLink sensor entity."""

    emeter_attr: str | None = None
    precision: int | None = None

SWIDGET_SENSORS: tuple[SwidgetSensorEntityDescription, ...] = (
    SwidgetSensorEntityDescription(
        key="Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        name="Current Consumption",
        emeter_attr="power",
        precision=1,
    ),
    SwidgetSensorEntityDescription(
        key="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Temperature",
        emeter_attr="temperature",
        precision=1,
    ),
    SwidgetSensorEntityDescription(
        key="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        name="Humidity",
        emeter_attr="humidity",
        precision=3,
    ),
    SwidgetSensorEntityDescription(
        key="Pressure",
        native_unit_of_measurement=PRESSURE_KPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        name="Air Pressure",
        emeter_attr="pressure",
        precision=3,
    ),
)

def async_emeter_from_device(
    device: SwidgetDevice, description: SwidgetSensorEntityDescription
) -> float | None:
    """Map a sensor key to the device attribute."""
    if attr := description.emeter_attr:
        if (val := getattr(device.emeter_realtime, attr)) is None:
            return None
        return round(cast(float, val), description.precision)

    # ATTR_TODAY_ENERGY_KWH
    if (emeter_today := device.emeter_today) is not None:
        return round(cast(float, emeter_today), description.precision)
    # today's consumption not available, when device was off all the day
    # bulb's do not report this information, so filter it out
    return None if device.is_bulb else 0.0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: SwidgetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SwidgetSensor] = []
    parent = coordinator.device

    def _async_sensors_for_device(device: SwidgetDevice) -> list[SwidgetSensor]:
        return [
            SwidgetSensor(device, coordinator, description)
            for description in SWIDGET_SENSORS
            if async_emeter_from_device(device, description) is not None
        ]

    entities.extend(_async_sensors_for_device(parent))

    async_add_entities(entities)


class SwidgetSensor(CoordinatedSwidgetEntity, SensorEntity):
    """Representation of a TPLink Smart Plug energy sensor."""

    entity_description: SwidgetSensorEntityDescription

    def __init__(
        self,
        device: SwidgetDevice,
        coordinator: SwidgetDataUpdateCoordinator,
        description: SwidgetSensorEntityDescription,
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
        return f"{self.device.id} {self.entity_description.name}"

    @property
    def native_value(self) -> float | None:
        """Return the sensors state."""
        return async_emeter_from_device(self.device, self.entity_description)
