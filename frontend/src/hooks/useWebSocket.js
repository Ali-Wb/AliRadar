import { useEffect, useRef, useState } from "react";

import * as alertStore from "../store/alertStore";
import * as deviceStore from "../store/deviceStore";

const WS_URL = "ws://127.0.0.1:8765/ws";
const MAX_DELAY_MS = 30000;
const MAX_FAILED_ATTEMPTS = 10;

export function useWebSocket() {
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const attemptsRef = useRef(0);

  const [isConnected, setIsConnected] = useState(deviceStore.getSnapshot().isConnected);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [lastError, setLastError] = useState(null);
  const [abandonedConnection, setAbandonedConnection] = useState(false);

  useEffect(() => {
    function cleanupSocket() {
      if (socketRef.current) {
        socketRef.current.onopen = null;
        socketRef.current.onclose = null;
        socketRef.current.onerror = null;
        socketRef.current.onmessage = null;
        socketRef.current.close();
        socketRef.current = null;
      }
    }

    function scheduleReconnect() {
      if (!shouldReconnectRef.current || abandonedConnection) {
        return;
      }

      attemptsRef.current += 1;
      setConnectionAttempts(attemptsRef.current);

      if (attemptsRef.current >= MAX_FAILED_ATTEMPTS) {
        setAbandonedConnection(true);
        return;
      }

      const delay = Math.min(1000 * (2 ** Math.max(attemptsRef.current - 1, 0)), MAX_DELAY_MS);
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    }

    function handleMessage(event) {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "device_update") {
          deviceStore.upsertDevice(message.device, message.sighting);
        } else if (message.type === "alert_event") {
          alertStore.addEvent(message);
        } else if (message.type === "stats_update") {
          deviceStore.setScannerStats(message);
        }
      } catch (error) {
        setLastError(error instanceof Error ? error.message : String(error));
      }
    }

    function connect() {
      if (!shouldReconnectRef.current || abandonedConnection) {
        return;
      }

      cleanupSocket();

      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        attemptsRef.current = 0;
        setConnectionAttempts(0);
        setAbandonedConnection(false);
        setLastError(null);
        setIsConnected(true);
        deviceStore.setConnected(true);
      };

      socket.onmessage = handleMessage;

      socket.onerror = () => {
        setLastError("WebSocket connection error");
      };

      socket.onclose = () => {
        setIsConnected(false);
        deviceStore.setConnected(false);
        if (shouldReconnectRef.current) {
          scheduleReconnect();
        }
      };
    }

    connect();

    return () => {
      shouldReconnectRef.current = false;
      window.clearTimeout(reconnectTimerRef.current);
      setIsConnected(false);
      deviceStore.setConnected(false);
      cleanupSocket();
    };
  }, [abandonedConnection]);

  return { isConnected, connectionAttempts, lastError, abandonedConnection };
}
