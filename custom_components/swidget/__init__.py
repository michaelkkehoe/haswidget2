"""The Swidget integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any
import logging

from .swidgetclient.device import SwidgetDevice
from .swidgetclient.exceptions import SwidgetException
from .swidgetclient.discovery import SwidgetDiscoveredDevice, discover_devices, discover_single

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_MAC,
    EVENT_HOMEASSISTANT_STARTED,
)

from homeassistant.core import callback, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval
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
    for mac, device in discovered_devices.items():
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
                data={
                    CONF_NAME: device.friendly_name,
                    CONF_HOST: device.host,
                    CONF_MAC: device.mac,
                },
            )
        )

async def async_discover_devices(hass: HomeAssistant) -> dict[str, SwidgetDevice]:
    """Force discover Swidget devices using """
    # broadcast_addresses = await network.async_get_ipv4_broadcast_addresses(hass)
    # tasks = [Discover.discover(target=str(address)) for address in broadcast_addresses]
    discovered_devices: dict[str, SwidgetDiscoveredDevice] = await discover_devices()
    # for device in discovered_devices:
    #     discovered_devices[dr.format_mac(device.mac)] = device
    _LOGGER.error(f"Forced Swidget Discovery found: {discovered_devices}")
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
        _LOGGER.error(f"Setup Data: {entry.data}")
        device: SwidgetDevice = await discover_single(entry.data['host'],
                                                      entry.data['password'],
                                                      False)
    except SwidgetException as ex:
        raise ConfigEntryNotReady from ex

    # session = async_get_clientsession(hass)
    hass.data[DOMAIN][entry.entry_id] = SwidgetDataUpdateCoordinator(hass, device)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    hass.loop.create_task(device._websocket.listen())
    _LOGGER.error(" async_setup_entry returned")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
    #     hass.data[DOMAIN].pop(entry.entry_id)
    # return unload_ok
    hass_data: dict[str, Any] = hass.data[DOMAIN]
    device: SwidgetDevice = hass_data[entry.entry_id].device
    _LOGGER.error(f" async_unload_entry: {device}")
    if device.use_websockets:
        await device._websocket.close()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass_data.pop(entry.entry_id)
    return unload_ok