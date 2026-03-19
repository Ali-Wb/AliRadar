from __future__ import annotations

import re

from backend.config import settings

MAC_PATTERN = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


def _clean_name(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).replace("\x00", "").strip()
    return cleaned or None


def normalize(raw: dict) -> dict | None:
    mac = str(raw.get("mac", "")).upper()
    if not MAC_PATTERN.match(mac):
        return None

    rssi = raw.get("rssi")
    if rssi is not None and rssi < settings.RSSI_MINIMUM:
        return None

    return {
        "mac": mac,
        "name": _clean_name(raw.get("name")),
        "rssi": rssi,
        "tx_power": raw.get("tx_power"),
        "service_uuids": [str(uuid).upper() for uuid in (raw.get("service_uuids") or [])],
        "manufacturer_data": dict(raw.get("manufacturer_data") or {}),
        "company_id": raw.get("company_id"),
        "bt_class_int": raw.get("bt_class_int"),
        "bt_major_class": raw.get("bt_major_class"),
        "source": raw.get("source"),
        "timestamp": raw.get("timestamp"),
    }
