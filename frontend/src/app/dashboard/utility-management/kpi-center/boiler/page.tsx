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

export default function BoilerKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-boiler", dateFrom, dateTo],
    queryFn: () => kpiApi.boiler({ date_from: dateFrom, date_to: dateTo }),
  });

  const trendQ = useQuery({
    queryKey: ["kpi-trend-boiler", dateFrom, dateTo],
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
            <Link href="/dashboard/utility-management/steam" className="text-sm text-blue-600 hover:underline">Operational Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #f97316", paddingLeft: 12 }}>
            Boiler / Steam KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track boiler efficiency, fuel consumption, steam generation, and condensate recovery.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Steam Generated"
          value={fmt(kpi?.steam_ton_total, 2)}
          unit="t"
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="Fuel Consumed"
          value={fmt(kpi?.fuel_consumed_total, 2)}
          unit={kpi?.fuel_unit ?? "Nm³"}
        />
        <KpiCard
          label="Gas per Ton Steam"
          value={fmt(kpi?.gas_per_ton_steam, 2)}
          unit={`${kpi?.fuel_unit ?? "Nm³"}/t`}
          warn={(kpi?.gas_per_ton_steam ?? 0) > 90}
        />
        <KpiCard
          label="Boiler Efficiency"
          value={pct(kpi?.boiler_efficiency_pct)}
          highlight={(kpi?.boiler_efficiency_pct ?? 0) >= 85}
          warn={(kpi?.boiler_efficiency_pct ?? 0) < 80 && (kpi?.boiler_efficiency_pct ?? 0) > 0}
          critical={(kpi?.boiler_efficiency_pct ?? 0) < 75 && (kpi?.boiler_efficiency_pct ?? 0) > 0}
        />
        <KpiCard
          label="Condensate Recovery"
          value={pct(kpi?.condensate_recovery_pct)}
          highlight={(kpi?.condensate_recovery_pct ?? 0) >= 80}
          warn={(kpi?.condensate_recovery_pct ?? 0) < 60 && (kpi?.condensate_recovery_pct ?? 0) > 0}
        />
        <KpiCard
          label="Blowdown Loss"
          value={pct(kpi?.blowdown_loss_pct)}
          highlight={(kpi?.blowdown_loss_pct ?? 0) <= 3}
          warn={(kpi?.blowdown_loss_pct ?? 0) > 5}
          critical={(kpi?.blowdown_loss_pct ?? 0) > 8}
        />
        <KpiCard
          label="Feedwater Used"
          value={fmt(kpi?.feedwater_m3_total, 1)}
          unit="m³"
        />
        <KpiCard
          label="Burner Runtime"
          value={fmt(kpi?.burner_runtime_hours, 1)}
          unit="h"
        />
        <KpiCard
          label="Avg Boiler Load"
          value={pct(kpi?.avg_boiler_load_pct)}
          highlight={(kpi?.avg_boiler_load_pct ?? 0) >= 70 && (kpi?.avg_boiler_load_pct ?? 0) <= 90}
          warn={(kpi?.avg_boiler_load_pct ?? 0) < 50 && (kpi?.avg_boiler_load_pct ?? 0) > 0}
        />
        <KpiCard
          label="Anomaly Count"
          value={kpi?.anomaly_count == null ? "—" : String(kpi.anomaly_count)}
          warn={(kpi?.anomaly_count ?? 0) > 0}
          critical={(kpi?.anomaly_count ?? 0) > 3}
        />
      </div>

      {/* Trend chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Steam & Gas Daily Trend</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="steam_ton" name="Steam (t)" stroke="#f97316" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="gas_nm3" name="Gas (Nm³)" stroke="#a78bfa" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Efficiency summary */}
      {kpi && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Efficiency Summary</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div className="space-y-1">
              <p className="text-gray-500">Boiler Efficiency</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${(kpi.boiler_efficiency_pct ?? 0) >= 85 ? "bg-green-500" : (kpi.boiler_efficiency_pct ?? 0) >= 80 ? "bg-amber-400" : "bg-red-500"}`}
                    style={{ width: `${Math.min(kpi.boiler_efficiency_pct ?? 0, 100)}%` }}
                  />
                </div>
                <span className="font-semibold">{pct(kpi.boiler_efficiency_pct)}</span>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-gray-500">Condensate Recovery</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${(kpi.condensate_recovery_pct ?? 0) >= 80 ? "bg-green-500" : "bg-amber-400"}`}
                    style={{ width: `${Math.min(kpi.condensate_recovery_pct ?? 0, 100)}%` }}
                  />
                </div>
                <span className="font-semibold">{pct(kpi.condensate_recovery_pct)}</span>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-gray-500">Blowdown Loss (lower is better)</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${(kpi.blowdown_loss_pct ?? 0) <= 3 ? "bg-green-500" : (kpi.blowdown_loss_pct ?? 0) <= 5 ? "bg-amber-400" : "bg-red-500"}`}
                    style={{ width: `${Math.min((kpi.blowdown_loss_pct ?? 0) * 5, 100)}%` }}
                  />
                </div>
                <span className="font-semibold">{pct(kpi.blowdown_loss_pct)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
