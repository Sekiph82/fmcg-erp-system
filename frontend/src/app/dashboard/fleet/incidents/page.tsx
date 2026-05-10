"use client";

import { useCallback, useEffect, useState } from "react";
import { listIncidents, createIncident, updateIncident, listVehicles, listDrivers, IncidentLog, IncidentStatus, IncidentType, Vehicle, FleetDriver, INCIDENT_STATUS_BADGE } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const TYPES: IncidentType[] = ["accident", "damage", "theft", "breakdown", "other"];
const STATUSES: IncidentStatus[] = ["open", "under_review", "resolved", "closed"];

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentLog[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [drivers, setDrivers] = useState<FleetDriver[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | "all">("all");
  const [form, setForm] = useState<Record<string, string>>({ incident_date: new Date().toISOString().split("T")[0], incident_type: "accident" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [inc, v, d] = await Promise.all([
        listIncidents(statusFilter === "all" ? undefined : { status: statusFilter }),
        listVehicles(),
        listDrivers(),
      ]);
      setIncidents(inc); setVehicles(v); setDrivers(d);
    } catch {}
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createIncident({ ...form });
      setShowForm(false); await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to log incident");
    }
    setSaving(false);
  }

  async function handleStatusChange(id: string, status: IncidentStatus) {
    await updateIncident(id, { status });
    await load();
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Incident Log</h1>
          <p className="text-sm text-gray-500 mt-1">{incidents.length} incident(s)</p>
        </div>
        <div className="flex gap-2">
          {(["all", ...STATUSES] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`text-sm px-3 py-1.5 rounded-lg capitalize ${statusFilter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
          <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Log Incident"}</Button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-red-200 p-6">
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vehicle</label>
              <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.vehicle_id || ""} onChange={(e) => setForm({ ...form, vehicle_id: e.target.value })}>
                <option value="">Select vehicle</option>
                {vehicles.map((v) => <option key={v.id} value={v.id}>{v.vehicle_code} — {v.plate_number}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Driver</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.driver_id || ""} onChange={(e) => setForm({ ...form, driver_id: e.target.value })}>
                <option value="">No driver</option>
                {drivers.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </div>
            <Input id="date" label="Incident Date" type="date" value={form.incident_date} onChange={(e) => setForm({ ...form, incident_date: e.target.value })} required />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm capitalize" value={form.incident_type} onChange={(e) => setForm({ ...form, incident_type: e.target.value })}>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <Input id="loc" label="Location" value={form.location || ""} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            <Input id="cost" label="Cost Estimate (KES)" type="number" step="0.01" value={form.cost_estimate || ""} onChange={(e) => setForm({ ...form, cost_estimate: e.target.value })} />
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" rows={2} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Log Incident</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="space-y-3">
          {incidents.map((inc) => {
            const v = vehicles.find((x) => x.id === inc.vehicle_id);
            const d = drivers.find((x) => x.id === inc.driver_id);
            return (
              <div key={inc.id} className={`bg-white rounded-xl border p-4 ${inc.status === "open" ? "border-red-200" : "border-gray-200"}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-bold text-gray-900">{v?.plate_number || "—"}</span>
                      <span className={`text-xs px-2 py-0.5 rounded capitalize font-medium ${INCIDENT_STATUS_BADGE[inc.status]}`}>
                        {inc.status.replace("_", " ")}
                      </span>
                      <span className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded capitalize">{inc.incident_type}</span>
                    </div>
                    <div className="text-sm text-gray-700">{inc.description || "No description"}</div>
                    <div className="flex gap-4 text-xs text-gray-500 mt-1">
                      <span>{inc.incident_date}</span>
                      {inc.location && <span>📍 {inc.location}</span>}
                      {inc.cost_estimate && <span>KES {Number(inc.cost_estimate).toLocaleString()}</span>}
                      {d && <span>Driver: {d.full_name}</span>}
                    </div>
                  </div>
                  <select className="text-xs border border-gray-200 rounded px-2 py-1 capitalize" value={inc.status} onChange={(e) => handleStatusChange(inc.id, e.target.value as IncidentStatus)}>
                    {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                  </select>
                </div>
              </div>
            );
          })}
          {incidents.length === 0 && <div className="text-center py-12 text-gray-400">No incidents found</div>}
        </div>
      )}
    </div>
  );
}
