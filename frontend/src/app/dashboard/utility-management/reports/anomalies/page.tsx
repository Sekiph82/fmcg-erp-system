"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { reportsApi } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const d30 = new Date(Date.now() - 30 * 86400_000).toISOString().slice(0, 10);
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });

const UTILITY_TYPES = ["", "ELECTRICITY", "WATER", "GAS", "STEAM", "COMPRESSED_AIR", "SOLAR"];
const SEVERITIES = ["", "CRITICAL", "ALERT", "WARNING", "INFO"];

const SEV_COLOR: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border-red-300",
  ALERT: "bg-orange-100 text-orange-700 border-orange-300",
  WARNING: "bg-amber-100 text-amber-700 border-amber-300",
  INFO: "bg-blue-100 text-blue-700 border-blue-300",
};

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

function AlarmTrendsTab({ dateFrom, dateTo, utilityType, severity }: {
  dateFrom: string; dateTo: string; utilityType: string; severity: string;
}) {
  const params = {
    date_from: dateFrom, date_to: dateTo,
    ...(utilityType ? { utility_type: utilityType } : {}),
    ...(severity ? { severity } : {}),
  };
  const q = useQuery({ queryKey: ["rpt-alarms", params], queryFn: () => reportsApi.alarmTrends(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border-2 border-red-400 bg-red-50 dark:bg-red-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">Total Events</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{d?.total_events ?? "—"}</p>
        </div>
        <div className="rounded-xl border-2 border-red-600 bg-red-100 dark:bg-red-950/30 p-4">
          <p className="text-xs font-medium text-gray-500">Critical</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{d?.critical_count ?? "—"}</p>
        </div>
        <div className="rounded-xl border-2 border-amber-400 bg-amber-50 dark:bg-amber-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">Unresolved</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">{d?.unresolved_count ?? "—"}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold">Alarm Trend by Severity</h3>
            <button onClick={() => reportsApi.exportAlarmTrends(params)} className="px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700">Export CSV</button>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="critical" name="Critical" stackId="s" fill="#ef4444" />
              <Bar dataKey="alert" name="Alert" stackId="s" fill="#f97316" />
              <Bar dataKey="warning" name="Warning" stackId="s" fill="#fbbf24" />
              <Bar dataKey="info" name="Info" stackId="s" fill="#60a5fa" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-3">Top Triggered Rules</h3>
          <div className="space-y-2">
            {(d?.top_rules ?? []).slice(0, 8).map((rule, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-xs text-gray-600 truncate flex-1">{rule.label}</span>
                <span className="text-xs font-semibold text-gray-800 ml-2">{rule.value}</span>
              </div>
            ))}
            {!d?.top_rules.length && <p className="text-xs text-gray-400">No alarm events</p>}
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
          <h3 className="text-sm font-semibold">Recent Alarm Events</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Event No", "Rule", "Utility", "Asset", "Device", "Severity", "Triggered At", "Value", "Threshold", "Status"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.recent ?? []).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{row.event_no}</td>
                  <td className="px-3 py-2 text-xs">{row.rule_name ?? row.rule_code ?? "—"}</td>
                  <td className="px-3 py-2">{row.utility_type ?? "—"}</td>
                  <td className="px-3 py-2">{row.asset_no ?? "—"}</td>
                  <td className="px-3 py-2">{row.device_code ?? "—"}</td>
                  <td className="px-3 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs border ${SEV_COLOR[row.severity ?? ""] ?? "border-gray-200"}`}>
                      {row.severity ?? "—"}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{row.triggered_at.slice(0, 16)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.triggered_value, 2)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.threshold_value, 2)}</td>
                  <td className="px-3 py-2">{row.status ?? "—"}</td>
                </tr>
              ))}
              {!d?.recent.length && <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No recent alarms</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function AbnormalTab({ dateFrom, dateTo, utilityType }: { dateFrom: string; dateTo: string; utilityType: string }) {
  const [threshold, setThreshold] = useState(30);
  const params = {
    date_from: dateFrom, date_to: dateTo,
    deviation_threshold_pct: threshold,
    ...(utilityType ? { utility_type: utilityType } : {}),
  };
  const q = useQuery({ queryKey: ["rpt-abnormal", params], queryFn: () => reportsApi.abnormalConsumption(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="flex gap-4 items-center flex-wrap">
        <div className="rounded-xl border-2 border-amber-400 bg-amber-50 dark:bg-amber-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">Anomaly Count</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">{d?.anomaly_count ?? "—"}</p>
        </div>
        <div className="rounded-xl border-2 border-red-400 bg-red-50 dark:bg-red-950/20 p-4">
          <p className="text-xs font-medium text-gray-500">High Deviation (&gt;{threshold}%)</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{d?.high_deviation_count ?? "—"}</p>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <label className="text-xs text-gray-500">Threshold %:</label>
          <input type="number" value={threshold} onChange={e => setThreshold(Number(e.target.value))}
            className="w-20 rounded-lg border border-gray-300 px-2 py-1 text-sm" min={5} max={200} step={5} />
          <button onClick={() => reportsApi.exportAbnormalConsumption(params)}
            className="px-3 py-1.5 text-xs bg-amber-600 text-white rounded-lg hover:bg-amber-700">Export CSV</button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 text-xs text-gray-500">
          {d?.rows.length ?? 0} deviation events — sorted by deviation magnitude
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Date", "Utility", "Department", "Quantity", "Unit", "Baseline Mean", "Deviation %", "Cost", "Anomaly", "Note"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).sort((a, b) => Math.abs(b.deviation_pct ?? 0) - Math.abs(a.deviation_pct ?? 0)).map((row, i) => {
                const devPct = row.deviation_pct ?? 0;
                const hi = Math.abs(devPct) > threshold;
                return (
                  <tr key={i} className={`hover:bg-gray-50 ${hi ? "bg-red-50/50 dark:bg-red-950/10" : "bg-amber-50/30 dark:bg-amber-950/5"}`}>
                    <td className="px-3 py-2 font-mono text-xs">{row.date}</td>
                    <td className="px-3 py-2">{row.utility_type}</td>
                    <td className="px-3 py-2">{row.department ?? "—"}</td>
                    <td className="px-3 py-2 text-right">{fmt(row.quantity)}</td>
                    <td className="px-3 py-2 text-gray-500">{row.unit ?? "—"}</td>
                    <td className="px-3 py-2 text-right">{fmt(row.mean_baseline)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${hi ? "text-red-600" : "text-amber-600"}`}>
                      {devPct > 0 ? "+" : ""}{fmt(row.deviation_pct, 1)}%
                    </td>
                    <td className="px-3 py-2 text-right">${fmt(row.total_cost, 2)}</td>
                    <td className="px-3 py-2 text-center">{row.is_anomaly ? <span className="text-red-500 font-bold">⚠</span> : "—"}</td>
                    <td className="px-3 py-2 text-xs text-gray-500 max-w-xs truncate">{row.anomaly_note ?? "—"}</td>
                  </tr>
                );
              })}
              {!d?.rows.length && <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No deviation events found</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

type Tab = "alarms" | "abnormal";

export default function AnomaliesPage() {
  const [dateFrom, setDateFrom] = useState(d30);
  const [dateTo, setDateTo] = useState(today);
  const [tab, setTab] = useState<Tab>("alarms");
  const [utilityType, setUtilityType] = useState("");
  const [severity, setSeverity] = useState("");

  const sel = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/reports" className="text-sm text-gray-500 hover:text-blue-600">← Reports</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #ef4444", paddingLeft: 12 }}>
            Anomalies & Alarms
          </h1>
        </div>
        <div className="flex gap-3 flex-wrap items-center bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
          <input type="date" className={sel} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span className="text-gray-400 text-xs">to</span>
          <input type="date" className={sel} value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <select className={sel} value={utilityType} onChange={e => setUtilityType(e.target.value)}>
            {UTILITY_TYPES.map(t => <option key={t} value={t}>{t || "All Utilities"}</option>)}
          </select>
          {tab === "alarms" && (
            <select className={sel} value={severity} onChange={e => setSeverity(e.target.value)}>
              {SEVERITIES.map(s => <option key={s} value={s}>{s || "All Severities"}</option>)}
            </select>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        {[
          { id: "alarms" as Tab, label: "Alarm Trends", color: "#ef4444" },
          { id: "abnormal" as Tab, label: "Abnormal Consumption", color: "#f97316" },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.id ? "text-white" : "bg-white dark:bg-gray-800 text-gray-600 border border-gray-200 dark:border-gray-700"}`}
            style={tab === t.id ? { backgroundColor: t.color } : {}}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "alarms" && <AlarmTrendsTab dateFrom={dateFrom} dateTo={dateTo} utilityType={utilityType} severity={severity} />}
      {tab === "abnormal" && <AbnormalTab dateFrom={dateFrom} dateTo={dateTo} utilityType={utilityType} />}
    </div>
  );
}
