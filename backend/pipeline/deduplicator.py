from __future__ import annotations


class Deduplicator:
    def __init__(self):
        self._fingerprints: dict[str, str] = {}

    def resolve(self, normalized: dict) -> str:
        fingerprint = self._build_fingerprint(normalized)
        mac = normalized["mac"]
        if fingerprint is None:
            return mac

        canonical_mac = self._fingerprints.get(fingerprint)
        if canonical_mac is not None:
            return canonical_mac

        self._fingerprints[fingerprint] = mac
        return mac

    def reset(self):
        self._fingerprints.clear()

    def _build_fingerprint(self, normalized: dict) -> str | None:
        service_uuids = sorted(str(uuid).upper() for uuid in (normalized.get("service_uuids") or []))
        company_id = normalized.get("company_id")
        name = normalized.get("name")
        cleaned_name = name.strip().lower() if isinstance(name, str) else None

        if not service_uuids and company_id is None and cleaned_name is None:
            return None

        return "|".join(
            [
                ",".join(service_uuids),
                "" if company_id is None else str(company_id),
                cleaned_name or "",
            ]
        )
