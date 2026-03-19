# AliRadar — Project Context

> This file is the single source of truth for Codex.
> Include it at the start of every session: "Read context.md before starting."

---

## What This Project Is

**AliRadar** is a Windows desktop Bluetooth proximity scanner. A USB Bluetooth dongle is plugged into a Windows PC. The app continuously scans for all nearby Bluetooth devices — phones, cars, AirTags, headphones, laptops, speakers, wearables — and displays them on a live radar dashboard.

**Final deliverable:** A single installable `AliRadar-Setup-1.0.0.exe` for Windows 10/11 x64 that runs without requiring Python or Node.js installed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| BLE scanning | Python `bleak==0.21.1` |
| Classic BT scanning | Python `pybluez2==0.46` |
| Backend API | `FastAPI==0.111.0` + `uvicorn[standard]==0.29.0` |
| Real-time events | `websockets==12.0` over WebSocket |
| Database | SQLite via `SQLAlchemy==2.0.30` + `aiosqlite==0.20.0` |
| DB migrations | `alembic==1.13.1` |
| Config | `pydantic-settings==2.2.1` |
| Frontend | React 18 + Vite 5, plain CSS (no Tailwind) |
| Desktop shell | Electron 30 |
| Backend packaging | PyInstaller 6.6.0 |
| App packaging | electron-builder 24 → NSIS installer |
| Tests | `pytest==8.2.0` + `pytest-asyncio==0.23.6` |

---

## Repository Structure

```
aliradar/
├── backend/
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── ble_scanner.py
│   │   ├── classic_scanner.py
│   │   └── scanner_manager.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── normalizer.py
│   │   ├── deduplicator.py
│   │   └── classifier.py
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── oui_lookup.py
│   │   ├── distance.py
│   │   ├── presence.py
│   │   └── alerts.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── queries.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── routes.py
│   │   └── ws_manager.py
│   ├── alembic/
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_pipeline.py
│   ├── config.py
│   ├── main.py
│   ├── aliradar-backend.spec
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RadarView/
│   │   │   │   ├── RadarView.jsx
│   │   │   │   └── RadarView.css
│   │   │   ├── DeviceList/
│   │   │   │   ├── DeviceList.jsx
│   │   │   │   └── DeviceList.css
│   │   │   ├── DeviceDetail/
│   │   │   │   ├── DeviceDetail.jsx
│   │   │   │   └── DeviceDetail.css
│   │   │   ├── Timeline/
│   │   │   │   ├── Timeline.jsx
│   │   │   │   └── Timeline.css
│   │   │   ├── Alerts/
│   │   │   │   ├── Alerts.jsx
│   │   │   │   └── Alerts.css
│   │   │   ├── StatusBar/
│   │   │   │   ├── StatusBar.jsx
│   │   │   │   └── StatusBar.css
│   │   │   └── ErrorBoundary.jsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js
│   │   │   ├── useDevices.js
│   │   │   └── useAlerts.js
│   │   ├── store/
│   │   │   ├── deviceStore.js
│   │   │   └── alertStore.js
│   │   ├── utils/
│   │   │   ├── deviceUtils.js
│   │   │   └── formatters.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── electron/
│   │   ├── main.js
│   │   └── preload.js
│   ├── assets/
│   │   └── icon.ico
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/
│   └── oui.csv
├── scripts/
│   ├── download_oui.py
│   └── build.py
├── .gitignore
├── README.md
├── PLAN.md
└── context.md
```

---

## Configuration (`backend/config.py`)

All settings are in `backend/config.py` as a `pydantic-settings` `Settings` class. A module-level `settings = Settings()` is imported everywhere. Settings can be overridden via `.env` file.

| Setting | Default | Description |
|---|---|---|
| `APP_NAME` | `"AliRadar"` | Application name |
| `VERSION` | `"1.0.0"` | App version |
| `HOST` | `"127.0.0.1"` | API server bind address |
| `PORT` | `8765` | API server port |
| `DB_PATH` | `"aliradar.db"` | SQLite database file path |
| `OUI_PATH` | `"../data/oui.csv"` | Path to IEEE OUI vendor CSV |
| `SCAN_INTERVAL_SECONDS` | `3.0` | Sleep between Classic BT inquiry cycles |
| `CLASSIC_INQUIRY_DURATION` | `8` | Seconds per Classic BT inquiry |
| `RSSI_PATH_LOSS_EXPONENT` | `2.5` | Path loss exponent `n` for distance formula |
| `TX_POWER_DEFAULT` | `-59` | Default TX power (dBm at 1m) used when not advertised |
| `RSSI_MINIMUM` | `-100` | Drop events weaker than this (dBm) |
| `MAX_DEVICE_AGE_MINUTES` | `10` | Remove from live view after N minutes of silence |
| `ALERT_LINGER_MINUTES` | `10` | Trigger linger alert after N minutes of continuous presence |
| `LOG_LEVEL` | `"INFO"` | Logging level |

---

## Database Schema

### Table: `devices`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `mac_address` | String(17) | unique, not null, indexed | `AA:BB:CC:DD:EE:FF` format |
| `name` | String(256) | nullable | Best known display name |
| `device_class` | String(64) | nullable | See Device Classes below |
| `manufacturer` | String(256) | nullable | From OUI lookup |
| `is_ble` | Boolean | default False | Seen via BLE |
| `is_classic` | Boolean | default False | Seen via Classic BT |
| `tx_power` | Integer | nullable | Advertised TX power (dBm) |
| `first_seen` | DateTime | not null, default utcnow | |
| `last_seen` | DateTime | not null, default utcnow, indexed | |
| `is_favorited` | Boolean | default False | User-marked |
| `user_label` | String(256) | nullable | User-assigned name |
| `notes` | Text | nullable | User notes |

### Table: `sightings`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `device_id` | Integer | FK devices.id, indexed | |
| `timestamp` | DateTime | not null, indexed | |
| `rssi` | Integer | not null | Signal strength (dBm) |
| `estimated_distance_m` | Float | nullable | Calculated metres |
| `raw_advertisement` | Text | nullable | JSON blob |

### Table: `alerts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `device_id` | Integer | FK devices.id, nullable | Null = any device |
| `rule_type` | String(64) | not null | See Alert Rule Types |
| `rule_value` | String(256) | nullable | Threshold / duration |
| `label` | String(256) | not null | Human-readable name |
| `is_active` | Boolean | default True | |
| `created_at` | DateTime | default utcnow | |

### Table: `alert_events`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `alert_id` | Integer | FK alerts.id, not null | |
| `device_id` | Integer | FK devices.id, not null | |
| `triggered_at` | DateTime | default utcnow, indexed | |
| `detail` | Text | nullable | JSON blob with context |

---

## Storage Query Functions

All functions in `backend/storage/queries.py`. All async. All use `select()` (not `session.query()`). All writes use `async with session.begin()`.

```python
# Devices
async def upsert_device(session, mac, name, device_class, manufacturer,
                         is_ble, is_classic, tx_power) -> tuple[Device, bool]
# Returns (device, is_new). Updates name/class/manufacturer/last_seen if device exists.

async def get_all_devices(session) -> list[Device]
# All devices ordered by last_seen desc

async def get_device_by_mac(session, mac: str) -> Device | None

async def get_active_devices(session, since_minutes: int) -> list[Device]
# Seen within last N minutes

async def update_device_label(session, mac: str, label: str, notes: str)

async def toggle_favorite(session, mac: str)

# Sightings
async def record_sighting(session, device_id: int, rssi: int,
                           distance_m: float | None, raw_adv: dict)

async def get_sightings_for_device(session, device_id: int, limit: int = 500) -> list[Sighting]

async def get_recent_sightings(session, minutes: int = 60) -> list[Sighting]
# All sightings across all devices for timeline view

# Alerts
async def get_active_alerts(session) -> list[Alert]

async def create_alert(session, rule_type: str, label: str,
                        device_id: int | None, rule_value: str | None) -> Alert

async def delete_alert(session, alert_id: int)

async def record_alert_event(session, alert_id: int, device_id: int, detail: dict)

async def get_recent_alert_events(session, limit: int = 50) -> list[AlertEvent]
```

---

## Device Classes

Valid values for `device_class` field:

| Value | Description |
|---|---|
| `phone` | Smartphone |
| `car` | Car Bluetooth head unit |
| `headphones` | Headphones, earbuds, AirPods |
| `laptop` | Laptop or desktop computer |
| `tablet` | Tablet device |
| `tag` | Tracking tag (AirTag, Tile, etc.) |
| `airtag` | Apple AirTag specifically |
| `speaker` | Bluetooth speaker |
| `wearable` | Smartwatch, fitness tracker |
| `unknown` | Unclassified device |

---

## Device Classification Rules

Applied in `backend/intelligence/classifier.py` in priority order (first match wins):

1. `company_id == 0x004C` AND service UUID `"FD6F"` present → `"airtag"`
2. Service UUID `"180D"` (Heart Rate) OR `"1816"` (Cycling Speed) present → `"wearable"`
3. Service UUID `"110A"` OR `"110B"` (A2DP audio) present → `"speaker"`
4. `company_id in {0x0075, 0x00E0}` (Garmin, Google) → `"wearable"`
5. Manufacturer name contains any of: `BMW`, `Mercedes`, `Toyota`, `Ford`, `Volkswagen`, `Audi`, `Honda`, `Hyundai`, `Kia`, `Tesla`, `Volvo`, `Porsche`, `Renault`, `Peugeot`, `Fiat` (case-insensitive) → `"car"`
6. Service UUID `"FE2C"` OR `"181A"` (Environmental Sensing) present → `"tag"`
7. `company_id == 0x004C` (Apple) → `"phone"`
8. Manufacturer name contains `"Samsung"` → `"phone"`
9. Service UUIDs `"180F"` AND `"1800"` both present → `"phone"`
10. Name contains any of: `MacBook`, `iPhone`, `iPad`, `Galaxy`, `Pixel`, `OnePlus`, `Xiaomi`, `Redmi` (case-insensitive) → `"phone"`
11. Name contains any of: `AirPods`, `WH-`, `WF-`, `Buds`, `Headphone`, `Earphone` (case-insensitive) → `"headphones"`
12. Name contains any of: `Laptop`, `ThinkPad`, `Surface`, `Dell`, `HP ` (case-insensitive) → `"laptop"`
13. Default → `"unknown"`

---

## Device Class Colors

Used consistently across RadarView, DeviceList, Timeline, and formatters:

| Class | Hex Color |
|---|---|
| `phone` | `#4fc3f7` |
| `car` | `#ffb74d` |
| `headphones` | `#ce93d8` |
| `laptop` | `#80cbc4` |
| `tablet` | `#80deea` |
| `tag` | `#fff176` |
| `airtag` | `#fff176` |
| `speaker` | `#a5d6a7` |
| `wearable` | `#f48fb1` |
| `unknown` | `#9e9e9e` |

---

## Distance Formula

```python
distance_metres = 10 ** ((tx_power - rssi) / (10 * n))
```

- `tx_power`: advertised power at 1 metre (dBm). Use `settings.TX_POWER_DEFAULT = -59` if not advertised.
- `rssi`: received signal strength (dBm).
- `n`: path loss exponent. Use `settings.RSSI_PATH_LOSS_EXPONENT = 2.5`.
- Clamp result to `[0.1, 500.0]` metres.
- Return `None` if `rssi < -100` or `rssi > 0`.

---

## Alert Rule Logic

Four rule types in `backend/intelligence/alerts.py`:

**`device_appeared`**
- Fires when `is_new == True` and `alert.device_id == device.id`.
- Fires only once per device per session.

**`new_unknown_device`**
- Fires when `is_new == True` and `device.device_class == "unknown"`.
- Fires for every new unknown device (no device_id filter needed).

**`device_lingered`**
- Fires when `presence_tracker.get_dwell_minutes(mac) >= float(alert.rule_value)`.
- Only fires for devices that are NOT favorited.
- Fires at most once per device per session (track fired MACs in memory).

**`rssi_threshold`**
- Fires when `sighting_rssi > int(alert.rule_value)` (device came very close).
- `alert.device_id` may be set (specific device) or None (any device).
- Rate-limited: fires at most once per device per 60 seconds.

---

## REST API Endpoints

All prefixed `/api/v1`. Implemented in `backend/api/routes.py`.

### `GET /devices`
Query params: `active_only: bool = True`, `class_filter: str | None`, `sort_by: str = "last_seen"`

Response:
```json
{
  "devices": [
    {
      "mac": "AA:BB:CC:DD:EE:FF",
      "name": "iPhone",
      "device_class": "phone",
      "manufacturer": "Apple Inc.",
      "is_ble": true,
      "is_classic": false,
      "first_seen": "2024-01-01T10:00:00Z",
      "last_seen": "2024-01-01T10:05:00Z",
      "last_rssi": -65,
      "last_distance_m": 3.2,
      "last_zone": "near",
      "is_favorited": false,
      "user_label": null
    }
  ],
  "total": 1,
  "active_count": 1
}
```

### `GET /devices/{mac}`
Returns full device + last 100 sightings array.

### `PATCH /devices/{mac}`
Body: `{ "user_label": str | null, "notes": str | null }`

### `POST /devices/{mac}/favorite`
Toggles `is_favorited`.

### `GET /sightings`
Query: `minutes: int = 60`. Returns all sightings in last N minutes.

### `GET /alerts/rules`
Returns all active alert rules.

### `POST /alerts/rules`
Body: `{ "rule_type": str, "label": str, "device_id": int | null, "rule_value": str | null }`

### `DELETE /alerts/rules/{alert_id}`

### `GET /alerts/events`
Returns last 50 alert events with embedded device info.

### `GET /stats`
Returns: `{ "ble_active": bool, "classic_active": bool, "ble_events": int, "classic_events": int, "errors": int, "uptime_seconds": int }`

---

## WebSocket Events

Backend → Frontend messages on `ws://127.0.0.1:8765/ws`. All JSON.

### `device_update`
```json
{
  "type": "device_update",
  "device": {
    "mac": "AA:BB:CC:DD:EE:FF",
    "name": "iPhone",
    "device_class": "phone",
    "manufacturer": "Apple Inc.",
    "is_ble": true,
    "is_classic": false,
    "first_seen": "2024-01-01T10:00:00Z",
    "last_seen": "2024-01-01T10:05:00Z",
    "is_favorited": false,
    "user_label": null
  },
  "sighting": {
    "rssi": -65,
    "distance_m": 3.2,
    "zone": "near"
  }
}
```

### `alert_event`
```json
{
  "type": "alert_event",
  "alert_id": 1,
  "alert_label": "New unknown device",
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "device_name": null,
  "triggered_at": "2024-01-01T10:05:00Z",
  "detail": {}
}
```

### `stats_update`
```json
{
  "type": "stats_update",
  "ble_active": true,
  "classic_active": true,
  "ble_events": 1240,
  "classic_events": 18,
  "errors": 0,
  "uptime_seconds": 120
}
```

---

## UI Layout

```
┌──────────────────────────────────────────────────────────┐  height: 36px
│  StatusBar                                                │
├───────────────────────────┬──────────────────────────────┤
│                           │                              │
│   RadarView               │   DeviceList                 │
│   width: 55%              │   width: 45%                 │
│   canvas 500×500          │   scrollable list            │
│                           │                              │
│                           │                              │
├───────────────────────────┴──────────────────────────────┤  height: 36px
│  [Timeline] [Alerts]  unread badge                  ▲▼   │  tab bar
├──────────────────────────────────────────────────────────┤  height: 220px
│  Timeline canvas  OR  Alerts panel                       │  collapsible
└──────────────────────────────────────────────────────────┘
```

- Middle section takes all remaining vertical space (`flex: 1`)
- DeviceDetail panel slides in from the right over the top of everything (`position: fixed`)
- Color scheme: dark background `#0a0f1a` (main), `#111827` (panels), `#1f2937` (cards)
- Font: system-ui or -apple-system stack

---

## Integration Test Events

Used in `backend/tests/test_pipeline.py` (Task 15).

```python
FAKE_EVENTS = [
    # 1. iPhone — Apple company ID, will become canonical MAC for dedup
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:01", "name": "iPhone", "rssi": -65,
     "tx_power": -59, "service_uuids": ["1800", "1801"],
     "manufacturer_data": {76: b"\x10\x05"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:00"},

    # 2. Samsung Galaxy
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:02", "name": "Galaxy S24", "rssi": -72,
     "tx_power": -59, "service_uuids": ["180F", "1800"],
     "manufacturer_data": {117: b"\x00\x01"}, "company_id": 0x0075,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:01"},

    # 3. BMW car via Classic BT
    {"source": "classic", "mac": "AA:BB:CC:DD:EE:03", "name": "BMW 5 Series",
     "rssi": None, "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": 0x200404, "bt_major_class": "phone",
     "timestamp": "2024-01-01T10:00:02"},

    # 4. iPhone with ROTATED MAC — same fingerprint as #1, should deduplicate
    {"source": "ble", "mac": "FF:EE:DD:CC:BB:01", "name": "iPhone", "rssi": -68,
     "tx_power": -59, "service_uuids": ["1800", "1801"],
     "manufacturer_data": {76: b"\x10\x05"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:01:00"},

    # 5. AirTag — FD6F service + Apple company ID
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:04", "name": None, "rssi": -55,
     "tx_power": -59, "service_uuids": ["FD6F"],
     "manufacturer_data": {76: b"\x12\x19"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:03"},

    # 6. AirPods Pro
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:05", "name": "AirPods Pro", "rssi": -50,
     "tx_power": -59, "service_uuids": [],
     "manufacturer_data": {76: b"\x0e\x20"}, "company_id": 0x004C,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:04"},

    # 7. Garmin watch — Heart Rate service UUID
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:06", "name": "Fenix 7", "rssi": -80,
     "tx_power": -59, "service_uuids": ["180D"],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:05"},

    # 8. Unknown device
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:07", "name": None, "rssi": -90,
     "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:06"},

    # 9. INVALID — bad MAC format, must be dropped by normalizer
    {"source": "ble", "mac": "INVALID", "name": "bad", "rssi": -50,
     "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:07"},

    # 10. WEAK SIGNAL — rssi below RSSI_MINIMUM, must be dropped
    {"source": "ble", "mac": "AA:BB:CC:DD:EE:08", "name": "weak", "rssi": -105,
     "tx_power": None, "service_uuids": [],
     "manufacturer_data": {}, "company_id": None,
     "bt_class_int": None, "bt_major_class": None,
     "timestamp": "2024-01-01T10:00:08"},
]
```

Expected results after processing all 10 events:
- **7 devices** in the DB (events 9 and 10 dropped; event 4 deduplicated to event 1's MAC)
- `AA:BB:CC:DD:EE:01` → `device_class = "phone"`, manufacturer contains `"Apple"`
- `AA:BB:CC:DD:EE:04` → `device_class = "airtag"`
- `AA:BB:CC:DD:EE:05` → `device_class = "headphones"`
- `AA:BB:CC:DD:EE:06` → `device_class = "wearable"`
- MAC `FF:EE:DD:CC:BB:01` resolves to canonical `AA:BB:CC:DD:EE:01` via deduplicator
- All valid BLE events (source = "ble", valid RSSI) have `distance_m` calculated
- Sightings table has 7 rows (one per unique resolved device)

---

## Electron Backend Spawn

In `frontend/electron/main.js`:

```javascript
const { app, BrowserWindow, dialog } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

const isDev = !app.isPackaged

const backendPath = isDev
  ? 'python'
  : path.join(process.resourcesPath, 'backend', 'aliradar-backend.exe')

const backendArgs = isDev
  ? [path.join(__dirname, '../../backend/main.py')]
  : []

const backendCwd = isDev
  ? path.join(__dirname, '../..')
  : process.resourcesPath

let backendProcess = null

function startBackend() {
  backendProcess = spawn(backendPath, backendArgs, { cwd: backendCwd })
  backendProcess.stdout.on('data', d => console.log('[backend]', d.toString().trim()))
  backendProcess.stderr.on('data', d => console.error('[backend]', d.toString().trim()))
  backendProcess.on('exit', code => console.log('[backend] exited with code', code))
}

function waitForBackend(maxAttempts = 30, interval = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0
    const check = () => {
      http.get('http://127.0.0.1:8765/api/v1/stats', res => {
        if (res.statusCode === 200) resolve()
        else retry()
      }).on('error', retry)
    }
    const retry = () => {
      attempts++
      if (attempts >= maxAttempts) reject(new Error('Backend failed to start'))
      else setTimeout(check, interval)
    }
    check()
  })
}
```

---

## Electron Builder Config

Add to `frontend/package.json` under `"build"` key:

```json
{
  "appId": "com.aliradar.app",
  "productName": "AliRadar",
  "directories": { "output": "../release" },
  "files": ["dist/**/*", "electron/**/*"],
  "extraResources": [
    { "from": "resources/backend", "to": "backend", "filter": ["**/*"] }
  ],
  "win": {
    "target": [{ "target": "nsis", "arch": ["x64"] }],
    "icon": "assets/icon.ico",
    "requestedExecutionLevel": "requireAdministrator"
  },
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true,
    "installerIcon": "assets/icon.ico",
    "installerHeaderIcon": "assets/icon.ico",
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true
  }
}
```

---

## Electron Auto-updater Stub

Add to `frontend/electron/main.js` (commented out, ready to enable):

```javascript
// Auto-updater (configure before releasing publicly)
// const { autoUpdater } = require('electron-updater')
// app.on('ready', () => {
//   autoUpdater.checkForUpdatesAndNotify()
// })
// autoUpdater.on('update-available', () => { ... })
// autoUpdater.on('update-downloaded', () => { autoUpdater.quitAndInstall() })
```

---

## PyInstaller Spec

File: `backend/aliradar-backend.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('../data/oui.csv', 'data'),
    ],
    hiddenimports=[
        'bleak',
        'bleak.backends.winrt',
        'bleak.backends.winrt.scanner',
        'bleak.backends.winrt.client',
        'pybluez2',
        'bluetooth',
        'aiosqlite',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.aiosqlite',
        'win32api',
        'win32con',
        'win32security',
        'pydantic_settings',
        'alembic',
        'alembic.runtime.migration',
        'alembic.operations',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='aliradar-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
```

---

## Key Technical Notes for Codex

**MAC Address Randomization:** Modern iOS and Android phones rotate their MAC address every ~15 minutes to prevent tracking. The `Deduplicator` mitigates this within a session by fingerprinting devices using their stable properties (service UUIDs + company_id + name). The first MAC observed for a fingerprint becomes the canonical MAC for that session. Cross-session linking is intentionally NOT done (privacy).

**Scanner Concurrency:** BLE and Classic BT share the same radio hardware. BLE scanning is continuous (passive). Classic BT inquiry blocks for ~8 seconds per cycle. Both run concurrently but Classic BT's blocking call runs in a thread executor so it doesn't block the asyncio event loop.

**DB Write Throttling:** The BLE scanner fires 50–200 events per second in busy environments. `ScannerManager` throttles DB sighting writes to once per 5 seconds per MAC address. Every event still updates the device's in-memory state and broadcasts to the frontend — only the DB write is throttled.

**Windows Admin Requirement:** Classic BT inquiry via `pybluez2` requires Administrator privileges on Windows. The app auto-relaunches with UAC elevation on startup. If admin is unavailable, only BLE scanning works.

**BLE Only Fallback:** If `pybluez2` fails to import (not installed or adapter unavailable), `CLASSIC_AVAILABLE = False` is set in `classic_scanner.py`. `ScannerManager.start()` catches this and logs a warning but continues with BLE-only mode. The app never crashes due to Classic BT unavailability.

**Frontend State Pattern:** No Redux or Zustand. Uses React's `useSyncExternalStore` with plain module-level store objects. Stores hold plain JS objects (not immutable). Mutations call `notify()` which triggers re-renders in subscribed components.

**RSSI Chart in DeviceDetail:** Drawn manually on a `<canvas>` element (no chart library). 60 data points, green line, Y-axis from -30 to -100 dBm (inverted — stronger signal at top), time on X-axis.

**Timeline Canvas:** Groups sightings into continuous bars with a 2-minute gap threshold. One row per device class (not per device). Colored by class. X-axis = last 60 minutes.

**Deduplicator Session Scope:** The deduplicator only links MACs within the same process session. On app restart, `Deduplicator.reset()` is called (it's a fresh instance) and all fingerprint mappings start fresh. This means a device that changed MAC overnight will appear as a new device after app restart — this is correct and expected behavior.
