from __future__ import annotations

import asyncio
import ctypes
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler

import uvicorn

from backend.api.server import app, scanner_manager
from backend.config import settings
from backend.storage.database import async_engine


async def _shutdown_runtime() -> None:
    await scanner_manager.stop()
    await async_engine.dispose()


def ensure_admin() -> None:
    if os.name != "nt":
        return

    try:
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        is_admin = False

    if is_admin:
        return

    params = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    raise SystemExit(0)


def configure_logging() -> None:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler("aliradar.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def install_signal_handlers() -> None:
    def _handle_signal(signum, _frame):
        logging.getLogger(__name__).info("Received signal %s, shutting down.", signum)
        try:
            asyncio.run(_shutdown_runtime())
        finally:
            raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


def main() -> None:
    ensure_admin()
    configure_logging()
    install_signal_handlers()
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")


if __name__ == "__main__":
    main()
