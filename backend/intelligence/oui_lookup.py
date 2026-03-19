from __future__ import annotations

import csv
from pathlib import Path

from backend.config import settings


class OUILookup:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.prefix_to_company: dict[str, str] = {}
        self._load()

    def _resolve_path(self) -> Path:
        if self.path.is_absolute():
            return self.path
        return Path(__file__).resolve().parents[1] / self.path

    def _load(self) -> None:
        resolved_path = self._resolve_path()
        if not resolved_path.exists():
            self.prefix_to_company = {}
            return

        mapping: dict[str, str] = {}
        with resolved_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                prefix = (row.get("Assignment") or "").strip().upper()
                company = (row.get("Organization Name") or "").strip()
                if len(prefix) == 6 and company:
                    mapping[prefix] = company

        self.prefix_to_company = mapping

    def lookup(self, mac: str) -> str | None:
        prefix = "".join(char for char in mac.upper() if char.isalnum())[:6]
        if len(prefix) != 6:
            return None
        return self.prefix_to_company.get(prefix)


_oui_lookup: OUILookup | None = None


def init_oui(path: str | Path = settings.OUI_PATH) -> OUILookup:
    global _oui_lookup
    _oui_lookup = OUILookup(path)
    return _oui_lookup


def get_manufacturer(mac: str) -> str | None:
    global _oui_lookup
    if _oui_lookup is None:
        _oui_lookup = init_oui(settings.OUI_PATH)
    return _oui_lookup.lookup(mac)
