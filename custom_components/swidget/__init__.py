"""The Swidget integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from .device import SwidgetDevice
from .exceptions import SwidgetException
from .discovery import discover_devices, discover_single

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    EVENT_HOMEASSISTANT_STARTED,
    Platform
)
from homeassistant.core import callback, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import SwidgetDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
DISCOVERY_INTERVAL = timedelta(minutes=15)

@callback
def async_trigger_discovery(
    hass: HomeAssistant,
    discovered_devices: dict[str, SwidgetDevice],
) -> None:
    """Trigger config flows for discovered devices."""
    for mac, ip_address in discovered_devices.items():
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
                data={
                    CONF_HOST: ip_address,
                    CONF_MAC: mac,
                },
            )
        )

async def async_discover_devices(hass: HomeAssistant) -> dict[str, SwidgetDevice]:
    """Force discover Swidget devices using """
    # broadcast_addresses = await network.async_get_ipv4_broadcast_addresses(hass)
    # tasks = [Discover.discover(target=str(address)) for address in broadcast_addresses]
    discovered_devices: dict[str, SwidgetDevice] = await discover_devices()
    # for device in discovered_devices:
    #     discovered_devices[dr.format_mac(device.mac)] = device
    _LOGGER.error(discovered_devices)
    return discovered_devices

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Swidget component."""
    hass.data[DOMAIN] = {}

    if discovered_devices := await async_discover_devices(hass):
        async_trigger_discovery(hass, discovered_devices)

    async def _async_discovery(*_: Any) -> None:
        if discovered := await async_discover_devices(hass):
            async_trigger_discovery(hass, discovered)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_discovery)
    async_track_time_interval(hass, _async_discovery, DISCOVERY_INTERVAL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Swidget from a config entry."""
    try:
        device: SwidgetDevice = await discover_single(entry.data['host'], entry.data['password'], False)
    except SwidgetException as ex:
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN][entry.entry_id] = SwidgetDataUpdateCoordinator(hass, device)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok