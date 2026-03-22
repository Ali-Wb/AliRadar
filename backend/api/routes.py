from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from backend.storage.models import Alert, AlertEvent, Device, Sighting
from backend.storage.queries import (
    create_alert,
    delete_alert,
    get_active_alerts,
    get_active_devices,
    get_all_devices,
    get_device_by_mac,
    get_recent_alert_events,
    get_recent_sightings,
    get_sightings_for_device,
    toggle_favorite,
    update_device_label,
)

router = APIRouter(prefix="/api/v1")
_session_factory = None
_scanner_manager = None
HTML_TAG_RE = re.compile(r"<[^>]+>")
VALID_SORT_FIELDS = {"last_seen", "name", "first_seen", "rssi", "distance"}


class DeviceUpdatePayload(BaseModel):
    user_label: str | None = None
    notes: str | None = None


class AlertCreatePayload(BaseModel):
    rule_type: str
    label: str
    device_id: int | None = None
    rule_value: str | None = None


def configure_routes(session_factory, scanner_manager) -> None:
    global _session_factory, _scanner_manager
    _session_factory = session_factory
    _scanner_manager = scanner_manager


def _sanitize_string(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = HTML_TAG_RE.sub("", value).strip()
    return cleaned[:max_length]


def _ensure_configured() -> tuple[Any, Any]:
    if _session_factory is None or _scanner_manager is None:
        raise RuntimeError("Routes are not configured")
    return _session_factory, _scanner_manager


def _deserialize_json_blob(value: str | None) -> dict | None:
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _serialize_sighting(sighting: Sighting | None) -> dict | None:
    if sighting is None:
        return None
    return {
        "id": sighting.id,
        "timestamp": sighting.timestamp.isoformat() if sighting.timestamp else None,
        "rssi": sighting.rssi,
        "estimated_distance_m": sighting.estimated_distance_m,
        "raw_advertisement": _deserialize_json_blob(sighting.raw_advertisement),
    }


def _serialize_device(device: Device, last_sighting: Sighting | None = None) -> dict:
    return {
        "mac": device.mac_address,
        "name": device.name,
        "device_class": device.device_class,
        "manufacturer": device.manufacturer,
        "is_ble": device.is_ble,
        "is_classic": device.is_classic,
        "first_seen": device.first_seen.isoformat() if device.first_seen else None,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "last_rssi": last_sighting.rssi if last_sighting else None,
        "last_distance_m": last_sighting.estimated_distance_m if last_sighting else None,
        "last_zone": None,
        "is_favorited": device.is_favorited,
        "user_label": device.user_label,
        "notes": device.notes,
    }


def _serialize_alert(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "device_id": alert.device_id,
        "rule_type": alert.rule_type,
        "rule_value": alert.rule_value,
        "label": alert.label,
        "is_active": alert.is_active,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


@router.get("/devices")
async def list_devices(
    active_only: bool = True,
    class_filter: str | None = None,
    sort_by: str = "last_seen",
):
    session_factory, _ = _ensure_configured()
    sanitized_class_filter = _sanitize_string(class_filter, 256)
    sort_key = _sanitize_string(sort_by, 32) or "last_seen"
    if sort_key not in VALID_SORT_FIELDS:
        raise HTTPException(status_code=422, detail="Invalid sort field")

    async with session_factory() as session:
        devices = await get_active_devices(session, 10) if active_only else await get_all_devices(session)

        if sanitized_class_filter:
            devices = [device for device in devices if device.device_class == sanitized_class_filter]

        device_rows: list[dict] = []
        for device in devices:
            sightings = await get_sightings_for_device(session, device.id, limit=1)
            last_sighting = sightings[0] if sightings else None
            row = _serialize_device(device, last_sighting)
            if row["last_distance_m"] is not None:
                distance = row["last_distance_m"]
                if distance < 1:
                    row["last_zone"] = "immediate"
                elif distance <= 5:
                    row["last_zone"] = "near"
                elif distance <= 20:
                    row["last_zone"] = "medium"
                elif distance <= 100:
                    row["last_zone"] = "far"
                else:
                    row["last_zone"] = "distant"
            device_rows.append(row)

        if sort_key == "last_seen":
            device_rows.sort(key=lambda device: device["last_seen"] or "", reverse=True)
        elif sort_key == "first_seen":
            device_rows.sort(key=lambda device: device["first_seen"] or "", reverse=True)
        elif sort_key == "name":
            device_rows.sort(key=lambda device: device["name"] or "")
        elif sort_key == "rssi":
            device_rows.sort(key=lambda device: device["last_rssi"] if device["last_rssi"] is not None else -999, reverse=True)
        elif sort_key == "distance":
            device_rows.sort(
                key=lambda device: device["last_distance_m"] if device["last_distance_m"] is not None else float("inf")
            )

        active_count = len(await get_active_devices(session, 10))
        return {"devices": device_rows, "total": len(device_rows), "active_count": active_count}


@router.get("/devices/{mac}")
async def get_device(mac: str):
    session_factory, _ = _ensure_configured()
    normalized_mac = _sanitize_string(mac, 17)
    async with session_factory() as session:
        device = await get_device_by_mac(session, normalized_mac)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        sightings = await get_sightings_for_device(session, device.id, limit=100)
        return {
            "device": _serialize_device(device, sightings[0] if sightings else None),
            "sightings": [_serialize_sighting(sighting) for sighting in sightings],
        }


@router.patch("/devices/{mac}")
async def patch_device(mac: str, payload: DeviceUpdatePayload):
    session_factory, _ = _ensure_configured()
    normalized_mac = _sanitize_string(mac, 17)
    user_label = _sanitize_string(payload.user_label, 256)
    notes = _sanitize_string(payload.notes, 4096)

    async with session_factory() as session:
        device = await update_device_label(session, normalized_mac, user_label, notes)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"device": _serialize_device(device)}


@router.post("/devices/{mac}/favorite")
async def favorite_device(mac: str):
    session_factory, _ = _ensure_configured()
    normalized_mac = _sanitize_string(mac, 17)

    async with session_factory() as session:
        device = await toggle_favorite(session, normalized_mac)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"device": _serialize_device(device)}


@router.get("/sightings")
async def list_sightings(minutes: int = Query(default=60, ge=1, le=1440)):
    session_factory, _ = _ensure_configured()
    async with session_factory() as session:
        sightings = await get_recent_sightings(session, minutes=minutes)
        return {"sightings": [_serialize_sighting(sighting) for sighting in sightings]}


@router.get("/alerts/rules")
async def list_alert_rules():
    session_factory, _ = _ensure_configured()
    async with session_factory() as session:
        alerts = await get_active_alerts(session)
        return {"alerts": [_serialize_alert(alert) for alert in alerts]}


@router.post("/alerts/rules")
async def post_alert_rule(payload: AlertCreatePayload):
    session_factory, _ = _ensure_configured()
    rule_type = _sanitize_string(payload.rule_type, 64)
    label = _sanitize_string(payload.label, 256)
    rule_value = _sanitize_string(payload.rule_value, 256)
    if not rule_type:
        raise HTTPException(status_code=422, detail="rule_type is required")
    if not label:
        raise HTTPException(status_code=422, detail="label is required")

    async with session_factory() as session:
        alert = await create_alert(
            session,
            rule_type=rule_type,
            label=label,
            device_id=payload.device_id,
            rule_value=rule_value,
        )
        return {"alert": _serialize_alert(alert)}


@router.delete("/alerts/rules/{alert_id}")
async def remove_alert_rule(alert_id: int):
    session_factory, _ = _ensure_configured()
    async with session_factory() as session:
        await delete_alert(session, alert_id)
    return {"deleted": True}


@router.get("/alerts/events")
async def list_alert_events():
    session_factory, _ = _ensure_configured()
    async with session_factory() as session:
        events = await get_recent_alert_events(session, limit=50)
        device_ids = [event.device_id for event in events]
        devices = {}
        if device_ids:
            result = await session.execute(select(Device).where(Device.id.in_(device_ids)))
            devices = {device.id: device for device in result.scalars().all()}
        return {
            "events": [
                {
                    "id": event.id,
                    "alert_id": event.alert_id,
                    "device_id": event.device_id,
                    "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
                    "detail": _deserialize_json_blob(event.detail),
                    "device": _serialize_device(devices[event.device_id]) if event.device_id in devices else None,
                }
                for event in events
            ]
        }


@router.get("/stats")
async def get_stats():
    _, scanner_manager = _ensure_configured()
    return scanner_manager.get_stats()
