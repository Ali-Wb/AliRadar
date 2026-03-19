from __future__ import annotations

from datetime import datetime, timedelta


class PresenceTracker:
    def __init__(self):
        self.seen_at: dict[str, datetime] = {}
        self.first_seen_at: dict[str, datetime] = {}

    def record(self, mac):
        now = datetime.utcnow()
        normalized_mac = mac.upper()
        self.first_seen_at.setdefault(normalized_mac, now)
        self.seen_at[normalized_mac] = now

    def is_active(self, mac, max_age_minutes):
        normalized_mac = mac.upper()
        last_seen = self.seen_at.get(normalized_mac)
        if last_seen is None:
            return False
        return last_seen >= datetime.utcnow() - timedelta(minutes=max_age_minutes)

    def get_active_macs(self, max_age_minutes):
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        return [mac for mac, last_seen in self.seen_at.items() if last_seen >= cutoff]

    def get_dwell_minutes(self, mac):
        normalized_mac = mac.upper()
        first_seen = self.first_seen_at.get(normalized_mac)
        if first_seen is None:
            return 0.0
        return (datetime.utcnow() - first_seen).total_seconds() / 60

    def remove(self, mac):
        normalized_mac = mac.upper()
        self.seen_at.pop(normalized_mac, None)
        self.first_seen_at.pop(normalized_mac, None)

    def clear(self):
        self.seen_at.clear()
        self.first_seen_at.clear()
