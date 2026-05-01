"use client";

import { useEffect, useState } from "react";
import { listDrivers, createDriver, updateDriver, FleetDriver, DriverStatus, DRIVER_STATUS_BADGE } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const STATUSES: DriverStatus[] = ["available", "on_trip", "off_duty", "inactive"];

export default function DriversPage() {
  const [drivers, setDrivers] = useState<FleetDriver[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<Record<string, string>>({ status: "available" });

  useEffect(() => { load(); }, []);
  async function load() {
    setLoading(true);
    try { setDrivers(await listDrivers()); } catch {}
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createDriver({ ...form });
      setShowForm(false); setForm({ status: "available" }); await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to create driver");
    }
    setSaving(false);
  }

  async function handleStatusChange(id: string, status: DriverStatus) {
    await updateDriver(id, { status });
    await load();
  }

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Drivers</h1>
          <p className="text-sm text-gray-500 mt-1">{drivers.length} driver(s)</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Driver"}</Button>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <Input id="code" label="Driver Code" value={form.driver_code || ""} onChange={(e) => setForm({ ...form, driver_code: e.target.value })} placeholder="Auto-generated if blank" />
            <Input id="name" label="Full Name" value={form.full_name || ""} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
            <Input id="phone" label="Phone" value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <Input id="license" label="License Number" value={form.license_number || ""} onChange={(e) => setForm({ ...form, license_number: e.target.value })} required />
            <Input id="class" label="License Class" value={form.license_class || ""} onChange={(e) => setForm({ ...form, license_class: e.target.value })} placeholder="A, B, CE..." />
            <Input id="expiry" label="License Expiry" type="date" value={form.license_expiry || ""} onChange={(e) => setForm({ ...form, license_expiry: e.target.value })} />
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Add Driver</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Code", "Name", "Phone", "License", "Class", "Expiry", "Status", ""].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {drivers.map((d) => {
                const expired = d.license_expiry && d.license_expiry < today;
                return (
                  <tr key={d.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-indigo-700">{d.driver_code}</td>
                    <td className="px-4 py-3 font-medium">{d.full_name}</td>
                    <td className="px-4 py-3 text-gray-600">{d.phone || "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs">{d.license_number}</td>
                    <td className="px-4 py-3 text-gray-600">{d.license_class || "—"}</td>
                    <td className={`px-4 py-3 text-xs ${expired ? "text-red-600 font-medium" : "text-gray-600"}`}>
                      {d.license_expiry || "—"}{expired ? " ⚠ Expired" : ""}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${DRIVER_STATUS_BADGE[d.status]}`}>
                        {d.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <select className="text-xs border border-gray-200 rounded px-2 py-1 capitalize" value={d.status} onChange={(e) => handleStatusChange(d.id, e.target.value as DriverStatus)}>
                        {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                      </select>
                    </td>
                  </tr>
                );
              })}
              {drivers.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No drivers found</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
