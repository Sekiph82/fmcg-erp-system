"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  productionCostApi, fmtKES,
  VarianceDetailRow, WorkCenterUtilRow,
} from "@/lib/productionCosting";

const today = new Date().toISOString().slice(0, 10);
const monthAgo = new Date(Date.now() - 30 * 86400 * 1000).toISOString().slice(0, 10);

function VarCell({ value }: { value: number }) {
  const color = value > 0 ? "text-red-600" : value < 0 ? "text-emerald-600" : "text-gray-500";
  return <span className={`font-semibold ${color}`}>{value > 0 ? "+" : ""}{fmtKES(value)}</span>;
}

function UtilBar({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-gray-400">—</span>;
  const clamp = Math.min(pct, 100);
  const color = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-400" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${clamp}%` }} />
      </div>
      <span className={`text-xs font-medium ${pct >= 90 ? "text-red-600" : pct >= 70 ? "text-amber-600" : "text-gray-600"}`}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

export default function VariancePage() {
  const [dateFrom, setDateFrom] = useState(monthAgo);
  const [dateTo, setDateTo] = useState(today);
  const [tab, setTab] = useState<"variance" | "utilization">("variance");

  const { data: varRows = [], isLoading: varLoading } = useQuery({
    queryKey: ["variance-detail", dateFrom, dateTo],
    queryFn: () => productionCostApi.varianceDetail({ date_from: dateFrom, date_to: dateTo }),
    enabled: tab === "variance",
  });

  const { data: utilRows = [], isLoading: utilLoading } = useQuery({
    queryKey: ["wc-util", dateFrom, dateTo],
    queryFn: () => productionCostApi.workCenterUtilization(dateFrom, dateTo),
    enabled: tab === "utilization",
  });

  const totalVarMat = varRows.reduce((s, r) => s + r.material_variance, 0);
  const totalVarLab = varRows.reduce((s, r) => s + r.labor_variance, 0);
  const totalVarMach = varRows.reduce((s, r) => s + r.machine_variance, 0);
  const totalVar = varRows.reduce((s, r) => s + r.total_variance, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Production Variance & Capacity</h1>
        <p className="text-sm text-gray-500 mt-1">Standard vs actual cost by component · work center utilization</p>
      </div>

      {/* Date filters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">From</label>
          <input type="date" className="border rounded px-3 py-1.5 text-sm" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">To</label>
          <input type="date" className="border rounded px-3 py-1.5 text-sm" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["variance", "utilization"] as const).map((t) => (
          <button
            key={t}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px capitalize ${tab === t ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            onClick={() => setTab(t)}
          >
            {t === "variance" ? "Variance Detail" : "Work Center Utilization"}
          </button>
        ))}
      </div>

      {tab === "variance" && (
        <>
          {/* Variance summary */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Material Variance", value: totalVarMat },
              { label: "Labor Variance",    value: totalVarLab },
              { label: "Machine Variance",  value: totalVarMach },
              { label: "Total Variance",    value: totalVar },
            ].map((k) => (
              <div key={k.label} className="bg-white rounded-lg border p-4">
                <p className="text-xs text-gray-500 mb-1">{k.label}</p>
                <VarCell value={k.value} />
              </div>
            ))}
          </div>

          <div className="bg-white rounded-lg border overflow-x-auto">
            <div className="px-5 py-3 border-b font-semibold text-gray-800">
              Order-Level Variance ({varRows.length} orders)
            </div>
            {varLoading ? (
              <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
            ) : (
              <table className="w-full text-sm min-w-[900px]">
                <thead>
                  <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                    <th className="px-4 py-2 text-left">Order</th>
                    <th className="px-4 py-2 text-left">Product</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-right">Std Mat</th>
                    <th className="px-4 py-2 text-right">Act Mat</th>
                    <th className="px-4 py-2 text-right">Mat Var</th>
                    <th className="px-4 py-2 text-right">Std Labor</th>
                    <th className="px-4 py-2 text-right">Act Labor</th>
                    <th className="px-4 py-2 text-right">Labor Var</th>
                    <th className="px-4 py-2 text-right">Total Var</th>
                    <th className="px-4 py-2 text-right">Var %</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {varRows.map((r) => (
                    <tr key={r.order_id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-indigo-700">{r.order_no}</td>
                      <td className="px-4 py-2 text-gray-700">{r.product_name ?? "—"}</td>
                      <td className="px-4 py-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${r.status === "COMPLETED" ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right text-gray-500">{fmtKES(r.std_material_cost)}</td>
                      <td className="px-4 py-2 text-right text-gray-500">{fmtKES(r.actual_material_cost)}</td>
                      <td className="px-4 py-2 text-right"><VarCell value={r.material_variance} /></td>
                      <td className="px-4 py-2 text-right text-gray-500">{fmtKES(r.std_labor_cost)}</td>
                      <td className="px-4 py-2 text-right text-gray-500">{fmtKES(r.actual_labor_cost)}</td>
                      <td className="px-4 py-2 text-right"><VarCell value={r.labor_variance} /></td>
                      <td className="px-4 py-2 text-right"><VarCell value={r.total_variance} /></td>
                      <td className={`px-4 py-2 text-right text-xs font-medium ${(r.variance_pct ?? 0) > 5 ? "text-red-600" : (r.variance_pct ?? 0) < -5 ? "text-emerald-600" : "text-gray-500"}`}>
                        {r.variance_pct != null ? `${r.variance_pct > 0 ? "+" : ""}${r.variance_pct.toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  ))}
                  {varRows.length === 0 && (
                    <tr><td colSpan={11} className="px-5 py-8 text-center text-gray-400">No variance data for selected period</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {tab === "utilization" && (
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b font-semibold text-gray-800">
            Work Center Utilization — {dateFrom} to {dateTo}
          </div>
          {utilLoading ? (
            <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-4 py-2 text-left">Work Center</th>
                  <th className="px-4 py-2 text-left">Code</th>
                  <th className="px-4 py-2 text-right">Capacity Hrs</th>
                  <th className="px-4 py-2 text-right">Actual Hrs</th>
                  <th className="px-4 py-2 text-left">Utilization</th>
                  <th className="px-4 py-2 text-right">Orders</th>
                  <th className="px-4 py-2 text-right">Labor Cost</th>
                  <th className="px-4 py-2 text-right">Machine Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {utilRows.map((r) => (
                  <tr key={r.work_center_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-800">{r.work_center_name}</td>
                    <td className="px-4 py-2.5 font-mono text-gray-500 text-xs">{r.work_center_code}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{r.capacity_hours?.toFixed(0) ?? "—"} h</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{r.actual_hours_used.toFixed(1)} h</td>
                    <td className="px-4 py-2.5"><UtilBar pct={r.utilization_pct} /></td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{r.completed_orders}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.labor_cost_incurred)}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{fmtKES(r.machine_cost_incurred)}</td>
                  </tr>
                ))}
                {utilRows.length === 0 && (
                  <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No work center data for selected period</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
