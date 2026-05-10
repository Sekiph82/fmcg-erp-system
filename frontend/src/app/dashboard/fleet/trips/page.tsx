"use client";

import { useCallback, useEffect, useState } from "react";
import { listTrips, createTrip, updateTrip, listVehicles, listDrivers, FleetTrip, TripStatus, TRIP_STATUS_BADGE } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const STATUSES: TripStatus[] = ["planned", "in_progress", "completed", "cancelled"];

export default function TripsPage() {
  const [trips, setTrips] = useState<FleetTrip[]>([]);
  const [vehicles, setVehicles] = useState<{ id: string; vehicle_code: string; plate_number: string }[]>([]);
  const [drivers, setDrivers] = useState<{ id: string; full_name: string }[]>([]);
  const [filter, setFilter] = useState<TripStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<Record<string, string>>({ trip_date: new Date().toISOString().split("T")[0], purpose: "delivery" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, v, d] = await Promise.all([
        listTrips(filter === "all" ? undefined : { status: filter }),
        listVehicles({ status: "active" }),
        listDrivers({ status: "available" }),
      ]);
      setTrips(t); setVehicles(v); setDrivers(d);
    } catch {}
    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createTrip({ ...form });
      setShowForm(false); await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create trip");
    }
    setSaving(false);
  }

  async function handleStatusChange(id: string, status: TripStatus) {
    await updateTrip(id, { status });
    await load();
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trips</h1>
          <p className="text-sm text-gray-500 mt-1">{trips.length} trip(s)</p>
        </div>
        <div className="flex gap-2">
          {(["all", ...STATUSES] as const).map((s) => (
            <button key={s} onClick={() => setFilter(s)} className={`text-sm px-3 py-1.5 rounded-lg capitalize ${filter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Plan Trip"}
          </Button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Plan New Trip</h2>
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
                <option value="">No driver assigned</option>
                {drivers.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </div>
            <Input id="trip_date" label="Trip Date" type="date" value={form.trip_date} onChange={(e) => setForm({ ...form, trip_date: e.target.value })} required />
            <Input id="purpose" label="Purpose" value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} placeholder="delivery / transfer / van_sales" />
            <Input id="start_loc" label="Start Location" value={form.start_location || ""} onChange={(e) => setForm({ ...form, start_location: e.target.value })} />
            <Input id="end_loc" label="End Location" value={form.end_location || ""} onChange={(e) => setForm({ ...form, end_location: e.target.value })} />
            <Input id="dist" label="Planned Distance (km)" type="number" value={form.planned_distance_km || ""} onChange={(e) => setForm({ ...form, planned_distance_km: e.target.value })} />
            <Input id="cargo" label="Cargo Weight (kg)" type="number" value={form.cargo_weight_kg || ""} onChange={(e) => setForm({ ...form, cargo_weight_kg: e.target.value })} />
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Create Trip</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Trip No.", "Date", "From → To", "Purpose", "Distance", "Status", ""].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {trips.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-700">{t.trip_no}</td>
                  <td className="px-4 py-3">{t.trip_date}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{t.start_location || "—"} → {t.end_location || "—"}</td>
                  <td className="px-4 py-3 capitalize text-gray-700">{t.purpose || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.actual_distance_km ? `${t.actual_distance_km}km` : t.planned_distance_km ? `~${t.planned_distance_km}km` : "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${TRIP_STATUS_BADGE[t.status]}`}>
                      {t.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <select className="text-xs border border-gray-200 rounded px-2 py-1 capitalize" value={t.status} onChange={(e) => handleStatusChange(t.id, e.target.value as TripStatus)}>
                      {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {trips.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No trips found</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
