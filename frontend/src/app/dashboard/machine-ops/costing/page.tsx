"use client";

import { EntityPicker } from "@/components/EntityPicker";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { moApi, CostContribution } from "@/lib/machineOperator";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { tx } from "@/lib/i18n/core";

const COLORS = ["#6366f1", "#f59e0b", "#22c55e", "#ef4444", "#06b6d4", "#8b5cf6"];
const formatCost = (value?: number | null) => value == null
  ? "Unavailable"
  : Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function CostingPage() {
  const [orderId, setOrderId] = useState("");
  const [fetchId, setFetchId] = useState("");

  const { data, isLoading } = useQuery<CostContribution>({
    queryKey: ["mo-costing", fetchId],
    queryFn: () => moApi.getCosting(fetchId),
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
        <a href="/dashboard/machine-ops" className="text-sm text-indigo-600 hover:underline">{tx("← Dashboard")}</a>
        <h1 className="text-xl font-bold text-gray-900">{tx("Machine + Labor Cost Estimates")}</h1>
      </div>

      <div className="bg-white rounded-lg border p-4 flex gap-3 items-end">
        <div className="flex-1 max-w-md">
          <label className="block text-xs font-medium text-gray-600 mb-1">{tx("Production order")}</label>
          <EntityPicker kind="production_order" label={tx("Production order")} value={orderId} onChange={setOrderId} />
        </div>
        <button onClick={() => setFetchId(orderId)} disabled={!orderId} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">{tx("Load")}</button>
      </div>

      {isLoading && <div className="text-sm text-gray-400">{tx("Loading…")}</div>}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cost Breakdown */}
          <div className="bg-white rounded-lg border p-5 space-y-4">
            <h2 className="font-semibold text-gray-800">{tx("Estimated Cost Breakdown")}</h2>
            <div className="space-y-2">
              {[
                { label: tx("Machine Runtime Estimate"), value: data.machine_cost_runtime, hrs: data.machine_runtime_hours, color: "bg-indigo-500" },
                { label: tx("Machine Setup Estimate"), value: data.machine_cost_setup, hrs: data.machine_setup_hours, color: "bg-violet-500" },
                { label: tx("Machine Energy Estimate"), value: data.machine_cost_energy, hrs: null, color: "bg-blue-500" },
                { label: tx("Labor Direct"), value: data.labor_cost_direct, hrs: data.labor_direct_hours, color: "bg-green-500" },
                { label: tx("Labor Overtime"), value: data.labor_cost_overtime, hrs: data.labor_overtime_hours, color: "bg-red-500" },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${row.color}`} />
                  <div className="flex-1">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-700">{row.label}</span>
                      <span className="text-sm font-semibold text-gray-900">{formatCost(row.value)}</span>
                    </div>
                    {row.hrs !== null && <p className="text-xs text-gray-400">{Number(row.hrs).toFixed(2)} {tx("hrs")}</p>}
                  </div>
                </div>
              ))}
              <div className="border-t pt-2 flex justify-between font-bold">
                <span>{tx("Total estimate")}</span>
                <span className="text-indigo-700">{formatCost(data.total_cost)}</span>
              </div>
              {data.variance_pct != null && (
                <div className={`text-xs ${Number(data.variance_pct) > 0 ? "text-red-600" : "text-green-600"}`}>
                  {tx("Variance vs standard:")} {Number(data.variance_pct) > 0 ? "+" : ""}{Number(data.variance_pct).toFixed(2)}%
                </div>
              )}
            </div>
          </div>

          {/* Estimate coverage and source lineage */}
          <section className="bg-white rounded-lg border p-5 space-y-3 lg:col-span-2">
            <h2 className="font-semibold text-gray-800">{tx("Estimate coverage and source records")}</h2>
            <p className={`text-sm ${data.attribution_complete ? "text-green-700" : "text-amber-700"}`}>
              {data.attribution_complete ? tx("All linked sources have an estimate basis.") : tx("Attribution is incomplete; total estimate is withheld until source gaps are resolved.")}
            </p>
            <p className="text-xs text-gray-500">{data.cost_unit_note}</p>
            <div className="grid gap-4 md:grid-cols-2 text-xs text-gray-600">
              <div>
                <h3 className="font-medium text-gray-800 mb-1">{tx("Machine estimates")}</h3>
                {data.machine_attributions.map((line) => (
                  <p key={line.machine_id} className="mb-2">{line.machine_code}{tx(": run")} {line.runtime_hours} {tx("h; setup")} {line.setup_hours} {tx("h; estimate")} {formatCost(line.total_cost)}{tx("; runtime logs")} {line.source_runtime_log_ids.join(", ") || tx("none")}{line.unavailable_runtime_log_ids.length ? `; unavailable ${line.unavailable_runtime_log_ids.join(", ")}` : ""}{line.overlapping_runtime_log_ids.length ? `; overlaps ${line.overlapping_runtime_log_ids.join(", ")}` : ""}</p>
                ))}
                {!data.machine_attributions.length && <p>{tx("No linked runtime records.")}</p>}
              </div>
              <div>
                <h3 className="font-medium text-gray-800 mb-1">{tx("Labor source records")}</h3>
                {data.labor_attributions.map((line) => (
                  <p key={line.labor_log_id} className="mb-2">{line.labor_log_id}: {line.included ? `direct ${formatCost(line.direct_cost)}, overtime ${formatCost(line.overtime_cost)}` : line.exclusion_reason}</p>
                ))}
                {!data.labor_attributions.length && <p>{tx("No linked labor records.")}</p>}
              </div>
            </div>
            <ul className="list-disc pl-5 text-xs text-gray-500 space-y-1">{data.data_notes.map((note) => <li key={note}>{note}</li>)}</ul>
          </section>

          {/* Pie chart */}
          {pieData.length > 0 && (
            <div className="bg-white rounded-lg border p-5">
              <h2 className="font-semibold text-gray-800 mb-4">{tx("Estimate Distribution")}</h2>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(((percent as number) ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                    {pieData.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={((v: number) => formatCost(v)) as never} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
