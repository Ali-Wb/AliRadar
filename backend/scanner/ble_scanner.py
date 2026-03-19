from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from bleak import BleakScanner
from bleak.exc import BleakError

from backend.config import settings

logger = logging.getLogger(__name__)


class BLEScanner:
    def __init__(self, callback):
        self._callback = callback
        self._scanner: BleakScanner | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        self._scanner = BleakScanner(
            detection_callback=self._detection_callback,
            scanning_mode="passive",
        )

        try:
            await self._scanner.start()
            self._running = True
        except BleakError as exc:
            logger.error(
                "BLE scanner could not start. No compatible Bluetooth adapter was found or the adapter is unavailable: %s",
                exc,
            )
            self._scanner = None
            self._running = False

    async def stop(self) -> None:
        if not self._running or self._scanner is None:
            return

        await self._scanner.stop()
        self._running = False
        self._scanner = None

    def _detection_callback(self, device, advertisement_data) -> None:
        if advertisement_data.rssi < settings.RSSI_MINIMUM:
            return

        raw = {
            "source": "ble",
            "mac": device.address.upper(),
            "name": advertisement_data.local_name or device.name or None,
            "rssi": advertisement_data.rssi,
            "tx_power": advertisement_data.tx_power,
            "service_uuids": [str(u).upper() for u in (advertisement_data.service_uuids or [])],
            "manufacturer_data": {
                k: v.hex() for k, v in (advertisement_data.manufacturer_data or {}).items()
            },
            "company_id": next(iter(advertisement_data.manufacturer_data.keys()), None)
            if advertisement_data.manufacturer_data
            else None,
            "service_data": {
                str(k): v.hex() for k, v in (advertisement_data.service_data or {}).items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        asyncio.get_event_loop().call_soon_threadsafe(
            asyncio.ensure_future,
            self._callback(raw),
        )
