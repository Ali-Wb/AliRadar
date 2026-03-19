import { useEffect, useMemo, useSyncExternalStore } from "react";

import { getSnapshot, subscribe } from "../store/alertStore";

let unreadCountState = 0;
let lastSeenEventKey = null;
let alertsPanelOpen = false;

export function setAlertsPanelOpen(isOpen) {
  alertsPanelOpen = Boolean(isOpen);
  if (alertsPanelOpen) {
    unreadCountState = 0;
    lastSeenEventKey = null;
  }
}

export function useAlerts() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  useEffect(() => {
    const firstEvent = snapshot.events[0];
    const currentKey = firstEvent
      ? `${firstEvent.id ?? ""}:${firstEvent.triggered_at ?? ""}`
      : null;

    if (!currentKey) {
      unreadCountState = 0;
      lastSeenEventKey = null;
      return;
    }

    if (alertsPanelOpen) {
      unreadCountState = 0;
      lastSeenEventKey = currentKey;
      return;
    }

    if (lastSeenEventKey !== currentKey) {
      unreadCountState = Math.min(snapshot.events.length, unreadCountState + 1);
      lastSeenEventKey = currentKey;
    }
  }, [snapshot.events]);

  return useMemo(
    () => ({
      rules: snapshot.rules,
      events: snapshot.events,
      unreadCount: unreadCountState,
    }),
    [snapshot.events, snapshot.rules],
  );
}
