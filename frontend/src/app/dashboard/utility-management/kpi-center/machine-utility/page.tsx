"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";
import { kpiApi } from "@/lib/utilityKpi";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) => n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;
const fmtCcy = (n?: number | null) => n == null ? "—" : `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function KpiCard({ label, value, unit, sub, highlight, warn, critical, flag }: {
  label: string; value: string; unit?: string; sub?: string;
  highlight?: boolean; warn?: boolean; critical?: boolean; flag?: boolean;
}) {
  const border = critical || flag
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

export default function MachineUtilityKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-machine-utility", dateFrom, dateTo],
    queryFn: () => kpiApi.machineUtility({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;

  // Radar chart data — normalize metrics to 0–100 for radar display
  const radarData = [
    {
      subject: "Efficiency",
      value: kpi?.avg_variance_pct != null ? Math.max(0, 100 - kpi.avg_variance_pct) : 0,
      fullMark: 100,
    },
    {
      subject: "Standby Control",
      value: kpi?.standby_pct != null ? Math.max(0, 100 - kpi.standby_pct) : 0,
      fullMark: 100,
    },
    {
      subject: "Energy/Runtime",
      // Lower electricity per runtime hour is better; normalize: assume target ≤50 kWh/h
      value: kpi?.electricity_per_runtime_h != null
        ? Math.max(0, Math.min(100, (1 - kpi.electricity_per_runtime_h / 100) * 100))
        : 0,
      fullMark: 100,
    },
    {
      subject: "Water/Batch",
      // Lower is better; assume target ≤5 m³/batch
      value: kpi?.water_per_batch != null
        ? Math.max(0, Math.min(100, (1 - kpi.water_per_batch / 10) * 100))
        : 0,
      fullMark: 100,
    },
    {
      subject: "Air/Batch",
      // Lower is better; assume target ≤50 Nm³/batch
      value: kpi?.air_per_batch != null
        ? Math.max(0, Math.min(100, (1 - kpi.air_per_batch / 100) * 100))
        : 0,
      fullMark: 100,
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/machine-utility" className="text-sm text-blue-600 hover:underline">Machine Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #818cf8", paddingLeft: 12 }}>
            Machine Utility KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Per-machine utility consumption, standby waste, variance flags, and cost per batch.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* Flag alerts */}
      {(kpi?.flag_high_variance || kpi?.flag_standby_waste) && (
        <div className="space-y-2">
          {kpi.flag_high_variance && (
            <div className="rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-300 dark:border-red-700 p-4 flex items-center gap-3">
              <span className="text-red-500 text-xl">🔴</span>
              <div className="text-sm">
                <p className="font-semibold text-red-800 dark:text-red-300">High Variance Flag</p>
                <p className="text-red-700 dark:text-red-400">
                  Average consumption variance {pct(kpi.avg_variance_pct)} exceeds acceptable threshold. Review machine calibration and process consistency.
                </p>
              </div>
            </div>
          )}
          {kpi.flag_standby_waste && (
            <div className="rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-700 p-4 flex items-center gap-3">
              <span className="text-amber-500 text-xl">⚡</span>
              <div className="text-sm">
                <p className="font-semibold text-amber-800 dark:text-amber-300">Standby Waste Flag</p>
                <p className="text-amber-700 dark:text-amber-400">
                  Machines consuming {pct(kpi.standby_pct)} of energy while idle. Consider auto-shutdown policies for non-production hours.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Consumption"
          value={fmt(kpi?.total_consumption, 1)}
          unit={kpi?.consumption_unit ?? "kWh"}
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="Electricity / Runtime Hour"
          value={fmt(kpi?.electricity_per_runtime_h, 2)}
          unit="kWh/h"
          warn={(kpi?.electricity_per_runtime_h ?? 0) > 75}
        />
        <KpiCard
          label="Water per Batch"
          value={fmt(kpi?.water_per_batch, 3)}
          unit="m³/batch"
          warn={(kpi?.water_per_batch ?? 0) > 5}
        />
        <KpiCard
          label="Air per Batch"
          value={fmt(kpi?.air_per_batch, 2)}
          unit="Nm³/batch"
        />
        <KpiCard
          label="Standby Consumption"
          value={pct(kpi?.standby_pct)}
          warn={(kpi?.standby_pct ?? 0) > 10}
          critical={(kpi?.standby_pct ?? 0) > 20}
          flag={kpi?.flag_standby_waste}
          sub="% of total while machine idle"
        />
        <KpiCard
          label="Cost per Batch"
          value={fmtCcy(kpi?.cost_per_batch)}
          unit="/batch"
        />
        <KpiCard
          label="Avg Consumption Variance"
          value={pct(kpi?.avg_variance_pct)}
          warn={(kpi?.avg_variance_pct ?? 0) > 15}
          critical={(kpi?.avg_variance_pct ?? 0) > 25}
          flag={kpi?.flag_high_variance}
          sub="vs expected standard consumption"
        />
        <KpiCard
          label="Anomaly Count"
          value={kpi?.anomaly_count == null ? "—" : String(kpi.anomaly_count)}
          warn={(kpi?.anomaly_count ?? 0) > 0}
          critical={(kpi?.anomaly_count ?? 0) > 3}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Radar chart */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Machine Performance Radar</h3>
          <p className="text-xs text-gray-400 mb-2">Higher score = better performance (normalized 0–100)</p>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
              <Radar name="Score" dataKey="value" stroke="#818cf8" fill="#818cf8" fillOpacity={0.3} />
              <Tooltip formatter={((v: number) => `${v.toFixed(0)}/100`) as never} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Summary table */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Consumption Summary</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400 border-b border-gray-100 dark:border-gray-700">
                <th className="text-left pb-2">Metric</th>
                <th className="text-right pb-2">Value</th>
                <th className="text-right pb-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {[
                { label: "Total Consumption", value: `${fmt(kpi?.total_consumption, 1)} ${kpi?.consumption_unit ?? "kWh"}`, ok: true },
                { label: "Electricity / h", value: `${fmt(kpi?.electricity_per_runtime_h, 2)} kWh/h`, ok: (kpi?.electricity_per_runtime_h ?? 0) <= 75 },
                { label: "Water / batch", value: `${fmt(kpi?.water_per_batch, 3)} m³`, ok: (kpi?.water_per_batch ?? 0) <= 5 },
                { label: "Air / batch", value: `${fmt(kpi?.air_per_batch, 2)} Nm³`, ok: true },
                { label: "Standby %", value: pct(kpi?.standby_pct), ok: (kpi?.standby_pct ?? 0) <= 10 },
                { label: "Cost / batch", value: fmtCcy(kpi?.cost_per_batch), ok: true },
                { label: "Variance %", value: pct(kpi?.avg_variance_pct), ok: (kpi?.avg_variance_pct ?? 0) <= 15 },
                { label: "Anomalies", value: String(kpi?.anomaly_count ?? "—"), ok: (kpi?.anomaly_count ?? 0) === 0 },
              ].map(row => (
                <tr key={row.label}>
                  <td className="py-2 text-gray-600 dark:text-gray-400">{row.label}</td>
                  <td className="py-2 text-right font-medium text-gray-800 dark:text-gray-200">{row.value}</td>
                  <td className="py-2 text-right">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${row.ok ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" : "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"}`}>
                      {row.ok ? "OK" : "Review"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
