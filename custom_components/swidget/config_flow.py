"""Config flow for Swidget integration."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from .swidgetclient.discovery import SwidgetDiscoveredDevice
from homeassistant.helpers.device_registry import format_mac
from . import async_discover_devices
from .swidgetclient.device import SwidgetDevice
from .swidgetclient.exceptions import SwidgetException
import voluptuous as vol
from homeassistant.helpers.typing import DiscoveryInfoType


from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MAC
from homeassistant.core import callback, HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST, default=""): str,
        vol.Optional("password"): str,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Return info that you want to store in the config entry.
    try:
        d = SwidgetDevice(data['host'], data['password'], False)
        await d.update()
        return {"title": f"{d.friendly_name}"}
    except:
        raise CannotConnect

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Swidget."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, SwidgetDiscoveredDevice] = {}
        self._discovered_device: SwidgetDiscoveredDevice | None = None

    VERSION = 1
    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle discovery via dhcp."""
        _LOGGER.error("Swidget device found via DHCP: %s", discovery_info)
        return await self._async_handle_discovery(
            discovery_info.ip, discovery_info.macaddress
        )

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Handle discovery via SSDP."""
        _LOGGER.error("Swidget device found via SSDP: %s", discovery_info)
        discovered_ip = urlparse(discovery_info.ssdp_headers["location"]).hostname
        discovered_mac = format_mac(discovery_info.ssdp_headers["USN"].split("-")[-1])
        return await self._async_handle_discovery(
            discovered_ip, discovered_mac
        )

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> FlowResult:
        """Handle integration discovery."""
        return await self._async_handle_discovery(
            discovery_info[CONF_HOST], discovery_info[CONF_MAC]
        )

    async def _async_handle_discovery(self, host: str, mac: str) -> FlowResult:
        """Handle any discovery."""
        await self.async_set_unique_id(dr.format_mac(mac))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._async_abort_entries_match({CONF_HOST: host})
        self.context[CONF_HOST] = host
        for progress in self._async_in_progress():
            if progress.get("context", {}).get(CONF_HOST) == host:
                return self.async_abort(reason="already_in_progress")

        self._discovered_device = SwidgetDiscoveredDevice(mac, host)
        await self.async_set_unique_id(
            dr.format_mac(mac), raise_on_progress=True
        )
        _LOGGER.error("SWIDGET: Moving to discovery_confirm()")
        return await self.async_step_discovery_confirm()


    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        assert self._discovered_device is not None
        if user_input is not None:
            _LOGGER.error(f"async_step_discovery_confirm() {user_input}")
            _LOGGER.error(f"discovered_device {self._discovered_device}")
            user_input['host'] = self._discovered_devices[user_input['device']].host
            info = await validate_input(self.hass, user_input)
            return self.async_create_entry(title=info["title"], data=user_input)
            # TODO FIX FIX FIX
            #self._discovered_device.password = user_input.get("password")
            return self._async_create_entry_from_device(self._discovered_device)
            # return self.async_create_entry(title=info["title"], data=user_input)

        self._set_confirm_only()
        placeholders = {
            "name": self._discovered_device.friendly_name,
            "host": self._discovered_device.host,
        }
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            description_placeholders=placeholders
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # return self.async_show_form(
            #     step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            # )
            if not (host := user_input[CONF_HOST]):
                return await self.async_step_pick_device()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step to pick discovered device."""
        if user_input is not None:
            # mac = user_input[CONF_DEVICE]
            # await self.async_set_unique_id(mac, raise_on_progress=False)
            # return self._async_create_entry_from_device(self._discovered_devices[mac])
            _LOGGER.error(f"user-Input: {user_input}")
            _LOGGER.error(f"discovered devices: {self._discovered_devices[user_input['device']].__dict__}")
            user_input['host'] = self._discovered_devices[user_input['device']].host
            info = await validate_input(self.hass, user_input)
            return self.async_create_entry(title=info["title"], data=user_input)


        configured_devices = {
            entry.unique_id for entry in self._async_current_entries()
        }
        _LOGGER.error(f"Configured Devices: {self._async_current_entries()}")
        self._discovered_devices = await async_discover_devices(self.hass)
        _LOGGER.error(f"Discovered Devices: {self._discovered_devices}")
        devices_name = {
            mac: f"{device.friendly_name} ({device.host})"
            for mac, device in self._discovered_devices.items()
            if mac not in configured_devices
        }
        # Check if there is at least one device
        if not devices_name:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE): vol.In(devices_name),
                        vol.Required("password"): str}),
        )

    @callback
    def _async_create_entry_from_device(self, device: SwidgetDiscoveredDevice) -> FlowResult:
        """Create a config entry from a smart device."""
        self._abort_if_unique_id_configured(updates={CONF_MAC: device.mac})
        return self.async_create_entry(
            title= device.friendly_name,
            data={
                CONF_HOST: device.host
            },
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
