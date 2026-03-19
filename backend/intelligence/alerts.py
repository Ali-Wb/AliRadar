from __future__ import annotations

import inspect
from datetime import datetime, timedelta

from backend.config import settings
from backend.intelligence.presence import PresenceTracker
from backend.storage.queries import get_active_alerts, record_alert_event


class AlertEngine:
    def __init__(self, session_factory, ws_broadcast_fn):
        self.session_factory = session_factory
        self.ws_broadcast_fn = ws_broadcast_fn
        self.presence_tracker = PresenceTracker()
        self._rules_cache = []
        self._rules_loaded_at: datetime | None = None
        self._appeared_fired: set[tuple[int, int]] = set()
        self._linger_fired: set[tuple[int, str]] = set()
        self._rssi_fired_at: dict[tuple[int, str], datetime] = {}

    async def check(self, device, sighting_rssi, is_new):
        mac = device.mac_address.upper()
        self.presence_tracker.record(mac)
        rules = await self._load_rules()

        for alert in rules:
            if alert.rule_type == "device_appeared":
                if not is_new or alert.device_id != device.id:
                    continue
                fire_key = (alert.id, device.id)
                if fire_key in self._appeared_fired:
                    continue
                self._appeared_fired.add(fire_key)
                await self._fire(alert, device, {"reason": "device_appeared", "is_new": True})
                continue

            if alert.rule_type == "new_unknown_device":
                if is_new and device.device_class == "unknown":
                    await self._fire(alert, device, {"reason": "new_unknown_device", "is_new": True})
                continue

            if alert.rule_type == "device_lingered":
                if device.is_favorited:
                    continue
                linger_minutes = float(alert.rule_value) if alert.rule_value is not None else float(settings.ALERT_LINGER_MINUTES)
                if self.presence_tracker.get_dwell_minutes(mac) < linger_minutes:
                    continue
                fire_key = (alert.id, mac)
                if fire_key in self._linger_fired:
                    continue
                self._linger_fired.add(fire_key)
                await self._fire(
                    alert,
                    device,
                    {
                        "reason": "device_lingered",
                        "dwell_minutes": self.presence_tracker.get_dwell_minutes(mac),
                        "threshold_minutes": linger_minutes,
                    },
                )
                continue

            if alert.rule_type == "rssi_threshold":
                threshold = int(alert.rule_value) if alert.rule_value is not None else settings.RSSI_MINIMUM
                if sighting_rssi is None or sighting_rssi <= threshold:
                    continue
                if alert.device_id is not None and alert.device_id != device.id:
                    continue
                fire_key = (alert.id, mac)
                last_fired = self._rssi_fired_at.get(fire_key)
                if last_fired is not None and last_fired >= datetime.utcnow() - timedelta(seconds=60):
                    continue
                self._rssi_fired_at[fire_key] = datetime.utcnow()
                await self._fire(
                    alert,
                    device,
                    {
                        "reason": "rssi_threshold",
                        "rssi": sighting_rssi,
                        "threshold": threshold,
                    },
                )

    async def _load_rules(self):
        now = datetime.utcnow()
        if self._rules_loaded_at is not None and now - self._rules_loaded_at < timedelta(seconds=30):
            return self._rules_cache

        async with self.session_factory() as session:
            self._rules_cache = await get_active_alerts(session)
        self._rules_loaded_at = now
        return self._rules_cache

    async def _fire(self, alert, device, detail):
        payload = {
            "alert_id": alert.id,
            "device_id": device.id,
            "mac": device.mac_address,
            "label": alert.label,
            "rule_type": alert.rule_type,
            "detail": detail,
            "triggered_at": datetime.utcnow().isoformat() + "Z",
        }

        async with self.session_factory() as session:
            await record_alert_event(session, alert.id, device.id, payload)

        result = self.ws_broadcast_fn(payload)
        if inspect.isawaitable(result):
            await result
