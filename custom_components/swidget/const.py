from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN = "swidget"
# PLATFORMS: Final = [Platform.BUTTON, Platform.LIGHT]
PLATFORMS: Final = [Platform.LIGHT, Platform.SENSOR, Platform.SWITCH]
