import { useMemo, useSyncExternalStore } from "react";

import { getSnapshot, subscribe } from "../store/deviceStore";

export function useDevices(filter = {}) {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const { devices, totalCount, activeCount } = useMemo(() => {
    const allDevices = Object.values(snapshot.devices);
    const normalizedQuery = (filter.searchQuery || "").trim().toLowerCase();
    const now = Date.now();
    const activeDevices = allDevices.filter((device) => {
      if (!device.last_seen) {
        return false;
      }
      const ageMs = now - Date.parse(device.last_seen);
      return Number.isFinite(ageMs) && ageMs <= 10 * 60 * 1000;
    });

    let filtered = [...allDevices];

    if (filter.activeOnly) {
      filtered = filtered.filter((device) => activeDevices.includes(device));
    }

    if (filter.classFilter) {
      filtered = filtered.filter((device) => device.device_class === filter.classFilter);
    }

    if (normalizedQuery) {
      filtered = filtered.filter((device) => {
        const haystack = [
          device.mac,
          device.name,
          device.user_label,
          device.manufacturer,
          device.device_class,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedQuery);
      });
    }

    const sortBy = filter.sortBy || "last_seen";
    filtered.sort((a, b) => {
      if (sortBy === "name") {
        return (a.name || a.user_label || a.mac).localeCompare(b.name || b.user_label || b.mac);
      }
      if (sortBy === "rssi") {
        return (b.last_rssi ?? -Infinity) - (a.last_rssi ?? -Infinity);
      }
      return Date.parse(b.last_seen || 0) - Date.parse(a.last_seen || 0);
    });

    return {
      devices: filtered,
      totalCount: allDevices.length,
      activeCount: activeDevices.length,
    };
  }, [filter.activeOnly, filter.classFilter, filter.searchQuery, filter.sortBy, snapshot.devices]);

  return { devices, totalCount, activeCount };
}
