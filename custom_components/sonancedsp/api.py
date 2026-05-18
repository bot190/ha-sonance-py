"""Helpers for interacting with the sonance-py library."""

from aiohttp import ClientSession
from sonance_py import SonanceDSP  # noqa: PLC0415


def create_sonance_dsp(host: str, port: int, session: ClientSession) -> object:
    """Create a Sonance DSP amplifier client."""

    return SonanceDSP(host, port=port, session=session)


async def async_read_basic_status(
    host: str, port: int, session: ClientSession
) -> object:
    """Read basic amplifier status used during config flow validation."""
    amplifier = create_sonance_dsp(host, port, session)
    return await amplifier.read_basic_status()
