import { useMemo, useState } from "react";

import { useDevices } from "../../hooks/useDevices";
import { getDeviceClassColor } from "../../utils/deviceUtils";
import "./DeviceList.css";

const CLASS_OPTIONS = [
  { label: "All", value: "" },
  { label: "Phone", value: "phone" },
  { label: "Car", value: "car" },
  { label: "Headphones", value: "headphones" },
  { label: "Laptop", value: "laptop" },
  { label: "Tag", value: "tag" },
  { label: "Wearable", value: "wearable" },
  { label: "Speaker", value: "speaker" },
  { label: "Unknown", value: "unknown" },
];

const SORT_OPTIONS = [
  { label: "Last seen", value: "last_seen" },
  { label: "Signal", value: "rssi" },
  { label: "Distance", value: "distance" },
  { label: "Name", value: "name" },
  { label: "First seen", value: "first_seen" },
];

function formatRelativeTime(timestamp) {
  if (!timestamp) {
    return "Unknown";
  }
  const diffSeconds = Math.max(0, Math.floor((Date.now() - Date.parse(timestamp)) / 1000));
  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  }
  return `${Math.floor(diffSeconds / 60)}m ago`;
}

function formatDistance(distance) {
  return typeof distance === "number" ? `${distance.toFixed(1)} m` : "--";
}

export default function DeviceList({ selectedMac, onDeviceSelect }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [sortBy, setSortBy] = useState("last_seen");
  const { devices } = useDevices({ activeOnly: false, classFilter, sortBy: "last_seen", searchQuery });

  const sortedDevices = useMemo(() => {
    const nextDevices = [...devices];
    nextDevices.sort((left, right) => {
      if (sortBy === "name") {
        return (left.user_label || left.name || left.mac).localeCompare(right.user_label || right.name || right.mac);
      }
      if (sortBy === "rssi") {
        return (right.last_rssi ?? -Infinity) - (left.last_rssi ?? -Infinity);
      }
      if (sortBy === "distance") {
        return (left.last_distance_m ?? Infinity) - (right.last_distance_m ?? Infinity);
      }
      if (sortBy === "first_seen") {
        return Date.parse(right.first_seen || 0) - Date.parse(left.first_seen || 0);
      }
      return Date.parse(right.last_seen || 0) - Date.parse(left.last_seen || 0);
    });
    return nextDevices;
  }, [devices, sortBy]);

  return (
    <div className="device-list-panel">
      <div className="device-list-panel__filters">
        <input
          className="device-list-panel__input"
          type="search"
          placeholder="Search devices"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
        <select value={classFilter} onChange={(event) => setClassFilter(event.target.value)}>
          {CLASS_OPTIONS.map((option) => (
            <option key={option.value || "all"} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="device-list-panel__rows">
        {sortedDevices.map((device) => {
          const isSelected = selectedMac === device.mac;
          return (
            <button
              key={device.mac}
              className={isSelected ? "device-row device-row--selected" : "device-row"}
              type="button"
              onClick={() => onDeviceSelect?.(device.mac)}
            >
              <div className="device-row__topline">
                <div className="device-row__title">
                  <span
                    className="device-row__class-dot"
                    style={{ backgroundColor: getDeviceClassColor(device.device_class) }}
                  />
                  <strong>{device.user_label || device.name || device.mac}</strong>
                </div>
                <span className="device-row__zone-badge">{device.last_zone || "unknown"}</span>
              </div>
              <div className="device-row__metrics">
                <span>{formatDistance(device.last_distance_m)}</span>
                <span>{device.last_rssi ?? "--"} dBm</span>
              </div>
              <div className="device-row__bottomline">
                <span>{device.manufacturer || "Unknown manufacturer"}</span>
                <span>{formatRelativeTime(device.last_seen)}</span>
                <span className="device-row__star">{device.is_favorited ? "★" : "☆"}</span>
              </div>
            </button>
          );
        })}
        {!sortedDevices.length ? <div className="device-row device-row--empty">No devices found.</div> : null}
      </div>
    </div>
  );
}
