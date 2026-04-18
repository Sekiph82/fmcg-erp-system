"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { reportsApi } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const ytdStart = today.slice(0, 4) + "-01-01";
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;

const TREND_ICON: Record<string, string> = { up: "↑", down: "↓", stable: "→" };
const TREND_COLOR: Record<string, string> = { up: "text-green-600", down: "text-red-500", stable: "text-gray-400" };

export default function SustainabilityPage() {
  const [dateFrom, setDateFrom] = useState(ytdStart);
  const [dateTo, setDateTo] = useState(today);

  const q = useQuery({
    queryKey: ["rpt-sustainability", dateFrom, dateTo],
    queryFn: () => reportsApi.sustainability({ date_from: dateFrom, date_to: dateTo }),
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #22c55e", paddingLeft: 12 }}>
            Sustainability Summary
          </h1>
          <p className="text-sm text-gray-500 mt-1">{dateFrom} — {dateTo}</p>
        </div>
        <div className="flex gap-3 items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3 flex-wrap">
          <input type="date" className={ic} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span className="text-gray-400 text-xs">to</span>
          <input type="date" className={ic} value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <button onClick={() => reportsApi.exportSustainability({ date_from: dateFrom, date_to: dateTo })}
            className="px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">Export CSV</button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="rounded-xl border-2 border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">⚡ Electricity</p>
          <p className="text-xl font-bold text-yellow-700 mt-1">{fmt(d?.total_electricity_kwh, 0)}<span className="text-sm font-normal text-gray-500 ml-1">kWh</span></p>
        </div>
        <div className="rounded-xl border-2 border-yellow-300 bg-yellow-50/50 dark:bg-yellow-950/10 p-4">
          <p className="text-xs font-medium text-gray-500">☀️ Solar</p>
          <p className="text-xl font-bold text-yellow-600 mt-1">{fmt(d?.solar_kwh, 0)}<span className="text-sm font-normal text-gray-500 ml-1">kWh</span></p>
          <p className="text-xs text-yellow-600 mt-1">{pct(d?.solar_pct)} of total</p>
        </div>
        <div className="rounded-xl border-2 border-blue-400 bg-blue-50 dark:bg-blue-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">💧 Water</p>
          <p className="text-xl font-bold text-blue-700 mt-1">{fmt(d?.total_water_m3)}<span className="text-sm font-normal text-gray-500 ml-1">m³</span></p>
        </div>
        <div className="rounded-xl border-2 border-teal-400 bg-teal-50 dark:bg-teal-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">♻️ Wastewater Treated</p>
          <p className="text-xl font-bold text-teal-700 mt-1">{fmt(d?.wastewater_treated_m3)}<span className="text-sm font-normal text-gray-500 ml-1">m³</span></p>
          <p className="text-xs text-teal-600 mt-1">Compliance: {pct(d?.compliance_rate_pct)}</p>
        </div>
        <div className="rounded-xl border-2 border-gray-400 bg-gray-50 dark:bg-gray-700/30 p-4">
          <p className="text-xs font-medium text-gray-500">🌿 Est. CO₂e</p>
          <p className="text-xl font-bold text-gray-700 dark:text-gray-200 mt-1">{fmt(d?.estimated_co2e_kg, 0)}<span className="text-sm font-normal text-gray-500 ml-1">kg</span></p>
          <p className="text-xs text-gray-400 mt-1">0.7 kgCO₂e/kWh grid factor</p>
        </div>
      </div>

      {/* Cost card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500">Total Utility Cost</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
              ${fmt(d?.total_utility_cost, 2)}
            </p>
          </div>
          <div className="text-5xl">💰</div>
        </div>
      </div>

      {/* Trend chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold mb-4">Sustainability Trend</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" name="Electricity (kWh)" stroke="#fbbf24" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="value2" name="Cost ($)" stroke="#f43f5e" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Metrics grid */}
      {d?.metrics && d.metrics.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-sm font-semibold mb-4">Sustainability Metrics</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {d.metrics.map((m, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                <div>
                  <p className="text-xs text-gray-500">{m.label}</p>
                  <p className="text-base font-semibold text-gray-900 dark:text-white">
                    {m.value == null ? "—" : `${m.value}`} {m.unit}
                  </p>
                  {m.benchmark && <p className="text-xs text-gray-400">Benchmark: {m.benchmark} {m.unit}</p>}
                </div>
                {m.trend && (
                  <span className={`text-lg font-bold ${TREND_COLOR[m.trend] ?? "text-gray-400"}`}>
                    {TREND_ICON[m.trend] ?? ""}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
