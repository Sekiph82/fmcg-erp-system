"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from "recharts";
import { kpiApi, type DailyTrendPoint } from "@/lib/utilityKpi";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) => n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;

function KpiCard({ label, value, unit, sub, highlight, warn }: { label: string; value: string; unit?: string; sub?: string; highlight?: boolean; warn?: boolean }) {
  const border = highlight ? "border-green-400 bg-green-50 dark:bg-green-950/20" : warn ? "border-amber-400 bg-amber-50 dark:bg-amber-950/20" : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800";
  return (
    <div className={`rounded-xl border-2 p-4 ${border}`}>
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{value}{unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

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

export default function WaterKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-water", dateFrom, dateTo],
    queryFn: () => kpiApi.water({ date_from: dateFrom, date_to: dateTo }),
  });

  const trendQ = useQuery({
    queryKey: ["kpi-trend-water", dateFrom, dateTo],
    queryFn: () => kpiApi.dailyTrend({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;
  const trend = trendQ.data ?? [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header with back links */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/water" className="text-sm text-blue-600 hover:underline">Operational Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #60a5fa", paddingLeft: 12 }}>Water KPI Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Track water consumption, process allocation, cost per m³, and production efficiency for the selected period.</p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* KPI cards grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Water m³ Total"
          value={fmt(kpi?.water_m3_total, 1)}
          unit="m³"
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="Process Water m³"
          value={fmt(kpi?.process_water_m3, 1)}
          unit="m³"
        />
        <KpiCard
          label="Total Cost"
          value={fmt(kpi?.total_cost, 2)}
          unit="$"
        />
        <KpiCard
          label="Cost per m³"
          value={fmt(kpi?.cost_per_m3, 4)}
          unit="$/m³"
        />
        <KpiCard
          label="m³ / Ton"
          value={fmt(kpi?.water_m3_per_ton, 3)}
          unit="m³/t"
        />
        <KpiCard
          label="Estimated %"
          value={pct(kpi?.estimated_pct)}
          warn={(kpi?.estimated_pct ?? 0) > 20}
        />
        <KpiCard
          label="Anomaly Count"
          value={kpi?.anomaly_count == null ? "—" : String(kpi.anomaly_count)}
          warn={(kpi?.anomaly_count ?? 0) > 0}
        />
      </div>

      {/* Trend chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Water KPI Dashboard — Daily Trend</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="water_m3" name="Water (m³)" stroke="#60a5fa" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
