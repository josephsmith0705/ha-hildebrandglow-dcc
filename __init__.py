"""The Glowmarkt Bright integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "glowmarkt_bright"
PLATFORMS = [Platform.SENSOR]

# Scan interval - check every 30 minutes (data may lag by 12 hours)
SCAN_INTERVAL = timedelta(minutes=30)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Glowmarkt Bright component."""
    hass.data.setdefault(DOMAIN, {})

    # Check if configuration exists in configuration.yaml
    if DOMAIN in config:
        # Load the sensor platform
        await hass.helpers.discovery.async_load_platform(
            Platform.SENSOR, DOMAIN, config[DOMAIN], config
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Glowmarkt Bright from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
