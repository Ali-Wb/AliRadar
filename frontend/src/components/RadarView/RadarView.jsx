import { useEffect, useMemo, useRef, useState } from "react";

import { getDeviceClassColor, macToAngle } from "../../utils/deviceUtils";
import "./RadarView.css";

const CANVAS_SIZE = 500;
const CENTER = CANVAS_SIZE / 2;
const RING_DEFINITIONS = [
  { label: "immediate", radius: 55 },
  { label: "near", radius: 110 },
  { label: "medium", radius: 165 },
  { label: "far", radius: 220 },
];

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function mapDistanceToRadius(distance, zone) {
  if (typeof distance !== "number") {
    return 210;
  }

  if (zone === "immediate") {
    return 30 + ((clamp(distance, 0, 1) - 0) / 1) * 25;
  }
  if (zone === "near") {
    return 55 + ((clamp(distance, 1, 5) - 1) / 4) * 55;
  }
  if (zone === "medium") {
    return 110 + ((clamp(distance, 5, 20) - 5) / 15) * 55;
  }
  if (zone === "far") {
    return 165 + ((clamp(distance, 20, 100) - 20) / 80) * 55;
  }
  return 210;
}

function getPulseStrength(lastSeen) {
  if (!lastSeen) {
    return null;
  }
  const elapsedMs = Date.now() - Date.parse(lastSeen);
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0 || elapsedMs > 3000) {
    return null;
  }
  return 1 - elapsedMs / 3000;
}

export default function RadarView({ devices = [], onDeviceSelect, selectedMac }) {
  const canvasRef = useRef(null);
  const frameRef = useRef(null);
  const layoutRef = useRef([]);
  const [tooltip, setTooltip] = useState(null);

  const deviceLayout = useMemo(
    () =>
      devices.map((device) => {
        const angle = macToAngle(device.mac);
        const radius = mapDistanceToRadius(device.last_distance_m, device.last_zone);
        const x = CENTER + Math.cos(angle) * radius;
        const y = CENTER + Math.sin(angle) * radius;
        const pulseStrength = getPulseStrength(device.last_seen);

        return {
          device,
          angle,
          radius,
          x,
          y,
          dotRadius: device.is_favorited ? 12 : 8,
          color: getDeviceClassColor(device.device_class),
          pulseStrength,
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
    let mounted = true;

    const drawFrame = (timestamp) => {
      if (!mounted) {
        return;
      }

      const sweepAngle = ((timestamp % 3000) / 3000) * Math.PI * 2;
      context.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
      context.fillStyle = "#0a0f1a";
      context.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

      context.save();
      context.translate(CENTER, CENTER);

      RING_DEFINITIONS.forEach(({ label, radius }) => {
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
        context.fillText(label, radius + 8, 4);
      });

      const gradient = context.createRadialGradient(0, 0, 0, 0, 0, 250);
      gradient.addColorStop(0, "rgba(0,255,120,0.22)");
      gradient.addColorStop(1, "rgba(0,255,120,0)");
      context.beginPath();
      context.moveTo(0, 0);
      context.arc(0, 0, 235, sweepAngle - 0.6, sweepAngle, false);
      context.closePath();
      context.fillStyle = gradient;
      context.fill();

      context.beginPath();
      context.moveTo(0, 0);
      context.lineTo(Math.cos(sweepAngle) * 235, Math.sin(sweepAngle) * 235);
      context.strokeStyle = "rgba(0,255,120,0.85)";
      context.lineWidth = 3;
      context.stroke();

      deviceLayout.forEach(({ device, x, y, dotRadius, color, pulseStrength }) => {
        const localX = x - CENTER;
        const localY = y - CENTER;

        if (pulseStrength) {
          context.beginPath();
          context.arc(localX, localY, dotRadius + (1 - pulseStrength) * 14, 0, Math.PI * 2);
          context.strokeStyle = `rgba(255,255,255,${pulseStrength * 0.45})`;
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

        if (selectedMac && selectedMac === device.mac) {
          context.beginPath();
          context.arc(localX, localY, dotRadius + 5, 0, Math.PI * 2);
          context.strokeStyle = "#ffffff";
          context.lineWidth = 2;
          context.stroke();
        }
      });

      context.restore();
      frameRef.current = window.requestAnimationFrame(drawFrame);
    };

    frameRef.current = window.requestAnimationFrame(drawFrame);

    return () => {
      mounted = false;
      if (frameRef.current) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [deviceLayout, selectedMac]);

  function getCanvasPoint(event) {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  function findDeviceAtPoint(point) {
    return layoutRef.current.find(({ x, y }) => {
      const dx = point.x - x;
      const dy = point.y - y;
      return Math.sqrt(dx * dx + dy * dy) <= 14;
    });
  }

  function handleClick(event) {
    const hit = findDeviceAtPoint(getCanvasPoint(event));
    if (hit && onDeviceSelect) {
      onDeviceSelect(hit.device.mac);
    }
  }

  function handleMouseMove(event) {
    const point = getCanvasPoint(event);
    const hit = findDeviceAtPoint(point);
    if (!hit) {
      setTooltip(null);
      return;
    }

    setTooltip({
      left: event.clientX + 12,
      top: event.clientY + 12,
      device: hit.device,
    });
  }

  return (
    <div className="radar-view">
      <canvas
        ref={canvasRef}
        className="radar-view__canvas"
        height={CANVAS_SIZE}
        width={CANVAS_SIZE}
        onClick={handleClick}
        onMouseLeave={() => setTooltip(null)}
        onMouseMove={handleMouseMove}
      />
      {tooltip ? (
        <div className="radar-view__tooltip" style={{ left: tooltip.left, top: tooltip.top }}>
          <strong>{tooltip.device.user_label || tooltip.device.name || tooltip.device.mac}</strong>
          <span>{tooltip.device.device_class || "unknown"}</span>
          <span>Distance: {tooltip.device.last_distance_m ?? "?"} m</span>
          <span>RSSI: {tooltip.device.last_rssi ?? "?"}</span>
        </div>
      ) : null}
    </div>
  );
}
