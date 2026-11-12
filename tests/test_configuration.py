import pytest

from custom_components.qingping_alarm_clock.qingping.configuration import Configuration


def _config_bytes(tz_byte: int, tz_plus: bool, night_mode: bool = False) -> bytes:
    return bytes([
        0x13, 0x02,
        3,            # sound volume
        0xFF, 0xFF,
        0x00,         # flags: ZH, 24h, celsius, alarms on
        tz_byte,      # timezone offset / 6 (absolute value)
        10,           # screen light time
        0x55,         # daytime/nighttime brightness (50 / 50)
        21, 0, 6, 0,  # night start/end
        1 if tz_plus else 0,
        1 if night_mode else 0,
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    ])


@pytest.mark.parametrize("tz_byte, tz_plus, expected_minutes", [
    (30, False, -180),  # UTC-3
    (30, True, 180),    # UTC+3
    (0, True, 0),       # UTC
])
def test_to_bytes_round_trips_timezone(tz_byte, tz_plus, expected_minutes):
    raw = _config_bytes(tz_byte, tz_plus)

    config = Configuration(raw)

    assert config.timezone_offset == expected_minutes
    written = config.to_bytes()
    # byte 1 differs by design: 0x02 in a read response, 0x01 in a write command
    assert written[:1] == raw[:1]
    assert written[1] == 0x01
    assert written[2:] == raw[2:]


def test_night_mode_toggle_works_with_negative_timezone():
    config = Configuration(_config_bytes(30, tz_plus=False))

    config.night_mode_enabled = True
    data = config.to_bytes()

    assert len(data) == 20
    assert data[6] == 30  # absolute offset / 6, sign lives in byte 13
    assert data[13] == 0
    assert data[14] == 1


def test_setting_negative_timezone_serializes_absolute_value():
    config = Configuration(_config_bytes(0, tz_plus=True))

    config.timezone_offset = -180
    data = config.to_bytes()

    assert data[6] == 30
    assert data[13] == 0
