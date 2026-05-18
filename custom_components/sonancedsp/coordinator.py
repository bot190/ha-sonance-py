"""Coordinator for Sonance DSP state."""

import logging
from dataclasses import dataclass
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from sonance_py import SonanceDSP, SonanceOutput

from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type SonanceDSPConfigEntry = ConfigEntry[SonanceDSPCoordinator]


@dataclass(frozen=True, slots=True)
class SonanceDSPData:
    """Snapshot of amplifier state."""

    general_settings: Any
    in_out_settings: Any


class SonanceDSPCoordinator(DataUpdateCoordinator[SonanceDSPData]):
    """Coordinate Sonance DSP state polling."""

    config_entry: SonanceDSPConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SonanceDSPConfigEntry,
        amplifier: SonanceDSP,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.amplifier: SonanceDSP = amplifier

    async def _async_update_data(self) -> SonanceDSPData:
        """Fetch fresh Sonance DSP state."""
        try:
            await self.amplifier.refresh()
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError) as err:
            raise UpdateFailed(f"Error communicating with amplifier: {err}") from err

        return self._snapshot()

    def _snapshot(self) -> SonanceDSPData:
        """Build a coordinator snapshot from the cached amplifier state."""
        return SonanceDSPData(
            general_settings=self.amplifier.general_settings,
            in_out_settings=self.amplifier.in_out_settings,
        )

    async def async_refresh_from_cache(self) -> None:
        """Push updated cached state to listeners after a successful write."""
        self.async_set_updated_data(self._snapshot())

    def get_output(self, output_group: str) -> SonanceOutput | None:
        """Return the current output matching a group identifier."""
        for output in self.amplifier.outputs:
            if output_group_id(output) == output_group:
                return output
        return None

    def get_output_groups(self) -> set[str]:
        """Return all active output groups."""
        return {output_group_id(output) for output in self.amplifier.outputs}

    async def async_close(self) -> None:
        """Close the underlying library client."""
        await self.amplifier.close()


def output_group_id(output: SonanceOutput) -> str:
    """Normalize an output's group identifier."""
    group = output.output_group
    return group.value if hasattr(group, "value") else str(group)
