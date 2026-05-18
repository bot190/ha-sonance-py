"""The Sonance DSP integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import create_sonance_dsp
from .const import DEFAULT_PORT
from .coordinator import SonanceDSPCoordinator

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

type SonanceDSPConfigEntry = ConfigEntry[SonanceDSPCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SonanceDSPConfigEntry) -> bool:
    """Set up Sonance DSP from a config entry."""
    session = async_get_clientsession(hass)
    amplifier = create_sonance_dsp(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        session,
    )
    coordinator = SonanceDSPCoordinator(hass, entry, amplifier)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.async_close()
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SonanceDSPConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_close()
    return unload_ok
