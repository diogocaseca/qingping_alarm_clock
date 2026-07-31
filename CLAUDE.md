# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (HACS-installable) for the Qingping Cleargrass CGD1 alarm clock. It talks to the physical device over Bluetooth LE using `bleak`, handling the device's proprietary auth handshake and binary GATT protocol to read/write configuration and alarms. There is no backend/server component — all logic runs inside Home Assistant's event loop.

## Development environment

There is no build system, test suite, linter, or CI in this repo — it's a plain Python package meant to be copied into a Home Assistant `custom_components` directory. There are no npm/pip scripts to run. To validate a change, you generally need to install the component into a real (or dev) Home Assistant instance with a Bluetooth adapter that can reach the physical clock.

Dependencies: `bleak>=0.17.0` (see [requirements.txt](requirements.txt) and [manifest.json](custom_components/qingping_alarm_clock/manifest.json)).

When bumping the integration version, update `version` in [manifest.json](custom_components/qingping_alarm_clock/manifest.json).

## Architecture

### Layering

- **`qingping/` package** — device protocol layer, independent of Home Assistant entity/platform concepts (though it does use `homeassistant.core.HomeAssistant` and the `bluetooth` integration to obtain a `BleakClient`).
  - [`qingping.py`](custom_components/qingping_alarm_clock/qingping/qingping.py) — the `Qingping` class: owns the `BleakClient`, handles connect/auth/disconnect lifecycle, all GATT reads/writes, and exposes high-level async methods (`set_alarm`, `delete_alarm`, `set_time`, `set_sound_volume`, `set_language`, etc.) used by entities and services.
  - [`configuration.py`](custom_components/qingping_alarm_clock/qingping/configuration.py) — `Configuration`: parses/serializes the 20-byte device config blob (sound volume, timezone, brightness, night mode, language, formats). Has an "expiry" (`CONFIGURATION_VALIDITY_TIME` = 30 min) so stale cached config triggers a re-read.
  - [`alarm.py`](custom_components/qingping_alarm_clock/qingping/alarm.py) — `Alarm`/`AlarmDay`: parses/serializes 5-byte alarm slot records (enabled, hour, minute, day-of-week bitmask, snooze).
  - [`eventbus.py`](custom_components/qingping_alarm_clock/qingping/eventbus.py) — minimal pub/sub (`EventBus`) used to push device events (connect/disconnect/config update/alarms update, see [`events.py`](custom_components/qingping_alarm_clock/qingping/events.py)) to entities, which update HA state accordingly.
  - [`util.py`](custom_components/qingping_alarm_clock/qingping/util.py) — `alarm_days_from_string` (service-call day parsing) and the `@updates_configuration` decorator, which wraps a setter to ensure connection + fresh config before running, then re-reads config after.
  - [`exceptions.py`](custom_components/qingping_alarm_clock/qingping/exceptions.py) — `NotConnectedError`, `NoConfigurationError` (both `HomeAssistantError` subclasses).

- **Home Assistant integration layer** (top-level module files):
  - [`__init__.py`](custom_components/qingping_alarm_clock/__init__.py) — `async_setup_entry`/`async_unload_entry`; creates one `Qingping` instance per config entry, stores it on `entry.runtime_data`, registers a Bluetooth discovery callback to opportunistically (re)connect, and forwards setup to the platforms in `PLATFORMS`.
  - [`config_flow.py`](custom_components/qingping_alarm_clock/config_flow.py) — UI config flow: discovers supported devices via BLE advertisement (Xiaomi service UUID + product id `0x0576`), or accepts a manual MAC, validates by connecting, then prompts for a friendly name.
  - Platform files — each maps `Qingping`/`Configuration`/`Alarm` state to HA entities and listens on `instance.eventbus` for updates: [`switch.py`](custom_components/qingping_alarm_clock/switch.py) (alarms-on, night-mode), [`number.py`](custom_components/qingping_alarm_clock/number.py) (volume, screen light time, brightness), [`select.py`](custom_components/qingping_alarm_clock/select.py) (language, time format, temp unit), [`time.py`](custom_components/qingping_alarm_clock/time.py) (night start/end), [`binary_sensor.py`](custom_components/qingping_alarm_clock/binary_sensor.py).
  - [`entity.py`](custom_components/qingping_alarm_clock/entity.py) — shared `DeviceInfo` builder used by all platforms.
  - [`services.py`](custom_components/qingping_alarm_clock/services.py) — registers the domain services (`set_alarm`, `delete_alarm`, `get_alarms`, `set_time`, `refresh`) with voluptuous schemas; each looks up the target `Qingping` instance by resolving the HA device_id to a Bluetooth MAC via the device registry, then calls the matching method on the instance.
  - [`const.py`](custom_components/qingping_alarm_clock/const.py) — domain name, service/attribute name constants, alarm slot count (19), connection/retry timing constants.
  - [`services.yaml`](custom_components/qingping_alarm_clock/services.yaml) / [`strings.json`](custom_components/qingping_alarm_clock/strings.json) / [`translations/en.json`](custom_components/qingping_alarm_clock/translations/en.json) — HA-facing service and UI text; keep these in sync with `services.py` and `config_flow.py` when adding/renaming fields or flow steps.

### Device protocol notes (relevant when touching `qingping/`)

- Connection flow: BLE connect → wait ~2s for service discovery → write a fixed 2-step auth handshake to `MAIN_CHAR` → subscribe to notifications on `CFG_READ_CHAR` → request config (`\x01\x02`) and alarms (`\x01\x06`), each awaited via an `asyncio.Event` set inside `_notification_handler`.
- Writes go through `_write_config` (to `CFG_WRITE_CHAR`), which also (re)schedules a `delayed_disconnect` after `DISCONNECT_DELAY` seconds of inactivity — the client doesn't stay connected indefinitely.
- `_ensure_connected` / `_ensure_configuration` / `_ensure_alarms` are the guard helpers most public methods call before touching the device; `_ensure_connected` retries connecting in a loop bounded by `CONNECTION_TIMEOUT`.
- Config and alarm setters mutate the in-memory `Configuration`/`Alarm` object first, then serialize with `to_bytes()` and write — `to_bytes()` enforces the exact wire layout (e.g. `Configuration.to_bytes()` raises if the result isn't 20 bytes), so keep byte offsets/lengths in `configuration.py` and `alarm.py` in sync with any parsing changes.
- Alarm slots (0–18, `ALARM_SLOTS_COUNT`) are fetched three at a time per notification (`slot_offset`, `slot_offset+1`, `slot_offset+2`); an all-`0xff` 5-byte record means the slot is unconfigured (`Alarm.is_configured` is `False`).
