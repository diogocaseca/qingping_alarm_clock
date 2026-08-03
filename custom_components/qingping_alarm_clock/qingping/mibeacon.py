"""Parser for the passive Xiaomi/Qingping MiBeacon BLE advertisement format.

This is unrelated to the GATT auth handshake in qingping.py — it decodes the
service_data broadcast passively by the device (no connection required).
Temperature, humidity and battery are transmitted unencrypted on the CGD1.
"""
import logging

_LOGGER = logging.getLogger(__name__)

OBJ_TEMPERATURE = 0x1004
OBJ_HUMIDITY = 0x1006
OBJ_BATTERY = 0x100A
OBJ_TEMPERATURE_HUMIDITY = 0x100D

FLAG_ENCRYPTED = 1 << 3
FLAG_MAC_INCLUDE = 1 << 4
FLAG_CAPABILITY_INCLUDE = 1 << 5
FLAG_OBJECT_INCLUDE = 1 << 6

CAPABILITY_IO_FLAG = 1 << 3


def parse_mibeacon(data: bytes) -> dict:
    """Extract temperature/humidity/battery from a MiBeacon service_data payload.

    Returns an empty dict if the payload is too short, encrypted, or doesn't
    contain any of the fields understood here.
    """
    if len(data) < 5:
        return {}

    frame_control = int.from_bytes(data[0:2], "little")
    if frame_control & FLAG_ENCRYPTED:
        _LOGGER.debug("MiBeacon payload is encrypted, cannot parse: %s", data.hex())
        return {}

    offset = 5  # frame control (2) + product id (2) + frame counter (1)

    if frame_control & FLAG_MAC_INCLUDE:
        offset += 6

    if frame_control & FLAG_CAPABILITY_INCLUDE:
        if len(data) <= offset:
            return {}
        capability = data[offset]
        offset += 1
        if capability & CAPABILITY_IO_FLAG:
            offset += 2

    if not frame_control & FLAG_OBJECT_INCLUDE:
        return {}

    result = {}
    while offset + 3 <= len(data):
        obj_id = int.from_bytes(data[offset:offset + 2], "little")
        obj_len = data[offset + 2]
        payload = data[offset + 3:offset + 3 + obj_len]
        offset += 3 + obj_len

        if len(payload) != obj_len:
            break  # truncated payload, stop parsing

        if obj_id == OBJ_TEMPERATURE and obj_len == 2:
            result["temperature"] = int.from_bytes(payload, "little", signed=True) / 10
        elif obj_id == OBJ_HUMIDITY and obj_len == 2:
            result["humidity"] = int.from_bytes(payload, "little", signed=False) / 10
        elif obj_id == OBJ_TEMPERATURE_HUMIDITY and obj_len == 4:
            result["temperature"] = int.from_bytes(payload[0:2], "little", signed=True) / 10
            result["humidity"] = int.from_bytes(payload[2:4], "little", signed=False) / 10
        elif obj_id == OBJ_BATTERY and obj_len >= 1:
            result["battery"] = payload[0]

    return result
