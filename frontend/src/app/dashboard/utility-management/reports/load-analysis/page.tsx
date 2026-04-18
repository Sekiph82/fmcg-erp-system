"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import { reportsApi } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const d30 = new Date(Date.now() - 30 * 86400_000).toISOString().slice(0, 10);
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;

const UTILITY_TYPES = ["", "ELECTRICITY", "WATER", "GAS", "STEAM", "COMPRESSED_AIR", "SOLAR"];

function DateFilter({ from, to, onFrom, onTo }: { from: string; to: string; onFrom: (v: string) => void; onTo: (v: string) => void }) {
  const ic = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";
  return (
    <div className="flex gap-3 items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
      <input type="date" className={ic} value={from} onChange={e => onFrom(e.target.value)} />
      <span className="text-gray-400 text-xs">to</span>
      <input type="date" className={ic} value={to} onChange={e => onTo(e.target.value)} />
    </div>
  );
}

function BaseLoadTab({ dateFrom, dateTo, utilityType }: { dateFrom: string; dateTo: string; utilityType: string }) {
  const params = { date_from: dateFrom, date_to: dateTo, ...(utilityType ? { utility_type: utilityType } : {}) };
  const q = useQuery({ queryKey: ["rpt-base-load", params], queryFn: () => reportsApi.baseLoad(params) });
  const d = q.data;

  const chartData = (d?.rows ?? []).map(r => ({
    utility: r.utility_type,
    min: r.min_daily, p10: r.p10_daily, p25: r.p25_daily,
    median: r.median_daily, mean: r.mean_daily, p75: r.p75_daily,
    p90: r.p90_daily, max: r.max_daily, base: r.base_load_est,
  }));

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Daily Consumption Distribution (by utility type)</h3>
          <button onClick={() => reportsApi.exportBaseLoad(params)} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="utility" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="min" name="Min" fill="#e2e8f0" radius={[2, 2, 0, 0]} />
            <Bar dataKey="p25" name="P25" fill="#a5b4fc" radius={[2, 2, 0, 0]} />
            <Bar dataKey="median" name="Median" fill="#818cf8" radius={[2, 2, 0, 0]} />
            <Bar dataKey="p75" name="P75" fill="#6366f1" radius={[2, 2, 0, 0]} />
            <Bar dataKey="max" name="Max" fill="#4338ca" radius={[2, 2, 0, 0]} />
            <Bar dataKey="base" name="Base Load Est." fill="#f97316" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Utility", "Unit", "Min", "P10", "P25", "Median", "Mean", "P75", "P90", "Max", "Base Load Est.", "Base Load %", "Base Cost"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-3 py-2 font-medium">{row.utility_type}</td>
                  <td className="px-3 py-2 text-gray-500">{row.unit ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.min_daily)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.p10_daily)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.p25_daily)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{fmt(row.median_daily)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.mean_daily)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.p75_daily)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.p90_daily)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.max_daily)}</td>
                  <td className="px-3 py-2 text-right font-semibold text-orange-600">{fmt(row.base_load_est)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.base_load_pct)}</td>
                  <td className="px-3 py-2 text-right">${fmt(row.cost_base_load, 2)}</td>
                </tr>
              ))}
              {!d?.rows.length && <tr><td colSpan={13} className="px-4 py-8 text-center text-gray-400">No data for selected range</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PeakDemandTab({ dateFrom, dateTo, utilityType }: { dateFrom: string; dateTo: string; utilityType: string }) {
  const [topN, setTopN] = useState(20);
  const params = { date_from: dateFrom, date_to: dateTo, top_n: topN, ...(utilityType ? { utility_type: utilityType } : {}) };
  const q = useQuery({ queryKey: ["rpt-peak-demand", params], queryFn: () => reportsApi.peakDemand(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border-2 border-orange-400 bg-orange-50 dark:bg-orange-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">Peak Date</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white mt-1">{d?.peak_date ?? "—"}</p>
        </div>
        <div className="rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <p className="text-xs font-medium text-gray-500">Peak Value</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {d?.peak_value == null ? "—" : fmt(d.peak_value)}
            {d?.peak_unit && <span className="text-sm font-normal text-gray-500 ml-1">{d.peak_unit}</span>}
          </p>
        </div>
        <div className="rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 col-span-2">
          <p className="text-xs font-medium text-gray-500">Utility</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{d?.utility_type ?? "ALL"}</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Peak Demand Trend</h3>
          <button onClick={() => reportsApi.exportPeakDemand(params)} className="px-3 py-1.5 text-xs bg-orange-600 text-white rounded-lg hover:bg-orange-700">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" name="Consumption" stroke="#f97316" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 flex justify-between border-b border-gray-100 dark:border-gray-700">
          <span className="text-xs text-gray-500">Top {topN} peak days</span>
          <select value={topN} onChange={e => setTopN(Number(e.target.value))}
            className="text-xs rounded border border-gray-300 px-2 py-1">
            {[10, 20, 30, 50].map(n => <option key={n} value={n}>Top {n}</option>)}
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Rank", "Date", "Utility", "Department", "Quantity", "Unit", "Cost", "Anomaly"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.top_days ?? []).map((row, i) => (
                <tr key={i} className={`hover:bg-gray-50 ${row.is_anomaly ? "bg-red-50/50 dark:bg-red-950/10" : ""}`}>
                  <td className="px-4 py-3 text-gray-400 font-mono">#{i + 1}</td>
                  <td className="px-4 py-3 font-mono text-xs">{row.date}</td>
                  <td className="px-4 py-3">{row.utility_type}</td>
                  <td className="px-4 py-3">{row.department ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-semibold">{fmt(row.quantity)}</td>
                  <td className="px-4 py-3 text-gray-500">{row.unit ?? "—"}</td>
                  <td className="px-4 py-3 text-right">${fmt(row.total_cost, 2)}</td>
                  <td className="px-4 py-3 text-center">{row.is_anomaly ? <span className="text-red-500 font-bold">⚠</span> : "—"}</td>
                </tr>
              ))}
              {!d?.top_days.length && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No data</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

type Tab = "base" | "peak";

export default function LoadAnalysisPage() {
  const [dateFrom, setDateFrom] = useState(d30);
  const [dateTo, setDateTo] = useState(today);
  const [tab, setTab] = useState<Tab>("base");
  const [utilityType, setUtilityType] = useState("");

  const sel = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/reports" className="text-sm text-gray-500 hover:text-blue-600">← Reports</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #818cf8", paddingLeft: 12 }}>
            Demand & Load Analysis
          </h1>
        </div>
        <div className="flex gap-3 flex-wrap items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
          <input type="date" className={sel} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span className="text-gray-400 text-xs">to</span>
          <input type="date" className={sel} value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <select className={sel} value={utilityType} onChange={e => setUtilityType(e.target.value)}>
            {UTILITY_TYPES.map(t => <option key={t} value={t}>{t || "All Utilities"}</option>)}
          </select>
        </div>
      </div>

      <div className="flex gap-2">
        {[{ id: "base" as Tab, label: "Base Load Analysis", color: "#818cf8" }, { id: "peak" as Tab, label: "Peak Demand", color: "#f97316" }].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.id ? "text-white" : "bg-white dark:bg-gray-800 text-gray-600 border border-gray-200 dark:border-gray-700"}`}
            style={tab === t.id ? { backgroundColor: t.color } : {}}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "base" && <BaseLoadTab dateFrom={dateFrom} dateTo={dateTo} utilityType={utilityType} />}
      {tab === "peak" && <PeakDemandTab dateFrom={dateFrom} dateTo={dateTo} utilityType={utilityType} />}
    </div>
  );
}
