"use client";

import { useCallback, useEffect, useState } from "react";
import { listVehicles, createVehicle, updateVehicle, Vehicle, VehicleStatus, VehicleType, VEHICLE_STATUS_BADGE } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const TYPES: VehicleType[] = ["truck", "van", "motorcycle", "pickup", "third_party"];
const STATUSES: VehicleStatus[] = ["active", "in_service", "maintenance", "inactive"];

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<VehicleStatus | "all">("all");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Partial<Vehicle>>({ vehicle_type: "truck", fuel_type: "diesel", status: "active" });
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { setVehicles(await listVehicles(filter === "all" ? undefined : { status: filter })); } catch {}
    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createVehicle(form);
      setShowForm(false); setForm({ vehicle_type: "truck", fuel_type: "diesel", status: "active" });
      await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create vehicle");
    }
    setSaving(false);
  }

  async function handleStatusChange(id: string, status: VehicleStatus) {
    await updateVehicle(id, { status });
    await load();
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fleet Vehicles</h1>
          <p className="text-sm text-gray-500 mt-1">{vehicles.length} vehicle(s)</p>
        </div>
        <div className="flex gap-2">
          {(["all", ...STATUSES] as const).map((s) => (
            <button key={s} onClick={() => setFilter(s)} className={`text-sm px-3 py-1.5 rounded-lg capitalize ${filter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Add Vehicle"}
          </Button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">New Vehicle</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <Input id="code" label="Vehicle Code" value={form.vehicle_code || ""} onChange={(e) => setForm({ ...form, vehicle_code: e.target.value })} required />
            <Input id="plate" label="Plate Number" value={form.plate_number || ""} onChange={(e) => setForm({ ...form, plate_number: e.target.value })} required />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm capitalize" value={form.vehicle_type} onChange={(e) => setForm({ ...form, vehicle_type: e.target.value as VehicleType })}>
                {TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fuel Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm capitalize" value={form.fuel_type} onChange={(e) => setForm({ ...form, fuel_type: e.target.value as Vehicle["fuel_type"] })}>
                {["petrol", "diesel", "electric", "hybrid"].map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <Input id="make" label="Make" value={form.make || ""} onChange={(e) => setForm({ ...form, make: e.target.value })} />
            <Input id="model" label="Model" value={form.model || ""} onChange={(e) => setForm({ ...form, model: e.target.value })} />
            <Input id="year" label="Year" type="number" value={String(form.year || "")} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })} />
            <Input id="cap_kg" label="Capacity (kg)" type="number" value={String(form.capacity_weight_kg || "")} onChange={(e) => setForm({ ...form, capacity_weight_kg: Number(e.target.value) })} />
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Create</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Code", "Plate", "Type", "Make/Model", "Capacity", "Fuel", "Status", ""].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {vehicles.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-700">{v.vehicle_code}</td>
                  <td className="px-4 py-3 font-medium">{v.plate_number}</td>
                  <td className="px-4 py-3 capitalize">{v.vehicle_type.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-gray-600">{[v.make, v.model].filter(Boolean).join(" ") || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{v.capacity_weight_kg ? `${v.capacity_weight_kg}kg` : "—"}</td>
                  <td className="px-4 py-3 capitalize text-gray-600">{v.fuel_type}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${VEHICLE_STATUS_BADGE[v.status]}`}>
                      {v.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <select className="text-xs border border-gray-200 rounded px-2 py-1" value={v.status} onChange={(e) => handleStatusChange(v.id, e.target.value as VehicleStatus)}>
                      {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {vehicles.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No vehicles found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
