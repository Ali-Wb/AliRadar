export const DEVICE_CLASS_COLORS = {
  phone: "#4fc3f7",
  car: "#ffb74d",
  headphones: "#ce93d8",
  laptop: "#80cbc4",
  tablet: "#80deea",
  tag: "#fff176",
  airtag: "#fff176",
  speaker: "#a5d6a7",
  wearable: "#f48fb1",
  unknown: "#9e9e9e",
};

export function sortDevices(devices, sortBy = "last_seen") {
  const sorted = [...(devices || [])];
  sorted.sort((left, right) => {
    if (sortBy === "name") {
      return String(left.user_label || left.name || left.mac || "").localeCompare(
        String(right.user_label || right.name || right.mac || ""),
      );
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
  return sorted;
}

export function filterDevices(devices, filter = {}) {
  const now = Date.now();
  const normalizedQuery = String(filter.searchQuery || "").trim().toLowerCase();

  return (devices || []).filter((device) => {
    if (filter.activeOnly) {
      const lastSeenMs = Date.parse(device.last_seen || 0);
      if (!Number.isFinite(lastSeenMs) || now - lastSeenMs > 10 * 60 * 1000) {
        return false;
      }
    }

    if (filter.classFilter && device.device_class !== filter.classFilter) {
      return false;
    }

    if (!normalizedQuery) {
      return true;
    }

    const haystack = [device.mac, device.name, device.user_label, device.manufacturer, device.device_class]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalizedQuery);
  });
}

export function macToAngle(mac) {
  const normalized = String(mac || "").replace(/[^0-9A-F]/gi, "").toUpperCase();
  if (!normalized) {
    return 0;
  }

  let hash = 0;
  for (let index = 0; index < normalized.length; index += 1) {
    hash = (hash + normalized.charCodeAt(index) * 31) % 360;
  }

  return (hash / 360) * Math.PI * 2;
}

export function getDeviceClassColor(deviceClass) {
  return DEVICE_CLASS_COLORS[deviceClass] || DEVICE_CLASS_COLORS.unknown;
}
