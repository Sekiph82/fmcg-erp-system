"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { kpiApi } from "@/lib/utilityKpi";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) => n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;

function KpiCard({ label, value, unit, sub, highlight, warn, critical }: {
  label: string; value: string; unit?: string; sub?: string;
  highlight?: boolean; warn?: boolean; critical?: boolean;
}) {
  const border = critical
    ? "border-red-400 bg-red-50 dark:bg-red-950/20"
    : warn
    ? "border-amber-400 bg-amber-50 dark:bg-amber-950/20"
    : highlight
    ? "border-green-400 bg-green-50 dark:bg-green-950/20"
    : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800";
  return (
    <div className={`rounded-xl border-2 p-4 ${border}`}>
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
        {value}{unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
      </p>
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

export default function CompressorKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-compressor", dateFrom, dateTo],
    queryFn: () => kpiApi.compressor({ date_from: dateFrom, date_to: dateTo }),
  });

  const trendQ = useQuery({
    queryKey: ["kpi-trend-compressor", dateFrom, dateTo],
    queryFn: () => kpiApi.dailyTrend({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;
  const trend = trendQ.data ?? [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/compressor" className="text-sm text-blue-600 hover:underline">Operational Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #22d3ee", paddingLeft: 12 }}>
            Compressed Air KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Monitor air generation efficiency, leak estimation, and compressor energy intensity.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Air Generated"
          value={fmt(kpi?.air_nm3_total, 1)}
          unit="Nm³"
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="Electricity Used"
          value={fmt(kpi?.electricity_kwh_total, 1)}
          unit="kWh"
        />
        <KpiCard
          label="Energy Intensity"
          value={fmt(kpi?.air_kwh_per_nm3, 4)}
          unit="kWh/Nm³"
          warn={(kpi?.air_kwh_per_nm3 ?? 0) > 0.12}
          critical={(kpi?.air_kwh_per_nm3 ?? 0) > 0.18}
          highlight={(kpi?.air_kwh_per_nm3 ?? 0) > 0 && (kpi?.air_kwh_per_nm3 ?? 0) <= 0.10}
        />
        <KpiCard
          label="Leak Estimate"
          value={pct(kpi?.leak_estimate_pct)}
          highlight={(kpi?.leak_estimate_pct ?? 0) > 0 && (kpi?.leak_estimate_pct ?? 0) <= 5}
          warn={(kpi?.leak_estimate_pct ?? 0) > 10}
          critical={(kpi?.leak_estimate_pct ?? 0) > 20}
        />
        <KpiCard
          label="Night Idle Consumption"
          value={fmt(kpi?.night_idle_kwh, 1)}
          unit="kWh"
          warn={(kpi?.night_idle_kwh ?? 0) > 200}
        />
        <KpiCard
          label="Avg Compressor Load"
          value={pct(kpi?.avg_load_pct)}
          highlight={(kpi?.avg_load_pct ?? 0) >= 70}
          warn={(kpi?.avg_load_pct ?? 0) < 50 && (kpi?.avg_load_pct ?? 0) > 0}
        />
        <KpiCard
          label="Runtime Hours"
          value={fmt(kpi?.runtime_hours, 1)}
          unit="h"
        />
        <KpiCard
          label="Anomaly Count"
          value={kpi?.anomaly_count == null ? "—" : String(kpi.anomaly_count)}
          warn={(kpi?.anomaly_count ?? 0) > 0}
          critical={(kpi?.anomaly_count ?? 0) > 3}
        />
      </div>

      {/* Alerts */}
      {((kpi?.leak_estimate_pct ?? 0) > 10 || (kpi?.air_kwh_per_nm3 ?? 0) > 0.15) && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-700 p-4 flex gap-3 items-start">
          <span className="text-amber-500 text-lg">⚠</span>
          <div className="text-sm">
            <p className="font-semibold text-amber-800 dark:text-amber-300">Efficiency Warning</p>
            <ul className="list-disc list-inside mt-1 text-amber-700 dark:text-amber-400 space-y-0.5">
              {(kpi?.leak_estimate_pct ?? 0) > 10 && (
                <li>Leak estimate {pct(kpi?.leak_estimate_pct)} exceeds 10% threshold — inspect distribution lines</li>
              )}
              {(kpi?.air_kwh_per_nm3 ?? 0) > 0.15 && (
                <li>Energy intensity {fmt(kpi?.air_kwh_per_nm3, 4)} kWh/Nm³ is above target — check compressor condition</li>
              )}
            </ul>
          </div>
        </div>
      )}

      {/* Trend chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Compressed Air & Electricity Daily Trend</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="compressed_air_nm3" name="Compressed Air (Nm³)" stroke="#22d3ee" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="electricity_kwh" name="Electricity (kWh)" stroke="#fbbf24" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
