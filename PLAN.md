# AliRadar — Task List

> Reference `context.md` at the start of every Codex session.
> Complete tasks in order. Each block below is one prompt — copy everything inside it.

---

## Task 1 — Project scaffold and Python environment

Read `context.md` for full project context before starting.

Create the full repository directory structure as defined in `context.md`. Do not write any logic yet — only create directories and empty placeholder files (`__init__.py`, etc.).

Create `backend/requirements.txt` with these exact pinned versions:
```
bleak==0.21.1
pybluez2==0.46
fastapi==0.111.0
uvicorn[standard]==0.29.0
websockets==12.0
sqlalchemy==2.0.30
aiosqlite==0.20.0
pydantic==2.7.1
pydantic-settings==2.2.1
pywin32==306
requests==2.31.0
pyinstaller==6.6.0
alembic==1.13.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

Create `backend/config.py` with a `Settings` class using `pydantic-settings`:
- `APP_NAME: str = "AliRadar"`
- `VERSION: str = "1.0.0"`
- `HOST: str = "127.0.0.1"`
- `PORT: int = 8765`
- `DB_PATH: str = "aliradar.db"`
- `OUI_PATH: str = "../data/oui.csv"`
- `SCAN_INTERVAL_SECONDS: float = 3.0`
- `CLASSIC_INQUIRY_DURATION: int = 8`
- `RSSI_PATH_LOSS_EXPONENT: float = 2.5`
- `TX_POWER_DEFAULT: int = -59`
- `RSSI_MINIMUM: int = -100`
- `MAX_DEVICE_AGE_MINUTES: int = 10`
- `ALERT_LINGER_MINUTES: int = 10`
- `LOG_LEVEL: str = "INFO"`

Load settings from an optional `.env` file. Export a module-level `settings = Settings()` instance.

Create `frontend/package.json`:
- name: `aliradar`, version: `1.0.0`
- dependencies: `react@^18.3.0`, `react-dom@^18.3.0`
- devDependencies: `vite@^5.2.0`, `@vitejs/plugin-react@^4.2.0`, `electron@^30.0.0`, `electron-builder@^24.13.0`, `concurrently@^8.2.0`
- scripts: `dev` (vite), `build` (vite build), `electron:dev` (concurrently vite + electron), `electron:build` (vite build then electron-builder)

Create `frontend/vite.config.js`: base `./`, build output `dist`, server port `5173`.

Create `scripts/download_oui.py`: downloads `https://standards-oui.ieee.org/oui/oui.csv` and saves to `data/oui.csv` with progress output.

Create `.gitignore` covering: `__pycache__`, `*.pyc`, `.venv`, `*.egg-info`, `node_modules`, `dist`, `*.db`, `.env`, `build/`, `release/`, `*.log`.

After creating all files, list the full directory tree to verify.

---

## Task 2 — Database models and storage layer

Read `context.md` for full project context before starting.

Create `backend/storage/models.py` with four SQLAlchemy ORM models: `Device`, `Sighting`, `Alert`, `AlertEvent`. Full schema is defined in `context.md` under "Database Schema".

Create `backend/storage/database.py`:
- Async engine using `aiosqlite`
- Sync engine for Alembic migrations
- `async def init_db()` — creates all tables
- `async def get_session()` — async context manager yielding `AsyncSession` with `expire_on_commit=False`

Create `backend/storage/queries.py` with all async query functions defined in `context.md` under "Storage Query Functions". All writes use `async with session.begin()`. All reads use `select()` statements. Handle `IntegrityError` gracefully in upsert operations. `upsert_device` must return `(Device, bool)` where the bool is `True` if the device was newly inserted.

---

## Task 3 — OUI lookup, distance calculator, classifier, presence tracker, alert engine

Read `context.md` for full project context before starting.

Create `backend/intelligence/oui_lookup.py`:
- Class `OUILookup`: loads `data/oui.csv` into a `dict[str, str]` (6-char hex prefix → company name). Handle missing file gracefully.
- `def lookup(self, mac: str) -> str | None`: O(1) lookup using first 6 hex chars of MAC.
- Module-level singleton pattern: `init_oui(path)` and `get_manufacturer(mac)`.

Create `backend/intelligence/distance.py`:
- `def rssi_to_distance(rssi, tx_power=-59, n=2.5) -> float | None`: formula `10 ** ((tx_power - rssi) / (10 * n))`, clamped to `[0.1, 500.0]` metres, returns `None` for invalid RSSI.
- `def distance_to_zone(distance_m) -> str`: `<1m` → `"immediate"`, `1–5m` → `"near"`, `5–20m` → `"medium"`, `20–100m` → `"far"`, `>100m` → `"distant"`.

Create `backend/intelligence/classifier.py`:
- `def classify_device(name, manufacturer, service_uuids, manufacturer_data, company_id) -> str`
- Classification rules in priority order are defined in `context.md` under "Device Classification Rules".

Create `backend/intelligence/presence.py`:
- Class `PresenceTracker` with in-memory `dict[str, datetime]`.
- Methods: `record(mac)`, `is_active(mac, max_age_minutes)`, `get_active_macs(max_age_minutes)`, `get_dwell_minutes(mac)`, `remove(mac)`, `clear()`.

Create `backend/intelligence/alerts.py`:
- Class `AlertEngine(session_factory, ws_broadcast_fn)`.
- `async def check(device, sighting_rssi, is_new)`: evaluates all active rules against this device event.
- `async def _load_rules()`: reloads rules from DB every 30 seconds (cached).
- `async def _fire(alert, device, detail)`: records `AlertEvent` and broadcasts via WebSocket.
- Rule logic for all four rule types defined in `context.md` under "Alert Rule Logic".

---

## Task 4 — BLE scanner

Read `context.md` for full project context before starting.

Create `backend/scanner/ble_scanner.py`.

Class `BLEScanner(callback)` using `bleak.BleakScanner` with the callback-based API (not async-for). Use `scanning_mode="passive"`.

`start()`: create scanner, register `_detection_callback`, call `await scanner.start()`. If `BleakError` is raised (adapter not found), log a clear human-readable error and do not crash.

`stop()`: `await scanner.stop()` if running.

`_detection_callback(device, advertisement_data)`: sync method. Build raw dict:
```python
{
    "source": "ble",
    "mac": device.address.upper(),
    "name": advertisement_data.local_name or device.name or None,
    "rssi": advertisement_data.rssi,
    "tx_power": advertisement_data.tx_power,
    "service_uuids": [str(u).upper() for u in (advertisement_data.service_uuids or [])],
    "manufacturer_data": {k: v.hex() for k, v in (advertisement_data.manufacturer_data or {}).items()},
    "company_id": next(iter(advertisement_data.manufacturer_data.keys()), None) if advertisement_data.manufacturer_data else None,
    "service_data": {str(k): v.hex() for k, v in (advertisement_data.service_data or {}).items()},
    "timestamp": datetime.utcnow().isoformat(),
}
```
Skip event if `rssi < settings.RSSI_MINIMUM`. Schedule async callback via `asyncio.get_event_loop().call_soon_threadsafe(asyncio.ensure_future, self._callback(raw))`.

---

## Task 5 — Classic Bluetooth scanner

Read `context.md` for full project context before starting.

Create `backend/scanner/classic_scanner.py`.

Classic BT inquiry is blocking — must run in `loop.run_in_executor(None, ...)` to avoid blocking asyncio.

Class `ClassicBTScanner(callback)`:
- `start()`: store event loop, set running, launch `_scan_loop()` as asyncio task.
- `_scan_loop()`: loop while running — call `_do_inquiry()` in executor, await callback for each result, sleep `settings.SCAN_INTERVAL_SECONDS`.
- `stop()`: set `_running = False`.
- `_do_inquiry() -> list[dict]`: calls `bluetooth.discover_devices(duration=settings.CLASSIC_INQUIRY_DURATION, lookup_names=True, lookup_class=True, flush_cache=True)`. Returns list of raw dicts with keys: `source`, `mac`, `name`, `rssi` (None), `tx_power` (None), `service_uuids` ([]), `manufacturer_data` ({}), `company_id` (None), `bt_class_int`, `bt_major_class`, `timestamp`. Handle `bluetooth.BluetoothError` and `OSError` — log and return `[]`.

Add `def parse_bt_class(bt_class_int: int) -> str`: extract major class from bits 8–12. Map: `0x01`→`"computer"`, `0x02`→`"phone"`, `0x04`→`"networking"`, `0x05`→`"audio"`, `0x06`→`"peripheral"`, else `"unknown"`.

Wrap the `import bluetooth` in a try/except at module level. If import fails, log `"Classic Bluetooth not available: pybluez2 import failed. Only BLE scanning will be active."` and set a module-level flag `CLASSIC_AVAILABLE = False`.

---

## Task 6 — Data pipeline

Read `context.md` for full project context before starting.

Create `backend/pipeline/normalizer.py`:
- `def normalize(raw: dict) -> dict | None`
- Validate MAC against regex `^([0-9A-F]{2}:){5}[0-9A-F]{2}$` after uppercasing. Return `None` if invalid.
- Return `None` if `rssi` is present and `< settings.RSSI_MINIMUM`.
- Clean `name`: strip whitespace, remove null bytes, set to `None` if empty.
- Return normalized dict with all keys guaranteed: `mac`, `name`, `rssi`, `tx_power`, `service_uuids`, `manufacturer_data`, `company_id`, `bt_class_int`, `bt_major_class`, `source`, `timestamp`.

Create `backend/pipeline/deduplicator.py`:
- Class `Deduplicator` with `self._fingerprints: dict[str, str]` (fingerprint → canonical MAC).
- `def resolve(self, normalized: dict) -> str`: compute fingerprint from sorted `service_uuids` + `company_id` + cleaned `name`. If fingerprint is computable and already seen, return stored canonical MAC. Otherwise store and return current MAC.
- `def reset(self)`: clear all fingerprints.
- Fingerprint is `None` (cannot deduplicate) when `service_uuids` is empty AND `company_id` is None AND `name` is None — in that case always return the MAC as-is.

Create `backend/pipeline/classifier.py` (enrichment wiring):
- `def enrich(normalized: dict) -> dict`: add `manufacturer` (from OUI), `device_class` (from classifier), `distance_m` and `distance_zone` (from distance module). Return enriched dict.

---

## Task 7 — Scanner manager

Read `context.md` for full project context before starting.

Create `backend/scanner/scanner_manager.py`.

Class `ScannerManager(session_factory, ws_broadcast_fn)`:
- Owns `BLEScanner`, `ClassicBTScanner`, `Deduplicator`, `PresenceTracker`, `AlertEngine`.
- `self._last_recorded: dict[str, datetime]` — throttle: only write sighting to DB if ≥5 seconds since last write for this MAC.
- `self._stats: dict` — counters for `ble_events`, `classic_events`, `errors`, `start_time`.

`start()`: init AlertEngine, start both scanners (each in try/except — log but continue if unavailable). If BOTH scanners fail, raise `RuntimeError("No Bluetooth adapters available")`. Log which scanners are active.

`stop()`: stop both scanners, set running False.

`_on_raw_event(raw: dict)` — hot path called on every scan event:
1. `normalize(raw)` → drop if None
2. `deduplicator.resolve()` → get canonical MAC, update `normalized["mac"]`
3. `enrich(normalized)` → add manufacturer, class, distance
4. `async with session`: `upsert_device()` → `(device, is_new)`, throttle-check then `record_sighting()`
5. `presence.record(mac)`
6. `await broadcast({"type": "device_update", "device": {...}, "sighting": {...}})`
7. `await alerts.check(device, rssi, is_new)`
8. Increment stats counter

Always broadcast and update presence even when skipping the DB sighting write (throttle). Never let an exception in steps 4–7 propagate and kill the loop — wrap in try/except and increment `errors` counter.

`get_stats() -> dict`: return copy of stats plus uptime.

---

## Task 8 — API server (REST + WebSocket)

Read `context.md` for full project context before starting.

Create `backend/api/ws_manager.py`:
- Class `WebSocketManager` with `self._connections: set[WebSocket]`.
- `connect(ws)`, `disconnect(ws)`, `broadcast(message: dict)`.
- `broadcast` sends to all connections concurrently via `asyncio.gather()`. On send failure, remove that connection from the set.

Create `backend/api/routes.py` using `APIRouter` with prefix `/api/v1`. Implement all endpoints defined in `context.md` under "REST API Endpoints". Apply input sanitization on all user-supplied string fields: strip whitespace, max 256 chars for labels, 4096 for notes, strip HTML tags.

Create `backend/api/server.py`:
- `FastAPI` app with `CORSMiddleware` allowing origins: `http://localhost:5173`, `app://.`, `http://localhost`.
- WebSocket endpoint at `/ws`: accept, add to manager, keep alive with `receive_text()` loop, disconnect on `WebSocketDisconnect`.
- `startup` event: `init_db()`, `init_oui(settings.OUI_PATH)`, `scanner_manager.start()`.
- `shutdown` event: `scanner_manager.stop()`.

Create `backend/main.py`:
- Check for Windows admin privileges using `ctypes.windll.shell32.IsUserAnAdmin()`. If not admin, re-launch with `ShellExecuteW` runas and exit.
- Configure logging: console at INFO, rotating file `aliradar.log` at DEBUG (max 5MB, keep 3 files), format `%(asctime)s [%(levelname)s] %(name)s: %(message)s`.
- Handle `SIGINT`/`SIGTERM` for graceful shutdown.
- Run `uvicorn` with `host=settings.HOST`, `port=settings.PORT`.

---

## Task 9 — Frontend: state stores and WebSocket hook

Read `context.md` for full project context before starting.

Create `frontend/src/store/deviceStore.js`:
Using the `useSyncExternalStore` pattern (no Redux/Zustand). State: `{ devices: {}, sightings: [], isConnected: false, scannerStats: {} }`.
Functions: `subscribe`, `getSnapshot`, `setConnected(bool)`, `upsertDevice(device, sighting)`, `setDevicesFromFetch(list)`, `updateDeviceLabel(mac, label, notes)`, `toggleFavorite(mac)`, `removeStaleDevices(maxAgeMinutes)`.

Create `frontend/src/store/alertStore.js`:
State: `{ rules: [], events: [] }`. Functions: `subscribe`, `getSnapshot`, `setRules(rules)`, `addEvent(event)` (prepend, cap at 50), `setEvents(events)`.

Create `frontend/src/hooks/useWebSocket.js`:
- Manages WebSocket to `ws://127.0.0.1:8765/ws`.
- Auto-reconnects with exponential backoff: 1s → 2s → 4s → 8s → max 30s.
- Tracks `connectionAttempts`. After 10 failed attempts, sets an `abandonedConnection` flag.
- Dispatches by `message.type`: `device_update` → `deviceStore.upsertDevice()`, `alert_event` → `alertStore.addEvent()`, `stats_update` → update stats.
- Uses `useRef` for the socket instance. Cleans up on unmount.
- Returns `{ isConnected, connectionAttempts, lastError, abandonedConnection }`.

Create `frontend/src/hooks/useDevices.js`:
Subscribes to `deviceStore` via `useSyncExternalStore`. Accepts `filter: { activeOnly, classFilter, sortBy, searchQuery }`. Returns `{ devices: filteredSortedArray, totalCount, activeCount }`.

Create `frontend/src/hooks/useAlerts.js`:
Subscribes to `alertStore`. Returns `{ rules, events, unreadCount }`. Tracks unread count (resets when user opens Alerts panel).

---

## Task 10 — Frontend: App shell and layout

Read `context.md` for full project context before starting.

Create `frontend/src/App.jsx` and `frontend/src/App.css`.

Layout:
```
┌──────────────────────────────────────────────────┐
│  StatusBar                                        │
├─────────────────┬────────────────────────────────┤
│  RadarView 55%  │  DeviceList 45%                 │
│                 │                                 │
├─────────────────┴────────────────────────────────┤
│  [Timeline tab] [Alerts tab]  ▲▼ collapse        │
├──────────────────────────────────────────────────┤
│  Timeline or Alerts panel (collapsible, 220px)   │
└──────────────────────────────────────────────────┘
```

On mount: fetch `/api/v1/devices?active_only=false` and `/api/v1/alerts/events`, populate stores. Connect WebSocket. Set up a 30-second interval calling `deviceStore.removeStaleDevices(settings.MAX_DEVICE_AGE_MINUTES)`.

Bottom panel: collapsible via toggle button. Default open. Active tab tracked in local state.

Create `frontend/src/main.jsx`: render `<ErrorBoundary><App /></ErrorBoundary>` into `#root`.

Create `frontend/src/components/ErrorBoundary.jsx`: class component, catches render errors, shows "Something went wrong" with a reload button (`window.location.reload()`).

Create `frontend/index.html`: standard Vite HTML shell with `<div id="root">` and `<script type="module" src="/src/main.jsx">`.

---

## Task 11 — Frontend: RadarView component

Read `context.md` for full project context before starting.

Create `frontend/src/components/RadarView/RadarView.jsx` and `RadarView.css`.

Canvas-based radar, `500×500` px, dark background `#0a0f1a`, animated with `requestAnimationFrame`.

**Rings:** 4 concentric rings at radii `55, 110, 165, 220` px (zones: immediate, near, medium, far). Stroke `rgba(0,200,100,0.15)`, fill `rgba(0,200,100,0.04)`. Label each ring with its zone name at the right edge.

**Sweep line:** Rotates 360° every 3 seconds. Bright green `rgba(0,255,120,0.85)` at current angle, fading trail using a gradient drawn as a filled arc wedge behind it.

**Device dots:**
- Position: stable angle from `macToAngle()` in `deviceUtils.js`, radius mapped from distance zone.
- Size: 8px radius, 12px for favorited devices.
- Color by class as defined in `context.md` under "Device Class Colors".
- Pulse ring animation (expanding ring that fades) for devices updated within the last 3 seconds.
- Selected device (`selectedMac` prop): draw a white ring around its dot.

**Distance → canvas radius mapping:**
- `immediate` (<1m): 30–55px
- `near` (1–5m): 55–110px
- `medium` (5–20m): 110–165px
- `far` (20–100m): 165–220px
- `distant` or unknown: 210px (outer edge)
- Interpolate within each range using the actual distance value.

**Interaction:**
- `onClick`: find dot within 14px of click, call `onDeviceSelect(mac)`.
- `onMouseMove`: show floating tooltip `<div>` at cursor with device name, class, distance, RSSI.

**Props:** `{ devices, onDeviceSelect, selectedMac }`

---

## Task 12 — Frontend: DeviceList and DeviceDetail components

Read `context.md` for full project context before starting.

Create `frontend/src/components/DeviceList/DeviceList.jsx` and `DeviceList.css`.

Filter bar: search input, class dropdown (All / Phone / Car / Headphones / Laptop / Tag / Wearable / Speaker / Unknown), sort dropdown (Last seen / Signal / Distance / Name / First seen).

Device rows:
- Colored class dot, device name (`user_label` ?? `name` ?? MAC), zone badge, distance, RSSI
- Second line: manufacturer, live "Xs ago" / "Xm ago" timestamp, star button
- Highlight row if MAC matches `selectedMac` prop
- Click row → call `onDeviceSelect(mac)`

Create `frontend/src/components/DeviceDetail/DeviceDetail.jsx` and `DeviceDetail.css`.

Slide-in panel (position fixed, right 0, width 380px, full height, background `#111827`, z-index 100). CSS transition on open/close.

Sections:
1. Header: inline-editable name `<input>`, class badge, close button
2. Identity: MAC, manufacturer, class, BLE/Classic badges
3. Signal: live RSSI and distance (from store subscription)
4. RSSI chart: `<canvas>` line chart of last 60 sightings. Y-axis -100 to -30 dBm. X-axis time. Green line, no library.
5. Presence: first seen, last seen, session dwell time
6. Notes: `<textarea>` saving on blur via `PATCH /api/v1/devices/{mac}`
7. Actions: Toggle Favorite, Create Alert for this device, copy MAC to clipboard

Fetch `GET /api/v1/devices/{mac}` when `mac` prop changes.

---

## Task 13 — Frontend: Timeline and Alerts components

Read `context.md` for full project context before starting.

Create `frontend/src/components/Timeline/Timeline.jsx` and `Timeline.css`.

Canvas-based timeline, height 180px. X-axis: last 60 minutes. Y-axis: one row per device class. Bars = continuous sighting periods (gap > 2 min = new bar). Colored by device class. Minimum bar width 4px. Hover tooltip: device name, time range, duration. Fetches `GET /api/v1/sightings?minutes=60` on mount and every 60 seconds.

Create `frontend/src/components/Alerts/Alerts.jsx` and `Alerts.css`.

Two tabs: **Events** and **Rules**.

Events tab: scrollable list, newest first. Each item: colored icon, label, device name, time ago, detail. "Clear all" button.

Rules tab: list of rules with type badge, label, delete button. "Add Rule" form:
- Rule type dropdown: `new_unknown_device`, `device_appeared`, `device_lingered`, `rssi_threshold`
- Label input
- Conditional field: device picker (for `device_appeared`), minutes input (for `device_lingered`), RSSI slider -90 to -40 (for `rssi_threshold`)
- Save → `POST /api/v1/alerts/rules`

---

## Task 14 — Frontend: StatusBar and utilities

Read `context.md` for full project context before starting.

Create `frontend/src/components/StatusBar/StatusBar.jsx` and `StatusBar.css`.

Height 36px. Left: "AliRadar" wordmark. Middle: BLE status dot + label, Classic BT status dot + label. Right: active device count, event rate, WebSocket connection dot (pulses green when live, red when disconnected).

If `abandonedConnection` from `useWebSocket` is true, show a full-width red banner: "Cannot connect to scanner backend. Is AliRadar running as Administrator?"

Create `frontend/src/utils/formatters.js`:
```javascript
formatTimeAgo(isoDate)        // "5s ago", "2m ago", "1h ago"
formatRSSI(rssi)              // "-65 dBm" or "—"
formatDistance(metres)        // "0.5m", "3.2m", "~45m"
formatDuration(seconds)       // "30s", "5m 12s", "2h 15m"
formatDateTime(isoDate)       // "Jan 1, 2024 10:05:32"
macToDisplayName(device)      // user_label ?? name ?? mac
classToColor(deviceClass)     // hex color (matches radar)
classToEmoji(deviceClass)     // 📱 🚗 🎧 💻 🏷️ ⌚ 🔊 ❓
```

Create `frontend/src/utils/deviceUtils.js`:
```javascript
sortDevices(devices, sortBy)    // "last_seen"|"rssi"|"distance"|"name"|"first_seen"
filterDevices(devices, filter)  // { searchQuery, classFilter, activeOnly }
macToAngle(mac)                 // deterministic 0–360° from MAC hash (sum of charCodes × prime mod 360)
```

---

## Task 15 — Integration tests

Read `context.md` for full project context before starting.

First run: `python scripts/download_oui.py` to ensure `data/oui.csv` exists.

Create `backend/tests/__init__.py` and `backend/tests/test_pipeline.py`.

Write a full async integration test using `pytest-asyncio` with an in-memory SQLite database. Initialize all pipeline components with real OUI data.

Feed the 10 fake scan events defined in `context.md` under "Integration Test Events" through the full pipeline (normalize → deduplicate → enrich → upsert_device → record_sighting).

Assert:
- 7 devices in the DB (invalid MAC dropped, weak RSSI dropped, rotated-MAC iPhone deduplicated)
- `AA:BB:CC:DD:EE:01` → `device_class == "phone"`, manufacturer contains `"Apple"`
- `AA:BB:CC:DD:EE:04` → `device_class == "airtag"`
- `AA:BB:CC:DD:EE:05` → `device_class == "headphones"`
- `AA:BB:CC:DD:EE:06` → `device_class == "wearable"`
- Rotated MAC `FF:EE:DD:CC:BB:01` resolves to canonical `AA:BB:CC:DD:EE:01`
- All valid BLE events have `distance_m` calculated
- Sightings count equals 7

Run: `python -m pytest backend/tests/test_pipeline.py -v`

All tests must pass before proceeding to Task 16.

---

## Task 16 — Production hardening

Read `context.md` for full project context before starting.

Apply all hardening items to existing files:

1. **Admin check** in `backend/main.py`: `ctypes.windll.shell32.IsUserAnAdmin()`. If not admin, re-launch via `ShellExecuteW` with `"runas"` and exit.

2. **Logging** in `backend/main.py`: rotating file handler (5MB max, 3 backups) + console handler. Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`.

3. **Graceful shutdown**: `SIGINT`/`SIGTERM` handlers call `scanner_manager.stop()` then close DB engine cleanly.

4. **Alembic setup**: create `backend/alembic.ini` and `backend/alembic/` directory. Create initial migration for all four models. On app startup in `server.py` startup event, run `alembic upgrade head` programmatically before `init_db()`.

5. **Vite production config**: set `base: './'`, define `__APP_VERSION__` from `package.json` via `define`, enable minification.

6. **Electron auto-updater stub**: add commented-out `electron-updater` block in `electron/main.js` as defined in `context.md` under "Electron Auto-updater Stub".

7. **API input sanitization**: verify all `PATCH` and `POST` endpoints trim whitespace, enforce max lengths (256 for labels, 4096 for notes), and strip HTML tags from string inputs.

---

## Task 17 — Electron shell

Read `context.md` for full project context before starting.

Create `frontend/electron/main.js`.

Backend spawning (dev vs production paths defined in `context.md` under "Electron Backend Spawn"):
- Dev: `spawn('python', ['backend/main.py'])` from repo root
- Production: `spawn(path.join(process.resourcesPath, 'backend', 'aliradar-backend.exe'))`
- Pipe stdout/stderr to console with `[backend]` prefix

Wait for backend: poll `GET http://127.0.0.1:8765/api/v1/stats` every 500ms. Timeout 15 seconds → `dialog.showErrorBox`. Only load frontend after 200 response.

Window: 1400×900, min 1100×700, `backgroundColor: "#0a0f1a"`, `contextIsolation: true`, `nodeIntegration: false`.
- Dev: `loadURL("http://localhost:5173")`
- Production: `loadFile("dist/index.html")`

On `app.on("will-quit")`: kill backend process.

Add Electron Builder config to `frontend/package.json` as defined in `context.md` under "Electron Builder Config".

Create `frontend/electron/preload.js`: expose only `window.aliradar = { version }` via `contextBridge`.

---

## Task 18 — Build script, packaging, and README

Read `context.md` for full project context before starting.

Create `scripts/build.py` — automated end-to-end build:
1. `pip install -r backend/requirements.txt`
2. `python scripts/download_oui.py` (skip if `data/oui.csv` exists)
3. `python -m pytest backend/tests/` — abort if any test fails
4. `pyinstaller backend/aliradar-backend.spec --distpath frontend/resources/backend`
5. `npm install` in `frontend/`
6. `npm run build` in `frontend/`
7. `electron-builder` → `release/AliRadar-Setup-1.0.0.exe`
8. Print output path

Create `backend/aliradar-backend.spec` using the full spec defined in `context.md` under "PyInstaller Spec".

Create `frontend/assets/icon.ico` — a valid minimal ICO file (32×32). Build must not fail due to missing icon.

Create `README.md` covering: project description, features list, requirements, quick start (dev), production build instructions, all config settings with descriptions, architecture overview linking to `context.md`, known limitations, MIT license.

**Final verification checklist:**
- [ ] `python scripts/download_oui.py` succeeds
- [ ] `python -m pytest backend/tests/ -v` — all pass
- [ ] `cd backend && python main.py` — starts, BLE scanning active
- [ ] `cd frontend && npm run dev` — Vite starts at port 5173
- [ ] Dashboard loads, WebSocket connects, devices appear within 10s
- [ ] Radar dots appear, clicking opens DeviceDetail
- [ ] Alert rule fires when condition is met
- [ ] `python scripts/build.py` → produces `release/AliRadar-Setup-1.0.0.exe`
- [ ] Installed `.exe` runs without Python or Node installed
