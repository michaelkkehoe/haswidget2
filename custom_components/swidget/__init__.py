"""The Swidget integration."""
from __future__ import annotations

import logging

from .device import SwidgetDevice
from .exceptions import SwidgetException
from .discovery import Discover

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import SwidgetDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the TP-Link component."""
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
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)
    _LOGGER.error(entry.data)
    print(entry.data)
    try:
        device: SwidgetDevice = await Discover.discover_single(entry.data['host'], entry.data['password'], False)
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
