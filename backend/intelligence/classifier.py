from __future__ import annotations


def _normalize_service_uuids(service_uuids) -> set[str]:
    normalized = set()
    for uuid in service_uuids or []:
        compact = str(uuid).replace("-", "").upper()
        if len(compact) >= 4:
            normalized.add(compact[-4:])
            normalized.add(compact)
    return normalized


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(needle.lower() in lowered for needle in needles)


def classify_device(name, manufacturer, service_uuids, manufacturer_data, company_id) -> str:
    del manufacturer_data

    device_name = name or ""
    maker = manufacturer or ""
    normalized_uuids = _normalize_service_uuids(service_uuids)

    if company_id == 0x004C and "FD6F" in normalized_uuids:
        return "airtag"

    if "180D" in normalized_uuids or "1816" in normalized_uuids:
        return "wearable"

    if "110A" in normalized_uuids or "110B" in normalized_uuids:
        return "speaker"

    if company_id in {0x0075, 0x00E0}:
        return "wearable"

    if _contains_any(
        maker,
        (
            "BMW",
            "Mercedes",
            "Toyota",
            "Ford",
            "Volkswagen",
            "Audi",
            "Honda",
            "Hyundai",
            "Kia",
            "Tesla",
            "Volvo",
            "Porsche",
            "Renault",
            "Peugeot",
            "Fiat",
        ),
    ):
        return "car"

    if "FE2C" in normalized_uuids or "181A" in normalized_uuids:
        return "tag"

    if company_id == 0x004C:
        return "phone"

    if "samsung" in maker.lower():
        return "phone"

    if "180F" in normalized_uuids and "1800" in normalized_uuids:
        return "phone"

    if _contains_any(device_name, ("MacBook", "iPhone", "iPad", "Galaxy", "Pixel", "OnePlus", "Xiaomi", "Redmi")):
        return "phone"

    if _contains_any(device_name, ("AirPods", "WH-", "WF-", "Buds", "Headphone", "Earphone")):
        return "headphones"

    if _contains_any(device_name, ("Laptop", "ThinkPad", "Surface", "Dell", "HP ")):
        return "laptop"

    return "unknown"
