from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from backend.intelligence.oui_lookup import init_oui
from backend.pipeline.classifier import enrich
from backend.pipeline.deduplicator import Deduplicator
from backend.pipeline.normalizer import normalize


FAKE_EVENTS = [
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:01", "name": "iPhone", "rssi": -65,
     "tx_power": -59, "service_uuids": ["1800", "1801"],
     "manufacturer_data": {76: b"\x10\x05"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:00"},
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:02", "name": "Galaxy S24", "rssi": -72,
     "tx_power": -59, "service_uuids": ["180F", "1800"],
     "manufacturer_data": {117: b"\x00\x01"}, "company_id": 0x0075,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:01"},
    {"source": "classic", "mac": "AA:BB:CC:DD:EE:03", "name": "BMW 5 Series",
     "rssi": None, "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": 0x200404, "bt_major_class": "phone",
     "timestamp": "2024-01-01T10:00:02"},
    {"source": "ble", "mac": "FF:EE:DD:CC:BB:01", "name": "iPhone", "rssi": -68,
     "tx_power": -59, "service_uuids": ["1800", "1801"],
     "manufacturer_data": {76: b"\x10\x05"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:01:00"},
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:04", "name": None, "rssi": -55,
     "tx_power": -59, "service_uuids": ["FD6F"],
     "manufacturer_data": {76: b"\x12\x19"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:03"},
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:05", "name": "AirPods Pro", "rssi": -50,
     "tx_power": -59, "service_uuids": [],
     "manufacturer_data": {76: b"\x0e\x20"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:04"},
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:06", "name": "Fenix 7", "rssi": -80,
     "tx_power": -59, "service_uuids": ["180D"],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:05"},
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:07", "name": None, "rssi": -90,
     "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:06"},
    {"source": "ble", "mac": "INVALID", "name": "bad", "rssi": -50,
     "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:07"},
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:08", "name": "weak", "rssi": -105,
     "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:08"},
]


@dataclass
class DeviceRow:
    id: int
    mac_address: str
    name: str | None
    device_class: str | None
    manufacturer: str | None
    is_ble: bool
    is_classic: bool
    tx_power: int | None


async def _init_db(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT UNIQUE NOT NULL,
            name TEXT,
            device_class TEXT,
            manufacturer TEXT,
            is_ble INTEGER NOT NULL,
            is_classic INTEGER NOT NULL,
            tx_power INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE sightings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            rssi INTEGER,
            estimated_distance_m REAL,
            raw_advertisement TEXT
        )
        """
    )
    connection.commit()


async def upsert_device(connection: sqlite3.Connection, enriched: dict) -> tuple[DeviceRow, bool]:
    row = connection.execute(
        "SELECT id, mac_address, name, device_class, manufacturer, is_ble, is_classic, tx_power FROM devices WHERE mac_address = ?",
        (enriched["mac"],),
    ).fetchone()

    if row is None:
        connection.execute(
            "INSERT INTO devices (mac_address, name, device_class, manufacturer, is_ble, is_classic, tx_power) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                enriched["mac"],
                enriched.get("name"),
                enriched.get("device_class"),
                enriched.get("manufacturer"),
                int(enriched.get("source") == "ble"),
                int(enriched.get("source") == "classic"),
                enriched.get("tx_power"),
            ),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, mac_address, name, device_class, manufacturer, is_ble, is_classic, tx_power FROM devices WHERE mac_address = ?",
            (enriched["mac"],),
        ).fetchone()
        return DeviceRow(*row), True

    connection.execute(
        "UPDATE devices SET name = COALESCE(?, name), device_class = COALESCE(?, device_class), manufacturer = COALESCE(?, manufacturer), is_ble = MAX(is_ble, ?), is_classic = MAX(is_classic, ?), tx_power = COALESCE(?, tx_power) WHERE mac_address = ?",
        (
            enriched.get("name"),
            enriched.get("device_class"),
            enriched.get("manufacturer"),
            int(enriched.get("source") == "ble"),
            int(enriched.get("source") == "classic"),
            enriched.get("tx_power"),
            enriched["mac"],
        ),
    )
    connection.commit()
    row = connection.execute(
        "SELECT id, mac_address, name, device_class, manufacturer, is_ble, is_classic, tx_power FROM devices WHERE mac_address = ?",
        (enriched["mac"],),
    ).fetchone()
    return DeviceRow(*row), False


async def record_sighting(connection: sqlite3.Connection, device_id: int, enriched: dict) -> None:
    connection.execute(
        "INSERT INTO sightings (device_id, rssi, estimated_distance_m, raw_advertisement) VALUES (?, ?, ?, ?)",
        (device_id, enriched.get("rssi"), enriched.get("distance_m"), str(enriched)),
    )
    connection.commit()


async def _run_pipeline_test() -> None:
    oui_path = Path(__file__).resolve().parents[2] / "data" / "oui.csv"
    init_oui(oui_path)

    connection = sqlite3.connect(":memory:")
    await _init_db(connection)

    deduplicator = Deduplicator()
    canonical_macs_seen: set[str] = set()
    resolved_macs: dict[str, str] = {}
    valid_ble_distances: list[float | None] = []

    for raw in FAKE_EVENTS:
        normalized = normalize(raw)
        if normalized is None:
            continue

        canonical_mac = deduplicator.resolve(normalized)
        resolved_macs[raw["mac"]] = canonical_mac
        normalized["mac"] = canonical_mac

        enriched = enrich(normalized)
        device, _ = await upsert_device(connection, enriched)

        if enriched["source"] == "ble":
            valid_ble_distances.append(enriched.get("distance_m"))

        if canonical_mac not in canonical_macs_seen:
            await record_sighting(connection, device.id, enriched)
            canonical_macs_seen.add(canonical_mac)

    devices = connection.execute(
        "SELECT mac_address, device_class, manufacturer FROM devices ORDER BY mac_address"
    ).fetchall()
    device_map = {mac: (device_class, manufacturer) for mac, device_class, manufacturer in devices}
    sightings_count = connection.execute("SELECT COUNT(*) FROM sightings").fetchone()[0]

    assert len(devices) == 7
    assert device_map["AA:BB:CC:DD:EE:01"][0] == "phone"
    assert "Apple" in (device_map["AA:BB:CC:DD:EE:01"][1] or "")
    assert device_map["AA:BB:CC:DD:EE:04"][0] == "airtag"
    assert device_map["AA:BB:CC:DD:EE:05"][0] == "headphones"
    assert device_map["AA:BB:CC:DD:EE:06"][0] == "wearable"
    assert resolved_macs["FF:EE:DD:CC:BB:01"] == "AA:BB:CC:DD:EE:01"
    assert all(distance is not None for distance in valid_ble_distances)
    assert sightings_count == 7


def test_pipeline_integration() -> None:
    asyncio.run(_run_pipeline_test())
