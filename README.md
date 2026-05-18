# Sonance DSP for Home Assistant

Home Assistant custom integration for Sonance DSP amplifiers using the
[`sonance-py`](https://pypi.org/project/sonance-py/) library.

The integration connects directly to the amplifier's local HTTP control
interface and creates media player entities for the amplifier's logical outputs.
It is intended for local control of source selection, volume, mute state, and
output grouping.

## Supported Devices

This integration targets Sonance DSP amplifiers that expose the Sonance web
control interface used by `sonance-py`.

Current behavior is developed around the logical output model exposed by the
library:

- each amplifier is represented as one Home Assistant device
- each active logical output is represented as a `media_player` entity
- stereo-paired outputs appear as one logical output entity
- split mono outputs appear as separate left and right output entities

## Features

- Config flow setup from the Home Assistant UI
- Local polling over the amplifier HTTP API
- One media player entity per logical output
- Source selection from the amplifier's configured source names
- Volume control mapped from Home Assistant's `0..1` scale to the amplifier's
  dB volume range
- Mute and unmute support
- Media player grouping support for joining outputs
- Unjoin support for splitting stereo outputs back to mono
- Device metadata from the amplifier, including model, serial number, firmware
  version, and configured amplifier name

The integration currently reports output entities as idle speakers. It does not
attempt to detect playback state from an upstream source device.

## Installation

### Manual Installation

1. Copy `custom_components/sonancedsp` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration**.
4. Search for **Sonance DSP**.

### HACS Custom Repository

If you use HACS, add this repository as a custom integration repository, install
the integration, then restart Home Assistant before adding **Sonance DSP** from
the integrations UI.

## Configuration

The config flow asks for:

- **Host**: the amplifier hostname or IP address
- **Port**: the HTTP port for the amplifier web control interface, default `80`

During setup, the integration reads basic amplifier status to verify the
connection. The amplifier serial number is used as the unique ID, so the same
physical amplifier cannot be configured twice. If the amplifier name is
available, it is used as the config entry title.

## Entity Behavior

Each media player entity maps to a logical output from `sonance-py`.

Entity names follow the current output shape:

- stereo outputs are named `Output N`
- mono outputs are named `Output N Left` or `Output N Right`

The integration exposes these extra state attributes:

- `channel_indexes`: physical channel indexes included in the logical output
- `output_group`: the amplifier output group identifier
- `stereo_mode`: the current stereo or mono mode

## Services

Use Home Assistant's standard `media_player` services with the Sonance DSP
entities:

- `media_player.select_source`
- `media_player.volume_set`
- `media_player.volume_mute`
- `media_player.join`
- `media_player.unjoin`

Joining outputs delegates to the amplifier output grouping support provided by
`sonance-py`. Unjoining a stereo output switches it back to mono mode.

## Polling

The integration uses Home Assistant's local polling model and refreshes amplifier
state every 10 seconds. After a successful write, the integration publishes the
updated cached state immediately so Home Assistant entities reflect the change
without waiting for the next polling interval.

## Development

This project uses `uv` for dependency management.

Install dependencies:

```bash
uv sync --group dev
```

Run tests:

```bash
uv run pytest
```

Run linting and formatting checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run type checking:

```bash
uv run pyright
```

## Project Layout

- `custom_components/sonancedsp/`: Home Assistant integration code
- `custom_components/sonancedsp/config_flow.py`: UI setup and connection
  validation
- `custom_components/sonancedsp/coordinator.py`: polling coordinator and
  amplifier state snapshots
- `custom_components/sonancedsp/media_player.py`: logical output media player
  entities
- `tests/`: config flow and media player tests
