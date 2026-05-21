"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
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

function ComplianceBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  const s = status.toUpperCase();
  const cls =
    s === "COMPLIANT" ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300" :
    s === "NON_COMPLIANT" || s === "NON-COMPLIANT" ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300" :
    "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border-yellow-300";
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-semibold ${cls}`}>
      {s === "COMPLIANT" ? "✓" : s.includes("NON") ? "✗" : "~"} {status}
    </span>
  );
}

export default function WastewaterKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-wastewater", dateFrom, dateTo],
    queryFn: () => kpiApi.wastewater({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;

  // Build simple parameter bar data for visualization
  const paramData = [
    { name: "COD Removal", value: kpi?.cod_removal_pct ?? 0, target: 90, unit: "%" },
    { name: "BOD Removal", value: kpi?.bod_removal_pct ?? 0, target: 90, unit: "%" },
    { name: "Compliance", value: kpi?.compliant_pct ?? 0, target: 95, unit: "%" },
  ].filter(d => d.value > 0);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/wastewater" className="text-sm text-blue-600 hover:underline">Operational Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #6ee7b7", paddingLeft: 12 }}>
            Wastewater Treatment KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Monitor effluent quality, treatment efficiency, regulatory compliance, and WWTP energy use.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* Compliance badge banner */}
      {(kpi?.non_compliant_count ?? 0) > 0 && (
        <div className="rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-300 dark:border-red-700 p-4 flex items-center gap-3">
          <span className="text-red-500 text-xl">⚠</span>
          <div>
            <p className="font-semibold text-red-800 dark:text-red-300">Compliance Alert</p>
            <p className="text-sm text-red-700 dark:text-red-400">
              {kpi?.non_compliant_count} non-compliant record(s) in the selected period. Review effluent parameters immediately.
            </p>
          </div>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="COD Removal"
          value={pct(kpi?.cod_removal_pct)}
          sub="Chemical oxygen demand"
          highlight={(kpi?.cod_removal_pct ?? 0) >= 90}
          warn={(kpi?.cod_removal_pct ?? 0) < 80 && (kpi?.cod_removal_pct ?? 0) > 0}
          critical={(kpi?.cod_removal_pct ?? 0) < 70 && (kpi?.cod_removal_pct ?? 0) > 0}
        />
        <KpiCard
          label="BOD Removal"
          value={pct(kpi?.bod_removal_pct)}
          sub="Biological oxygen demand"
          highlight={(kpi?.bod_removal_pct ?? 0) >= 90}
          warn={(kpi?.bod_removal_pct ?? 0) < 80 && (kpi?.bod_removal_pct ?? 0) > 0}
          critical={(kpi?.bod_removal_pct ?? 0) < 70 && (kpi?.bod_removal_pct ?? 0) > 0}
        />
        <KpiCard
          label="Avg Dissolved O₂"
          value={fmt(kpi?.avg_do_mgl, 2)}
          unit="mg/L"
          highlight={(kpi?.avg_do_mgl ?? 0) >= 2}
          warn={(kpi?.avg_do_mgl ?? 0) < 1.5 && (kpi?.avg_do_mgl ?? 0) > 0}
          critical={(kpi?.avg_do_mgl ?? 0) < 1 && (kpi?.avg_do_mgl ?? 0) > 0}
        />
        <KpiCard
          label="Avg Effluent pH"
          value={fmt(kpi?.avg_effluent_ph, 2)}
          highlight={(kpi?.avg_effluent_ph ?? 0) >= 6.5 && (kpi?.avg_effluent_ph ?? 0) <= 8.5}
          warn={!!kpi?.avg_effluent_ph && ((kpi.avg_effluent_ph < 6 || kpi.avg_effluent_ph > 9))}
          critical={!!kpi?.avg_effluent_ph && ((kpi.avg_effluent_ph < 5.5 || kpi.avg_effluent_ph > 9.5))}
        />
        <KpiCard
          label="Sludge Produced"
          value={fmt(kpi?.sludge_kg_total, 1)}
          unit="kg"
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="WWTP Power Used"
          value={fmt(kpi?.power_kwh_total, 1)}
          unit="kWh"
        />
        <KpiCard
          label="Power per m³"
          value={fmt(kpi?.power_per_m3, 4)}
          unit="kWh/m³"
          warn={(kpi?.power_per_m3 ?? 0) > 1.5}
        />
        <KpiCard
          label="Compliance Rate"
          value={pct(kpi?.compliant_pct)}
          highlight={(kpi?.compliant_pct ?? 0) >= 95}
          warn={(kpi?.compliant_pct ?? 0) < 80 && (kpi?.compliant_pct ?? 0) > 0}
          critical={(kpi?.compliant_pct ?? 0) < 70 && (kpi?.compliant_pct ?? 0) > 0}
        />
        <KpiCard
          label="Non-Compliant Records"
          value={kpi?.non_compliant_count == null ? "—" : String(kpi.non_compliant_count)}
          critical={(kpi?.non_compliant_count ?? 0) > 0}
        />
        <KpiCard
          label="Anomaly Count"
          value={kpi?.anomaly_count == null ? "—" : String(kpi.anomaly_count)}
          warn={(kpi?.anomaly_count ?? 0) > 0}
        />
      </div>

      {/* Treatment efficiency bar chart */}
      {paramData.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Treatment Efficiency vs Target</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={paramData} layout="vertical" margin={{ top: 4, right: 40, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={v => `${v}%`} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
              <Tooltip formatter={((v: number) => `${v.toFixed(1)}%`) as never} />
              <ReferenceLine x={90} stroke="#22c55e" strokeDasharray="4 4" label={{ value: "Target 90%", position: "top", fontSize: 10, fill: "#22c55e" }} />
              <Bar dataKey="value" name="Actual %" fill="#6ee7b7" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* pH and DO status */}
      {kpi && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Effluent Quality Parameters</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div className="text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <p className="text-xs text-gray-500 mb-1">pH (Target: 6.5–8.5)</p>
              <p className={`text-lg font-bold ${(kpi.avg_effluent_ph ?? 0) >= 6.5 && (kpi.avg_effluent_ph ?? 0) <= 8.5 ? "text-green-600" : "text-red-600"}`}>
                {fmt(kpi.avg_effluent_ph, 2)}
              </p>
            </div>
            <div className="text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <p className="text-xs text-gray-500 mb-1">DO mg/L (Target: ≥2)</p>
              <p className={`text-lg font-bold ${(kpi.avg_do_mgl ?? 0) >= 2 ? "text-green-600" : "text-amber-600"}`}>
                {fmt(kpi.avg_do_mgl, 2)}
              </p>
            </div>
            <div className="text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <p className="text-xs text-gray-500 mb-1">COD Removal (Target: ≥90%)</p>
              <p className={`text-lg font-bold ${(kpi.cod_removal_pct ?? 0) >= 90 ? "text-green-600" : "text-red-600"}`}>
                {pct(kpi.cod_removal_pct)}
              </p>
            </div>
            <div className="text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <p className="text-xs text-gray-500 mb-1">Compliance Rate</p>
              <p className={`text-lg font-bold ${(kpi.compliant_pct ?? 0) >= 95 ? "text-green-600" : (kpi.compliant_pct ?? 0) >= 80 ? "text-amber-600" : "text-red-600"}`}>
                {pct(kpi.compliant_pct)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
