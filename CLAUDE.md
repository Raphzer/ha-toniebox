# CLAUDE.md — ha-toniebox

## Project Overview

Home Assistant custom integration for Toniebox devices, installable via HACS.
Domain: `tonies` | Version: `0.1.1` | Min HA: `2026.1.0`
Depends on: `tonies-api>=0.1.4` (PyPI — source at `Raphzer/tonies-api` on GitHub)

---

## Architecture

### Integration Pattern
- **IoT class:** `cloud_push` — data pulled from Tonies cloud API
- **Config flow:** Email + password authentication (unique ID = lowercased email)
- **Coordinator:** `ToniesCoordinator` manages both polling (Classic) and WebSocket (Gen 2)

### Dual-Mode Hardware Support

| Feature | Classic (Gen 1) | Gen 2 |
|---|---|---|
| Update method | Polling REST (5 min) | WebSocket real-time |
| Battery sensor | No | Yes |
| Sleep command | No | Yes (button) |
| Active Tonie sensor | No | Yes |
| Chapter sensor | No | Yes |
| Online status | No | Yes |
| Speaker volume | 25/50/75/100% (snapped) | 25–100% (1% steps) |
| LED control | Select (on/dimmed/off) | Number (0–100%, light ring) |
| Headphone volume | 25/50/75/100% (snapped) | 25–100% (1% steps) |
| Bedtime speaker volume | No | 25–100% (1% steps) |
| Bedtime headphone volume | No | 25–100% (1% steps) |
| Bedtime LED brightness | No | 0–100% (1% steps) |

`is_tng` property on `ToniesBaseEntity` (mirrors `Toniebox.is_tng` from the lib) gates Gen 2-only features.

### Data Flow
```
TonieAPIClient (tonies-api lib)
        │
        ├── REST polling → Classic boxes (every 300s)
        └── WebSocket → Gen 2 boxes (real-time)
                │
        ToniesCoordinator
                │
        ToniesData(boxes, households_with_tonies, ws_state)
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
├── sensor.py          # Battery, Active Tonie (+ entity_picture), Connection,
│                      # Chapter, Library count, ContentTonieSensor, CreativeTonieSensor
├── button.py          # Sleep Now button (Gen 2 only, momentary press)
├── select.py          # LED brightness select (on/dimmed/off) — Classic only
├── number.py          # Headphone volume (all) + speaker volume, LED brightness,
│                      # bedtime controls (Gen 2 only)
└── translations/
    ├── en.json
    └── fr.json

blueprints/automation/tonies/
├── volume_bedtime.yaml       # Reduce volume at bedtime, restore at wake
├── notify_tonie_change.yaml  # Notify when Tonie changes
├── low_battery_sleep.yaml    # Auto-sleep on low battery (uses button.press)
└── sleep_schedule.yaml       # Enforce quiet hours (Gen 2 only, uses button.press)

brands/
└── icon.png                  # Integration icon for HACS brand validation
```

---

## Key Classes & Responsibilities

### `ToniesCoordinator` (`coordinator.py`)
Central data manager. Owns:
- `async_setup()` / `async_teardown()` — API client lifecycle with SSL in thread pool
- Polling loop for Classic boxes
- WebSocket listener for Gen 2 boxes with MQTT topic parsing
- Per-box `ws_state` dict: `online`, `battery`, `charging`, `tonie_id`, `tonie_name`, `tonie_image`, `headphones`, `chapter`, `chapter_until_ms`, `chapter_duration`
- `_find_tonie_by_id(tonie_id)` — case-insensitive lookup for NFC chip UID → library tonie
- Service methods: `sleep_box`, `set_volume`, `set_headphone_volume`, `set_led`, `set_lightring_brightness`, `set_bedtime_volume`, `set_bedtime_headphone_volume`, `set_bedtime_lightring_brightness`

### `ToniesBaseEntity` (`entity.py`)
Base for all entities. Provides `_box`, `_ws` (ws_state dict), `is_tng`, and `device_info` with:
- `manufacturer = "Boxine"`
- `model = "Toniebox Go"` (Gen 2) or `"Toniebox"` (Classic)

### Media Player (`media_player.py`)
Primary entity per box. State machine:
- `OFF` → box offline (Gen 2) or never connected
- `PLAYING` → tonie active (tonie_id set)
- `IDLE` → online but no tonie (Classic always IDLE)

### `ToniesTonieSensor` (`sensor.py`)
- `native_value` = tonie name (looked up from library if bare NFC UID received)
- `entity_picture` = tonie image URL (replaces icon when tonie is active)
- Attributes: `tonie_id`, `tonie_image_url`, `chapter`, `chapter_remaining_s`, `chapter_duration_s`

### `ToniesChapterSensor` (`sensor.py`)
- `native_value` = chapter number (int)
- Attributes: `chapter_duration_s`, `chapter_remaining_s`
- `chapter_remaining_s` is computed at read time from `chapter_until_ms` (absolute timestamp)

### `ToniesLibrarySensor` (`sensor.py`)
Global sensor (one per config entry, not per box). Plain `SensorEntity` — not a `CoordinatorEntity`. Subscribes to coordinator updates manually in `async_added_to_hass`. Must call `super().__init__()`. Grouped under the virtual "Tonies Library" device (`DeviceEntryType.SERVICE`).

### `TonieSleepButton` (`button.py`)
Momentary button — Gen 2 only. `async_press()` calls `coordinator.sleep_box(mac_address)`. No state to persist.

### Service (`__init__.py`)
`tonies.get_tonies_list` fires `tonies_list_result` event (bypasses HA's 16KB attribute limit). Declared in `services.yaml`.

### Error Handling (`config_flow.py`)
Two custom exceptions:
- `InvalidAuth` — bad credentials (`TonieAuthError` from lib — note: singular, NOT `ToniesAuthError`)
- `CannotConnect` — network / API failure (all other exceptions)

---

## WebSocket Event Handling

The `_on_ws_event` callback in `ToniesCoordinator` handles these topic patterns:

| Topic contains | Parsed fields |
|---|---|
| `online-state` | `online` — accepts both `"online"` and `"connected"` as truthy |
| `metrics/battery` | `battery` (%), `charging` (bool) |
| `playback/state` | `tonie_id`, `tonie_name`, `tonie_image`, `chapter`, `chapter_until_ms`, `chapter_duration` |
| `metrics/headphones` | `headphones` (bool) |

**Tonie field formats in `playback/state`:**
- `dict` → full object with `id`, `name`, `imageUrl`
- `str` → bare NFC chip UID → lookup via `_find_tonie_by_id()` (case-insensitive)
- `None` → tonie removed, clear all state

---

## Development Setup

### Commands
```bash
scripts/setup    # Install Python dependencies
scripts/lint     # Ruff format + check with autofix
scripts/develop  # Start local HA on port 8123 with debug logging
```

### Requirements
- `homeassistant==2026.3.2`
- `ruff==0.14.14`
- `colorlog==6.10.1`

### Linting
Uses **Ruff** for both formatting and linting. CI enforces `ruff check` and `ruff format --check` on every push and PR.

---

## Adding a New Platform

1. Create `custom_components/tonies/<platform>.py` extending `ToniesBaseEntity`
2. Add platform name to `PLATFORMS` list in `const.py`
3. Gate Gen 2-only features with `self.is_tng`
4. Register via `async_setup_entry` in the platform file (standard HA pattern)
5. Add translation keys to `strings.json`, `translations/en.json`, `translations/fr.json`

---

## Adding a New Coordinator Service

1. Add method to `ToniesCoordinator` in `coordinator.py`
2. Call the underlying `tonies-api` client method
3. Call `self.async_request_refresh()` after state mutation if needed
4. If exposing as an HA service, register in `__init__.py` under `async_setup_entry`

---

## Important Constraints

- **SSL handling must run in thread pool** — certifi cert reads use `with open(...)` via `async_add_executor_job` to avoid blocking the event loop and prevent handle leaks
- **Volume on Classic is snapped** to `[25, 50, 75, 100]%` — never send arbitrary values
- **Sleep is a button, not a switch** — use `button.press`, not `switch.turn_on`; do not add a persistent state
- **`strings.json` is French** (used as default) — keep `en.json` and `fr.json` in sync; `en.json` must be in English
- **Error taxonomy in config_flow**: `TonieAuthError` (singular — lib class name) → `InvalidAuth`; `ToniesApiError` + all others → `CannotConnect`. Never raise `InvalidAuth` for network errors
- **Setup failures raise `ConfigEntryNotReady`** — do not `return False` in `async_setup_entry`; HA will retry automatically
- **`ToniesLibrarySensor`** does not extend `CoordinatorEntity` — plain `SensorEntity`, must call `super().__init__()`, subscribes manually via `async_added_to_hass`
- **`select.py` LED is Classic-only** — Gen 2 boxes use `TngLedBrightnessNumber` (light ring, 0–100%); never create `ToniesLedSelect` for a Gen 2 box
- **`number.py` Gen 2 entities**: `TngSpeakerVolumeNumber`, `TngLedBrightnessNumber`, `TngBedtimeSpeakerVolumeNumber`, `TngBedtimeHeadphoneVolumeNumber`, `TngBedtimeLedBrightnessNumber` — all gated by `is_tng` in `async_setup_entry`
- **`chapter_remaining_s`** is a snapshot computed at entity read time from `chapter_until_ms`; it is not updated continuously between WebSocket events
- **`config/configuration.yaml`** is the only config file preserved in `.gitignore` (local dev only)
- **`homeassistant` package excluded** from Dependabot auto-updates (pinned manually)

---

## CI / Validation

| Workflow | Trigger | Jobs |
|---|---|---|
| `lint.yml` | push to main, PRs | Ruff check + format |
| `validate.yml` | daily, dispatch, main changes | Hassfest + HACS validation |

HACS config (`hacs.json`): `content_in_root: false`, renders README, min HA `2026.1.0`.
Topics GitHub requis : `hacs`, `homeassistant`.
