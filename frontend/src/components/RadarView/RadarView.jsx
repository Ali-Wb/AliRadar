import { useEffect, useMemo, useRef, useState } from "react";

import { getDeviceClassColor, macToAngle } from "../../utils/deviceUtils";
import "./RadarView.css";

const CANVAS_SIZE = 500;
const CENTER = CANVAS_SIZE / 2;
const RING_DEFINITIONS = [
  { label: "immediate", radius: 55, start: 0, end: 1, minCanvasRadius: 30, maxCanvasRadius: 55 },
  { label: "near", radius: 110, start: 1, end: 5, minCanvasRadius: 55, maxCanvasRadius: 110 },
  { label: "medium", radius: 165, start: 5, end: 20, minCanvasRadius: 110, maxCanvasRadius: 165 },
  { label: "far", radius: 220, start: 20, end: 100, minCanvasRadius: 165, maxCanvasRadius: 220 },
];
const SWEEP_PERIOD_MS = 3000;
const SWEEP_TRAIL_ARC = Math.PI / 3;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function mapDistanceToRadius(distance, zone) {
  if (typeof distance !== "number") {
    return 210;
  }

  const ring = RING_DEFINITIONS.find((entry) => entry.label === zone);
  if (!ring) {
    return 210;
  }

  const progress = (clamp(distance, ring.start, ring.end) - ring.start) / (ring.end - ring.start || 1);
  return ring.minCanvasRadius + progress * (ring.maxCanvasRadius - ring.minCanvasRadius);
}

function getPulseProgress(lastSeen) {
  if (!lastSeen) {
    return null;
  }

  const elapsedMs = Date.now() - Date.parse(lastSeen);
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0 || elapsedMs > 3000) {
    return null;
  }

  return elapsedMs / 3000;
}

function formatDistance(distance) {
  return typeof distance === "number" ? `${distance.toFixed(1)} m` : "Unknown";
}

export default function RadarView({ devices = [], onDeviceSelect, selectedMac }) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const layoutRef = useRef([]);
  const [tooltip, setTooltip] = useState(null);

  const deviceLayout = useMemo(
    () =>
      devices.map((device) => {
        const angle = macToAngle(device.mac);
        const radius = mapDistanceToRadius(device.last_distance_m, device.last_zone);
        const x = CENTER + Math.cos(angle) * radius;
        const y = CENTER + Math.sin(angle) * radius;

        return {
          device,
          x,
          y,
          dotRadius: device.is_favorited ? 12 : 8,
          color: getDeviceClassColor(device.device_class),
          pulseProgress: getPulseProgress(device.last_seen),
        };
      }),
    [devices],
  );

  useEffect(() => {
    layoutRef.current = deviceLayout;
  }, [deviceLayout]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return undefined;
    }

    let isMounted = true;

    const draw = (timestamp) => {
      if (!isMounted) {
        return;
      }

      const sweepAngle = ((timestamp % SWEEP_PERIOD_MS) / SWEEP_PERIOD_MS) * Math.PI * 2;
      context.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
      context.fillStyle = "#0a0f1a";
      context.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

      context.save();
      context.translate(CENTER, CENTER);

      for (const { label, radius } of RING_DEFINITIONS) {
        context.beginPath();
        context.arc(0, 0, radius, 0, Math.PI * 2);
        context.fillStyle = "rgba(0,200,100,0.04)";
        context.strokeStyle = "rgba(0,200,100,0.15)";
        context.lineWidth = 1;
        context.fill();
        context.stroke();

        context.fillStyle = "rgba(0,255,120,0.55)";
        context.font = "12px system-ui";
        context.textAlign = "left";
        context.textBaseline = "middle";
        context.fillText(label, radius + 8, 0);
      }

      const sweepGradient = context.createLinearGradient(0, 0, Math.cos(sweepAngle) * 235, Math.sin(sweepAngle) * 235);
      sweepGradient.addColorStop(0, "rgba(0,255,120,0.22)");
      sweepGradient.addColorStop(0.6, "rgba(0,255,120,0.08)");
      sweepGradient.addColorStop(1, "rgba(0,255,120,0)");
      context.beginPath();
      context.moveTo(0, 0);
      context.arc(0, 0, 235, sweepAngle - SWEEP_TRAIL_ARC, sweepAngle, false);
      context.closePath();
      context.fillStyle = sweepGradient;
      context.fill();

      context.beginPath();
      context.moveTo(0, 0);
      context.lineTo(Math.cos(sweepAngle) * 235, Math.sin(sweepAngle) * 235);
      context.strokeStyle = "rgba(0,255,120,0.85)";
      context.lineWidth = 3;
      context.stroke();

      for (const { device, x, y, dotRadius, color, pulseProgress } of deviceLayout) {
        const localX = x - CENTER;
        const localY = y - CENTER;

        if (pulseProgress !== null) {
          context.beginPath();
          context.arc(localX, localY, dotRadius + pulseProgress * 16, 0, Math.PI * 2);
          context.strokeStyle = `rgba(255,255,255,${0.5 * (1 - pulseProgress)})`;
          context.lineWidth = 2;
          context.stroke();
        }

        context.beginPath();
        context.arc(localX, localY, dotRadius, 0, Math.PI * 2);
        context.fillStyle = color;
        context.shadowColor = color;
        context.shadowBlur = 12;
        context.fill();
        context.shadowBlur = 0;

        if (selectedMac === device.mac) {
          context.beginPath();
          context.arc(localX, localY, dotRadius + 5, 0, Math.PI * 2);
          context.strokeStyle = "#ffffff";
          context.lineWidth = 2;
          context.stroke();
        }
      }

      context.restore();
      animationFrameRef.current = window.requestAnimationFrame(draw);
    };

    animationFrameRef.current = window.requestAnimationFrame(draw);

    return () => {
      isMounted = false;
      if (animationFrameRef.current) {
        window.cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [deviceLayout, selectedMac]);

  function getCanvasCoordinates(event) {
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = CANVAS_SIZE / rect.width;
    const scaleY = CANVAS_SIZE / rect.height;
    return {
      x: (event.clientX - rect.left) * scaleX,
      y: (event.clientY - rect.top) * scaleY,
    };
  }

  function findHitDevice(point) {
    return layoutRef.current.find(({ x, y }) => {
      const dx = point.x - x;
      const dy = point.y - y;
      return Math.sqrt(dx * dx + dy * dy) <= 14;
    });
  }

  function handleCanvasClick(event) {
    const hit = findHitDevice(getCanvasCoordinates(event));
    if (hit && onDeviceSelect) {
      onDeviceSelect(hit.device.mac);
    }
  }

  function handleCanvasMouseMove(event) {
    const hit = findHitDevice(getCanvasCoordinates(event));
    if (!hit) {
      setTooltip(null);
      return;
    }

    setTooltip({
      device: hit.device,
      left: event.clientX + 12,
      top: event.clientY + 12,
    });
  }

  return (
    <div className="radar-view">
      <canvas
        ref={canvasRef}
        className="radar-view__canvas"
        width={CANVAS_SIZE}
        height={CANVAS_SIZE}
        onClick={handleCanvasClick}
        onMouseLeave={() => setTooltip(null)}
        onMouseMove={handleCanvasMouseMove}
      />
      {tooltip ? (
        <div className="radar-view__tooltip" style={{ left: tooltip.left, top: tooltip.top }}>
          <strong>{tooltip.device.user_label || tooltip.device.name || tooltip.device.mac}</strong>
          <span>Class: {tooltip.device.device_class || "unknown"}</span>
          <span>Distance: {formatDistance(tooltip.device.last_distance_m)}</span>
          <span>RSSI: {tooltip.device.last_rssi ?? "Unknown"}</span>
        </div>
      ) : null}
    </div>
  );
}
