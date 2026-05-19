"""Media player support for Sonance DSP outputs."""

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from sonance_py import SonanceOutput

from . import SonanceDSPConfigEntry
from .const import DOMAIN, MIN_VOLUME_DB
from .coordinator import SonanceDSPCoordinator, output_group_id

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.GROUPING
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonanceDSPConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sonance DSP media players."""
    coordinator = entry.runtime_data
    known_groups: set[str] = set()

    @callback
    def async_add_missing_entities() -> None:
        """Add entities for newly available logical outputs."""
        new_groups = coordinator.get_output_groups() - known_groups
        if not new_groups:
            return

        entities = [
            SonanceDSPMediaPlayer(coordinator, output_group)
            for output_group in sorted(new_groups)
        ]
        known_groups.update(new_groups)
        async_add_entities(entities)
        for entity in entities:
            entity.async_schedule_update_ha_state()

    async_add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_missing_entities))


class SonanceDSPMediaPlayer(
    CoordinatorEntity[SonanceDSPCoordinator], MediaPlayerEntity
):
    """Representation of a Sonance DSP logical output."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_has_entity_name = True
    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = SUPPORTED_FEATURES

    def __init__(self, coordinator: SonanceDSPCoordinator, output_group: str) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._output_group = output_group

        serial_number = coordinator.data.general_settings.serial_number
        self._attr_unique_id = f"{serial_number}_{output_group}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
            manufacturer="Sonance",
            model=coordinator.data.general_settings.amplifier_model,
            name=coordinator.data.general_settings.amplifier_name,
            serial_number=serial_number,
            sw_version=coordinator.data.general_settings.firmware_version,
        )
        self._update_name()

    @property
    def available(self) -> bool:
        """Return whether this output is currently available."""
        return super().available and self._output is not None

    @property
    def _output(self) -> SonanceOutput | None:
        """Return the current live library output for this entity."""
        return self.coordinator.get_output(self._output_group)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh cached attributes after coordinator updates."""
        self._update_name()
        super()._handle_coordinator_update()

    @property
    def state(self) -> MediaPlayerState:
        """Return the current entity state."""
        if not self.available:
            return MediaPlayerState.OFF
        return MediaPlayerState.IDLE

    @property
    def group_members(self) -> list[str]:
        """Return outputs using the same primary source."""
        if not (output := self._output):
            return []

        return [
            entity_id
            for member in self.coordinator.amplifier.outputs
            if member.source_1 == output.source_1
            if (entity_id := self._entity_id_for_output_group(output_group_id(member)))
        ]

    @property
    def source_list(self) -> list[str] | None:
        """Return available sources."""
        if not (output := self._output):
            return None
        return list(output.source_names())

    @property
    def source(self) -> str | None:
        """Return the selected source name."""
        if not (output := self._output):
            return None
        sources = output.source_names()
        if output.source_1 >= len(sources):
            return None
        return sources[output.source_1]

    @property
    def volume_level(self) -> float | None:
        """Return the volume level on a 0..1 scale."""
        if not (output := self._output):
            return None
        maximum_volume = int(output.maximum_volume)
        if maximum_volume <= MIN_VOLUME_DB:
            return 0.0

        volume = int(output.volume)
        return max(
            0.0,
            min(1.0, (volume - MIN_VOLUME_DB) / (maximum_volume - MIN_VOLUME_DB)),
        )

    @property
    def is_volume_muted(self) -> bool | None:
        """Return whether the output is muted."""
        if not (output := self._output):
            return None
        return str(output.muted) == "on"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not (output := self._output):
            return {"output_group": self._output_group}
        return {
            "channel_indexes": list(output.channel_indexes),
            "output_group": self._output_group,
            "stereo_mode": str(output.stereo_mode),
        }

    async def async_select_source(self, source: str) -> None:
        """Select the primary source."""
        output = self._require_output()
        await output.set_source_by_name(source)
        await self.coordinator.async_refresh_from_cache()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the output volume level."""
        output = self._require_output()
        maximum_volume = int(output.maximum_volume)
        value = round(MIN_VOLUME_DB + volume * (maximum_volume - MIN_VOLUME_DB))
        await output.set_volume(value)
        await self.coordinator.async_refresh_from_cache()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute the output."""
        output = self._require_output()
        await output.set_muted(mute)
        await self.coordinator.async_refresh_from_cache()

    async def async_join_players(self, group_members: list[str]) -> None:
        """Join member outputs to this output."""
        output = self._require_output()
        members = [
            self._resolve_group_member(entity_id)
            for entity_id in group_members
            if entity_id != self.entity_id
        ]
        await output.join(members)
        await self.coordinator.async_refresh_from_cache()

    async def async_unjoin_player(self) -> None:
        """Split a stereo output back into mono outputs."""
        output = self._require_output()

        await output.set_source_1((output.number - 1) * 2)
        await self.coordinator.async_refresh_from_cache()

    def _resolve_group_member(self, entity_id: str) -> SonanceOutput:
        """Resolve a Home Assistant entity ID to a live Sonance output."""
        entity_registry = er.async_get(self.hass)
        if not (entity_entry := entity_registry.async_get(entity_id)):
            raise ServiceValidationError(f"Entity {entity_id} was not found")
        if entity_entry.platform != DOMAIN:
            raise ServiceValidationError(
                f"Entity {entity_id} is not a Sonance DSP media player"
            )

        member_group = entity_entry.unique_id.rsplit("_", 1)[-1]
        if not (output := self.coordinator.get_output(member_group)):
            raise ServiceValidationError(
                f"Output for {entity_id} is not currently active"
            )
        return output

    def _require_output(self) -> SonanceOutput:
        """Return the current output or raise if it is unavailable."""
        if not (output := self._output):
            raise ServiceValidationError(
                f"Output group {self._output_group} is not currently active"
            )
        return output

    def _entity_id_for_output_group(self, output_group: str) -> str | None:
        """Resolve an output group to its media player entity ID."""
        return er.async_get(self.hass).async_get_entity_id(
            "media_player",
            DOMAIN,
            f"{self.coordinator.data.general_settings.serial_number}_{output_group}",
        )

    def _update_name(self) -> None:
        """Update the entity name from the current output shape."""
        output = self._output
        if output is None:
            return

        if len(output.channel_indexes) == 2:
            self._attr_name = f"Output {output.number}"
            return

        channel = output.channel_indexes[0]
        side = "Left" if channel % 2 == 0 else "Right"
        self._attr_name = f"Output {output.number} {side}"
