"""Tests for Sonance DSP media players."""

from unittest.mock import patch

import pytest
from custom_components.sonancedsp.const import DEFAULT_PORT, DOMAIN
from homeassistant.components.media_player import (
    ATTR_GROUP_MEMBERS,
    SERVICE_JOIN,
    SERVICE_UNJOIN,
)
from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("enable_sonancedsp_custom_integration")


async def test_setup_creates_one_media_player_per_output(
    hass: HomeAssistant, fake_amplifier
) -> None:
    """Test setup creates one entity per logical output."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Rack",
        data={CONF_HOST: "1.1.1.1", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.sonancedsp.create_sonance_dsp",
        return_value=fake_amplifier,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("media_player.living_rack_output_1") is not None
    assert hass.states.get("media_player.living_rack_output_2") is not None


async def test_join_service_uses_output_join(
    hass: HomeAssistant, fake_amplifier
) -> None:
    """Test the media_player.join action delegates to sonance-py output.join."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Rack",
        data={CONF_HOST: "1.1.1.1", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.sonancedsp.create_sonance_dsp",
        return_value=fake_amplifier,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    target = entity_registry.async_get_entity_id(
        MEDIA_PLAYER_DOMAIN, DOMAIN, "SERIAL123_a"
    )
    member = entity_registry.async_get_entity_id(
        MEDIA_PLAYER_DOMAIN, DOMAIN, "SERIAL123_b"
    )

    assert target is not None
    assert member is not None

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_JOIN,
        {
            ATTR_ENTITY_ID: target,
            ATTR_GROUP_MEMBERS: member,
        },
        blocking=True,
    )

    join_calls = fake_amplifier.outputs[0].join_calls
    assert len(join_calls) == 1
    assert join_calls[0] == [fake_amplifier.outputs[1]]


async def test_group_members_are_outputs_using_same_source(
    hass: HomeAssistant, fake_amplifier
) -> None:
    """Test group members report outputs using the same input."""
    fake_amplifier.outputs[1].source_1 = fake_amplifier.outputs[0].source_1
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Rack",
        data={CONF_HOST: "1.1.1.1", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.sonancedsp.create_sonance_dsp",
        return_value=fake_amplifier,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("media_player.living_rack_output_1")
    assert state is not None
    assert state.attributes[ATTR_GROUP_MEMBERS] == [
        "media_player.living_rack_output_1",
        "media_player.living_rack_output_2",
    ]


async def test_unjoin_sets_output_to_matching_input(
    hass: HomeAssistant, fake_amplifier
) -> None:
    """Test unjoin resets a stereo output to its matching input."""
    fake_amplifier.outputs[2].source_1 = 0
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Living Rack",
        data={CONF_HOST: "1.1.1.1", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.sonancedsp.create_sonance_dsp",
        return_value=fake_amplifier,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    target = entity_registry.async_get_entity_id(
        MEDIA_PLAYER_DOMAIN, DOMAIN, "SERIAL123_c"
    )

    assert target is not None

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_UNJOIN,
        {ATTR_ENTITY_ID: target},
        blocking=True,
    )

    output = fake_amplifier.outputs[2]
    assert output.set_source_1_calls == [4]
    assert output.source_1 == 4
