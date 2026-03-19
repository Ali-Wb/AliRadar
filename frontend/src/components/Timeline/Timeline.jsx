import { useEffect, useMemo, useRef, useState } from "react";

import { getDeviceClassColor } from "../../utils/deviceUtils";
import "./Timeline.css";

const API_BASE_URL = "http://127.0.0.1:8765/api/v1";
const TIMELINE_WIDTH = 900;
const TIMELINE_HEIGHT = 180;
const ROW_HEIGHT = 24;
const LEFT_GUTTER = 90;
const TOP_GUTTER = 18;
const GAP_THRESHOLD_MS = 2 * 60 * 1000;

function parseRawAdvertisement(rawAdvertisement) {
  if (!rawAdvertisement) {
    return {};
  }
  if (typeof rawAdvertisement === "object") {
    return rawAdvertisement;
  }
  try {
    return JSON.parse(rawAdvertisement);
  } catch {
    return {};
  }
}

function formatDuration(durationMs) {
  const totalMinutes = Math.max(1, Math.round(durationMs / 60000));
  return `${totalMinutes} min`;
}

function formatRange(start, end) {
  const startText = new Date(start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const endText = new Date(end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${startText} – ${endText}`;
}

export default function Timeline() {
  const canvasRef = useRef(null);
  const segmentsRef = useRef([]);
  const [sightings, setSightings] = useState([]);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadSightings() {
      const response = await fetch(`${API_BASE_URL}/sightings?minutes=60`);
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      if (!isCancelled) {
        setSightings(payload.sightings || []);
      }
    }

    loadSightings();
    const intervalId = window.setInterval(loadSightings, 60000);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const rows = useMemo(() => {
    const classRows = new Map();
    for (const sighting of sightings) {
      const raw = parseRawAdvertisement(sighting.raw_advertisement);
      const deviceClass = raw.device_class || "unknown";
      const row = classRows.get(deviceClass) || [];
      row.push({ ...sighting, raw });
      classRows.set(deviceClass, row);
    }

    return Array.from(classRows.entries()).map(([deviceClass, values]) => ({
      deviceClass,
      values: values.sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp)),
    }));
  }, [sightings]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    context.clearRect(0, 0, TIMELINE_WIDTH, TIMELINE_HEIGHT);
    context.fillStyle = "#0f172a";
    context.fillRect(0, 0, TIMELINE_WIDTH, TIMELINE_HEIGHT);
    context.font = "12px system-ui";
    context.textBaseline = "middle";

    const now = Date.now();
    const startWindow = now - 60 * 60 * 1000;
    const drawableWidth = TIMELINE_WIDTH - LEFT_GUTTER - 16;
    const nextSegments = [];

    rows.forEach((row, rowIndex) => {
      const y = TOP_GUTTER + rowIndex * ROW_HEIGHT;
      context.fillStyle = "#9ca3af";
      context.fillText(row.deviceClass, 8, y + 10);

      let currentSegment = null;

      row.values.forEach((entry) => {
        const timestamp = Date.parse(entry.timestamp);
        if (!Number.isFinite(timestamp)) {
          return;
        }

        if (!currentSegment || timestamp - currentSegment.end > GAP_THRESHOLD_MS) {
          if (currentSegment) {
            nextSegments.push(currentSegment);
          }
          currentSegment = {
            deviceClass: row.deviceClass,
            deviceName: entry.raw.name || entry.raw.user_label || entry.raw.mac || "Unknown device",
            start: timestamp,
            end: timestamp,
            raw: entry.raw,
            y,
          };
        } else {
          currentSegment.end = timestamp;
        }
      });

      if (currentSegment) {
        nextSegments.push(currentSegment);
      }
    });

    nextSegments.forEach((segment) => {
      const x1 = LEFT_GUTTER + ((segment.start - startWindow) / (60 * 60 * 1000)) * drawableWidth;
      const x2 = LEFT_GUTTER + ((segment.end - startWindow) / (60 * 60 * 1000)) * drawableWidth;
      const width = Math.max(4, x2 - x1);
      const y = segment.y;

      context.fillStyle = getDeviceClassColor(segment.deviceClass);
      context.fillRect(x1, y, width, 14);
      segment.bounds = { x: x1, y, width, height: 14 };
    });

    for (let minute = 0; minute <= 60; minute += 10) {
      const x = LEFT_GUTTER + (minute / 60) * drawableWidth;
      context.strokeStyle = "rgba(255,255,255,0.08)";
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, TIMELINE_HEIGHT);
      context.stroke();

      context.fillStyle = "#9ca3af";
      context.fillText(`${60 - minute}m`, x - 10, TIMELINE_HEIGHT - 12);
    }

    segmentsRef.current = nextSegments;
  }, [rows]);

  function handleMouseMove(event) {
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = TIMELINE_WIDTH / rect.width;
    const scaleY = TIMELINE_HEIGHT / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;

    const hit = segmentsRef.current.find((segment) => {
      if (!segment.bounds) {
        return false;
      }
      return (
        x >= segment.bounds.x &&
        x <= segment.bounds.x + segment.bounds.width &&
        y >= segment.bounds.y &&
        y <= segment.bounds.y + segment.bounds.height
      );
    });

    if (!hit) {
      setTooltip(null);
      return;
    }

    setTooltip({
      left: event.clientX + 12,
      top: event.clientY + 12,
      content: {
        name: hit.deviceName,
        range: formatRange(hit.start, hit.end),
        duration: formatDuration(hit.end - hit.start || 60000),
      },
    });
  }

  return (
    <div className="timeline-view">
      <canvas
        ref={canvasRef}
        className="timeline-view__canvas"
        width={TIMELINE_WIDTH}
        height={TIMELINE_HEIGHT}
        onMouseLeave={() => setTooltip(null)}
        onMouseMove={handleMouseMove}
      />
      {tooltip ? (
        <div className="timeline-view__tooltip" style={{ left: tooltip.left, top: tooltip.top }}>
          <strong>{tooltip.content.name}</strong>
          <span>{tooltip.content.range}</span>
          <span>{tooltip.content.duration}</span>
        </div>
      ) : null}
    </div>
  );
}
