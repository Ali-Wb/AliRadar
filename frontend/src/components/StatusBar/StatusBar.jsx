import { formatDuration } from "../../utils/formatters";
import "./StatusBar.css";

function StatusPill({ active, label }) {
  return (
    <div className="status-bar__pill">
      <span className={active ? "status-bar__dot status-bar__dot--active" : "status-bar__dot"} />
      <span>{label}</span>
    </div>
  );
}

export default function StatusBar({
  scannerStats = {},
  activeDeviceCount = 0,
  isConnected = false,
  abandonedConnection = false,
}) {
  const totalEvents = (scannerStats.ble_events ?? 0) + (scannerStats.classic_events ?? 0);
  const uptimeSeconds = scannerStats.uptime_seconds ?? 0;
  const eventRate = uptimeSeconds > 0 ? (totalEvents / uptimeSeconds).toFixed(1) : "0.0";

  return (
    <div className="status-bar-shell">
      {abandonedConnection ? (
        <div className="status-bar__banner">
          Cannot connect to scanner backend. Is AliRadar running as Administrator?
        </div>
      ) : null}
      <div className="status-bar-component">
        <div className="status-bar__wordmark">AliRadar</div>
        <div className="status-bar__middle">
          <StatusPill active={Boolean(scannerStats.ble_active)} label="BLE" />
          <StatusPill active={Boolean(scannerStats.classic_active)} label="Classic BT" />
        </div>
        <div className="status-bar__right">
          <span>{activeDeviceCount} active</span>
          <span>{eventRate}/s</span>
          <span>{formatDuration(uptimeSeconds)}</span>
          <span className={isConnected ? "status-bar__ws status-bar__ws--live" : "status-bar__ws status-bar__ws--offline"}>
            <span className="status-bar__ws-dot" />
            WS
          </span>
        </div>
      </div>
    </div>
  );
}
