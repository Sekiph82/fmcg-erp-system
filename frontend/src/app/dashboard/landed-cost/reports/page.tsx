"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { lcApi, fmtCurrency } from "@/lib/landed_cost";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from "recharts";

const COLORS = ["#3b82f6","#f97316","#10b981","#8b5cf6","#ef4444","#eab308","#06b6d4","#ec4899"];

export default function LandedCostReports() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo]     = useState("");

  const params = {
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo   ? { date_to: dateTo }     : {}),
  };

  const { data: byType = [], isLoading: l1 } = useQuery<Record<string, unknown>[]>({
    queryKey: ["lc-report-type", dateFrom, dateTo],
    queryFn: () => lcApi.reportCostByType(params),
  });

  const { data: byMat = [], isLoading: l2 } = useQuery<Record<string, unknown>[]>({
    queryKey: ["lc-report-mat", dateFrom, dateTo],
    queryFn: () => lcApi.reportAllocationByMaterial(params),
  });

  const chartTypeData = byType.map((r) => ({
    name: String(r.cost_type).replace(/_/g, " "),
    total: Number(r.total_amount),
    pct: Number(r.pct_of_total),
  }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Landed Cost Reports</h1>

      {/* Date filters */}
      <div className="flex gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Bill Date From</label>
          <input type="date" className="border rounded-lg px-3 py-1.5 text-sm"
            value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Bill Date To</label>
          <input type="date" className="border rounded-lg px-3 py-1.5 text-sm"
            value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        {(dateFrom || dateTo) && (
          <button onClick={() => { setDateFrom(""); setDateTo(""); }}
            className="text-xs text-gray-500 hover:underline">
            Clear
          </button>
        )}
      </div>

      {/* Cost by Type */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Cost by Type (Posted)</h2>
        {l1 ? <p className="text-sm text-gray-400">Loading…</p> : byType.length === 0 ? (
          <p className="text-sm text-gray-400">No data.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartTypeData}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                <Bar dataKey="total" radius={[4, 4, 0, 0]}>
                  {chartTypeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={chartTypeData} dataKey="total" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {chartTypeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Legend />
                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
        {byType.length > 0 && (
          <table className="w-full text-sm mt-4">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Cost Type", "Total Amount", "# Docs", "% of Total"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {byType.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs font-medium">{String(r.cost_type).replace(/_/g, " ")}</td>
                  <td className="px-4 py-2 font-semibold">{fmtCurrency(Number(r.total_amount))}</td>
                  <td className="px-4 py-2 text-gray-600">{String(r.doc_count)}</td>
                  <td className="px-4 py-2 text-gray-600">{Number(r.pct_of_total).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Allocation by Material */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Allocation by Material (Posted)</h2>
        {l2 ? <p className="text-sm text-gray-400">Loading…</p> : byMat.length === 0 ? (
          <p className="text-sm text-gray-400">No data.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Material", "Total Allocated", "# Docs", "Avg Per Unit"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {byMat.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs">{String(r.material_name ?? "—")}</td>
                  <td className="px-4 py-2 font-semibold">{fmtCurrency(Number(r.total_allocated))}</td>
                  <td className="px-4 py-2 text-gray-600">{String(r.doc_count)}</td>
                  <td className="px-4 py-2 text-gray-600">{r.avg_per_unit != null ? Number(r.avg_per_unit).toFixed(4) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
