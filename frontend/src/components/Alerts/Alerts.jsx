import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { setAlertsPanelOpen, useAlerts } from "../../hooks/useAlerts";
import * as alertStore from "../../store/alertStore";
import * as deviceStore from "../../store/deviceStore";
import { getDeviceClassColor } from "../../utils/deviceUtils";
import "./Alerts.css";

const API_BASE_URL = "http://127.0.0.1:8765/api/v1";
const RULE_TYPES = ["new_unknown_device", "device_appeared", "device_lingered", "rssi_threshold"];

function formatRelativeTime(timestamp) {
  if (!timestamp) {
    return "Unknown";
  }
  const diffSeconds = Math.max(0, Math.floor((Date.now() - Date.parse(timestamp)) / 1000));
  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  }
  if (diffSeconds < 3600) {
    return `${Math.floor(diffSeconds / 60)}m ago`;
  }
  return `${Math.floor(diffSeconds / 3600)}h ago`;
}

export default function Alerts() {
  const [activeTab, setActiveTab] = useState("events");
  const [ruleType, setRuleType] = useState("new_unknown_device");
  const [label, setLabel] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [minutes, setMinutes] = useState(10);
  const [rssiThreshold, setRssiThreshold] = useState(-60);
  const { events, rules } = useAlerts();
  const deviceSnapshot = useSyncExternalStore(deviceStore.subscribe, deviceStore.getSnapshot, deviceStore.getSnapshot);

  useEffect(() => {
    setAlertsPanelOpen(activeTab === "alerts");
    return () => setAlertsPanelOpen(false);
  }, [activeTab]);

  useEffect(() => {
    let isCancelled = false;

    async function loadRules() {
      const response = await fetch(`${API_BASE_URL}/alerts/rules`);
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      if (!isCancelled) {
        alertStore.setRules(payload.alerts || []);
      }
    }

    loadRules();
    return () => {
      isCancelled = true;
    };
  }, []);

  const devices = useMemo(() => Object.values(deviceSnapshot.devices), [deviceSnapshot.devices]);

  async function handleDeleteRule(alertId) {
    await fetch(`${API_BASE_URL}/alerts/rules/${alertId}`, { method: "DELETE" });
    alertStore.setRules(rules.filter((rule) => rule.id !== alertId));
  }

  async function handleSaveRule(event) {
    event.preventDefault();

    const body = {
      rule_type: ruleType,
      label,
      device_id: ruleType === "device_appeared" ? Number(deviceId) || null : null,
      rule_value:
        ruleType === "device_lingered"
          ? String(minutes)
          : ruleType === "rssi_threshold"
            ? String(rssiThreshold)
            : null,
    };

    const response = await fetch(`${API_BASE_URL}/alerts/rules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return;
    }

    const payload = await response.json();
    alertStore.setRules([payload.alert, ...rules]);
    setLabel("");
  }

  return (
    <div className="alerts-panel-view">
      <div className="alerts-panel-view__tabs">
        <button
          type="button"
          className={activeTab === "events" ? "alerts-tab alerts-tab--active" : "alerts-tab"}
          onClick={() => setActiveTab("events")}
        >
          Events
        </button>
        <button
          type="button"
          className={activeTab === "rules" ? "alerts-tab alerts-tab--active" : "alerts-tab"}
          onClick={() => setActiveTab("rules")}
        >
          Rules
        </button>
      </div>

      {activeTab === "events" ? (
        <div className="alerts-panel-view__events">
          <div className="alerts-panel-view__toolbar">
            <button type="button" onClick={() => alertStore.setEvents([])}>Clear all</button>
          </div>
          {events.map((event) => (
            <article key={`${event.id}-${event.triggered_at}`} className="alert-event-card">
              <span
                className="alert-event-card__icon"
                style={{ backgroundColor: getDeviceClassColor(event.device?.device_class) }}
              />
              <div className="alert-event-card__content">
                <strong>{event.label || event.alert_label || "Alert"}</strong>
                <p>{event.device?.name || event.device?.user_label || event.device_mac || "Unknown device"}</p>
                <p>{formatRelativeTime(event.triggered_at)}</p>
                <p>{event.detail || "No detail"}</p>
              </div>
            </article>
          ))}
          {!events.length ? <div className="alerts-empty">No alert events yet.</div> : null}
        </div>
      ) : (
        <div className="alerts-panel-view__rules">
          <div className="alerts-rules-list">
            {rules.map((rule) => (
              <article key={rule.id} className="alert-rule-card">
                <div>
                  <span className="alert-rule-card__badge">{rule.rule_type}</span>
                  <strong>{rule.label}</strong>
                </div>
                <button type="button" onClick={() => handleDeleteRule(rule.id)}>Delete</button>
              </article>
            ))}
          </div>

          <form className="alert-form" onSubmit={handleSaveRule}>
            <h3>Add Rule</h3>
            <select value={ruleType} onChange={(event) => setRuleType(event.target.value)}>
              {RULE_TYPES.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
            <input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Rule label" />

            {ruleType === "device_appeared" ? (
              <select value={deviceId} onChange={(event) => setDeviceId(event.target.value)}>
                <option value="">Select device</option>
                {devices.map((device) => (
                  <option key={device.mac} value={device.id}>{device.user_label || device.name || device.mac}</option>
                ))}
              </select>
            ) : null}

            {ruleType === "device_lingered" ? (
              <input type="number" min="1" value={minutes} onChange={(event) => setMinutes(event.target.value)} />
            ) : null}

            {ruleType === "rssi_threshold" ? (
              <label className="alert-form__slider">
                <span>{rssiThreshold} dBm</span>
                <input
                  type="range"
                  min="-90"
                  max="-40"
                  value={rssiThreshold}
                  onChange={(event) => setRssiThreshold(event.target.value)}
                />
              </label>
            ) : null}

            <button type="submit">Save</button>
          </form>
        </div>
      )}
    </div>
  );
}
