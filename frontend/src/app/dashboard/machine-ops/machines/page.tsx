"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, Machine, MachineStatus, MachineFamily, MACHINE_STATUS_COLORS } from "@/lib/machineOperator";

const FAMILIES: MachineFamily[] = ["FILLING", "MIXING", "PACKAGING", "LABELING", "PALLETIZING", "CONVEYOR", "WEIGHING", "INSPECTION", "UTILITY", "OTHER"];

export default function MachinesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Machine | null>(null);
  const [filterStatus, setFilterStatus] = useState<MachineStatus | "">("");
  const [form, setForm] = useState({
    machine_code: "", machine_name: "", machine_family: "OTHER" as MachineFamily,
    manufacturer: "", model_no: "", serial_no: "", line_id: "",
    rated_capacity_per_hour: "", capacity_uom: "KG",
    setup_time_standard_min: "0", cleanup_time_standard_min: "0", changeover_time_standard_min: "0",
    hourly_cost_rate: "", energy_cost_per_hour: "", notes: "",
  });

  const { data, isLoading } = useQuery<Machine[]>({
    queryKey: ["mo-machines", filterStatus],
    queryFn: () => moApi.listMachines(filterStatus ? { status: filterStatus } : {}).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => moApi.createMachine({
      ...form,
      rated_capacity_per_hour: form.rated_capacity_per_hour ? parseFloat(form.rated_capacity_per_hour) : undefined,
      setup_time_standard_min: parseInt(form.setup_time_standard_min),
      cleanup_time_standard_min: parseInt(form.cleanup_time_standard_min),
      changeover_time_standard_min: parseInt(form.changeover_time_standard_min),
      hourly_cost_rate: form.hourly_cost_rate ? parseFloat(form.hourly_cost_rate) : undefined,
      energy_cost_per_hour: form.energy_cost_per_hour ? parseFloat(form.energy_cost_per_hour) : undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-machines"] });
      qc.invalidateQueries({ queryKey: ["mo-dashboard"] });
      setShowCreate(false);
    },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: MachineStatus }) => moApi.updateMachine(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mo-machines"] }),
  });

  const machines = data || [];
  const counts = {
    ACTIVE: machines.filter((m) => m.status === "ACTIVE").length,
    MAINTENANCE: machines.filter((m) => m.status === "MAINTENANCE").length,
    INACTIVE: machines.filter((m) => m.status === "INACTIVE").length,
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Machine Master</h1>
        </div>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">+ Add Machine</button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Total", value: machines.length, color: "text-gray-900" },
          { label: "Active", value: counts.ACTIVE, color: "text-green-700" },
          { label: "In Maintenance", value: counts.MAINTENANCE, color: "text-orange-600" },
          { label: "Inactive", value: counts.INACTIVE, color: "text-gray-500" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="bg-white rounded-lg border p-3 flex gap-3 flex-wrap">
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as any)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">All Statuses</option>
          {["ACTIVE", "MAINTENANCE", "INACTIVE", "RETIRED"].map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      {/* Machine List */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Code", "Name", "Family", "Line", "Capacity/hr", "Std Speed", "Cost/hr", "Setup min", "Status", "Actions"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {machines.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs font-medium">{m.machine_code}</td>
                <td className="px-4 py-2.5 text-sm">{m.machine_name}</td>
                <td className="px-4 py-2.5 text-xs">{m.machine_family}</td>
                <td className="px-4 py-2.5 text-xs">{m.line_id || "—"}</td>
                <td className="px-4 py-2.5 text-xs">{m.rated_capacity_per_hour ? `${Number(m.rated_capacity_per_hour).toLocaleString()} ${m.capacity_uom || ""}` : "—"}</td>
                <td className="px-4 py-2.5 text-xs">{m.standard_speed || "—"}</td>
                <td className="px-4 py-2.5 text-xs">{m.hourly_cost_rate ? `KES ${Number(m.hourly_cost_rate).toLocaleString()}` : "—"}</td>
                <td className="px-4 py-2.5 text-xs">{m.setup_time_standard_min ?? 0} min</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${MACHINE_STATUS_COLORS[m.status]}`}>{m.status}</span>
                </td>
                <td className="px-4 py-2.5 flex gap-2">
                  <button onClick={() => setSelected(selected?.id === m.id ? null : m)} className="text-xs text-indigo-600 hover:underline">Detail</button>
                  {m.status === "ACTIVE" && (
                    <button onClick={() => updateStatus.mutate({ id: m.id, status: "MAINTENANCE" })} className="text-xs text-orange-500 hover:underline">→ Maint</button>
                  )}
                  {m.status === "MAINTENANCE" && (
                    <button onClick={() => updateStatus.mutate({ id: m.id, status: "ACTIVE" })} className="text-xs text-green-600 hover:underline">→ Active</button>
                  )}
                </td>
              </tr>
            ))}
            {!isLoading && !machines.length && (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400 text-sm">No machines found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Panel */}
      {selected && (
        <div className="bg-white rounded-lg border p-5">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-gray-900">{selected.machine_code} — {selected.machine_name}</h2>
            <button onClick={() => setSelected(null)} className="text-xs text-gray-400 hover:text-gray-600">✕ Close</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {[
              { label: "Manufacturer", value: selected.manufacturer },
              { label: "Model", value: selected.model_no },
              { label: "Serial", value: selected.serial_no },
              { label: "Commission Date", value: selected.commission_date },
              { label: "Rated Capacity", value: selected.rated_capacity_per_hour ? `${selected.rated_capacity_per_hour} ${selected.capacity_uom || ""}` : "—" },
              { label: "Hourly Cost", value: selected.hourly_cost_rate ? `KES ${Number(selected.hourly_cost_rate).toLocaleString()}/hr` : "—" },
              { label: "Energy Cost", value: selected.energy_cost_per_hour ? `KES ${Number(selected.energy_cost_per_hour).toLocaleString()}/hr` : "—" },
              { label: "OEE Tracking", value: selected.oee_tracking_enabled ? "Enabled" : "Disabled" },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-gray-500">{label}</p>
                <p className="font-medium text-gray-800">{value || "—"}</p>
              </div>
            ))}
          </div>
          {selected.notes && <p className="mt-3 text-xs text-gray-500">Notes: {selected.notes}</p>}
          <div className="mt-4 flex gap-2">
            <a href={`/dashboard/machine-ops/performance?machine_id=${selected.id}`} className="text-xs text-indigo-600 border border-indigo-200 px-3 py-1.5 rounded-lg hover:bg-indigo-50">View Performance</a>
            <a href={`/dashboard/machine-ops/runtime?machine_id=${selected.id}`} className="text-xs text-blue-600 border border-blue-200 px-3 py-1.5 rounded-lg hover:bg-blue-50">View Runtime</a>
            <a href={`/dashboard/machine-ops/downtime?machine_id=${selected.id}`} className="text-xs text-red-600 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-50">Downtime History</a>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[640px] max-h-[90vh] overflow-y-auto space-y-4">
            <h2 className="font-bold text-gray-900">Add Machine</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Machine Code *", field: "machine_code", placeholder: "MCH-001" },
                { label: "Machine Name *", field: "machine_name", placeholder: "Filling Line 1" },
                { label: "Manufacturer", field: "manufacturer", placeholder: "Krones" },
                { label: "Model No", field: "model_no", placeholder: "BF-5000" },
                { label: "Serial No", field: "serial_no", placeholder: "" },
                { label: "Line ID", field: "line_id", placeholder: "LINE-A" },
                { label: "Rated Capacity/hr", field: "rated_capacity_per_hour", placeholder: "5000" },
                { label: "Cost Rate (KES/hr)", field: "hourly_cost_rate", placeholder: "2500" },
                { label: "Energy (KES/hr)", field: "energy_cost_per_hour", placeholder: "150" },
                { label: "Setup Time (min)", field: "setup_time_standard_min", placeholder: "30" },
                { label: "Cleanup Time (min)", field: "cleanup_time_standard_min", placeholder: "15" },
                { label: "Changeover (min)", field: "changeover_time_standard_min", placeholder: "45" },
              ].map(({ label, field, placeholder }) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input
                    value={(form as Record<string, string>)[field]}
                    onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={placeholder}
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Machine Family</label>
                <select value={form.machine_family} onChange={(e) => setForm((p) => ({ ...p, machine_family: e.target.value as MachineFamily }))} className="w-full border rounded px-3 py-2 text-sm">
                  {FAMILIES.map((f) => <option key={f}>{f}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Capacity UOM</label>
                <select value={form.capacity_uom} onChange={(e) => setForm((p) => ({ ...p, capacity_uom: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                  {["KG", "L", "PCS", "CTN", "units/hr"].map((u) => <option key={u}>{u}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
              <textarea value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => create.mutate()} disabled={!form.machine_code || !form.machine_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {create.isPending ? "Saving…" : "Add Machine"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
