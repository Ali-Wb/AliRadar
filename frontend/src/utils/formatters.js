import { DEVICE_CLASS_COLORS } from "./deviceUtils";

export function formatTimeAgo(isoDate) {
  if (!isoDate) {
    return "—";
  }
  const diffSeconds = Math.max(0, Math.floor((Date.now() - Date.parse(isoDate)) / 1000));
  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  }
  if (diffSeconds < 3600) {
    return `${Math.floor(diffSeconds / 60)}m ago`;
  }
  return `${Math.floor(diffSeconds / 3600)}h ago`;
}

export function formatRSSI(rssi) {
  return typeof rssi === "number" ? `${rssi} dBm` : "—";
}

export function formatDistance(metres) {
  if (typeof metres !== "number") {
    return "—";
  }
  if (metres < 10) {
    return `${metres.toFixed(1)}m`;
  }
  return `~${Math.round(metres)}m`;
}

export function formatDuration(seconds) {
  const totalSeconds = Math.max(0, Math.floor(seconds || 0));
  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }
  if (totalSeconds < 3600) {
    return `${Math.floor(totalSeconds / 60)}m ${totalSeconds % 60}s`;
  }
  return `${Math.floor(totalSeconds / 3600)}h ${Math.floor((totalSeconds % 3600) / 60)}m`;
}

export function formatDateTime(isoDate) {
  if (!isoDate) {
    return "—";
  }
  return new Date(isoDate).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function macToDisplayName(device) {
  return device?.user_label || device?.name || device?.mac || "Unknown device";
}

export function classToColor(deviceClass) {
  return DEVICE_CLASS_COLORS[deviceClass] || DEVICE_CLASS_COLORS.unknown;
}

export function classToEmoji(deviceClass) {
  return {
    phone: "📱",
    car: "🚗",
    headphones: "🎧",
    laptop: "💻",
    tag: "🏷️",
    airtag: "🏷️",
    wearable: "⌚",
    speaker: "🔊",
    unknown: "❓",
  }[deviceClass] || "❓";
}
