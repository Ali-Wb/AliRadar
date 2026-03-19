from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from backend.config import settings

logger = logging.getLogger(__name__)

try:
    import bluetooth

    CLASSIC_AVAILABLE = True
except ImportError:
    bluetooth = None
    CLASSIC_AVAILABLE = False
    logger.warning(
        "Classic Bluetooth not available: pybluez2 import failed. Only BLE scanning will be active."
    )


def parse_bt_class(bt_class_int: int) -> str:
    major_class = (bt_class_int >> 8) & 0x1F
    return {
        0x01: "computer",
        0x02: "phone",
        0x04: "networking",
        0x05: "audio",
        0x06: "peripheral",
    }.get(major_class, "unknown")


class ClassicBTScanner:
    def __init__(self, callback):
        self._callback = callback
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return

        self._loop = asyncio.get_running_loop()
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())

    async def _scan_loop(self) -> None:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        while self._running:
            results = await self._loop.run_in_executor(None, self._do_inquiry)
            for result in results:
                await self._callback(result)

            if not self._running:
                break

            await asyncio.sleep(settings.SCAN_INTERVAL_SECONDS)

    async def stop(self) -> None:
        self._running = False

    def _do_inquiry(self) -> list[dict]:
        if not CLASSIC_AVAILABLE or bluetooth is None:
            return []

        try:
            devices = bluetooth.discover_devices(
                duration=settings.CLASSIC_INQUIRY_DURATION,
                lookup_names=True,
                lookup_class=True,
                flush_cache=True,
            )
        except (bluetooth.BluetoothError, OSError) as exc:
            logger.error("Classic Bluetooth inquiry failed: %s", exc)
            return []

        timestamp = datetime.utcnow().isoformat()
        results: list[dict] = []
        for mac, name, bt_class_int in devices:
            results.append(
                {
                    "source": "classic",
                    "mac": mac.upper(),
                    "name": name or None,
                    "rssi": None,
                    "tx_power": None,
                    "service_uuids": [],
                    "manufacturer_data": {},
                    "company_id": None,
                    "bt_class_int": bt_class_int,
                    "bt_major_class": parse_bt_class(bt_class_int),
                    "timestamp": timestamp,
                }
            )
        return results
