"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { reportsApi } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;
const PIE_COLORS = ["#fbbf24", "#60a5fa", "#a78bfa", "#f97316", "#22d3ee", "#34d399", "#f43f5e"];

const GROUP_BY_OPTIONS = [
  { value: "department", label: "Department" },
  { value: "production_line", label: "Production Line" },
  { value: "machine_ref", label: "Machine" },
  { value: "product", label: "Product" },
  { value: "batch", label: "Batch" },
];

const UTILITY_TYPES = ["", "ELECTRICITY", "WATER", "GAS", "STEAM", "COMPRESSED_AIR", "SOLAR"];

export default function CostAllocationPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);
  const [groupBy, setGroupBy] = useState("department");
  const [utilityType, setUtilityType] = useState("");

  const params = {
    date_from: dateFrom, date_to: dateTo,
    group_by: groupBy,
    ...(utilityType ? { utility_type: utilityType } : {}),
  };

  const q = useQuery({
    queryKey: ["rpt-cost-allocation", params],
    queryFn: () => reportsApi.costAllocation(params),
  });
  const d = q.data;

  const ic = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/reports" className="text-sm text-gray-500 hover:text-blue-600">← Reports</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #f43f5e", paddingLeft: 12 }}>
            Cost Allocation Report
          </h1>
          <p className="text-sm text-gray-500 mt-1">Total: <strong>${fmt(d?.total_cost, 2)}</strong> — grouped by <strong>{GROUP_BY_OPTIONS.find(o => o.value === groupBy)?.label}</strong></p>
        </div>
        <div className="flex gap-3 items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3 flex-wrap">
          <input type="date" className={ic} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span className="text-gray-400 text-xs">to</span>
          <input type="date" className={ic} value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <select className={ic} value={groupBy} onChange={e => setGroupBy(e.target.value)}>
            {GROUP_BY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className={ic} value={utilityType} onChange={e => setUtilityType(e.target.value)}>
            {UTILITY_TYPES.map(t => <option key={t} value={t}>{t || "All Utilities"}</option>)}
          </select>
          <button onClick={() => reportsApi.exportCostAllocation(params)} className="px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">Export CSV</button>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-4">Cost by {GROUP_BY_OPTIONS.find(o => o.value === groupBy)?.label}</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={d?.rows ?? []} layout="vertical" margin={{ top: 4, right: 16, left: 80, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="dimension" tick={{ fontSize: 10 }} width={75} />
              <Tooltip formatter={(v: number) => [`$${v.toFixed(2)}`, "Allocated Cost"]} />
              <Bar dataKey="allocated_cost" name="Cost ($)" fill="#f43f5e" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-4">Cost by Utility Type</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={d?.by_utility ?? []} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={100}
                label={({ label, pct: p }) => `${label} ${p ? Number(p).toFixed(0) : ""}%`}>
                {(d?.by_utility ?? []).map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 text-xs text-gray-500">
          {d?.rows.length ?? 0} rows
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {[GROUP_BY_OPTIONS.find(o => o.value === groupBy)?.label ?? "Dimension", "Utility", "Allocated Cost", "Quantity", "Unit", "Cost/Unit", "Cost/Ton", "Prod Vol (kg)", "Alloc #", "% of Total"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-4 py-3 font-medium">{row.dimension}</td>
                  <td className="px-4 py-3">{row.utility_type ?? "ALL"}</td>
                  <td className="px-4 py-3 text-right font-mono">${fmt(row.allocated_cost, 2)}</td>
                  <td className="px-4 py-3 text-right">{fmt(row.allocated_quantity)}</td>
                  <td className="px-4 py-3 text-gray-500">{row.quantity_unit ?? "—"}</td>
                  <td className="px-4 py-3 text-right">{fmt(row.cost_per_unit, 4)}</td>
                  <td className="px-4 py-3 text-right">{fmt(row.cost_per_ton, 4)}</td>
                  <td className="px-4 py-3 text-right">{fmt(row.production_volume_kg, 0)}</td>
                  <td className="px-4 py-3 text-right">{row.allocation_count ?? "—"}</td>
                  <td className="px-4 py-3 text-right">{pct(row.pct_of_total)}</td>
                </tr>
              ))}
              {!d?.rows.length && (
                <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No allocations for selected range</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
