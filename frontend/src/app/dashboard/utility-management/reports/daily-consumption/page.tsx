"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { reportsApi, type DailyConsumptionReport, type DailySummaryReport } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });

const UTILITY_TYPES = ["", "ELECTRICITY", "WATER", "GAS", "STEAM", "COMPRESSED_AIR", "SOLAR"];

function KpiCard({ label, value, unit, sub }: { label: string; value: string; unit?: string; sub?: string }) {
  return (
    <div className="rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
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
    <div className="flex gap-3 items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3 flex-wrap">
      <input type="date" className={ic} value={from} onChange={e => onFrom(e.target.value)} />
      <span className="text-gray-400 text-xs">to</span>
      <input type="date" className={ic} value={to} onChange={e => onTo(e.target.value)} />
    </div>
  );
}

function SummaryView({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const q = useQuery({
    queryKey: ["rpt-daily-summary", dateFrom, dateTo],
    queryFn: () => reportsApi.dailySummary({ date_from: dateFrom, date_to: dateTo }),
  });
  const d: DailySummaryReport | undefined = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <KpiCard label="Total Cost" value={fmt(d?.total_cost, 2)} unit="$" />
        <KpiCard label="Utility Types" value={d ? String(d.rows.length) : "—"} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Cost Trend</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" name="Cost ($)" stroke="#94a3b8" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
            <tr>
              {["Utility Type", "Quantity", "Unit", "Total Cost", "Avg Daily", "Tx Count"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {(d?.rows ?? []).map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                <td className="px-4 py-3 font-medium">{row.utility_type}</td>
                <td className="px-4 py-3">{fmt(row.quantity)}</td>
                <td className="px-4 py-3 text-gray-500">{row.unit ?? "—"}</td>
                <td className="px-4 py-3">{fmt(row.total_cost, 2)}</td>
                <td className="px-4 py-3">{fmt(row.avg_daily)}</td>
                <td className="px-4 py-3">{row.tx_count ?? "—"}</td>
              </tr>
            ))}
            {!d?.rows.length && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No data for selected range</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ConsumptionView({ dateFrom, dateTo, utilityType, dept, shift }: {
  dateFrom: string; dateTo: string; utilityType: string; dept: string; shift: string;
}) {
  const params = {
    date_from: dateFrom, date_to: dateTo,
    ...(utilityType ? { utility_type: utilityType } : {}),
    ...(dept ? { department: dept } : {}),
    ...(shift ? { shift_ref: shift } : {}),
  };
  const q = useQuery({
    queryKey: ["rpt-daily-consumption", params],
    queryFn: () => reportsApi.dailyConsumption(params),
  });
  const d: DailyConsumptionReport | undefined = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <KpiCard label="Total Quantity" value={fmt(d?.total_quantity)} unit={d?.unit ?? ""} />
        <KpiCard label="Total Cost" value={fmt(d?.total_cost, 2)} unit="$" />
        <KpiCard label="Records" value={d ? String(d.rows.length) : "—"} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Daily Consumption Trend</h3>
          <button
            onClick={() => reportsApi.exportDailyConsumption(params)}
            className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Export CSV
          </button>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis yAxisId="qty" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="cost" orientation="right" tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Bar yAxisId="qty" dataKey="value" name="Quantity" fill="#60a5fa" radius={[2, 2, 0, 0]} />
            <Bar yAxisId="cost" dataKey="value2" name="Cost ($)" fill="#f97316" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 text-xs text-gray-500">
          {d?.rows.length ?? 0} rows
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Date", "Utility", "Quantity", "Unit", "Cost", "Dept", "Shift", "Tx#"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-4 py-2 font-mono text-xs">{row.date}</td>
                  <td className="px-4 py-2">{row.utility_type}</td>
                  <td className="px-4 py-2 text-right">{fmt(row.quantity)}</td>
                  <td className="px-4 py-2 text-gray-500">{row.unit ?? "—"}</td>
                  <td className="px-4 py-2 text-right">{fmt(row.total_cost, 2)}</td>
                  <td className="px-4 py-2">{row.department ?? "—"}</td>
                  <td className="px-4 py-2">{row.shift_ref ?? "—"}</td>
                  <td className="px-4 py-2 text-right">{row.tx_count ?? "—"}</td>
                </tr>
              ))}
              {!d?.rows.length && (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No data for selected range</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function DailyConsumptionPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);
  const [view, setView] = useState<"detail" | "summary">("detail");
  const [utilityType, setUtilityType] = useState("");
  const [dept, setDept] = useState("");
  const [shift, setShift] = useState("");

  const sel = "px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/reports" className="text-sm text-gray-500 hover:text-blue-600">← Reports</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #60a5fa", paddingLeft: 12 }}>
            Daily Consumption Report
          </h1>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
          <button onClick={() => setView("detail")} className={`px-4 py-2 text-sm ${view === "detail" ? "bg-blue-600 text-white" : "bg-white dark:bg-gray-700 text-gray-600"}`}>Detail</button>
          <button onClick={() => setView("summary")} className={`px-4 py-2 text-sm ${view === "summary" ? "bg-blue-600 text-white" : "bg-white dark:bg-gray-700 text-gray-600"}`}>Summary</button>
        </div>
        {view === "detail" && (
          <>
            <select className={sel} value={utilityType} onChange={e => setUtilityType(e.target.value)}>
              {UTILITY_TYPES.map(t => <option key={t} value={t}>{t || "All Utilities"}</option>)}
            </select>
            <input placeholder="Department" className={sel} value={dept} onChange={e => setDept(e.target.value)} />
            <input placeholder="Shift (e.g. A)" className={sel} value={shift} onChange={e => setShift(e.target.value)} />
          </>
        )}
      </div>

      {view === "summary"
        ? <SummaryView dateFrom={dateFrom} dateTo={dateTo} />
        : <ConsumptionView dateFrom={dateFrom} dateTo={dateTo} utilityType={utilityType} dept={dept} shift={shift} />
      }
    </div>
  );
}
