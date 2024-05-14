from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN = "swidget"
PLATFORMS: Final = [Platform.BUTTON, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR, Platform.CAMERA]
