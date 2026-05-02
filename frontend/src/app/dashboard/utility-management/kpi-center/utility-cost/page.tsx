"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from "recharts";
import { kpiApi } from "@/lib/utilityKpi";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) => n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const fmtCcy = (n?: number | null, cc = "$") => n == null ? "—" : `${cc}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

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

const COST_COLORS: Record<string, string> = {
  electricity: "#fbbf24",
  water: "#60a5fa",
  gas: "#a78bfa",
  steam: "#f97316",
  other: "#94a3b8",
};

export default function UtilityCostKpiPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);

  const kpiQ = useQuery({
    queryKey: ["kpi-utility-cost", dateFrom, dateTo],
    queryFn: () => kpiApi.utilityCost({ date_from: dateFrom, date_to: dateTo }),
  });

  const trendQ = useQuery({
    queryKey: ["kpi-trend-cost", dateFrom, dateTo],
    queryFn: () => kpiApi.dailyTrend({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi = kpiQ.data;
  const trend = trendQ.data ?? [];
  const cc = kpi?.currency_code ?? "$";

  // Pie data from utility cost breakdown
  const pieData = [
    { name: "Electricity", key: "electricity", value: kpi?.electricity_cost ?? 0 },
    { name: "Water", key: "water", value: kpi?.water_cost ?? 0 },
    { name: "Gas", key: "gas", value: kpi?.gas_cost ?? 0 },
    { name: "Steam", key: "steam", value: kpi?.steam_cost ?? 0 },
    { name: "Other", key: "other", value: kpi?.other_cost ?? 0 },
  ].filter(d => d.value > 0);

  // Bar chart data for cost breakdown
  const barData = pieData.map(d => ({ name: d.name, cost: d.value }));

  const unpaidPct = kpi?.total_cost && kpi?.unpaid_amount
    ? (kpi.unpaid_amount / kpi.total_cost) * 100
    : 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300">|</span>
            <Link href="/dashboard/utility-management/billing" className="text-sm text-blue-600 hover:underline">Billing Records →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #94a3b8", paddingLeft: 12 }}>
            Utility Cost KPI Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Full cost overview across all utility types — bills, cost per ton, and unpaid amounts.
          </p>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* Unpaid alert */}
      {(kpi?.unpaid_amount ?? 0) > 0 && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-700 p-4 flex items-center gap-3">
          <span className="text-amber-500 text-xl">💰</span>
          <div className="text-sm">
            <p className="font-semibold text-amber-800 dark:text-amber-300">Outstanding Payments</p>
            <p className="text-amber-700 dark:text-amber-400">
              {fmtCcy(kpi?.unpaid_amount, cc)} ({unpaidPct.toFixed(1)}% of period total) pending payment across {kpi?.total_bills} bill(s).
            </p>
          </div>
          <Link href="/dashboard/utility-management/billing" className="ml-auto text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 px-3 py-1.5 rounded-lg hover:bg-amber-200 transition-colors">
            View Bills →
          </Link>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Utility Cost"
          value={fmtCcy(kpi?.total_cost, cc)}
          sub={`${dateFrom} – ${dateTo}`}
        />
        <KpiCard
          label="Cost per Ton"
          value={fmtCcy(kpi?.cost_per_ton, cc)}
          unit="/t"
          sub="Based on production volume"
        />
        <KpiCard
          label="Cost per Batch"
          value={fmtCcy(kpi?.cost_per_batch, cc)}
          unit="/batch"
        />
        <KpiCard
          label="Total Bills"
          value={kpi?.total_bills == null ? "—" : String(kpi.total_bills)}
        />
        <KpiCard
          label="Electricity Cost"
          value={fmtCcy(kpi?.electricity_cost, cc)}
        />
        <KpiCard
          label="Water Cost"
          value={fmtCcy(kpi?.water_cost, cc)}
        />
        <KpiCard
          label="Gas Cost"
          value={fmtCcy(kpi?.gas_cost, cc)}
        />
        <KpiCard
          label="Steam Cost"
          value={fmtCcy(kpi?.steam_cost, cc)}
        />
        <KpiCard
          label="Other Costs"
          value={fmtCcy(kpi?.other_cost, cc)}
        />
        <KpiCard
          label="Unpaid Amount"
          value={fmtCcy(kpi?.unpaid_amount, cc)}
          critical={(kpi?.unpaid_amount ?? 0) > 0}
          sub={unpaidPct > 0 ? `${unpaidPct.toFixed(1)}% of total` : undefined}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Pie chart */}
        {pieData.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Cost Distribution by Utility</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90}
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                  {pieData.map(d => <Cell key={d.key} fill={COST_COLORS[d.key] ?? "#94a3b8"} />)}
                </Pie>
                <Tooltip formatter={(v: unknown) => fmtCcy(v as number | null | undefined, cc)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Bar chart */}
        {barData.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Cost by Utility Type</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={barData} layout="vertical" margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => `${cc}${v.toLocaleString()}`} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={90} />
                <Tooltip formatter={(v: unknown) => fmtCcy(v as number | null | undefined, cc)} />
                <Bar dataKey="cost" name="Cost" radius={[0, 4, 4, 0]}>
                  {barData.map((d, i) => {
                    const key = d.name.toLowerCase();
                    const colorKey = Object.keys(COST_COLORS).find(k => key.includes(k)) ?? "other";
                    return <Cell key={i} fill={COST_COLORS[colorKey]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Daily cost trend */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Daily Total Utility Cost Trend</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${cc}${v.toLocaleString()}`} />
            <Tooltip formatter={(v: unknown) => fmtCcy(v as number | null | undefined, cc)} />
            <Bar dataKey="total_cost" name="Daily Cost" fill="#94a3b8" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
