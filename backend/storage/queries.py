from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.storage.models import Alert, AlertEvent, Device, Sighting


async def upsert_device(
    session: AsyncSession,
    mac,
    name,
    device_class,
    manufacturer,
    is_ble,
    is_classic,
    tx_power,
) -> tuple[Device, bool]:
    existing = await get_device_by_mac(session, mac)
    if existing is not None:
        async with session.begin():
            existing.name = name or existing.name
            existing.device_class = device_class or existing.device_class
            existing.manufacturer = manufacturer or existing.manufacturer
            existing.is_ble = existing.is_ble or is_ble
            existing.is_classic = existing.is_classic or is_classic
            existing.tx_power = tx_power if tx_power is not None else existing.tx_power
            existing.last_seen = datetime.utcnow()
            await session.flush()
        return existing, False

    device = Device(
        mac_address=mac,
        name=name,
        device_class=device_class,
        manufacturer=manufacturer,
        is_ble=is_ble,
        is_classic=is_classic,
        tx_power=tx_power,
    )

    try:
        async with session.begin():
            session.add(device)
            await session.flush()
        return device, True
    except IntegrityError:
        await session.rollback()
        existing = await get_device_by_mac(session, mac)
        if existing is None:
            raise

        async with session.begin():
            existing.name = name or existing.name
            existing.device_class = device_class or existing.device_class
            existing.manufacturer = manufacturer or existing.manufacturer
            existing.is_ble = existing.is_ble or is_ble
            existing.is_classic = existing.is_classic or is_classic
            existing.tx_power = tx_power if tx_power is not None else existing.tx_power
            existing.last_seen = datetime.utcnow()
            await session.flush()
        return existing, False


async def get_all_devices(session: AsyncSession) -> list[Device]:
    result = await session.execute(select(Device).order_by(Device.last_seen.desc()))
    return list(result.scalars().all())


async def get_device_by_mac(session: AsyncSession, mac: str) -> Device | None:
    result = await session.execute(select(Device).where(Device.mac_address == mac))
    return result.scalar_one_or_none()


async def get_active_devices(session: AsyncSession, since_minutes: int) -> list[Device]:
    cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
    result = await session.execute(
        select(Device).where(Device.last_seen >= cutoff).order_by(Device.last_seen.desc())
    )
    return list(result.scalars().all())


async def update_device_label(session: AsyncSession, mac: str, label: str, notes: str):
    device = await get_device_by_mac(session, mac)
    if device is None:
        return None

    async with session.begin():
        device.user_label = label
        device.notes = notes
        await session.flush()
    return device


async def toggle_favorite(session: AsyncSession, mac: str):
    device = await get_device_by_mac(session, mac)
    if device is None:
        return None

    async with session.begin():
        device.is_favorited = not device.is_favorited
        await session.flush()
    return device


async def record_sighting(
    session: AsyncSession,
    device_id: int,
    rssi: int,
    distance_m: float | None,
    raw_adv: dict,
):
    sighting = Sighting(
        device_id=device_id,
        rssi=rssi,
        estimated_distance_m=distance_m,
        raw_advertisement=json.dumps(raw_adv) if raw_adv is not None else None,
    )
    async with session.begin():
        session.add(sighting)
        await session.flush()
    return sighting


async def get_sightings_for_device(
    session: AsyncSession, device_id: int, limit: int = 500
) -> list[Sighting]:
    result = await session.execute(
        select(Sighting)
        .where(Sighting.device_id == device_id)
        .order_by(Sighting.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_sightings(session: AsyncSession, minutes: int = 60) -> list[Sighting]:
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    result = await session.execute(
        select(Sighting)
        .where(Sighting.timestamp >= cutoff)
        .order_by(Sighting.timestamp.desc())
    )
    return list(result.scalars().all())


async def get_active_alerts(session: AsyncSession) -> list[Alert]:
    result = await session.execute(select(Alert).where(Alert.is_active.is_(True)).order_by(Alert.created_at.desc()))
    return list(result.scalars().all())


async def create_alert(
    session: AsyncSession,
    rule_type: str,
    label: str,
    device_id: int | None,
    rule_value: str | None,
) -> Alert:
    alert = Alert(rule_type=rule_type, label=label, device_id=device_id, rule_value=rule_value)
    async with session.begin():
        session.add(alert)
        await session.flush()
    return alert


async def delete_alert(session: AsyncSession, alert_id: int):
    async with session.begin():
        await session.execute(delete(Alert).where(Alert.id == alert_id))


async def record_alert_event(session: AsyncSession, alert_id: int, device_id: int, detail: dict):
    alert_event = AlertEvent(
        alert_id=alert_id,
        device_id=device_id,
        detail=json.dumps(detail) if detail is not None else None,
    )
    async with session.begin():
        session.add(alert_event)
        await session.flush()
    return alert_event


async def get_recent_alert_events(session: AsyncSession, limit: int = 50) -> list[AlertEvent]:
    result = await session.execute(select(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(limit))
    return list(result.scalars().all())
