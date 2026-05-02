"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { reportsApi } from "@/lib/utilitiesReports";

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";
const fmt = (n?: number | null, dp = 1) =>
  n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
const pct = (n?: number | null) => n == null ? "—" : `${fmt(n, 1)}%`;
const PIE_COLORS = ["#22d3ee", "#a78bfa", "#34d399", "#f97316", "#f43f5e", "#facc15", "#818cf8"];

function KpiCard({ label, value, unit, warn, ok }: { label: string; value: string; unit?: string; warn?: boolean; ok?: boolean }) {
  const border = ok ? "border-green-400 bg-green-50 dark:bg-green-950/20"
    : warn ? "border-amber-400 bg-amber-50 dark:bg-amber-950/20"
    : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800";
  return (
    <div className={`rounded-xl border-2 p-4 ${border}`}>
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
        {value}{unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
      </p>
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

function ChemicalTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const params = { date_from: dateFrom, date_to: dateTo };
  const q = useQuery({ queryKey: ["rpt-chemical", params], queryFn: () => reportsApi.chemicalTreatment(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Total Dosed" value={fmt(d?.total_dosed)} unit="kg" />
        <KpiCard label="Total Cost" value={fmt(d?.total_cost, 2)} unit="$" />
        <KpiCard label="Overdose Events" value={d?.overdose_count == null ? "—" : String(d.overdose_count)} warn={(d?.overdose_count ?? 0) > 0} />
        <KpiCard label="Underdose Events" value={d?.underdose_count == null ? "—" : String(d.underdose_count)} warn={(d?.underdose_count ?? 0) > 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-4">By Chemical</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={d?.by_chemical ?? []} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={75} label={(props: any) => `${props.name} ${props.pct ? Number(props.pct).toFixed(0) : ""}%`}>
                {(d?.by_chemical ?? []).map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-4">By Treatment Area</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={d?.by_area ?? []} layout="vertical" margin={{ top: 4, right: 16, left: 60, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 10 }} width={55} />
              <Tooltip />
              <Bar dataKey="value" name="Qty (kg)" fill="#34d399" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 flex justify-between border-b border-gray-100 dark:border-gray-700">
          <span className="text-xs text-gray-500">{d?.rows.length ?? 0} records</span>
          <button onClick={() => reportsApi.exportChemicalTreatment(params)} className="px-3 py-1 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">Export CSV</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Record", "Chemical", "Category", "Area", "Qty", "Unit", "Target ppm", "Actual ppm", "Cost", "OD", "UD"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className={`hover:bg-gray-50 ${row.overdose_flag || row.underdose_flag ? "bg-amber-50/50 dark:bg-amber-950/10" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{row.record_no}</td>
                  <td className="px-3 py-2">{row.chemical_name ?? "—"}</td>
                  <td className="px-3 py-2">{row.chemical_category ?? "—"}</td>
                  <td className="px-3 py-2">{row.treatment_area ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.quantity_dosed, 2)}</td>
                  <td className="px-3 py-2">{row.unit ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.target_dose_ppm, 1)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.actual_dose_ppm, 1)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.total_cost, 2)}</td>
                  <td className="px-3 py-2 text-center">{row.overdose_flag ? <span className="text-red-500 font-bold text-xs">OD</span> : "—"}</td>
                  <td className="px-3 py-2 text-center">{row.underdose_flag ? <span className="text-amber-500 font-bold text-xs">UD</span> : "—"}</td>
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

function SolarTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const params = { date_from: dateFrom, date_to: dateTo };
  const q = useQuery({ queryKey: ["rpt-solar", params], queryFn: () => reportsApi.solarGeneration(params) });
  const d = q.data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <KpiCard label="Generated" value={fmt(d?.total_generated_kwh, 0)} unit="kWh" />
        <KpiCard label="Self-Consumed" value={fmt(d?.total_self_consumption_kwh, 0)} unit="kWh" ok={(d?.total_self_consumption_kwh ?? 0) > 0} />
        <KpiCard label="Grid Export" value={fmt(d?.total_grid_export_kwh, 0)} unit="kWh" />
        <KpiCard label="Avg PR Ratio" value={fmt(d?.avg_pr_ratio, 3)} ok={(d?.avg_pr_ratio ?? 0) >= 0.75} />
        <KpiCard label="Solar Contribution" value={pct(d?.avg_contribution_pct)} ok={(d?.avg_contribution_pct ?? 0) >= 10} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Solar Generation vs Consumption</h3>
          <button onClick={() => reportsApi.exportSolarGeneration(params)} className="px-3 py-1.5 text-xs bg-yellow-500 text-white rounded-lg hover:bg-yellow-600">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" name="Generated (kWh)" stroke="#facc15" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="value2" name="Self-Consumed (kWh)" stroke="#a3e635" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Date", "Asset", "Generated", "Self-Used", "Grid Export", "Irradiance", "PR Ratio", "Inv Eff %", "Capacity %", "Contribution %"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-3 py-2 font-mono text-xs">{row.date}</td>
                  <td className="px-3 py-2">{row.asset_no ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.energy_generated_kwh, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.self_consumption_kwh, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.grid_export_kwh, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.irradiance_wm2, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.pr_ratio, 3)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.inverter_efficiency_pct)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.capacity_factor_pct)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.solar_contribution_pct)}</td>
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

function WastewaterTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const params = { date_from: dateFrom, date_to: dateTo };
  const q = useQuery({ queryKey: ["rpt-wastewater", params], queryFn: () => reportsApi.wastewaterCompliance(params) });
  const d = q.data;

  const statusColor = (s?: string | null) =>
    s === "COMPLIANT" ? "text-green-600 font-semibold" : s === "NON_COMPLIANT" ? "text-red-600 font-semibold" : "text-amber-500";

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <KpiCard label="Compliant" value={d?.compliant_count == null ? "—" : String(d.compliant_count)} ok={(d?.compliant_count ?? 0) > 0} />
        <KpiCard label="Non-Compliant" value={d?.non_compliant_count == null ? "—" : String(d.non_compliant_count)} warn={(d?.non_compliant_count ?? 0) > 0} />
        <KpiCard label="Borderline" value={d?.borderline_count == null ? "—" : String(d.borderline_count)} warn={(d?.borderline_count ?? 0) > 0} />
        <KpiCard label="Compliance Rate" value={pct(d?.compliance_rate_pct)} ok={(d?.compliance_rate_pct ?? 0) >= 95} warn={(d?.compliance_rate_pct ?? 100) < 80} />
        <KpiCard label="Avg COD Removal" value={pct(d?.avg_cod_removal_pct)} ok={(d?.avg_cod_removal_pct ?? 0) >= 85} />
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Compliance Trend</h3>
          <button onClick={() => reportsApi.exportWastewaterCompliance(params)} className="px-3 py-1.5 text-xs bg-teal-600 text-white rounded-lg hover:bg-teal-700">Export CSV</button>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={d?.trend ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" name="COD Removal %" stroke="#34d399" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="value2" name="Compliance %" stroke="#22c55e" dot={false} strokeWidth={1} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700 text-xs uppercase text-gray-500">
              <tr>
                {["Record", "DateTime", "Stage", "COD In", "COD Out", "COD Rmv %", "BOD In", "Eff pH", "DO", "Sludge", "Status"].map(h => (
                  <th key={h} className="px-3 py-3 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(d?.rows ?? []).map((row, i) => (
                <tr key={i} className={`hover:bg-gray-50 ${row.compliance_status === "NON_COMPLIANT" ? "bg-red-50/50 dark:bg-red-950/10" : ""}`}>
                  <td className="px-3 py-2 font-mono text-xs">{row.record_no}</td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{row.record_datetime.slice(0, 16)}</td>
                  <td className="px-3 py-2">{row.process_stage ?? "—"}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.influent_cod_mgl, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.effluent_cod_mgl, 0)}</td>
                  <td className="px-3 py-2 text-right">{pct(row.cod_removal_pct)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.influent_bod_mgl, 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.effluent_ph, 1)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.do_mgl, 1)}</td>
                  <td className="px-3 py-2 text-right">{fmt(row.sludge_produced_kg, 0)}</td>
                  <td className={`px-3 py-2 ${statusColor(row.compliance_status)}`}>{row.compliance_status ?? "—"}</td>
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

type Tab = "chemical" | "solar" | "wastewater";

export default function TreatmentPage() {
  const [dateFrom, setDateFrom] = useState(mtdStart);
  const [dateTo, setDateTo] = useState(today);
  const [tab, setTab] = useState<Tab>("chemical");

  const tabs: { id: Tab; label: string; color: string }[] = [
    { id: "chemical", label: "Chemical Treatment", color: "#34d399" },
    { id: "solar", label: "Solar Generation", color: "#facc15" },
    { id: "wastewater", label: "Wastewater Compliance", color: "#22c55e" },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/reports" className="text-sm text-gray-500 hover:text-blue-600">← Reports</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #34d399", paddingLeft: 12 }}>
            Treatment & Renewables
          </h1>
        </div>
        <DateFilter from={dateFrom} to={dateTo} onFrom={setDateFrom} onTo={setDateTo} />
      </div>

      <div className="flex gap-2">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.id ? "text-white" : "bg-white dark:bg-gray-800 text-gray-600 border border-gray-200 dark:border-gray-700"}`}
            style={tab === t.id ? { backgroundColor: t.color } : {}}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "chemical" && <ChemicalTab dateFrom={dateFrom} dateTo={dateTo} />}
      {tab === "solar" && <SolarTab dateFrom={dateFrom} dateTo={dateTo} />}
      {tab === "wastewater" && <WastewaterTab dateFrom={dateFrom} dateTo={dateTo} />}
    </div>
  );
}
