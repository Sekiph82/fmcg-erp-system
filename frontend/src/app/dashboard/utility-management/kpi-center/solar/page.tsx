"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area } from "recharts";
import { kpiApi } from "@/lib/utilityKpi";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) => n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;

function KpiCard({ label, value, unit, sub, highlight, warn, badge }: {
  label: string; value: string; unit?: string; sub?: string;
  highlight?: boolean; warn?: boolean; badge?: string;
}) {
  const border = warn
    ? "border-amber-400 bg-amber-50 dark:bg-amber-950/20"
    : highlight
    ? "border-green-400 bg-green-50 dark:bg-green-950/20"
    : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800";
  return (
    <div className={`rounded-xl border-2 p-4 ${border}`}>
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
        {badge && <span className="text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 px-1.5 py-0.5 rounded font-medium">{badge}</span>}
      </div>
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

export default function SolarKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-solar", dateFrom, dateTo],
    queryFn: () => kpiApi.solar({ date_from: dateFrom, date_to: dateTo }),
  });

  const trendQ = useQuery({
    queryKey: ["kpi-trend-solar", dateFrom, dateTo],
    queryFn: () => kpiApi.dailyTrend({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;
  const trend = trendQ.data ?? [];

  // Compute self-consumption rate from kpi
  const selfConsumptionRate = kpi?.kwh_generated && kpi.kwh_self_consumed
    ? (kpi.kwh_self_consumed / kpi.kwh_generated) * 100
    : null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/solar" className="text-sm text-blue-600 hover:underline">Operational Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #facc15", paddingLeft: 12 }}>
            Solar Energy KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track solar generation, self-consumption, performance ratio, and grid contribution.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Generated"
          value={fmt(kpi?.kwh_generated, 1)}
          unit="kWh"
          sub={`${dateFrom} – ${dateTo}`}
          highlight={(kpi?.kwh_generated ?? 0) > 0}
          badge="Solar"
        />
        <KpiCard
          label="Self Consumed"
          value={fmt(kpi?.kwh_self_consumed, 1)}
          unit="kWh"
        />
        <KpiCard
          label="Exported to Grid"
          value={fmt(kpi?.kwh_exported, 1)}
          unit="kWh"
        />
        <KpiCard
          label="Solar Contribution"
          value={pct(kpi?.solar_contribution_pct)}
          highlight={(kpi?.solar_contribution_pct ?? 0) >= 15}
          warn={(kpi?.solar_contribution_pct ?? 0) < 5 && (kpi?.solar_contribution_pct ?? 0) > 0}
        />
        <KpiCard
          label="Self-Consumption Rate"
          value={pct(selfConsumptionRate)}
          highlight={(selfConsumptionRate ?? 0) >= 80}
          warn={(selfConsumptionRate ?? 0) < 50 && (selfConsumptionRate ?? 0) > 0}
        />
        <KpiCard
          label="Performance Ratio (PR)"
          value={fmt(kpi?.avg_pr_ratio, 3)}
          highlight={(kpi?.avg_pr_ratio ?? 0) >= 0.75}
          warn={(kpi?.avg_pr_ratio ?? 0) < 0.65 && (kpi?.avg_pr_ratio ?? 0) > 0}
        />
        <KpiCard
          label="Capacity Factor"
          value={pct(kpi?.avg_capacity_factor)}
          highlight={(kpi?.avg_capacity_factor ?? 0) >= 15}
          warn={(kpi?.avg_capacity_factor ?? 0) < 10 && (kpi?.avg_capacity_factor ?? 0) > 0}
        />
        <KpiCard
          label="Inverter Efficiency"
          value={pct(kpi?.avg_inverter_efficiency)}
          highlight={(kpi?.avg_inverter_efficiency ?? 0) >= 96}
          warn={(kpi?.avg_inverter_efficiency ?? 0) < 93 && (kpi?.avg_inverter_efficiency ?? 0) > 0}
        />
        <KpiCard
          label="Anomaly Count"
          value={kpi?.anomaly_count == null ? "—" : String(kpi.anomaly_count)}
          warn={(kpi?.anomaly_count ?? 0) > 0}
        />
      </div>

      {/* Generation breakdown */}
      {kpi && kpi.kwh_generated && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Energy Distribution</h3>
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="flex-1 space-y-3">
              <div>
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Self Consumed</span>
                  <span>{pct(selfConsumptionRate)}</span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-3">
                  <div className="bg-yellow-400 h-3 rounded-full" style={{ width: `${Math.min(selfConsumptionRate ?? 0, 100)}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Exported</span>
                  <span>{kpi.kwh_generated ? pct(((kpi.kwh_exported ?? 0) / kpi.kwh_generated) * 100) : "—"}</span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-3">
                  <div className="bg-blue-400 h-3 rounded-full" style={{ width: `${kpi.kwh_generated ? Math.min(((kpi.kwh_exported ?? 0) / kpi.kwh_generated) * 100, 100) : 0}%` }} />
                </div>
              </div>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 flex flex-col justify-center gap-1 min-w-[180px]">
              <p><span className="inline-block w-3 h-3 rounded-full bg-yellow-400 mr-2" />Self consumed: {fmt(kpi.kwh_self_consumed, 1)} kWh</p>
              <p><span className="inline-block w-3 h-3 rounded-full bg-blue-400 mr-2" />Exported: {fmt(kpi.kwh_exported, 1)} kWh</p>
              <p className="font-medium text-gray-700 dark:text-gray-300 pt-1">Total: {fmt(kpi.kwh_generated, 1)} kWh</p>
            </div>
          </div>
        </div>
      )}

      {/* Trend chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Solar vs Total Electricity — Daily Trend</h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="solarGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#facc15" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#facc15" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="elecGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Area type="monotone" dataKey="electricity_kwh" name="Total Electricity (kWh)" stroke="#fbbf24" fill="url(#elecGrad)" strokeWidth={2} dot={false} />
            <Area type="monotone" dataKey="solar_kwh" name="Solar (kWh)" stroke="#facc15" fill="url(#solarGrad)" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
