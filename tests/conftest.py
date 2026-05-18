"""Common fixtures for the Sonance DSP tests."""

from __future__ import annotations

from collections.abc import Generator
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant


class FakeOnOff(StrEnum):
    """Fake on/off enum matching sonance-py values."""

    ON = "on"
    OFF = "off"


class FakeOutputGroup(StrEnum):
    """Fake output group enum matching sonance-py values."""

    A = "a"
    B = "b"


class FakeStereoMode(StrEnum):
    """Fake stereo mode enum matching sonance-py values."""

    STEREO = "stereo"
    MONO = "mono"


class FakeOutput:
    """Fake Sonance output object."""

    def __init__(
        self,
        amplifier: FakeAmplifier,
        group: FakeOutputGroup,
        channel_number: int,
        channel_indexes: tuple[int, ...],
        *,
        source_1: int = 0,
        volume: str = "-60",
        maximum_volume: str = "-20",
        muted: FakeOnOff = FakeOnOff.OFF,
        stereo_mode: FakeStereoMode = FakeStereoMode.STEREO,
    ) -> None:
        """Initialize the fake output."""
        self._amplifier = amplifier
        self.output_group = group
        self.number = channel_number
        self.channel_indexes = channel_indexes
        self.source_1 = source_1
        self.volume = volume
        self.maximum_volume = maximum_volume
        self.muted = muted
        self.stereo_mode = stereo_mode
        self.channels = tuple(
            SimpleNamespace(
                index=channel_index,
                number=channel_number,
                side="left" if idx == 0 else "right",
            )
            for idx, channel_index in enumerate(channel_indexes)
        )
        self.join_calls: list[list[FakeOutput]] = []

    def source_names(self) -> tuple[str, ...]:
        """Return available sources."""
        return (
            "Input 1L",
            "Input 1R",
            "Input 2L",
            "Input 2R",
        )

    async def set_source_by_name(self, name: str) -> None:
        """Set the source by name."""
        self.source_1 = self.source_names().index(name)

    async def set_volume(self, value: int) -> None:
        """Set the volume."""
        self.volume = str(value)

    async def set_muted(self, value: FakeOnOff | bool) -> None:
        """Set the mute state."""
        self.muted = FakeOnOff.ON if value in (True, FakeOnOff.ON) else FakeOnOff.OFF

    async def join(self, members: list[FakeOutput]) -> None:
        """Record join calls."""
        self.join_calls.append(members)

    async def set_stereo_mode(self, value: str) -> None:
        """Set stereo mode."""
        self.stereo_mode = FakeStereoMode(value)


class FakeAmplifier:
    """Fake Sonance amplifier."""

    def __init__(self) -> None:
        """Initialize the fake amplifier."""
        self.general_settings = SimpleNamespace(
            amplifier_name="Living Rack",
            amplifier_model="DSP8-130",
            firmware_version="1.0.0",
            serial_number="SERIAL123",
        )
        self.in_out_settings = SimpleNamespace()
        self._outputs = {
            FakeOutputGroup.A: FakeOutput(
                self, FakeOutputGroup.A, 1, (0, 1), source_1=0
            ),
            FakeOutputGroup.B: FakeOutput(
                self, FakeOutputGroup.B, 2, (2, 3), source_1=2
            ),
        }

    @property
    def outputs(self) -> tuple[FakeOutput, ...]:
        """Return the current outputs."""
        return tuple(self._outputs.values())

    async def refresh(self) -> None:
        """Refresh cached state."""

    async def close(self) -> None:
        """Close the client."""


@pytest.fixture
def enable_sonancedsp_custom_integration(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expose the repo-root custom component to Home Assistant's custom loader."""
    import custom_components  # noqa: PLC0415

    custom_path = Path(__file__).parents[1] / "custom_components"
    monkeypatch.setattr(
        custom_components,
        "__path__",
        [*custom_components.__path__, str(custom_path)],
    )
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.sonancedsp.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def fake_amplifier() -> FakeAmplifier:
    """Return a fake amplifier."""
    return FakeAmplifier()


@pytest.fixture(autouse=True)
def bypass_requirements() -> Generator[AsyncMock]:
    """Bypass requirement installation for tests."""
    with patch(
        "homeassistant.requirements.async_process_requirements",
        return_value=True,
    ) as mock_requirements:
        yield mock_requirements
