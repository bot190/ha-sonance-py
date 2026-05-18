"""Test the Sonance DSP config flow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.sonancedsp.config_flow import CannotConnect
from custom_components.sonancedsp.const import DEFAULT_PORT, DOMAIN
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("enable_sonancedsp_custom_integration")


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.sonancedsp.config_flow.async_read_basic_status",
        return_value=SimpleNamespace(
            amplifier_name="Living Rack",
            amplifier_model="DSP8-130",
            serial_number="SERIAL123",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: DEFAULT_PORT,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Rack"
    assert result["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.sonancedsp.config_flow.async_read_basic_status",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: DEFAULT_PORT,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(
        "custom_components.sonancedsp.config_flow.async_read_basic_status",
        return_value=SimpleNamespace(
            amplifier_name="Living Rack",
            amplifier_model="DSP8-130",
            serial_number="SERIAL123",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: DEFAULT_PORT,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_serial_aborts(hass: HomeAssistant) -> None:
    """Test duplicate devices are aborted by serial number."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Living Rack",
        data={CONF_HOST: "1.1.1.1", CONF_PORT: DEFAULT_PORT},
        unique_id="SERIAL123",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.sonancedsp.config_flow.async_read_basic_status",
        return_value=SimpleNamespace(
            amplifier_name="Living Rack",
            amplifier_model="DSP8-130",
            serial_number="SERIAL123",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.2",
                CONF_PORT: DEFAULT_PORT,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
