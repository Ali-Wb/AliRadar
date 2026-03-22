import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import * as deviceStore from "../../store/deviceStore";
import { getDeviceClassColor } from "../../utils/deviceUtils";
import "./DeviceDetail.css";

const API_BASE_URL = "http://127.0.0.1:8765/api/v1";

function formatTimestamp(value) {
  if (!value) {
    return "Unknown";
  }
  return new Date(value).toLocaleString();
}

function formatDistance(distance) {
  return typeof distance === "number" ? `${distance.toFixed(1)} m` : "Unknown";
}

export default function DeviceDetail({ mac, onClose }) {
  const chartRef = useRef(null);
  const snapshot = useSyncExternalStore(deviceStore.subscribe, deviceStore.getSnapshot, deviceStore.getSnapshot);
  const liveDevice = mac ? snapshot.devices[mac] : null;
  const [detailDevice, setDetailDevice] = useState(null);
  const [detailSightings, setDetailSightings] = useState([]);
  const [draftName, setDraftName] = useState("");
  const [draftNotes, setDraftNotes] = useState("");

  useEffect(() => {
    if (!mac) {
      setDetailDevice(null);
      setDetailSightings([]);
      setDraftName("");
      setDraftNotes("");
      return;
    }

    let isCancelled = false;

    async function loadDevice() {
      const response = await fetch(`${API_BASE_URL}/devices/${encodeURIComponent(mac)}`);
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      if (!isCancelled) {
        setDetailDevice(payload.device || null);
        setDetailSightings(payload.sightings || []);
        setDraftName(payload.device?.user_label || payload.device?.name || "");
        setDraftNotes(payload.device?.notes || "");
      }
    }

    loadDevice();
    return () => {
      isCancelled = true;
    };
  }, [mac]);

  const device = liveDevice || detailDevice;

  const chartSightings = useMemo(() => {
    const liveSightings = snapshot.sightings.filter((sighting) => sighting.mac === mac);
    return [...liveSightings, ...detailSightings]
      .slice(0, 60)
      .reverse();
  }, [detailSightings, mac, snapshot.sightings]);

  useEffect(() => {
    const canvas = chartRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#0f172a";
    context.fillRect(0, 0, canvas.width, canvas.height);

    context.strokeStyle = "rgba(255,255,255,0.08)";
    context.lineWidth = 1;
    [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
      const y = ratio * canvas.height;
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(canvas.width, y);
      context.stroke();
    });

    if (!chartSightings.length) {
      return;
    }

    context.beginPath();
    chartSightings.forEach((sighting, index) => {
      const rssi = typeof sighting.rssi === "number" ? sighting.rssi : -100;
      const x = (index / Math.max(chartSightings.length - 1, 1)) * canvas.width;
      const normalized = (Math.min(Math.max(rssi, -100), -30) + 100) / 70;
      const y = canvas.height - normalized * canvas.height;
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });
    context.strokeStyle = "#22c55e";
    context.lineWidth = 2;
    context.stroke();
  }, [chartSightings]);

  async function saveDetails() {
    if (!mac) {
      return;
    }

    const response = await fetch(`${API_BASE_URL}/devices/${encodeURIComponent(mac)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_label: draftName, notes: draftNotes }),
    });

    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    deviceStore.updateDeviceLabel(mac, payload.device?.user_label ?? draftName, payload.device?.notes ?? draftNotes);
    setDetailDevice(payload.device || detailDevice);
  }

  async function handleToggleFavorite() {
    if (!mac) {
      return;
    }
    const response = await fetch(`${API_BASE_URL}/devices/${encodeURIComponent(mac)}/favorite`, { method: "POST" });
    if (response.ok) {
      deviceStore.toggleFavorite(mac);
    }
  }

  async function handleCreateAlert() {
    if (!device) {
      return;
    }
    await fetch(`${API_BASE_URL}/alerts/rules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rule_type: "device_appeared",
        label: `Watch ${device.user_label || device.name || device.mac}`,
        device_id: device.id ?? null,
        rule_value: null,
      }),
    });
  }

  async function handleCopyMac() {
    if (mac) {
      await navigator.clipboard.writeText(mac);
    }
  }

  const dwellMinutes = useMemo(() => {
    if (!device?.first_seen || !device?.last_seen) {
      return "Unknown";
    }
    const diffMs = Date.parse(device.last_seen) - Date.parse(device.first_seen);
    if (!Number.isFinite(diffMs)) {
      return "Unknown";
    }
    return `${Math.max(0, Math.round(diffMs / 60000))} min`;
  }, [device]);

  return (
    <aside className={mac ? "device-detail device-detail--open" : "device-detail"}>
      <div className="device-detail__header">
        <div>
          <input
            className="device-detail__name-input"
            value={draftName}
            onBlur={saveDetails}
            onChange={(event) => setDraftName(event.target.value)}
            placeholder="Device name"
          />
          <span
            className="device-detail__class-badge"
            style={{ backgroundColor: getDeviceClassColor(device?.device_class) }}
          >
            {device?.device_class || "unknown"}
          </span>
        </div>
        <button type="button" onClick={onClose}>Close</button>
      </div>

      <section className="device-detail__section">
        <h3>Identity</h3>
        <p>MAC: {device?.mac || mac || "Unknown"}</p>
        <p>Manufacturer: {device?.manufacturer || "Unknown"}</p>
        <p>Class: {device?.device_class || "unknown"}</p>
        <div className="device-detail__badges">
          <span>{device?.is_ble ? "BLE" : "No BLE"}</span>
          <span>{device?.is_classic ? "Classic" : "No Classic"}</span>
        </div>
      </section>

      <section className="device-detail__section">
        <h3>Signal</h3>
        <p>RSSI: {device?.last_rssi ?? "Unknown"}</p>
        <p>Distance: {formatDistance(device?.last_distance_m)}</p>
      </section>

      <section className="device-detail__section">
        <h3>RSSI chart</h3>
        <canvas ref={chartRef} className="device-detail__chart" width="340" height="140" />
      </section>

      <section className="device-detail__section">
        <h3>Presence</h3>
        <p>First seen: {formatTimestamp(device?.first_seen)}</p>
        <p>Last seen: {formatTimestamp(device?.last_seen)}</p>
        <p>Session dwell: {dwellMinutes}</p>
      </section>

      <section className="device-detail__section">
        <h3>Notes</h3>
        <textarea
          className="device-detail__notes"
          value={draftNotes}
          onBlur={saveDetails}
          onChange={(event) => setDraftNotes(event.target.value)}
          placeholder="Add notes"
        />
      </section>

      <section className="device-detail__section">
        <h3>Actions</h3>
        <div className="device-detail__actions">
          <button type="button" onClick={handleToggleFavorite}>Toggle Favorite</button>
          <button type="button" onClick={handleCreateAlert}>Create Alert</button>
          <button type="button" onClick={handleCopyMac}>Copy MAC</button>
        </div>
      </section>
    </aside>
  );
}
