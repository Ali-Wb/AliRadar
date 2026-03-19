from __future__ import annotations

from backend.config import settings
from backend.intelligence.classifier import classify_device
from backend.intelligence.distance import distance_to_zone, rssi_to_distance
from backend.intelligence.oui_lookup import get_manufacturer


def enrich(normalized: dict) -> dict:
    manufacturer = get_manufacturer(normalized["mac"])
    device_class = classify_device(
        normalized.get("name"),
        manufacturer,
        normalized.get("service_uuids") or [],
        normalized.get("manufacturer_data") or {},
        normalized.get("company_id"),
    )
    distance_m = rssi_to_distance(
        normalized.get("rssi"),
        tx_power=normalized.get("tx_power") if normalized.get("tx_power") is not None else settings.TX_POWER_DEFAULT,
        n=settings.RSSI_PATH_LOSS_EXPONENT,
    )

    enriched = dict(normalized)
    enriched.update(
        {
            "manufacturer": manufacturer,
            "device_class": device_class,
            "distance_m": distance_m,
            "distance_zone": distance_to_zone(distance_m),
        }
    )
    return enriched
