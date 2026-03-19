from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api.routes import configure_routes, router
from backend.storage.models import Base
from backend.storage.queries import create_alert, record_alert_event, record_sighting, upsert_device


class StubScannerManager:
    def get_stats(self) -> dict:
        return {
            "ble_active": True,
            "classic_active": False,
            "ble_events": 1,
            "classic_events": 0,
            "errors": 0,
            "uptime_seconds": 5,
        }


@asynccontextmanager
async def session_factory_fixture(session_maker):
    session = session_maker()
    try:
        yield session
    finally:
        await session.close()


def build_test_client(session_maker) -> TestClient:
    app = FastAPI()

    @asynccontextmanager
    async def session_factory():
        async with session_factory_fixture(session_maker) as session:
            yield session

    configure_routes(session_factory, StubScannerManager())
    app.include_router(router)
    return TestClient(app)


def test_device_and_alert_responses_deserialize_json():
    async def setup_data(session_maker):
        async with session_maker() as session:
            device, _ = await upsert_device(
                session,
                mac="AA:BB:CC:DD:EE:FF",
                name="Phone",
                device_class="phone",
                manufacturer="Apple Inc.",
                is_ble=True,
                is_classic=False,
                tx_power=-59,
            )
            await record_sighting(
                session,
                device_id=device.id,
                rssi=-55,
                distance_m=1.5,
                raw_adv={"hello": "world"},
            )
            alert = await create_alert(
                session,
                rule_type="device_appeared",
                label="Known device",
                device_id=device.id,
                rule_value=None,
            )
            await record_alert_event(
                session,
                alert_id=alert.id,
                device_id=device.id,
                detail={"reason": "matched"},
            )

    async def run_assertions(client):
        device_response = client.get("/api/v1/devices/AA:BB:CC:DD:EE:FF")
        assert device_response.status_code == 200
        device_payload = device_response.json()
        assert device_payload["sightings"][0]["raw_advertisement"] == {"hello": "world"}

        events_response = client.get("/api/v1/alerts/events")
        assert events_response.status_code == 200
        events_payload = events_response.json()
        assert events_payload["events"][0]["detail"] == {"reason": "matched"}

    import asyncio

    async def main():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await setup_data(session_maker)
        with build_test_client(session_maker) as client:
            await run_assertions(client)
        await engine.dispose()

    asyncio.run(main())


def test_post_alert_rule_rejects_blank_required_fields():
    import asyncio

    async def main():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        with build_test_client(session_maker) as client:
            response = client.post(
                "/api/v1/alerts/rules",
                json={"rule_type": "   ", "label": "<b>   </b>", "device_id": None, "rule_value": None},
            )
            assert response.status_code == 422
        await engine.dispose()

    asyncio.run(main())
