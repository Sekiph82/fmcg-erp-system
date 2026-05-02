"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, DowntimeIntel, DowntimeClass, Machine, DOWNTIME_CLASS_LABELS } from "@/lib/machineOperator";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const DOWNTIME_CLASSES: DowntimeClass[] = [
  "MECHANICAL_BREAKDOWN", "ELECTRICAL_ISSUE", "PNEUMATIC_ISSUE",
  "MATERIAL_SHORTAGE", "PACKAGING_SHORTAGE", "OPERATOR_UNAVAILABLE",
  "QC_WAITING", "CHANGEOVER_DELAY", "CLEANING_DELAY",
  "MAINTENANCE_INTERVENTION", "SPEED_LOSS", "MICRO_STOP",
  "PLANNED_STOP", "UNPLANNED_STOP", "UTILITY_ISSUE", "OTHER",
];

export default function DowntimePage() {
  const qc = useQueryClient();
  const [machineId, setMachineId] = useState("");
  const [filterClass, setFilterClass] = useState<DowntimeClass | "">("");
  const [showLog, setShowLog] = useState(false);
  const [form, setForm] = useState({
    machine_id: "", downtime_class: "MECHANICAL_BREAKDOWN" as DowntimeClass,
    start_time: "", end_time: "", root_cause: "", units_lost: "", notes: "",
  });
  const [success, setSuccess] = useState("");

  const { data: machines } = useQuery<Machine[]>({
    queryKey: ["mo-machines"],
    queryFn: () => moApi.listMachines(),
  });

  const { data, isLoading } = useQuery<DowntimeIntel[]>({
    queryKey: ["mo-downtime", machineId, filterClass],
    queryFn: () => moApi.listDowntime({
      ...(machineId ? { machine_id: machineId } : {}),
      ...(filterClass ? { downtime_class: filterClass } : {}),
    }),
  });

  const logDt = useMutation({
    mutationFn: () => moApi.logDowntime({
      machine_id: form.machine_id,
      downtime_class: form.downtime_class,
      start_time: form.start_time,
      end_time: form.end_time || undefined,
      root_cause: form.root_cause,
      units_lost: form.units_lost ? parseFloat(form.units_lost) : undefined,
      notes: form.notes,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-downtime"] });
      qc.invalidateQueries({ queryKey: ["mo-dashboard"] });
      setShowLog(false);
      setSuccess("Downtime event logged.");
      setTimeout(() => setSuccess(""), 4000);
    },
  });

  const list = data || [];
  const totalMin = list.reduce((s, d) => s + (Number(d.duration_minutes) || 0), 0);
  const totalCost = list.reduce((s, d) => s + (Number(d.cost_impact) || 0), 0);
  const repeats = list.filter((d) => d.repeat_occurrence).length;

  // Build class distribution for chart
  const classCount: Record<string, number> = {};
  list.forEach((d) => {
    const k = DOWNTIME_CLASS_LABELS[d.downtime_class] || d.downtime_class;
    classCount[k] = (classCount[k] || 0) + (Number(d.duration_minutes) || 0);
  });
  const chartData = Object.entries(classCount).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([name, value]) => ({ name, value: +value.toFixed(0) }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Downtime Intelligence Board</h1>
        </div>
        <button onClick={() => setShowLog(true)} className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700">+ Log Downtime</button>
      </div>

      {success && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{success}</div>}

      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Events", value: list.length },
          { label: "Total Downtime", value: `${totalMin.toFixed(0)} min`, color: totalMin > 120 ? "text-red-600" : "text-gray-900" },
          { label: "Repeat Events", value: repeats, color: repeats > 0 ? "text-orange-600" : "text-gray-700" },
          { label: "Est. Cost", value: `KES ${totalCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: "text-red-700" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-3 text-center">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-xl font-bold ${s.color || "text-gray-900"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-lg border p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Downtime by Classification (minutes)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 120 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={120} />
              <Tooltip />
              <Bar dataKey="value" name="Min" fill="#ef4444" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg border p-3 flex flex-wrap gap-3">
        <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">All Machines</option>
          {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code}</option>)}
        </select>
        <select value={filterClass} onChange={(e) => setFilterClass(e.target.value as any)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">All Classes</option>
          {DOWNTIME_CLASSES.map((c) => <option key={c} value={c}>{DOWNTIME_CLASS_LABELS[c] || c}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Machine", "Class", "Start", "Duration", "Root Cause", "Cost", "Flags"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {list.map((d) => (
              <tr key={d.id} className={`hover:bg-gray-50 ${d.repeat_occurrence ? "bg-orange-50" : ""}`}>
                <td className="px-4 py-2.5 font-mono text-xs">{d.machine_name || d.machine_id?.slice(0, 8)}</td>
                <td className="px-4 py-2.5 text-xs">{DOWNTIME_CLASS_LABELS[d.downtime_class] || d.downtime_class}</td>
                <td className="px-4 py-2.5 text-xs">{new Date(d.start_time).toLocaleString()}</td>
                <td className="px-4 py-2.5 text-xs font-medium">{d.duration_minutes ? `${Number(d.duration_minutes).toFixed(0)} min` : "—"}</td>
                <td className="px-4 py-2.5 text-xs max-w-48 truncate">{d.root_cause || "—"}</td>
                <td className="px-4 py-2.5 text-xs text-red-600">{d.cost_impact ? `KES ${Number(d.cost_impact).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—"}</td>
                <td className="px-4 py-2.5 text-xs space-x-1">
                  {d.repeat_occurrence && <span className="bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded text-xs">Repeat</span>}
                  {d.maintenance_escalated && <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-xs">Escalated</span>}
                </td>
              </tr>
            ))}
            {!isLoading && !list.length && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400 text-sm">No downtime events found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Log Downtime Modal */}
      {showLog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[480px] space-y-4">
            <h2 className="font-bold text-gray-900">Log Downtime Event</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Machine *</label>
              <select value={form.machine_id} onChange={(e) => setForm((p) => ({ ...p, machine_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— select machine —</option>
                {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code} — {m.machine_name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Downtime Class *</label>
              <select value={form.downtime_class} onChange={(e) => setForm((p) => ({ ...p, downtime_class: e.target.value as DowntimeClass }))} className="w-full border rounded px-3 py-2 text-sm">
                {DOWNTIME_CLASSES.map((c) => <option key={c} value={c}>{DOWNTIME_CLASS_LABELS[c] || c}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Start Time *</label>
                <input type="datetime-local" value={form.start_time} onChange={(e) => setForm((p) => ({ ...p, start_time: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">End Time</label>
                <input type="datetime-local" value={form.end_time} onChange={(e) => setForm((p) => ({ ...p, end_time: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Units Lost</label>
                <input type="number" value={form.units_lost} onChange={(e) => setForm((p) => ({ ...p, units_lost: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Root Cause</label>
              <textarea value={form.root_cause} onChange={(e) => setForm((p) => ({ ...p, root_cause: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm" placeholder="Describe root cause" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowLog(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => logDt.mutate()} disabled={!form.machine_id || !form.start_time} className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                {logDt.isPending ? "Logging…" : "Log Downtime"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
