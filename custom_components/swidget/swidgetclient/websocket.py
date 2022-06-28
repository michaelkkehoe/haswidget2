import asyncio
from datetime import datetime
import logging
import ssl
from time import time
import aiohttp

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

SIGNAL_CONNECTION_STATE = "plexwebsocket_state"

ERROR_AUTH_FAILURE = "Authorization failure"
ERROR_TOO_MANY_RETRIES = "Too many retries"
ERROR_UNKNOWN = "Unknown"

MAX_FAILED_ATTEMPTS = 5

STATE_CONNECTED = "connected"
STATE_DISCONNECTED = "disconnected"
STATE_STARTING = "starting"
STATE_STOPPED = "stopped"


class SwidgetWebsocket:
    """Represent a websocket connection to a Swidget Device"""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        host,
        secret_key,
        callback,
        session=None,
        verify_ssl=False,
    ):

        self.session = session or aiohttp.ClientSession()
        self.uri = self._get_uri(host, secret_key)
        self.callback = callback
        self._ssl = False if verify_ssl is False else None
        self._state = None
        self.failed_attempts = 0
        self._error_reason = None

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @state.setter
    def state(self, value):
        """Set the state."""
        self._state = value
        _LOGGER.debug("Websocket %s", value)
        self.callback(value)
        self._error_reason = None

    @staticmethod
    def _get_uri(host, secret_key):
        """Generate the websocket URI"""
        return f"wss://{host}/api/v1/sock?x-secret-key={secret_key}"

    async def running(self):
        """Open a persistent websocket connection and act on events."""
        self.state = STATE_STARTING

        try:
            print(self.uri)
            headers = {'Connection': 'Upgrade'}
            async with self.session.ws_connect(self.uri, headers=headers, verify_ssl=False) as self.ws_client:
                self.state = STATE_CONNECTED
                self.failed_attempts = 0
                async for message in self.ws_client:
                    if self.state == STATE_STOPPED:
                        break

                    if message.type == aiohttp.WSMsgType.TEXT:
                        msg = message.json()
                        msgtype = msg["request_id"]
                        self.callback(msgtype, msg, None)

                    elif message.type == aiohttp.WSMsgType.CLOSED:
                        _LOGGER.warning("AIOHTTP websocket connection closed")
                        break

                    elif message.type == aiohttp.WSMsgType.ERROR:
                        _LOGGER.error("AIOHTTP websocket error")
                        break

        except aiohttp.ClientResponseError as error:
            if error.code == 401:
                _LOGGER.error("Credentials rejected: %s", error)
                self._error_reason = ERROR_AUTH_FAILURE
            else:
                _LOGGER.error("Unexpected response received: %s", error)
                self._error_reason = ERROR_UNKNOWN
            self.state = STATE_STOPPED
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as error:
            if self.failed_attempts >= MAX_FAILED_ATTEMPTS:
                self._error_reason = ERROR_TOO_MANY_RETRIES
                self.state = STATE_STOPPED
            elif self.state != STATE_STOPPED:
                retry_delay = min(2 ** (self.failed_attempts - 1) * 30, 300)
                self.failed_attempts += 1
                _LOGGER.exception(
                    "Websocket connection failed, retrying in %ds: %s",
                    retry_delay,
                    error,
                )
                self.state = STATE_DISCONNECTED
                await asyncio.sleep(retry_delay)
        except Exception as error:  # pylint: disable=broad-except
            if self.state != STATE_STOPPED:
                _LOGGER.exception("Unexpected exception occurred: %s", error)
                self._error_reason = ERROR_UNKNOWN
                self.state = STATE_STOPPED
        else:
            if self.state != STATE_STOPPED:
                self.state = STATE_DISCONNECTED

                await asyncio.sleep(5)


    async def send_str(self, message):
        await self.ws_client.send_str(message)

    async def listen(self):
        """Close the listening websocket."""
        self.failed_attempts = 0
        while self.state != STATE_STOPPED:
            await self.running()

    def close(self):
        """Close the listening websocket."""
        self.state = STATE_STOPPED
