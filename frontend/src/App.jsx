import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { useAlerts } from "./hooks/useAlerts";
import { useDevices } from "./hooks/useDevices";
import { useWebSocket } from "./hooks/useWebSocket";
import * as alertStore from "./store/alertStore";
import * as deviceStore from "./store/deviceStore";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8765/api/v1";
const MAX_DEVICE_AGE_MINUTES = 10;

export default function App() {
  const [activeTab, setActiveTab] = useState("timeline");
  const [isBottomPanelOpen, setIsBottomPanelOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const { isConnected, connectionAttempts, lastError, abandonedConnection } = useWebSocket();
  const { devices, totalCount, activeCount } = useDevices({
    activeOnly: false,
    classFilter: null,
    sortBy: "last_seen",
    searchQuery: "",
  });
  const { events, unreadCount } = useAlerts();
  const deviceSnapshot = useSyncExternalStore(deviceStore.subscribe, deviceStore.getSnapshot, deviceStore.getSnapshot);

  useEffect(() => {
    let isCancelled = false;

    async function loadInitialData() {
      try {
        setIsLoading(true);
        const [devicesResponse, alertEventsResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/devices?active_only=false`),
          fetch(`${API_BASE_URL}/alerts/events`),
        ]);

        if (!devicesResponse.ok || !alertEventsResponse.ok) {
          throw new Error("Failed to load initial application data");
        }

        const devicesPayload = await devicesResponse.json();
        const alertEventsPayload = await alertEventsResponse.json();

        if (isCancelled) {
          return;
        }

        deviceStore.setDevicesFromFetch(devicesPayload.devices || []);
        alertStore.setEvents(alertEventsPayload.events || []);
        setLoadError(null);
      } catch (error) {
        if (!isCancelled) {
          setLoadError(error instanceof Error ? error.message : String(error));
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadInitialData();

    const intervalId = window.setInterval(() => {
      deviceStore.removeStaleDevices(MAX_DEVICE_AGE_MINUTES);
    }, 30000);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const statusText = useMemo(() => {
    if (abandonedConnection) {
      return "Connection abandoned";
    }
    if (isConnected) {
      return "Connected";
    }
    return "Connecting";
  }, [abandonedConnection, isConnected]);

  return (
    <div className="app-shell">
      <header className="status-bar">
        <div>
          <strong>AliRadar</strong>
          <span className="status-pill">{statusText}</span>
        </div>
        <div className="status-bar__metrics">
          <span>Devices: {totalCount}</span>
          <span>Active: {activeCount}</span>
          <span>BLE: {deviceSnapshot.scannerStats.ble_events ?? 0}</span>
          <span>Classic: {deviceSnapshot.scannerStats.classic_events ?? 0}</span>
          <span>Errors: {deviceSnapshot.scannerStats.errors ?? 0}</span>
        </div>
      </header>

      <main className="app-main">
        <section className="app-panel app-panel--radar">
          <div className="panel-heading">
            <h2>RadarView</h2>
            <span>{deviceSnapshot.isConnected ? "Live" : "Offline"}</span>
          </div>
          <div className="panel-placeholder">Radar canvas placeholder</div>
        </section>

        <section className="app-panel app-panel--devices">
          <div className="panel-heading">
            <h2>DeviceList</h2>
            <span>{devices.length} shown</span>
          </div>
          <div className="device-list">
            {devices.map((device) => (
              <article key={device.mac} className="device-card">
                <div>
                  <strong>{device.user_label || device.name || device.mac}</strong>
                  <p>{device.manufacturer || "Unknown manufacturer"}</p>
                </div>
                <div className="device-card__meta">
                  <span>{device.device_class || "unknown"}</span>
                  <span>{device.last_zone || "unknown"}</span>
                </div>
              </article>
            ))}
            {!devices.length && <div className="empty-state">No devices available yet.</div>}
          </div>
        </section>
      </main>

      <section className="bottom-panel-tabs">
        <div className="tab-buttons">
          <button
            className={activeTab === "timeline" ? "tab-button tab-button--active" : "tab-button"}
            onClick={() => setActiveTab("timeline")}
            type="button"
          >
            Timeline
          </button>
          <button
            className={activeTab === "alerts" ? "tab-button tab-button--active" : "tab-button"}
            onClick={() => setActiveTab("alerts")}
            type="button"
          >
            Alerts {unreadCount > 0 ? <span className="badge">{unreadCount}</span> : null}
          </button>
        </div>
        <button
          className="collapse-button"
          onClick={() => setIsBottomPanelOpen((currentValue) => !currentValue)}
          type="button"
        >
          {isBottomPanelOpen ? "▼" : "▲"}
        </button>
      </section>

      {isBottomPanelOpen ? (
        <section className="bottom-panel-content">
          {activeTab === "timeline" ? (
            <div className="panel-placeholder panel-placeholder--bottom">Timeline panel placeholder</div>
          ) : (
            <div className="alerts-panel">
              {events.map((event) => (
                <article key={`${event.id ?? "event"}-${event.triggered_at ?? Math.random()}`} className="alert-card">
                  <strong>{event.alert_label || event.label || "Alert"}</strong>
                  <p>{event.device_mac || event.mac || "Unknown device"}</p>
                </article>
              ))}
              {!events.length && <div className="empty-state">No alerts recorded yet.</div>}
            </div>
          )}
        </section>
      ) : null}

      <footer className="app-footer">
        {isLoading ? <span>Loading initial data…</span> : null}
        {loadError ? <span className="error-text">{loadError}</span> : null}
        {lastError ? <span className="error-text">{lastError}</span> : null}
        {!loadError && !lastError && !isLoading ? <span>Ready.</span> : null}
        <span>Reconnect attempts: {connectionAttempts}</span>
      </footer>
    </div>
  );
}
