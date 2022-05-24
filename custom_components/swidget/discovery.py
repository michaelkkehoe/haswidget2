import asyncio
import json
import socket
from typing import Awaitable, Callable, Dict, Optional, Type, cast
from urllib.parse import urlparse

import ssdp

from .device import DeviceType, SwidgetDevice
from .exceptions import SwidgetException

RESPONSE_SEC = 2
SWIDGET_ST = "urn:swidget:pico:1"

device_addresses = set()


class SwidgetProtocol(ssdp.SimpleServiceDiscoveryProtocol):
    """Protocol to handle responses and requests."""

    def response_received(self, response: ssdp.SSDPResponse, addr: tuple):
        """Handle an incoming response."""
        headers = {h[0]: h[1] for h in response.headers}
        mac_address = headers["USN"].split("-")[-1]
        ip_address = urlparse(headers["LOCATION"]).hostname
        device_addresses.add((mac_address, ip_address))

class Discover:
    async def discover_devices(self):
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            SwidgetProtocol, family=socket.AF_INET
        )

        # Send out an M-SEARCH request, requesting Swidget service types.
        search_request = ssdp.SSDPRequest(
            "M-SEARCH",
            headers={
                "HOST": "239.255.255.250:1900",
                "MAN": '"ssdp:discover"',
                "MX": RESPONSE_SEC,
                "ST": SWIDGET_ST,
            },
        )
        search_request.sendto(transport, (SwidgetProtocol.MULTICAST_ADDRESS, 1900))
        await asyncio.sleep(RESPONSE_SEC + 0.5)
        return device_addresses

    @staticmethod
    async def discover_single(host: str, password: str, ssl: bool) -> SwidgetDevice:
        """Discover a single device by the given IP address.

        :param host: Hostname of device to query
        :rtype: SwidgetDevice
        :return: Object for querying/controlling found device.
        """
        protocol = TPLinkSmartHomeProtocol(host)

        swidget_device = await SwidgetDevice(host, password, ssl).get_summary()
        device_type = swidget_device.device_type
        device_class = Discover._get_device_class(device_type)
        dev = device_class(host, password, False)
        await dev.update()

        return dev

    @staticmethod
    def _get_device_class(device_type: str) -> Type[SwidgetDevice]:
        """Find SmartDevice subclass for device described by passed data."""
        if device_type == DeviceType.Outlet:
            return SwidgetOutlet
        elif device_type == DeviceType.Switch:
            return SwidgetSwitch
        elif device_type == DeviceType.Dimmer:
            return SwidgetDimmer
        raise SwidgetException("Unknown device type: %s" % device_type)
