"use client";
import { useEffect, useState } from "react";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

interface Dash { readings_last_1h: number; open_alerts: number; critical_alerts: number; active_machines_24h: number; registered_devices?: number; }
interface MachineState { machine_id: string; machine_name: string | null; state: string; changed_at: string; minutes_in_state: number | null; }
interface Alert { id: string; machine_id: string; machine_name: string | null; metric_name: string; triggered_value: number; severity: string; status: string; triggered_at: string; acknowledged_by: string | null; }
interface SensorReading { machine_id: string; machine_name: string | null; metric_name: string; avg: number; min: number; max: number; unit: string | null; readings: number; }
interface ThresholdForm { machine_id: string; metric_name: string; min_threshold: string; max_threshold: string; severity: string; description: string; }
interface IngestForm { machine_id: string; metric_name: string; value: string; unit: string; source: string; }

const STATE_COLOR: Record<string, string> = {
  RUNNING: "bg-green-500", IDLE: "bg-amber-400", DOWN: "bg-red-500",
  FAULT: "bg-red-700", MAINTENANCE: "bg-blue-400", OFFLINE: "bg-gray-400",
};
const SEV_COLOR: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800 font-bold", WARNING: "bg-amber-100 text-amber-700", INFO: "bg-blue-100 text-blue-700",
};

export default function IoTDashboardPage() {
  const [dash, setDash] = useState<Dash | null>(null);
  const [states, setStates] = useState<MachineState[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [sensors, setSensors] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "alerts" | "sensors" | "ingest" | "thresholds">("overview");
  const [ingestForm, setIngestForm] = useState<IngestForm>({ machine_id: "", metric_name: "", value: "", unit: "", source: "HTTP" });
  const [thresholdForm, setThresholdForm] = useState<ThresholdForm>({ machine_id: "", metric_name: "", min_threshold: "", max_threshold: "", severity: "WARNING", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ingestResult, setIngestResult] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [d, s, a, sr] = await Promise.all([
        fetch("/api/v1/iot/dashboard").then(r => r.json()),
        fetch("/api/v1/iot/machines/current-states").then(r => r.json()),
        fetch("/api/v1/iot/alerts?status=OPEN&limit=20").then(r => r.json()),
        fetch("/api/v1/iot/sensors/summary?hours=1").then(r => r.json()),
      ]);
      setDash(d); setStates(s); setAlerts(a); setSensors(sr);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const ingest = async () => {
    setSaving(true); setError(null); setIngestResult(null);
    try {
      const r = await fetch("/api/v1/iot/ingest", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ machine_id: ingestForm.machine_id, metric_name: ingestForm.metric_name, value: Number(ingestForm.value), unit: ingestForm.unit || undefined, source: ingestForm.source }),
      });
      if (!r.ok) throw new Error(await r.text());
      const res = await r.json();
      setIngestResult(`Ingested: ${res.machine_id} / ${res.metric} = ${res.value}`);
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const addThreshold = async () => {
    setSaving(true); setError(null);
    try {
      const r = await fetch("/api/v1/iot/thresholds", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          machine_id: thresholdForm.machine_id, metric_name: thresholdForm.metric_name,
          min_threshold: thresholdForm.min_threshold ? Number(thresholdForm.min_threshold) : undefined,
          max_threshold: thresholdForm.max_threshold ? Number(thresholdForm.max_threshold) : undefined,
          severity: thresholdForm.severity, description: thresholdForm.description || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setThresholdForm({ machine_id: "", metric_name: "", min_threshold: "", max_threshold: "", severity: "WARNING", description: "" });
      load();
    } catch (e) { setError(String(e)); }
    setSaving(false);
  };

  const ackAlert = async (id: string) => {
    await fetch(`/api/v1/iot/alerts/${id}/acknowledge?acknowledged_by=Operator`, { method: "POST" });
    load();
  };

  const fmtMins = (mins: number | null) => {
    if (mins === null) return "—";
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  };

  return (
    <RequirePermission permission="iot.view">
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">IoT / Machine Data Streaming</h1>
          <p className="text-sm text-gray-500 mt-0.5">Real-time sensor data, machine states, and alert monitoring</p>
        </div>
        <button onClick={load} disabled={loading}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          Refresh
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* KPI strip */}
      {dash && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Readings (1h)", value: dash.readings_last_1h, color: "text-blue-600" },
            { label: "Active Machines (24h)", value: dash.active_machines_24h, color: "text-gray-800" },
            { label: "Open Alerts", value: dash.open_alerts, color: "text-amber-600" },
            { label: "Critical Alerts", value: dash.critical_alerts, color: "text-red-600" },
          ].map((k) => (
            <div key={k.label} className={`bg-white border rounded-lg p-4 shadow-sm ${k.label === "Critical Alerts" && k.value > 0 ? "border-red-300 bg-red-50" : ""}`}>
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b flex-wrap">
        {([["overview","Machine States"],["alerts","Alerts"],["sensors","Sensor Summary"],["ingest","Ingest Data"],["thresholds","+ Threshold"]] as const).map(([t,l]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab===t?"border-blue-600 text-blue-600":"border-transparent text-gray-500 hover:text-gray-700"}`}>{l}</button>
        ))}
      </div>

      {/* Machine States */}
      {tab === "overview" && (
        <div>
          {states.length === 0 ? (
            <div className="bg-gray-50 border rounded-lg p-8 text-center text-sm text-gray-400">
              No machines reporting yet. Ingest a reading or post a state change to see machines here.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {states.map((m) => (
                <div key={m.machine_id} className="bg-white border rounded-xl p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-gray-900">{m.machine_name || m.machine_id}</p>
                      <p className="text-xs text-gray-400 font-mono">{m.machine_id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`h-3 w-3 rounded-full ${STATE_COLOR[m.state] ?? "bg-gray-400"}`} />
                      <span className="text-xs font-semibold text-gray-700">{m.state}</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">In state: {fmtMins(m.minutes_in_state)}</p>
                  {/* Last metrics */}
                  <div className="mt-2 space-y-1">
                    {sensors.filter(s => s.machine_id === m.machine_id).slice(0, 3).map(s => (
                      <div key={s.metric_name} className="flex items-center justify-between text-xs">
                        <span className="text-gray-500 capitalize">{s.metric_name.replace(/_/g, " ")}</span>
                        <span className="font-mono text-gray-700">{s.avg.toFixed(2)} {s.unit ?? ""}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Alerts */}
      {tab === "alerts" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Open Alerts ({alerts.length})</h2></div>
          {alerts.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No open alerts.</div> : (
            <div className="divide-y">
              {alerts.map((a) => (
                <div key={a.id} className="px-4 py-3 flex items-center gap-4">
                  <span className={`text-xs rounded-full px-2 py-0.5 ${SEV_COLOR[a.severity] ?? "bg-gray-100"}`}>{a.severity}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{a.machine_name || a.machine_id} — {a.metric_name}</p>
                    <p className="text-xs text-gray-500">Value: <strong>{a.triggered_value}</strong> · {a.triggered_at?.slice(0, 16).replace("T", " ")}</p>
                  </div>
                  <button onClick={() => ackAlert(a.id)} className="text-xs text-blue-600 hover:text-blue-800 shrink-0">Ack</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sensor summary */}
      {tab === "sensors" && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50"><h2 className="text-sm font-semibold text-gray-700">Sensor Summary — Last 1 Hour</h2></div>
          {sensors.length === 0 ? <div className="p-6 text-sm text-gray-400 text-center">No sensor data in last hour.</div> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr><th className="text-left px-4 py-2">Machine</th><th className="text-left px-4 py-2">Metric</th><th className="text-left px-4 py-2">Avg</th><th className="text-left px-4 py-2">Min</th><th className="text-left px-4 py-2">Max</th><th className="text-left px-4 py-2">Readings</th></tr>
              </thead>
              <tbody className="divide-y">
                {sensors.map((s, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{s.machine_name || s.machine_id}</td>
                    <td className="px-4 py-2.5 text-gray-600 capitalize">{s.metric_name.replace(/_/g, " ")} {s.unit ? `(${s.unit})` : ""}</td>
                    <td className="px-4 py-2.5 font-mono text-blue-600">{s.avg.toFixed(2)}</td>
                    <td className="px-4 py-2.5 font-mono text-gray-500">{s.min.toFixed(2)}</td>
                    <td className="px-4 py-2.5 font-mono text-gray-500">{s.max.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-gray-400">{s.readings}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Manual ingest */}
      {tab === "ingest" && (
        <PermissionGuard permission="iot.ingest">
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-lg">
          <h2 className="text-sm font-semibold text-gray-700">Manual Sensor Data Ingest</h2>
          <p className="text-xs text-gray-400">For testing. In production, devices POST to <code className="bg-gray-100 px-1 rounded">/api/v1/iot/ingest</code> directly.</p>
          {ingestResult && <div className="bg-green-50 border border-green-200 rounded p-2 text-xs text-green-700">{ingestResult}</div>}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Machine ID *","machine_id","e.g. LINE-A-001"],["Metric Name *","metric_name","e.g. temperature"],["Value *","value","e.g. 85.3"],["Unit","unit","e.g. °C"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(ingestForm as unknown as Record<string,string>)[key]}
                  onChange={(e) => setIngestForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
          </div>
          <button onClick={ingest} disabled={saving || !ingestForm.machine_id || !ingestForm.metric_name || !ingestForm.value}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Ingesting…" : "Ingest Reading"}</button>
        </div>
        </PermissionGuard>
      )}

      {/* Add threshold */}
      {tab === "thresholds" && (
        <PermissionGuard permission="iot.configure">
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-3 max-w-lg">
          <h2 className="text-sm font-semibold text-gray-700">Add Alert Threshold</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {([["Machine ID *","machine_id","e.g. LINE-A-001"],["Metric Name *","metric_name","e.g. temperature"],["Min Threshold","min_threshold","e.g. 20"],["Max Threshold","max_threshold","e.g. 95"],["Description","description","Optional"]] as const).map(([label,key,ph]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input type="text" placeholder={ph} value={(thresholdForm as unknown as Record<string,string>)[key]}
                  onChange={(e) => setThresholdForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Severity</label>
              <select value={thresholdForm.severity} onChange={(e) => setThresholdForm((p) => ({ ...p, severity: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none">
                {["INFO","WARNING","CRITICAL"].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <button onClick={addThreshold} disabled={saving || !thresholdForm.machine_id || !thresholdForm.metric_name}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50">{saving ? "Adding…" : "Add Threshold"}</button>
        </div>
        </PermissionGuard>
      )}

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Integration Guide</p>
        <p className="text-xs">
          Devices POST to <code className="bg-blue-100 px-1 rounded">POST /api/v1/iot/ingest</code> with JSON: machine_id, metric_name, value, unit, source (MQTT|OPC-UA|HTTP).
          For MQTT: use a bridge that subscribes to topics and forwards to this API.
          For OPC-UA: use node-opcua or Python opcua-asyncio with HTTP forwarding.
        </p>
      </div>
    </div>
    </RequirePermission>
  );
}
