"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, PerformanceSnapshot, Machine } from "@/lib/machineOperator";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

function OEEBadge({ oee }: { oee?: number | null }) {
  if (oee == null) return <span className="text-xs text-gray-400">—</span>;
  const pct = Number(oee) * 100;
  const cls = pct >= 85 ? "bg-green-100 text-green-700" : pct >= 65 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700";
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{pct.toFixed(1)}%</span>;
}

export default function PerformancePage() {
  const qc = useQueryClient();
  const [machineId, setMachineId] = useState("");

  const { data: machines } = useQuery<Machine[]>({
    queryKey: ["mo-machines"],
    queryFn: () => moApi.listMachines().then((r) => r.data),
  });

  const { data: snapshots, isLoading } = useQuery<PerformanceSnapshot[]>({
    queryKey: ["mo-performance", machineId],
    queryFn: () => moApi.listPerformance(machineId ? { machine_id: machineId } : {}).then((r) => r.data),
  });

  const compute = useMutation({
    mutationFn: () => moApi.computePerformance(machineId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mo-performance"] }),
  });

  const snaps = (snapshots || []).slice(0, 30).reverse();
  const chartData = snaps.map((s) => ({
    date: s.snapshot_date,
    oee: s.oee ? +(Number(s.oee) * 100).toFixed(1) : null,
    availability: s.availability ? +(Number(s.availability) * 100).toFixed(1) : null,
    performance: s.performance ? +(Number(s.performance) * 100).toFixed(1) : null,
    quality: s.quality_rate ? +(Number(s.quality_rate) * 100).toFixed(1) : null,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Machine Performance (OEE)</h1>
      </div>

      <div className="bg-white rounded-lg border p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Machine</label>
          <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="border rounded px-3 py-2 text-sm w-64">
            <option value="">All Machines</option>
            {(machines || []).map((m) => <option key={m.id} value={m.id}>{m.machine_code} — {m.machine_name}</option>)}
          </select>
        </div>
        {machineId && (
          <button onClick={() => compute.mutate()} disabled={compute.isPending} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
            {compute.isPending ? "Computing…" : "Compute Today"}
          </button>
        )}
      </div>

      {/* OEE Trend Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-lg border p-5">
          <h2 className="font-semibold text-gray-800 mb-4">OEE Trend (last 30 days)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
              <Tooltip formatter={(v: number) => `${v}%`} />
              <ReferenceLine y={85} stroke="#22c55e" strokeDasharray="4 4" label={{ value: "World Class 85%", fill: "#22c55e", fontSize: 10 }} />
              <ReferenceLine y={65} stroke="#f59e0b" strokeDasharray="4 4" />
              <Bar dataKey="oee" name="OEE" fill="#6366f1" radius={[3, 3, 0, 0]} />
              <Bar dataKey="availability" name="Availability" fill="#22c55e" radius={[3, 3, 0, 0]} />
              <Bar dataKey="performance" name="Performance" fill="#f59e0b" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading && <div className="p-6 text-gray-400 text-sm">Loading…</div>}
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{["Date", "Machine", "Planned", "Run", "Setup", "Downtime", "Changeover", "Units", "Good", "Avail", "Perf", "Quality", "OEE", "Cost", "Flags"].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-600 whitespace-nowrap">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y">
            {(snapshots || []).map((s) => (
              <tr key={s.id} className={`hover:bg-gray-50 ${s.anomaly_flag ? "bg-red-50" : ""}`}>
                <td className="px-3 py-2 text-xs font-medium">{s.snapshot_date}</td>
                <td className="px-3 py-2 text-xs font-mono">{s.machine_code || s.machine_id?.slice(0, 8)}</td>
                <td className="px-3 py-2 text-xs">{s.planned_time_min} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.run_time_min).toFixed(0)} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.setup_time_min).toFixed(0)} min</td>
                <td className={`px-3 py-2 text-xs font-medium ${s.high_downtime_flag ? "text-red-600" : ""}`}>{Number(s.downtime_min).toFixed(0)} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.changeover_time_min).toFixed(0)} min</td>
                <td className="px-3 py-2 text-xs">{Number(s.units_produced).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs">{Number(s.good_units).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs">{s.availability ? `${(Number(s.availability) * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-3 py-2 text-xs">{s.performance ? `${(Number(s.performance) * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-3 py-2 text-xs">{s.quality_rate ? `${(Number(s.quality_rate) * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-3 py-2"><OEEBadge oee={s.oee} /></td>
                <td className="px-3 py-2 text-xs">{s.machine_cost_actual ? `KES ${Number(s.machine_cost_actual).toLocaleString()}` : "—"}</td>
                <td className="px-3 py-2 text-xs">
                  {s.low_oee_flag && <span className="bg-red-100 text-red-700 text-xs px-1.5 py-0.5 rounded mr-1">Low OEE</span>}
                  {s.high_downtime_flag && <span className="bg-orange-100 text-orange-700 text-xs px-1.5 py-0.5 rounded">Hi DT</span>}
                </td>
              </tr>
            ))}
            {!isLoading && !(snapshots?.length) && (
              <tr><td colSpan={15} className="px-4 py-8 text-center text-gray-400 text-sm">No performance snapshots. Select a machine and click "Compute Today".</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
