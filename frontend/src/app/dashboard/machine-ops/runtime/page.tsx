"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, RuntimeLog, RuntimeActivity, Machine, ACTIVITY_COLORS } from "@/lib/machineOperator";

const ACTIVITIES: RuntimeActivity[] = ["SETUP", "RUNNING", "PAUSED", "IDLE", "DOWNTIME", "CLEANUP", "CHANGEOVER", "MAINTENANCE", "QC_WAIT"];

export default function RuntimePage() {
  const qc = useQueryClient();
  const [machineId, setMachineId] = useState("");
  const [showLog, setShowLog] = useState(false);
  const [form, setForm] = useState({
    machine_id: "", activity_type: "RUNNING" as RuntimeActivity,
    start_time: "", end_time: "", reason_code: "", notes: "",
  });
  const [success, setSuccess] = useState("");

  const { data: machines } = useQuery<Machine[]>({
    queryKey: ["mo-machines"],
    queryFn: () => moApi.listMachines(),
  });

  const { data, isLoading } = useQuery<RuntimeLog[]>({
    queryKey: ["mo-runtime", machineId],
    queryFn: () => moApi.listRuntime(machineId ? { machine_id: machineId } : {}),
  });

  const log = useMutation({
    mutationFn: () => moApi.logRuntime({
      machine_id: form.machine_id,
      activity_type: form.activity_type,
      start_time: form.start_time,
      end_time: form.end_time || undefined,
      reason_code: form.reason_code || undefined,
      notes: form.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mo-runtime"] });
      setShowLog(false);
      setSuccess("Runtime log created.");
      setTimeout(() => setSuccess(""), 3000);
    },
  });

  const logs = data || [];
  const totalByActivity: Record<string, number> = {};
  logs.forEach((l) => {
    const k = l.activity_type;
    totalByActivity[k] = (totalByActivity[k] || 0) + (Number(l.duration_minutes) || 0);
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
          <h1 className="text-xl font-bold text-gray-900">Machine Runtime Logs</h1>
        </div>
        <button onClick={() => setShowLog(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">+ Log Activity</button>
      </div>

      {success && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{success}</div>}

      {/* Activity Summary Bars */}
      {Object.keys(totalByActivity).length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-800 mb-3 text-sm">Activity Distribution (minutes)</h2>
          <div className="space-y-2">
            {ACTIVITIES.filter((a) => totalByActivity[a] > 0).map((a) => {
              const val = totalByActivity[a] || 0;
              const total = Object.values(totalByActivity).reduce((s, v) => s + v, 0);
              const pct = total > 0 ? (val / total) * 100 : 0;
              return (
                <div key={a} className="flex items-center gap-2">
                  <div className="w-24 text-xs text-gray-600">{a}</div>
                  <div className="flex-1 bg-gray-100 rounded-full h-4">
                    <div className={`h-4 rounded-full ${ACTIVITY_COLORS[a] || "bg-gray-400"}`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="w-20 text-xs text-gray-600 text-right">{val.toFixed(0)} min ({pct.toFixed(0)}%)</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border p-3 flex gap-3">
        <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="border rounded px-3 py-1.5 text-sm w-64">
          <option value="">All Machines</option>
          {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code} — {m.machine_name}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Machine", "Activity", "Start", "End", "Duration", "Reason", "Operator"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {logs.map((l) => (
              <tr key={l.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs">{l.machine_name || l.machine_id?.slice(0, 8)}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium text-white ${ACTIVITY_COLORS[l.activity_type] || "bg-gray-400"}`}>{l.activity_type}</span>
                </td>
                <td className="px-4 py-2.5 text-xs">{new Date(l.start_time).toLocaleString()}</td>
                <td className="px-4 py-2.5 text-xs">{l.end_time ? new Date(l.end_time).toLocaleString() : "—"}</td>
                <td className="px-4 py-2.5 text-xs font-medium">{l.duration_minutes ? `${Number(l.duration_minutes).toFixed(0)} min` : "—"}</td>
                <td className="px-4 py-2.5 text-xs">{l.reason_code || "—"}</td>
                <td className="px-4 py-2.5 text-xs">{l.operator_name || "—"}</td>
              </tr>
            ))}
            {!isLoading && !logs.length && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400 text-sm">No runtime logs found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showLog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[480px] space-y-4">
            <h2 className="font-bold text-gray-900">Log Machine Activity</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Machine *</label>
              <select value={form.machine_id} onChange={(e) => setForm((p) => ({ ...p, machine_id: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— select machine —</option>
                {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code} — {m.machine_name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Activity *</label>
              <select value={form.activity_type} onChange={(e) => setForm((p) => ({ ...p, activity_type: e.target.value as RuntimeActivity }))} className="w-full border rounded px-3 py-2 text-sm">
                {ACTIVITIES.map((a) => <option key={a}>{a}</option>)}
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
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Reason Code</label>
              <input value={form.reason_code} onChange={(e) => setForm((p) => ({ ...p, reason_code: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder="e.g. PLANNED_MAINTENANCE" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowLog(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={() => log.mutate()} disabled={!form.machine_id || !form.start_time} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {log.isPending ? "Logging…" : "Log Activity"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
