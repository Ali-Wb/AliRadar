from __future__ import annotations


def rssi_to_distance(rssi, tx_power=-59, n=2.5) -> float | None:
    if rssi is None or rssi < -100 or rssi > 0:
        return None

    distance_metres = 10 ** ((tx_power - rssi) / (10 * n))
    return max(0.1, min(500.0, distance_metres))


def distance_to_zone(distance_m) -> str:
    if distance_m is None:
        return "unknown"
    if distance_m < 1:
        return "immediate"
    if distance_m <= 5:
        return "near"
    if distance_m <= 20:
        return "medium"
    if distance_m <= 100:
        return "far"
    return "distant"
