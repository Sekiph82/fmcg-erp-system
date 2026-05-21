"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import {
  kpiApi,
  UTILITY_CHART_COLORS,
  UTILITY_CHART_LABELS,
  type MainDashboardKPIs,
  type DailyTrendPoint,
  type TopConsumers,
} from "@/lib/utilityKpi";

// ── Helpers ───────────────────────────────────────────────────────────────────

const today = new Date().toISOString().slice(0, 10);
const mtdStart = today.slice(0, 8) + "01";

function fmt(n?: number | null, dp = 1) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

function pct(n?: number | null) {
  if (n == null) return "—";
  return `${fmt(n, 1)}%`;
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

type KpiStatus = "good" | "warn" | "critical" | "neutral" | "info";

function KpiCard({
  label, value, unit, sub, status = "neutral", estimated, href, children,
}: {
  label: string; value: string | number; unit?: string;
  sub?: string; status?: KpiStatus; estimated?: boolean; href?: string;
  children?: React.ReactNode;
}) {
  const borderMap: Record<KpiStatus, string> = {
    good:     "border-green-400 dark:border-green-500",
    warn:     "border-amber-400 dark:border-amber-400",
    critical: "border-red-500 dark:border-red-500",
    neutral:  "border-gray-200 dark:border-gray-700",
    info:     "border-blue-400 dark:border-blue-500",
  };
  const bgMap: Record<KpiStatus, string> = {
    good:     "bg-green-50 dark:bg-green-950/20",
    warn:     "bg-amber-50 dark:bg-amber-950/20",
    critical: "bg-red-50 dark:bg-red-950/20",
    neutral:  "bg-white dark:bg-gray-800",
    info:     "bg-blue-50 dark:bg-blue-950/20",
  };
  const card = (
    <div className={`rounded-xl border-2 p-4 ${borderMap[status]} ${bgMap[status]} h-full`}>
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-tight">{label}</p>
        {estimated && (
          <span className="text-[9px] bg-amber-100 dark:bg-amber-900/40 text-amber-700 px-1.5 py-0.5 rounded font-medium ml-1 shrink-0">EST</span>
        )}
      </div>
      <p className="text-xl font-bold text-gray-900 dark:text-white mt-1 leading-tight">
        {value}
        {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      {children}
    </div>
  );
  if (href) return <Link href={href} className="block hover:opacity-90 transition-opacity">{card}</Link>;
  return card;
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ title, href, color }: { title: string; href: string; color: string }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider"
        style={{ borderLeft: `3px solid ${color}`, paddingLeft: 8 }}>
        {title}
      </h2>
      <Link href={href}
        className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium">
        Full Dashboard →
      </Link>
    </div>
  );
}

// ── Alarm banner ──────────────────────────────────────────────────────────────

function AlarmBanner({ critical, warning, estimated }: {
  critical: number; warning: number; estimated: boolean;
}) {
  if (!critical && !warning && !estimated) return null;
  return (
    <div className="flex flex-wrap gap-3 mb-4">
      {critical > 0 && (
        <div className="flex items-center gap-2 bg-red-50 dark:bg-red-950/30 border border-red-300 dark:border-red-700 rounded-lg px-4 py-2">
          <span className="text-red-500 font-bold text-lg">!</span>
          <span className="text-sm font-semibold text-red-700 dark:text-red-400">
            {critical} Critical Alarm{critical > 1 ? "s" : ""}
          </span>
        </div>
      )}
      {warning > 0 && (
        <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-700 rounded-lg px-4 py-2">
          <span className="text-amber-500 font-bold text-lg">!</span>
          <span className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            {warning} Warning{warning > 1 ? "s" : ""}
          </span>
        </div>
      )}
      {estimated && (
        <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-950/30 border border-blue-300 dark:border-blue-700 rounded-lg px-4 py-2">
          <span className="text-blue-500 text-sm">~</span>
          <span className="text-sm text-blue-700 dark:text-blue-400">Some values are estimated</span>
        </div>
      )}
    </div>
  );
}

// ── Compliance badge ──────────────────────────────────────────────────────────

function ComplianceBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="text-gray-400">—</span>;
  const map: Record<string, { bg: string; label: string }> = {
    COMPLIANT:     { bg: "bg-green-100 text-green-700", label: "Compliant" },
    NON_COMPLIANT: { bg: "bg-red-100 text-red-700",   label: "Non-Compliant" },
    BORDERLINE:    { bg: "bg-amber-100 text-amber-700", label: "Borderline" },
    NOT_TESTED:    { bg: "bg-gray-100 text-gray-500",  label: "Not Tested" },
  };
  const s = map[status] ?? { bg: "bg-gray-100 text-gray-500", label: status };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${s.bg}`}>{s.label}</span>;
}

// ── Sub-dashboard navigation cards ───────────────────────────────────────────

const SUB_DASHBOARDS = [
  { label: "Electricity",          href: "/dashboard/utility-management/kpi-center/electricity",    color: "#fbbf24", icon: "⚡" },
  { label: "Water",                href: "/dashboard/utility-management/kpi-center/water",          color: "#60a5fa", icon: "💧" },
  { label: "Soft Water",           href: "/dashboard/utility-management/kpi-center/soft-water",     color: "#93c5fd", icon: "🌊" },
  { label: "Boiler / Steam",       href: "/dashboard/utility-management/kpi-center/boiler",         color: "#f97316", icon: "♨️" },
  { label: "Compressed Air",       href: "/dashboard/utility-management/kpi-center/compressor",     color: "#22d3ee", icon: "💨" },
  { label: "Solar",                href: "/dashboard/utility-management/kpi-center/solar",          color: "#facc15", icon: "☀️" },
  { label: "Chemicals",            href: "/dashboard/utility-management/kpi-center/chemicals",      color: "#86efac", icon: "🧪" },
  { label: "Wastewater",           href: "/dashboard/utility-management/kpi-center/wastewater",     color: "#6b7280", icon: "♻️" },
  { label: "Utility Cost",         href: "/dashboard/utility-management/kpi-center/utility-cost",   color: "#f472b6", icon: "💰" },
  { label: "Machine Utility",      href: "/dashboard/utility-management/kpi-center/machine-utility", color: "#a78bfa", icon: "⚙️" },
];

// ── Top consumers chart ───────────────────────────────────────────────────────

type ConsumerDim = "department" | "production_line" | "machine_ref";

function TopConsumersPanel({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const [dim, setDim] = useState<ConsumerDim>("department");
  const { data } = useQuery({
    queryKey: ["top-consumers", dim, dateFrom, dateTo],
    queryFn: () => kpiApi.topConsumers({ dimension: dim, date_from: dateFrom, date_to: dateTo }),
  });

  const rows = data?.rows ?? [];
  const dimLabels: Record<ConsumerDim, string> = {
    department: "Department",
    production_line: "Production Line",
    machine_ref: "Machine",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Top Consumers</h3>
        <div className="flex gap-1">
          {(Object.keys(dimLabels) as ConsumerDim[]).map(d => (
            <button key={d} onClick={() => setDim(d)}
              className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${
                dim === d ? "bg-blue-600 text-white" : "border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}>
              {dimLabels[d]}
            </button>
          ))}
        </div>
      </div>
      {rows.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={rows.slice(0, 8).map(r => ({ name: r.label.slice(0, 18), qty: Number(r.consumption), pct: r.pct_of_total }))}
            layout="vertical" margin={{ left: 110, right: 20, top: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10 }} />
            <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={108} />
            <Tooltip formatter={((v: number) => [fmt(v, 1), "Consumption"]) as never} />
            <Bar dataKey="qty" fill="#60a5fa" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-center text-gray-400 py-10 text-sm">No transaction data for this period.</p>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function UtilityKpiCenter() {
  const [dateFrom, setDateFrom]     = useState(mtdStart);
  const [dateTo, setDateTo]         = useState(today);
  const [reportDate, setReportDate] = useState(today);
  const [prodTons, setProdTons]     = useState<string>("");

  const mainQ = useQuery({
    queryKey: ["kpi-main", reportDate, prodTons],
    queryFn:  () => kpiApi.mainDashboard({
      report_date: reportDate,
      production_tons: prodTons ? +prodTons : undefined,
    }),
  });

  const trendQ = useQuery({
    queryKey: ["kpi-trend", dateFrom, dateTo],
    queryFn:  () => kpiApi.dailyTrend({ date_from: dateFrom, date_to: dateTo }),
  });

  const kpi   = mainQ.data;
  const trend = trendQ.data ?? [];

  const TREND_KEYS: Array<keyof DailyTrendPoint> = ["electricity_kwh", "water_m3", "gas_nm3", "steam_ton", "solar_kwh"];

  const inputCls = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Utilities KPI Center</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            All utility KPIs in one view — formulas computed server-side. EST tag = estimated data.
          </p>
        </div>
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500 uppercase">Report Date</label>
            <input type="date" className={inputCls} value={reportDate}
              onChange={e => setReportDate(e.target.value)} />
          </div>
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500 uppercase">Trend From</label>
            <input type="date" className={inputCls} value={dateFrom}
              onChange={e => setDateFrom(e.target.value)} />
          </div>
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500 uppercase">Trend To</label>
            <input type="date" className={inputCls} value={dateTo}
              onChange={e => setDateTo(e.target.value)} />
          </div>
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500 uppercase">Prod. Tons (today)</label>
            <input type="number" step="any" className={inputCls + " w-24"} placeholder="optional"
              value={prodTons} onChange={e => setProdTons(e.target.value)} />
          </div>
        </div>
      </div>

      {/* Alarm banner */}
      {kpi && (
        <AlarmBanner
          critical={kpi.critical_alarm_count}
          warning={kpi.warning_alarm_count}
          estimated={kpi.has_estimated_data}
        />
      )}

      {/* ── Electricity ── */}
      <section>
        <SectionHeader title="Electricity" href="/dashboard/utility-management/kpi-center/electricity" color="#fbbf24" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard label="kWh Today" value={fmt(kpi?.electricity_kwh_today)} unit="kWh" estimated={kpi?.has_estimated_data} href="/dashboard/utility-management/kpi-center/electricity" />
          <KpiCard label="kWh MTD" value={fmt(kpi?.electricity_kwh_mtd, 0)} unit="kWh" href="/dashboard/utility-management/kpi-center/electricity" />
          <KpiCard label="kWh / Ton" value={fmt(kpi?.electricity_kwh_per_ton)} unit="kWh/t" sub={kpi?.production_tons_today ? `${fmt(kpi.production_tons_today, 1)} t today` : "set prod. tons"} />
          <KpiCard label="Solar Today" value={fmt(kpi?.solar_kwh_today)} unit="kWh" status={kpi?.solar_kwh_today ? "good" : "neutral"} href="/dashboard/utility-management/kpi-center/solar" />
          <KpiCard label="Solar Contribution" value={pct(kpi?.solar_contribution_pct)} status={kpi?.solar_contribution_pct && kpi.solar_contribution_pct > 10 ? "good" : "neutral"} href="/dashboard/utility-management/kpi-center/solar" />
        </div>
      </section>

      {/* ── Water & Gas ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section>
          <SectionHeader title="Water" href="/dashboard/utility-management/kpi-center/water" color="#60a5fa" />
          <div className="grid grid-cols-3 gap-3">
            <KpiCard label="m³ Today" value={fmt(kpi?.water_m3_today, 2)} unit="m³" href="/dashboard/utility-management/kpi-center/water" />
            <KpiCard label="m³ / Ton" value={fmt(kpi?.water_m3_per_ton, 3)} unit="m³/t" />
            <KpiCard label="Soft Water m³" value={fmt(kpi?.soft_water_m3_today, 2)} unit="m³"
              sub={`Conv ${pct(kpi?.soft_water_conversion_pct)}`} href="/dashboard/utility-management/kpi-center/soft-water" />
          </div>
        </section>
        <section>
          <SectionHeader title="Gas" href="/dashboard/utility-management/kpi-center/boiler" color="#a78bfa" />
          <div className="grid grid-cols-3 gap-3">
            <KpiCard label="Nm³ Today" value={fmt(kpi?.gas_nm3_today)} unit="Nm³" />
            <KpiCard label="Nm³ / Ton" value={fmt(kpi?.gas_nm3_per_ton, 2)} unit="Nm³/t" />
            <KpiCard label="Gas / Ton Steam" value={fmt(kpi?.gas_per_ton_steam, 3)} unit="Nm³/t" href="/dashboard/utility-management/kpi-center/boiler" />
          </div>
        </section>
      </div>

      {/* ── Boiler / Steam ── */}
      <section>
        <SectionHeader title="Boiler / Steam" href="/dashboard/utility-management/kpi-center/boiler" color="#f97316" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard label="Steam Today" value={fmt(kpi?.steam_ton_today, 2)} unit="t" href="/dashboard/utility-management/kpi-center/boiler" />
          <KpiCard label="Boiler Efficiency" value={pct(kpi?.boiler_efficiency_pct)}
            status={kpi?.boiler_efficiency_pct && kpi.boiler_efficiency_pct > 80 ? "good" : kpi?.boiler_efficiency_pct && kpi.boiler_efficiency_pct < 70 ? "warn" : "neutral"} />
          <KpiCard label="Condensate Recovery" value={pct(kpi?.condensate_recovery_pct)}
            status={kpi?.condensate_recovery_pct && kpi.condensate_recovery_pct > 75 ? "good" : "warn"} />
          <KpiCard label="Blowdown Loss" value={pct(kpi?.blowdown_loss_pct)}
            status={kpi?.blowdown_loss_pct && kpi.blowdown_loss_pct > 5 ? "warn" : "good"} />
          <KpiCard label="Gas / Ton Steam" value={fmt(kpi?.gas_per_ton_steam, 3)} unit="Nm³/t" />
        </div>
      </section>

      {/* ── Compressed Air ── */}
      <section>
        <SectionHeader title="Compressed Air" href="/dashboard/utility-management/kpi-center/compressor" color="#22d3ee" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard label="Air Nm³ Today" value={fmt(kpi?.air_nm3_today)} unit="Nm³" href="/dashboard/utility-management/kpi-center/compressor" />
          <KpiCard label="kWh / Nm³" value={fmt(kpi?.air_kwh_per_nm3, 4)} unit="kWh/Nm³"
            status={kpi?.air_kwh_per_nm3 && kpi.air_kwh_per_nm3 < 0.12 ? "good" : kpi?.air_kwh_per_nm3 && kpi.air_kwh_per_nm3 > 0.15 ? "warn" : "neutral"} />
          <KpiCard label="Leak Estimate" value={pct(kpi?.leak_estimate_pct)}
            status={kpi?.leak_estimate_pct && kpi.leak_estimate_pct > 15 ? "critical" : kpi?.leak_estimate_pct && kpi.leak_estimate_pct > 8 ? "warn" : "good"} />
          <KpiCard label="Compressor Load" value={pct(kpi?.compressor_efficiency_pct)}
            status={kpi?.compressor_efficiency_pct && kpi.compressor_efficiency_pct > 85 ? "warn" : "good"} />
        </div>
      </section>

      {/* ── Soft Water ── */}
      <section>
        <SectionHeader title="Soft Water" href="/dashboard/utility-management/kpi-center/soft-water" color="#93c5fd" />
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Soft Water m³" value={fmt(kpi?.soft_water_m3_today, 2)} unit="m³" href="/dashboard/utility-management/kpi-center/soft-water" />
          <KpiCard label="Conversion Efficiency" value={pct(kpi?.soft_water_conversion_pct)}
            status={kpi?.soft_water_conversion_pct && kpi.soft_water_conversion_pct > 85 ? "good" : "warn"} />
          <KpiCard label="Salt per m³" value={fmt(kpi?.salt_per_m3_soft, 3)} unit="kg/m³" />
        </div>
      </section>

      {/* ── Wastewater ── */}
      <section>
        <SectionHeader title="Wastewater Treatment" href="/dashboard/utility-management/kpi-center/wastewater" color="#6b7280" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard label="COD Removal" value={pct(kpi?.cod_removal_pct)}
            status={kpi?.cod_removal_pct && kpi.cod_removal_pct > 90 ? "good" : kpi?.cod_removal_pct && kpi.cod_removal_pct < 80 ? "critical" : "warn"}
            href="/dashboard/utility-management/kpi-center/wastewater" />
          <KpiCard label="Compliance Status" value="" sub={undefined}>
            <div className="mt-2"><ComplianceBadge status={kpi?.wastewater_compliance} /></div>
          </KpiCard>
          <KpiCard label="Treatment Cost/m³" value={fmt(kpi?.wastewater_cost_per_m3, 4)} unit="$/m³" />
          <KpiCard label="Chemical Cost Today" value={fmt(kpi?.chemical_cost_today)} unit="$"
            href="/dashboard/utility-management/kpi-center/chemicals" />
        </div>
      </section>

      {/* ── Cost ── */}
      <section>
        <SectionHeader title="Utility Cost" href="/dashboard/utility-management/kpi-center/utility-cost" color="#f472b6" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard label="Cost Today" value={fmt(kpi?.utility_cost_today)} unit={kpi?.currency_code ?? "USD"} href="/dashboard/utility-management/kpi-center/utility-cost" />
          <KpiCard label="Cost MTD" value={fmt(kpi?.utility_cost_mtd, 0)} unit={kpi?.currency_code ?? "USD"} />
          <KpiCard label="Cost / Ton" value={fmt(kpi?.utility_cost_per_ton, 4)} unit={`${kpi?.currency_code ?? "USD"}/t`} />
          <KpiCard label="Cost / Batch" value={fmt(kpi?.utility_cost_per_batch, 4)} unit={kpi?.currency_code ?? "USD"} />
        </div>
      </section>

      {/* ── Machine Utility ── */}
      <section>
        <SectionHeader title="Machine Utility" href="/dashboard/utility-management/kpi-center/machine-utility" color="#a78bfa" />
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Standby Consumption" value={pct(kpi?.machine_standby_pct)}
            status={kpi?.machine_standby_pct && kpi.machine_standby_pct > 20 ? "warn" : "good"}
            href="/dashboard/utility-management/kpi-center/machine-utility" />
          <KpiCard label="Machine Cost / Batch" value={fmt(kpi?.utility_cost_per_batch, 4)} unit={kpi?.currency_code ?? "USD"} />
          <KpiCard label="Dept. Utility Intensity" value={fmt(kpi?.dept_utility_intensity, 4)} />
        </div>
      </section>

      {/* ── Multi-utility trend chart ── */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
          Multi-Utility Daily Trend
          <span className="text-xs font-normal text-gray-400 ml-2">{dateFrom} → {dateTo}</span>
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }}
              tickFormatter={d => d.slice(5)} />
            <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
            <Tooltip
              formatter={((v: number, name: string) => [
                (v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 }),
                UTILITY_CHART_LABELS[name as keyof typeof UTILITY_CHART_LABELS] ?? name,
              ]) as never}
              labelFormatter={l => `Date: ${l}`}
            />
            <Legend formatter={name => UTILITY_CHART_LABELS[name] ?? name} />
            {TREND_KEYS.filter(k => trend.some(t => t[k] != null)).map(key => (
              <Line key={key} yAxisId="left" type="monotone" dataKey={key}
                stroke={UTILITY_CHART_COLORS[key] ?? "#9ca3af"}
                dot={false} strokeWidth={2}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── Top consumers ── */}
      <TopConsumersPanel dateFrom={dateFrom} dateTo={dateTo} />

      {/* ── Sub-dashboard navigation ── */}
      <div>
        <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">
          Specialized Dashboards
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {SUB_DASHBOARDS.map(s => (
            <Link key={s.href} href={s.href}
              className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow group">
              <span className="text-2xl">{s.icon}</span>
              <div>
                <p className="text-sm font-semibold text-gray-800 dark:text-white group-hover:text-blue-600">{s.label}</p>
                <p className="text-xs text-gray-400">View KPIs →</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

// Override for the compliance card that needs a child (workaround)
KpiCard.displayName = "KpiCard";
