"use client";

import { useEffect, useState } from "react";
import { listFuelLogs, createFuelLog, listVehicles, FuelLog, Vehicle } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function FuelLogPage() {
  const [logs, setLogs] = useState<FuelLog[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [vehicleFilter, setVehicleFilter] = useState("");
  const [form, setForm] = useState<Record<string, string>>({ fuel_date: new Date().toISOString().split("T")[0] });

  useEffect(() => { load(); }, [vehicleFilter]);
  async function load() {
    setLoading(true);
    try {
      const [l, v] = await Promise.all([
        listFuelLogs(vehicleFilter ? { vehicle_id: vehicleFilter } : undefined),
        listVehicles(),
      ]);
      setLogs(l); setVehicles(v);
    } catch {}
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createFuelLog({ ...form });
      setShowForm(false); await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to log fuel");
    }
    setSaving(false);
  }

  const totalCost = logs.reduce((s, l) => s + Number(l.fuel_cost), 0);
  const totalLiters = logs.reduce((s, l) => s + Number(l.fuel_quantity_liters), 0);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fuel Log</h1>
          <p className="text-sm text-gray-500 mt-1">{logs.length} records · {totalLiters.toFixed(1)}L · KES {totalCost.toLocaleString()}</p>
        </div>
        <div className="flex gap-2">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={vehicleFilter} onChange={(e) => setVehicleFilter(e.target.value)}>
            <option value="">All vehicles</option>
            {vehicles.map((v) => <option key={v.id} value={v.id}>{v.vehicle_code} ({v.plate_number})</option>)}
          </select>
          <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Log Fuel"}</Button>
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
            <Input id="date" label="Date" type="date" value={form.fuel_date} onChange={(e) => setForm({ ...form, fuel_date: e.target.value })} required />
            <Input id="qty" label="Quantity (L)" type="number" step="0.001" value={form.fuel_quantity_liters || ""} onChange={(e) => setForm({ ...form, fuel_quantity_liters: e.target.value })} required />
            <Input id="cost" label="Total Cost (KES)" type="number" step="0.01" value={form.fuel_cost || ""} onChange={(e) => setForm({ ...form, fuel_cost: e.target.value })} required />
            <Input id="odo" label="Odometer (km)" type="number" step="0.1" value={form.odometer_reading || ""} onChange={(e) => setForm({ ...form, odometer_reading: e.target.value })} />
            <Input id="station" label="Fuel Station" value={form.fuel_station || ""} onChange={(e) => setForm({ ...form, fuel_station: e.target.value })} />
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Save</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Date", "Vehicle", "Quantity (L)", "Cost (KES)", "KES/L", "Odometer", "Station"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((l) => {
                const v = vehicles.find((x) => x.id === l.vehicle_id);
                return (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{l.fuel_date}</td>
                    <td className="px-4 py-3 font-mono text-xs text-indigo-700">{v?.plate_number || "—"}</td>
                    <td className="px-4 py-3">{Number(l.fuel_quantity_liters).toFixed(1)}</td>
                    <td className="px-4 py-3 font-medium">{Number(l.fuel_cost).toLocaleString()}</td>
                    <td className="px-4 py-3 text-gray-600">{l.cost_per_liter ? Number(l.cost_per_liter).toFixed(2) : "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{l.odometer_reading ? `${Number(l.odometer_reading).toLocaleString()} km` : "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{l.fuel_station || "—"}</td>
                  </tr>
                );
              })}
              {logs.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No fuel records</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
