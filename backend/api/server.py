from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import configure_routes, router
from backend.api.ws_manager import WebSocketManager
from backend.config import settings
from backend.intelligence.oui_lookup import init_oui
from backend.scanner.scanner_manager import ScannerManager
from backend.storage.database import get_session, init_db

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)
ws_manager = WebSocketManager()
scanner_manager = ScannerManager(get_session, ws_manager.broadcast)
configure_routes(get_session, scanner_manager)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "app://.", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    init_oui(settings.OUI_PATH)
    await scanner_manager.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await scanner_manager.stop()
