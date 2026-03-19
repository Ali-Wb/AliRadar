from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta

from backend.intelligence.alerts import AlertEngine
from backend.intelligence.presence import PresenceTracker
from backend.pipeline.classifier import enrich
from backend.pipeline.deduplicator import Deduplicator
from backend.pipeline.normalizer import normalize
from backend.scanner.ble_scanner import BLEScanner
from backend.scanner.classic_scanner import CLASSIC_AVAILABLE, ClassicBTScanner
from backend.storage.queries import record_sighting, upsert_device

logger = logging.getLogger(__name__)


class ScannerManager:
    def __init__(self, session_factory, ws_broadcast_fn):
        self.session_factory = session_factory
        self.ws_broadcast_fn = ws_broadcast_fn
        self.ble_scanner = BLEScanner(self._on_raw_event)
        self.classic_scanner = ClassicBTScanner(self._on_raw_event)
        self.deduplicator = Deduplicator()
        self.presence = PresenceTracker()
        self.alerts = AlertEngine(session_factory, ws_broadcast_fn)
        self._last_recorded: dict[str, datetime] = {}
        self._stats: dict = {
            "ble_events": 0,
            "classic_events": 0,
            "errors": 0,
            "start_time": datetime.utcnow(),
        }
        self._running = False
        self._ble_active = False
        self._classic_active = False

    async def start(self) -> None:
        self.alerts = AlertEngine(self.session_factory, self.ws_broadcast_fn)
        self._stats["start_time"] = datetime.utcnow()
        self._running = True
        self._ble_active = False
        self._classic_active = False

        try:
            await self.ble_scanner.start()
            self._ble_active = self.ble_scanner._running
        except Exception as exc:
            logger.exception("BLE scanner failed to start: %s", exc)

        try:
            await self.classic_scanner.start()
            self._classic_active = CLASSIC_AVAILABLE and self.classic_scanner._running
            if not CLASSIC_AVAILABLE:
                logger.warning("Classic Bluetooth scanner unavailable; continuing in BLE-only mode.")
        except Exception as exc:
            logger.exception("Classic Bluetooth scanner failed to start: %s", exc)

        if not self._ble_active and not self._classic_active:
            self._running = False
            raise RuntimeError("No Bluetooth adapters available")

        logger.info(
            "ScannerManager started. BLE active=%s, Classic active=%s",
            self._ble_active,
            self._classic_active,
        )

    async def stop(self) -> None:
        self._running = False
        await self.ble_scanner.stop()
        await self.classic_scanner.stop()
        self._ble_active = False
        self._classic_active = False

    async def _on_raw_event(self, raw: dict) -> None:
        normalized = normalize(raw)
        if normalized is None:
            return

        canonical_mac = self.deduplicator.resolve(normalized)
        normalized["mac"] = canonical_mac
        enriched = enrich(normalized)
        mac = enriched["mac"]
        source = enriched.get("source")

        self.presence.record(mac)

        device = None
        is_new = False
        should_record_sighting = self._should_record_sighting(mac)

        try:
            async with self.session_factory() as session:
                device, is_new = await upsert_device(
                    session,
                    mac=mac,
                    name=enriched.get("name"),
                    device_class=enriched.get("device_class"),
                    manufacturer=enriched.get("manufacturer"),
                    is_ble=source == "ble",
                    is_classic=source == "classic",
                    tx_power=enriched.get("tx_power"),
                )
                if should_record_sighting:
                    await record_sighting(
                        session,
                        device_id=device.id,
                        rssi=enriched.get("rssi"),
                        distance_m=enriched.get("distance_m"),
                        raw_adv=enriched,
                    )
                    self._last_recorded[mac] = datetime.utcnow()
        except Exception as exc:
            self._stats["errors"] += 1
            logger.exception("Failed to persist scan event for %s: %s", mac, exc)

        try:
            await self._broadcast(
                {
                    "type": "device_update",
                    "device": self._build_device_payload(device, enriched),
                    "sighting": {
                        "rssi": enriched.get("rssi"),
                        "distance_m": enriched.get("distance_m"),
                        "zone": enriched.get("distance_zone"),
                    },
                }
            )
        except Exception as exc:
            self._stats["errors"] += 1
            logger.exception("Failed to broadcast scan event for %s: %s", mac, exc)

        if device is not None:
            try:
                await self.alerts.check(device, enriched.get("rssi"), is_new)
            except Exception as exc:
                self._stats["errors"] += 1
                logger.exception("Failed to evaluate alerts for %s: %s", mac, exc)

        if source == "ble":
            self._stats["ble_events"] += 1
        elif source == "classic":
            self._stats["classic_events"] += 1

    def get_stats(self) -> dict:
        now = datetime.utcnow()
        start_time = self._stats["start_time"]
        stats = dict(self._stats)
        stats.update(
            {
                "ble_active": self._ble_active,
                "classic_active": self._classic_active,
                "uptime_seconds": int((now - start_time).total_seconds()),
            }
        )
        return stats

    def _should_record_sighting(self, mac: str) -> bool:
        last_recorded = self._last_recorded.get(mac)
        if last_recorded is None:
            return True
        return datetime.utcnow() - last_recorded >= timedelta(seconds=5)

    def _build_device_payload(self, device, enriched: dict) -> dict:
        if device is None:
            return {
                "mac": enriched.get("mac"),
                "name": enriched.get("name"),
                "device_class": enriched.get("device_class"),
                "manufacturer": enriched.get("manufacturer"),
                "is_ble": enriched.get("source") == "ble",
                "is_classic": enriched.get("source") == "classic",
                "first_seen": None,
                "last_seen": enriched.get("timestamp"),
                "is_favorited": False,
                "user_label": None,
            }

        return {
            "mac": device.mac_address,
            "name": device.name,
            "device_class": device.device_class,
            "manufacturer": device.manufacturer,
            "is_ble": device.is_ble,
            "is_classic": device.is_classic,
            "first_seen": device.first_seen.isoformat() if device.first_seen else None,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "is_favorited": device.is_favorited,
            "user_label": device.user_label,
        }

    async def _broadcast(self, payload: dict) -> None:
        result = self.ws_broadcast_fn(payload)
        if inspect.isawaitable(result):
            await result
