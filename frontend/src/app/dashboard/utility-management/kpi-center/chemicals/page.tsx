"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { kpiApi } from "@/lib/utilityKpi";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) => n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const fmtCcy = (n?: number | null) => n == null ? "—" : `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function KpiCard({ label, value, unit, sub, highlight, warn }: {
  label: string; value: string; unit?: string; sub?: string; highlight?: boolean; warn?: boolean;
}) {
  const border = warn
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

const COST_COLORS = ["#60a5fa", "#f97316", "#22d3ee", "#a78bfa"];

export default function ChemicalsKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-chemicals", dateFrom, dateTo],
    queryFn: () => kpiApi.chemicals({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;

  // Build pie data from category costs
  const pieData = [
    { name: "Boiler Chemicals", value: kpi?.boiler_cost ?? 0 },
    { name: "Cooling Treatment", value: kpi?.cooling_cost ?? 0 },
    { name: "WWTP Chemicals", value: kpi?.wwtp_cost ?? 0 },
    { name: "Other", value: Math.max(0, (kpi?.total_cost ?? 0) - (kpi?.boiler_cost ?? 0) - (kpi?.cooling_cost ?? 0) - (kpi?.wwtp_cost ?? 0)) },
  ].filter(d => d.value > 0);

  const days = dateFrom && dateTo
    ? Math.max(1, Math.round((new Date(dateTo).getTime() - new Date(dateFrom).getTime()) / 86400000) + 1)
    : 30;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/chemical-treatment" className="text-sm text-blue-600 hover:underline">Operational Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #34d399", paddingLeft: 12 }}>
            Treatment Chemicals KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track chemical costs and consumption across boiler, cooling, and wastewater treatment.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Chemical Cost"
          value={fmtCcy(kpi?.total_cost)}
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="Cost per Day"
          value={fmtCcy(kpi?.cost_per_day)}
          unit="/day"
        />
        <KpiCard
          label="Total Consumed"
          value={fmt(kpi?.total_consumed_kg, 1)}
          unit="kg"
        />
        <KpiCard
          label="Distinct Chemicals"
          value={kpi?.distinct_chemicals == null ? "—" : String(kpi.distinct_chemicals)}
        />
        <KpiCard
          label="Boiler Chemicals"
          value={fmtCcy(kpi?.boiler_cost)}
          sub="Antiscalant, biocide, etc."
        />
        <KpiCard
          label="Cooling Treatment"
          value={fmtCcy(kpi?.cooling_cost)}
          sub="Corrosion inhibitors, biocide"
        />
        <KpiCard
          label="WWTP Chemicals"
          value={fmtCcy(kpi?.wwtp_cost)}
          sub="Coagulants, flocculants, pH"
        />
      </div>

      {/* Cost breakdown pie */}
      {pieData.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Cost by Treatment Category</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(((percent as number) ?? 0) * 100).toFixed(0)}%`}>
                  {pieData.map((_, i) => <Cell key={i} fill={COST_COLORS[i % COST_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={((v: number) => fmtCcy(v)) as never} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Cost Breakdown Detail</h3>
            <div className="space-y-3 mt-2">
              {pieData.map((item, i) => (
                <div key={item.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: COST_COLORS[i % COST_COLORS.length] }} />
                    <span className="text-gray-700 dark:text-gray-300">{item.name}</span>
                  </div>
                  <div className="flex gap-4 text-gray-500">
                    <span>{fmtCcy(item.value)}</span>
                    <span className="text-gray-400">{kpi?.total_cost ? `${((item.value / kpi.total_cost) * 100).toFixed(1)}%` : "—"}</span>
                  </div>
                </div>
              ))}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-2 flex justify-between font-semibold text-sm">
                <span className="text-gray-700 dark:text-gray-300">Total</span>
                <span>{fmtCcy(kpi?.total_cost)}</span>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-3">Period: {days} days · Avg {fmtCcy(kpi?.cost_per_day)}/day</p>
          </div>
        </div>
      )}

      {kpiQ.isLoading && (
        <div className="flex justify-center py-12 text-gray-400 text-sm">Loading chemical KPIs...</div>
      )}
    </div>
  );
}
