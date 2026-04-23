"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, CostContribution } from "@/lib/machineOperator";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

const COLORS = ["#6366f1", "#f59e0b", "#22c55e", "#ef4444", "#06b6d4", "#8b5cf6"];

export default function CostingPage() {
  const [orderId, setOrderId] = useState("");
  const [fetchId, setFetchId] = useState("");

  const { data, isLoading } = useQuery<CostContribution>({
    queryKey: ["mo-costing", fetchId],
    queryFn: () => moApi.getCosting(fetchId).then((r) => r.data),
    enabled: !!fetchId,
  });

  const pieData = data ? [
    { name: "Machine Runtime", value: Number(data.machine_cost_runtime) },
    { name: "Machine Setup", value: Number(data.machine_cost_setup) },
    { name: "Machine Energy", value: Number(data.machine_cost_energy) },
    { name: "Labor Direct", value: Number(data.labor_cost_direct) },
    { name: "Labor Overtime", value: Number(data.labor_cost_overtime) },
  ].filter((p) => p.value > 0) : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Machine + Labor Cost Contribution</h1>
      </div>

      <div className="bg-white rounded-lg border p-4 flex gap-3 items-end">
        <div className="flex-1 max-w-md">
          <label className="block text-xs font-medium text-gray-600 mb-1">Production Order ID</label>
          <input value={orderId} onChange={(e) => setOrderId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" placeholder="UUID" />
        </div>
        <button onClick={() => setFetchId(orderId)} disabled={!orderId} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">Load</button>
      </div>

      {isLoading && <div className="text-sm text-gray-400">Loading…</div>}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cost Breakdown */}
          <div className="bg-white rounded-lg border p-5 space-y-4">
            <h2 className="font-semibold text-gray-800">Cost Breakdown</h2>
            <div className="space-y-2">
              {[
                { label: "Machine Runtime", value: data.machine_cost_runtime, hrs: data.machine_runtime_hours, color: "bg-indigo-500" },
                { label: "Machine Setup", value: data.machine_cost_setup, hrs: data.machine_setup_hours, color: "bg-violet-500" },
                { label: "Machine Energy", value: data.machine_cost_energy, hrs: null, color: "bg-blue-500" },
                { label: "Labor Direct", value: data.labor_cost_direct, hrs: data.labor_direct_hours, color: "bg-green-500" },
                { label: "Labor Overtime", value: data.labor_cost_overtime, hrs: data.labor_overtime_hours, color: "bg-red-500" },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${row.color}`} />
                  <div className="flex-1">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-700">{row.label}</span>
                      <span className="text-sm font-semibold text-gray-900">KES {Number(row.value).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                    {row.hrs !== null && <p className="text-xs text-gray-400">{Number(row.hrs).toFixed(2)} hrs</p>}
                  </div>
                </div>
              ))}
              <div className="border-t pt-2 flex justify-between font-bold">
                <span>Total Cost</span>
                <span className="text-indigo-700">KES {Number(data.total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </div>
              {data.variance_pct != null && (
                <div className={`text-xs ${Number(data.variance_pct) > 0 ? "text-red-600" : "text-green-600"}`}>
                  Variance vs standard: {Number(data.variance_pct) > 0 ? "+" : ""}{Number(data.variance_pct).toFixed(2)}%
                </div>
              )}
            </div>
          </div>

          {/* Pie chart */}
          {pieData.length > 0 && (
            <div className="bg-white rounded-lg border p-5">
              <h2 className="font-semibold text-gray-800 mb-4">Cost Distribution</h2>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                    {pieData.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => `KES ${v.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
