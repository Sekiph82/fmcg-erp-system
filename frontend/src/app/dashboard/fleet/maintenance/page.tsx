"use client";

import { useEffect, useState } from "react";
import { listMaintenance, createMaintenance, updateMaintenance, listVehicles, MaintenanceRecord, Vehicle, MaintenanceType } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const TYPES: MaintenanceType[] = ["service", "repair", "inspection", "tyre", "other"];

export default function MaintenancePage() {
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [filterCompleted, setFilterCompleted] = useState<boolean | undefined>(false);
  const [form, setForm] = useState<Record<string, string>>({ maintenance_date: new Date().toISOString().split("T")[0], maintenance_type: "service" });

  useEffect(() => { load(); }, [filterCompleted]);
  async function load() {
    setLoading(true);
    try {
      const [r, v] = await Promise.all([listMaintenance({ completed: filterCompleted }), listVehicles()]);
      setRecords(r); setVehicles(v);
    } catch {}
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createMaintenance({ ...form });
      setShowForm(false); await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create record");
    }
    setSaving(false);
  }

  async function markComplete(id: string) {
    await updateMaintenance(id, { completed: true });
    await load();
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Maintenance Tracker</h1>
          <p className="text-sm text-gray-500 mt-1">{records.length} record(s)</p>
        </div>
        <div className="flex gap-2">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={String(filterCompleted ?? "")} onChange={(e) => {
            const v = e.target.value;
            setFilterCompleted(v === "" ? undefined : v === "true");
          }}>
            <option value="">All</option>
            <option value="false">Pending</option>
            <option value="true">Completed</option>
          </select>
          <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Record"}</Button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vehicle</label>
              <select required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.vehicle_id || ""} onChange={(e) => setForm({ ...form, vehicle_id: e.target.value })}>
                <option value="">Select vehicle</option>
                {vehicles.map((v) => <option key={v.id} value={v.id}>{v.vehicle_code} — {v.plate_number}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm capitalize" value={form.maintenance_type} onChange={(e) => setForm({ ...form, maintenance_type: e.target.value })}>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <Input id="date" label="Date" type="date" value={form.maintenance_date} onChange={(e) => setForm({ ...form, maintenance_date: e.target.value })} required />
            <Input id="cost" label="Cost (KES)" type="number" step="0.01" value={form.cost || ""} onChange={(e) => setForm({ ...form, cost: e.target.value })} />
            <Input id="vendor" label="Vendor / Workshop" value={form.vendor || ""} onChange={(e) => setForm({ ...form, vendor: e.target.value })} />
            <Input id="next_due" label="Next Due Date" type="date" value={form.next_due_date || ""} onChange={(e) => setForm({ ...form, next_due_date: e.target.value })} />
            <Input id="downtime" label="Downtime (days)" type="number" value={form.downtime_days || ""} onChange={(e) => setForm({ ...form, downtime_days: e.target.value })} />
            <div className="flex items-end">
              <Input id="desc" label="Description" value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Save</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="space-y-3">
          {records.map((r) => {
            const v = vehicles.find((x) => x.id === r.vehicle_id);
            return (
              <div key={r.id} className={`bg-white rounded-xl border p-4 ${r.completed ? "border-gray-100 opacity-60" : "border-gray-200"}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-bold text-indigo-700">{v?.plate_number || "—"}</span>
                      <span className={`text-xs px-2 py-0.5 rounded capitalize font-medium ${r.completed ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                        {r.completed ? "Completed" : r.maintenance_type}
                      </span>
                    </div>
                    <div className="text-sm text-gray-700">{r.description || r.maintenance_type}</div>
                    <div className="flex gap-4 text-xs text-gray-500 mt-1">
                      <span>{r.maintenance_date}</span>
                      {r.cost && <span>KES {Number(r.cost).toLocaleString()}</span>}
                      {r.vendor && <span>{r.vendor}</span>}
                      {r.next_due_date && <span>Next: {r.next_due_date}</span>}
                      {r.downtime_days && <span>Downtime: {r.downtime_days}d</span>}
                    </div>
                  </div>
                  {!r.completed && (
                    <button onClick={() => markComplete(r.id)} className="text-xs text-green-600 hover:underline">
                      Mark Complete
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {records.length === 0 && <div className="text-center py-12 text-gray-400">No maintenance records found</div>}
        </div>
      )}
    </div>
  );
}
