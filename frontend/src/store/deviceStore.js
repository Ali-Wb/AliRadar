const listeners = new Set();

const state = {
  devices: {},
  sightings: [],
  isConnected: false,
  scannerStats: {},
};

function notify() {
  listeners.forEach((listener) => listener());
}

function cloneState() {
  return {
    devices: { ...state.devices },
    sightings: [...state.sightings],
    isConnected: state.isConnected,
    scannerStats: { ...state.scannerStats },
  };
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot() {
  return cloneState();
}

export function setConnected(isConnected) {
  state.isConnected = Boolean(isConnected);
  notify();
}

export function setScannerStats(scannerStats) {
  state.scannerStats = { ...(scannerStats || {}) };
  notify();
}

export function upsertDevice(device, sighting) {
  if (!device?.mac) {
    return;
  }

  const existing = state.devices[device.mac] || {};
  state.devices[device.mac] = {
    ...existing,
    ...device,
    last_rssi: sighting?.rssi ?? existing.last_rssi ?? null,
    last_distance_m: sighting?.distance_m ?? existing.last_distance_m ?? null,
    last_zone: sighting?.zone ?? existing.last_zone ?? null,
    last_seen: device.last_seen ?? existing.last_seen ?? null,
  };

  if (sighting) {
    state.sightings = [
      {
        mac: device.mac,
        timestamp: device.last_seen ?? new Date().toISOString(),
        ...sighting,
      },
      ...state.sightings,
    ].slice(0, 500);
  }

  notify();
}

export function setDevicesFromFetch(list) {
  const nextDevices = {};
  for (const device of list || []) {
    if (device?.mac) {
      nextDevices[device.mac] = { ...device };
    }
  }
  state.devices = nextDevices;
  notify();
}

export function updateDeviceLabel(mac, label, notes) {
  if (!state.devices[mac]) {
    return;
  }

  state.devices[mac] = {
    ...state.devices[mac],
    user_label: label,
    notes,
  };
  notify();
}

export function toggleFavorite(mac) {
  if (!state.devices[mac]) {
    return;
  }

  state.devices[mac] = {
    ...state.devices[mac],
    is_favorited: !state.devices[mac].is_favorited,
  };
  notify();
}

export function removeStaleDevices(maxAgeMinutes) {
  const cutoff = Date.now() - maxAgeMinutes * 60 * 1000;
  let changed = false;
  const nextDevices = {};

  for (const [mac, device] of Object.entries(state.devices)) {
    const lastSeen = device.last_seen ? Date.parse(device.last_seen) : NaN;
    if (!Number.isNaN(lastSeen) && lastSeen >= cutoff) {
      nextDevices[mac] = device;
    } else if (Number.isNaN(lastSeen)) {
      nextDevices[mac] = device;
    } else {
      changed = true;
    }
  }

  if (changed) {
    state.devices = nextDevices;
    notify();
  }
}
