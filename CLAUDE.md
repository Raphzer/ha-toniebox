# CLAUDE.md — ha-toniebox

## Project Overview

Home Assistant custom integration for Toniebox devices, installable via HACS.
Domain: `tonies` | Version: `0.1.0` | Min HA: `2026.1.0`
Depends on: `tonies-api>=0.1.4` (PyPI — source at `Raphzer/tonies-api` on GitHub)

---

## Architecture

### Integration Pattern
- **IoT class:** `cloud_push` — data pulled from Tonies cloud API
- **Config flow:** Email + password authentication (unique ID = lowercased email)
- **Coordinator:** `ToniesCoordinator` manages both polling (Classic) and WebSocket (TNG)

### Dual-Mode Hardware Support
Two distinct Toniebox generations with different capabilities:

| Feature | Classic | TNG (Toniebox Go) |
|---|---|---|
| Update method | Polling (5 min) | WebSocket real-time |
| Battery sensor | No | Yes |
| Sleep command | No | Yes |
| Active Tonie sensor | No | Yes |
| Online status | No | Yes |
| Speaker volume | 25/50/75/100% (snapped) | 25–100% (1% steps) |
| LED control | Select (on/dimmed/off) | Number (0–100%, light ring) |
| Headphone volume | 25/50/75/100% (snapped) | 25–100% (1% steps) |
| Bedtime speaker volume | No | 25–100% (1% steps) |
| Bedtime headphone volume | No | 25–100% (1% steps) |
| Bedtime LED brightness | No | 0–100% (1% steps) |

`is_tng` property on `ToniesBaseEntity` gates TNG-only features.

### Data Flow
```
TonieAPIClient (tonies-api lib)
        │
        ├── REST polling → Classic boxes (every 300s)
        └── WebSocket → TNG boxes (real-time)
                │
        ToniesCoordinator
                │
        ToniesData(boxes, households, ws_state)
                │
        Platform entities (HA state machine)
```

---

## File Map

```
custom_components/tonies/
├── __init__.py        # Entry setup/unload, service registration
├── const.py           # All constants (domain, keys, intervals, options)
├── coordinator.py     # ToniesCoordinator + ToniesData + WebSocket handling
├── entity.py          # ToniesBaseEntity (shared device_info, is_tng)
├── config_flow.py     # ToniesConfigFlow (user auth step)
├── manifest.json      # Domain metadata + requirements
├── strings.json       # Default strings (French)
├── media_player.py    # Media player platform (main entity per box)
├── sensor.py          # Battery, Active Tonie, Online status, Library count
├── switch.py          # Sleep switch (TNG only, momentary)
├── select.py          # LED brightness select (on/dimmed/off) — Classic only
├── number.py          # Headphone volume (all) + speaker volume, LED brightness, bedtime controls (TNG only)
└── translations/
    ├── en.json
    └── fr.json

blueprints/automation/tonies/
├── volume_bedtime.yaml       # Reduce volume at bedtime, restore at wake
├── notify_tonie_change.yaml  # Notify when Tonie changes
├── low_battery_sleep.yaml    # Auto-sleep on low battery
└── sleep_schedule.yaml       # Enforce quiet hours (TNG only)

.github/
├── workflows/lint.yml        # Ruff check + format (push/PR)
├── workflows/validate.yml    # Hassfest + HACS validation
└── dependabot.yml            # Daily dep updates (HA excluded)

scripts/
├── setup      # pip install -r requirements.txt
├── lint       # ruff format + ruff check --fix
└── develop    # Start local HA instance with custom_components in PYTHONPATH
```

---

## Key Classes & Responsibilities

### `ToniesCoordinator` (`coordinator.py`)
Central data manager. Owns:
- `async_setup()` / `async_teardown()` — API client lifecycle with SSL in thread pool
- Polling loop for Classic boxes
- WebSocket listener for TNG boxes with MQTT topic parsing
- Per-box `ws_state` dict: `online`, `battery`, `charging`, `tonie_id`, `tonie_name`, `tonie_image`, `headphones`
- Service methods: `sleep_box`, `set_volume`, `set_headphone_volume`, `set_led`, `set_lightring_brightness`, `set_bedtime_volume`, `set_bedtime_headphone_volume`, `set_bedtime_lightring_brightness`

### `ToniesBaseEntity` (`entity.py`)
Base for all entities. Provides `_box`, `_ws` (ws_state dict), `is_tng`, and `device_info` with manufacturer "Boxine".

### Media Player (`media_player.py`)
Primary entity per box. State machine:
- `OFF` → box offline (TNG) or never
- `PLAYING` → tonie active (tonie_id set)
- `IDLE` → online but no tonie (Classic always IDLE)

### `ToniesLibrarySensor` (`sensor.py`)
Global sensor (one per config entry, not per box). Plain `SensorEntity` — not a `CoordinatorEntity`. Subscribes to coordinator updates manually in `async_added_to_hass`. No `device_info`. Must call `super().__init__()`.

### Service (`__init__.py`)
`tonies.get_tonies_list` fires `tonies_list_result` event (bypasses HA's 16KB attribute limit). Declared in `services.yaml` alongside the Python files (not in `custom_components/` root).

### Error Handling (`config_flow.py`)
Two custom exceptions:
- `InvalidAuth` — bad credentials (`TonieAuthError` from lib — note: singular, NOT `ToniesAuthError`)
- `CannotConnect` — network / API failure (all other exceptions)

Both must have matching keys in `strings.json`, `translations/en.json`, `translations/fr.json`.

---

## Development Setup

### Prerequisites
- Python 3.14 (devcontainer uses `mcr.microsoft.com/devcontainers/python:3.14`)
- System packages: `ffmpeg`, `libturbojpeg0`, `libpcap-dev`

### Commands
```bash
scripts/setup    # Install Python dependencies
scripts/lint     # Ruff format + check with autofix
scripts/develop  # Start local HA on port 8123 with debug logging
```

### Requirements
- `homeassistant==2025.2.4`
- `ruff==0.14.14`
- `colorlog==6.10.1`

### Linting
Uses **Ruff** for both formatting and linting. CI enforces `ruff check` and `ruff format --check` on every push and PR.

---

## Adding a New Platform

1. Create `custom_components/tonies/<platform>.py` extending `ToniesBaseEntity`
2. Add platform name to `PLATFORMS` list in `const.py`
3. Gate TNG-only features with `self.is_tng`
4. Register via `async_setup_entry` in the platform file (standard HA pattern)
5. Add translation keys to `strings.json`, `translations/en.json`, `translations/fr.json`

---

## Adding a New Coordinator Service

1. Add method to `ToniesCoordinator` in `coordinator.py`
2. Call the underlying `tonies-api` client method
3. Call `self.async_update_listeners()` after state mutation
4. If exposing as an HA service, register in `__init__.py` under `async_setup_entry`

---

## Important Constraints

- **SSL handling must run in thread pool** — `asyncio.get_event_loop().run_in_executor()` for SSL context creation to avoid blocking the event loop; file reads (certifi certs) must also use `with open(...)` to avoid handle leaks
- **Volume on Classic is snapped** to 25/50/75/100% — never send arbitrary values
- **Sleep switch is momentary** — turns on, sends command, immediately turns back off; do not persist ON state
- **`strings.json` is French** (used as default) — keep `en.json` and `fr.json` translations in sync; `en.json` must be in English
- **Error taxonomy in config_flow**: `TonieAuthError` (singular — lib class name) → `InvalidAuth` (bad credentials); `ToniesApiError` + all others → `CannotConnect` (transient failure). Never raise `InvalidAuth` for network errors
- **Setup failures raise `ConfigEntryNotReady`** — do not `return False` in `async_setup_entry`; HA will retry automatically
- **`ToniesLibrarySensor`** does not extend `CoordinatorEntity` — it is a plain `SensorEntity` that calls `super().__init__()` and subscribes manually via `async_added_to_hass`. It has no `device_info` (floating entity by design)
- **`config/configuration.yaml`** is the only config file preserved in `.gitignore` (local dev only)
- **`homeassistant` package excluded** from Dependabot auto-updates (pinned manually)
- **`select.py` LED is Classic-only** — TNG boxes use `TngLedBrightnessNumber` (light ring, 0–100%); never create `ToniesLedSelect` for a TNG box
- **`number.py` TNG entities**: `TngSpeakerVolumeNumber`, `TngLedBrightnessNumber`, `TngBedtimeSpeakerVolumeNumber`, `TngBedtimeHeadphoneVolumeNumber`, `TngBedtimeLedBrightnessNumber` — all gated by `is_tng` in `async_setup_entry`

---

## CI / Validation

| Workflow | Trigger | Jobs |
|---|---|---|
| `lint.yml` | push to main, PRs | Ruff check + format |
| `validate.yml` | daily, dispatch, main changes | Hassfest + HACS validation |

HACS config (`hacs.json`): `content_in_root: false`, renders README, min HA `2026.1.0`.
