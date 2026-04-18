"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { reportsApi } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;

function KpiCard({ label, value, unit, sub, warn, ok }: {
  label: string; value: string; unit?: string; sub?: string; warn?: boolean; ok?: boolean;
}) {
  const border = ok ? "border-green-400 bg-green-50 dark:bg-green-950/20"
    : warn ? "border-amber-400 bg-amber-50 dark:bg-amber-950/20"
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

function BoilerTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const params = { date_from: dateFrom, date_to: dateTo };
  const q = useQuery({ queryKey: ["rpt-boiler", params], queryFn: () => reportsApi.boilerEfficiency(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <KpiCard label="Avg Efficiency" value={pct(d?.avg_efficiency_pct)} ok={(d?.avg_efficiency_pct ?? 0) >= 80} warn={(d?.avg_efficiency_pct ?? 100) < 70} />
        <KpiCard label="Total Steam" value={fmt(d?.total_steam_kg, 0)} unit="kg" />
        <KpiCard label="Total Fuel" value={fmt(d?.total_fuel)} />
        <KpiCard label="Avg Load" value={pct(d?.avg_load_pct)} />
        <KpiCard label="Condensate Recovery" value={pct(d?.condensate_recovery_pct)} ok={(d?.condensate_recovery_pct ?? 0) >= 70} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Boiler Efficiency Trend</h3>
          <button onClick={() => reportsApi.exportBoilerEfficiency(params)} className="px-3 py-1.5 text-xs bg-orange-600 text-white rounded-lg hover:bg-orange-700">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" name="Efficiency %" stroke="#f97316" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="value2" name="Load %" stroke="#fb923c" dot={false} strokeWidth={1} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Record", "Asset", "DateTime", "Shift", "Steam (kg)", "Fuel", "Efficiency %", "Load %", "Blowdown %", "Anomaly"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className={`hover:bg-gray-50 dark:hover:bg-gray-750 ${row.is_anomaly ? "bg-red-50/50 dark:bg-red-950/10" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{row.record_no}</td>
                  <td className="px-3 py-2">{row.asset_no ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{row.record_datetime.slice(0, 16)}</td>
                  <td className="px-3 py-2">{row.shift_ref ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.steam_generated_kg, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.fuel_consumption)} {row.fuel_unit}</td>
                  <td className="px-3 py-2 text-right">{pct(row.boiler_efficiency_pct)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.boiler_load_pct)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.blowdown_pct)}</td>
                  <td className="px-3 py-2 text-center">{row.is_anomaly ? <span className="text-red-500 font-bold">⚠</span> : "—"}</td>
                </tr>
              ))}
              {!d?.rows.length && <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No records</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CompressorTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const params = { date_from: dateFrom, date_to: dateTo };
  const q = useQuery({ queryKey: ["rpt-compressor", params], queryFn: () => reportsApi.compressorPerformance(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Total Air" value={fmt(d?.total_air_nm3, 0)} unit="Nm³" />
        <KpiCard label="Total kWh" value={fmt(d?.total_kwh, 0)} unit="kWh" />
        <KpiCard label="Specific Energy" value={fmt(d?.avg_specific_energy, 3)} unit="kWh/Nm³" />
        <KpiCard label="Avg Load" value={pct(d?.avg_load_pct)} />
        <KpiCard label="Avg Leak" value={pct(d?.avg_leak_pct)} warn={(d?.avg_leak_pct ?? 0) > 10} />
        <KpiCard label="Total Leak Vol" value={fmt(d?.total_leak_nm3, 0)} unit="Nm³" warn={(d?.total_leak_nm3 ?? 0) > 0} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Compressor Performance Trend</h3>
          <button onClick={() => reportsApi.exportCompressorPerformance(params)} className="px-3 py-1.5 text-xs bg-cyan-600 text-white rounded-lg hover:bg-cyan-700">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" name="Air (Nm³)" stroke="#22d3ee" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="value2" name="kWh" stroke="#0ea5e9" dot={false} strokeWidth={1} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Record", "Asset", "DateTime", "Air (Nm³)", "kWh", "Spec Energy", "Load %", "Leak %", "Leak Vol", "Night Idle", "Anomaly"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className={`hover:bg-gray-50 ${row.is_anomaly ? "bg-red-50/50 dark:bg-red-950/10" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{row.record_no}</td>
                  <td className="px-3 py-2">{row.asset_no ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{row.record_datetime.slice(0, 16)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.air_generated_nm3, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.electricity_used_kwh, 1)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.specific_energy_kwh_m3, 3)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.load_pct)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.leak_estimation_pct)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.leak_volume_nm3, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.night_idle_kwh, 1)}</td>
                  <td className="px-3 py-2 text-center">{row.is_anomaly ? <span className="text-red-500 font-bold">⚠</span> : "—"}</td>
                </tr>
              ))}
              {!d?.rows.length && <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">No records</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SoftWaterTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const params = { date_from: dateFrom, date_to: dateTo };
  const q = useQuery({ queryKey: ["rpt-softwater", params], queryFn: () => reportsApi.softWater(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Treated Volume" value={fmt(d?.total_volume_treated_m3)} unit="m³" />
        <KpiCard label="Raw Water Input" value={fmt(d?.total_raw_water_m3)} unit="m³" />
        <KpiCard label="Salt Used" value={fmt(d?.total_salt_kg, 0)} unit="kg" />
        <KpiCard label="Salt per m³" value={fmt(d?.avg_salt_per_m3, 2)} unit="kg/m³" />
        <KpiCard label="Avg Efficiency" value={pct(d?.avg_efficiency_pct)} ok={(d?.avg_efficiency_pct ?? 0) >= 85} />
        <KpiCard label="Conversion %" value={pct(d?.conversion_pct)} ok={(d?.conversion_pct ?? 0) >= 90} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Soft Water Trend</h3>
          <button onClick={() => reportsApi.exportSoftWater(params)} className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="value" name="Treated (m³)" fill="#a78bfa" radius={[2, 2, 0, 0]} />
            <Bar dataKey="value2" name="Salt (kg)" fill="#c4b5fd" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Record", "Asset", "DateTime", "Treated (m³)", "Raw (m³)", "Salt (kg)", "Salt/m³", "Eff %", "Feed HDN", "Prod HDN", "Regens"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-3 py-2 font-mono text-xs">{row.record_no}</td>
                  <td className="px-3 py-2">{row.asset_no ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{row.record_datetime.slice(0, 16)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.volume_treated_m3)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.raw_water_input_m3)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.salt_consumed_kg, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.salt_per_m3, 2)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.efficiency_pct)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.feed_water_hardness_ppm, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.product_water_hardness_ppm, 0)}</td>
                  <td className="px-3 py-2 text-right">{row.regeneration_count ?? "—"}</td>
                </tr>
              ))}
              {!d?.rows.length && <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">No records</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

type Tab = "boiler" | "compressor" | "softwater";

export default function EquipmentEfficiencyPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);
  const [tab, setTab] = useState<Tab>("boiler");

  const tabs: { id: Tab; label: string; color: string }[] = [
    { id: "boiler", label: "Boiler & Steam", color: "#f97316" },
    { id: "compressor", label: "Compressor", color: "#22d3ee" },
    { id: "softwater", label: "Soft Water", color: "#a78bfa" },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/reports" className="text-sm text-gray-500 hover:text-blue-600">← Reports</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #f97316", paddingLeft: 12 }}>
            Equipment Efficiency
          </h1>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      <div className="flex gap-2">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.id ? "text-white" : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700"}`}
            style={tab === t.id ? { backgroundColor: t.color } : {}}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "boiler" && <BoilerTab dateFrom={dateFrom} dateTo={dateTo} />}
      {tab === "compressor" && <CompressorTab dateFrom={dateFrom} dateTo={dateTo} />}
      {tab === "softwater" && <SoftWaterTab dateFrom={dateFrom} dateTo={dateTo} />}
    </div>
  );
}
