"""Parser for the Qingping-specific BLE advertisement format used by the CGD1.

This is a different, simpler dialect than the generic Xiaomi "MiBeacon" format
used by most other Xiaomi ecosystem devices (single-byte device id and object
type codes instead of two-byte ones, and no encryption on this device).
Reverse-engineered from the `qingping-ble` library that backs Home Assistant's
official "Qingping" integration:
https://github.com/Bluetooth-Devices/qingping-ble
"""
import struct

OBJ_TEMPERATURE_HUMIDITY = 0x01
OBJ_BATTERY = 0x02

_TEMP_HUMIDITY_STRUCT = struct.Struct("<hH")


def parse_advertisement(data: bytes) -> dict:
    """Extract temperature/humidity/battery from a Qingping advertisement payload.

    Layout: byte 0 flags, byte 1 device id, bytes 2-7 mac, then a sequence of
    (1-byte type, 1-byte length, payload) objects starting at byte 8.
    Returns an empty dict if the payload is too short or has no objects
    understood here.
    """
    if len(data) < 10:
        return {}

    offset = 8
    result = {}

    while offset + 2 <= len(data):
        obj_id = data[offset]
        obj_len = data[offset + 1]
        payload = data[offset + 2:offset + 2 + obj_len]
        offset += 2 + obj_len

        if len(payload) != obj_len:
            break  # truncated payload, stop parsing

        if obj_id == OBJ_TEMPERATURE_HUMIDITY and obj_len == 4:
            temp, humidity = _TEMP_HUMIDITY_STRUCT.unpack(payload)
            result["temperature"] = temp / 10
            result["humidity"] = humidity / 10
        elif obj_id == OBJ_BATTERY and obj_len == 1:
            result["battery"] = payload[0]

    return result
