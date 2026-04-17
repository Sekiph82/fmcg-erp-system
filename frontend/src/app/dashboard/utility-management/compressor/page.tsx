"use client";

/**
 * Compressor & Compressed Air Management Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Plant-wide compressed air monitoring with KPIs, trend charts, shift analysis,
 * cost breakdown, and compressor records CRUD.
 *
 * Sections:
 *   1. Scope filters (date, asset, department, shift, line)
 *   2. KPI strip with anomaly flags
 *   3. Daily trend — air volume + electricity + specific energy
 *   4. Shift analysis + cost breakdown by dimension
 *   5. Compressor records table (CRUD + export + import)
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import {
  compressorApi,
  downloadCompressorCsv,
  COMPRESSOR_STATUS_LABELS,
  COMPRESSOR_STATUS_COLORS,
  COMPRESSOR_STATUS_BG,
  DRYER_STATUS_COLORS,
  type CompressorRecord,
  type CompressorRecordCreate,
  type CompressorRecordUpdate,
  type CompressorAsset,
  type CompressorFilters,
  type CompressorStatus,
} from "@/lib/compressor";
import { importApi, type ImportResult } from "@/lib/importApi";

// ── Palette ─────────────────────────────────────────────────────────────────
const SKY    = "#38bdf8";
const GREEN  = "#4ade80";
const AMBER  = "#fbbf24";
const ORANGE = "#fb923c";
const RED    = "#f87171";
const VIOLET = "#a78bfa";
const SLATE  = "#94a3b8";
const TEAL   = "#2dd4bf";

const BAR_COLORS = [
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
  "#f59e0b", "#10b981", "#ef4444", "#6366f1",
];

// ── Helpers ──────────────────────────────────────────────────────────────────
const n = (v: number | string | null | undefined, dp = 1) =>
  v != null ? parseFloat(String(v)).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

const fmtDate = (d: string) => {
  try { return new Date(d).toLocaleDateString(); } catch { return d; }
};

// ── KPI Card ─────────────────────────────────────────────────────────────────
interface KPICardProps {
  label:    string;
  value:    React.ReactNode;
  sub?:     React.ReactNode;
  accent?:  string;
  flag?:    boolean;
  flagMsg?: string;
}
function KPICard({ label, value, sub, accent = "border-slate-700", flag, flagMsg }: KPICardProps) {
  return (
    <div className={`bg-slate-800 border rounded-lg p-4 flex flex-col gap-1 ${flag ? "border-red-500/60" : accent}`}>
      <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
      <span className="text-xl font-semibold text-white">{value}</span>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
      {flag && flagMsg && <span className="text-xs text-red-400 font-medium">{flagMsg}</span>}
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: CompressorStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${COMPRESSOR_STATUS_BG[status]} ${COMPRESSOR_STATUS_COLORS[status]}`}>
      {COMPRESSOR_STATUS_LABELS[status]}
    </span>
  );
}

// ── Import Modal ──────────────────────────────────────────────────────────────
function ImportModal({ module, label, onClose }: { module: string; label: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [file, setFile]     = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy]     = useState(false);
  const [err, setErr]       = useState<string | null>(null);

  const run = async (doImport: boolean) => {
    if (!file) return;
    setBusy(true); setErr(null); setResult(null);
    try {
      const r = doImport
        ? await importApi.runImport(module, file)
        : await importApi.validate(module, file);
      setResult(r);
      if (doImport && r.imported) {
        qc.invalidateQueries({ queryKey: ["cpr-records"] });
        qc.invalidateQueries({ queryKey: ["cpr-kpis"] });
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Unknown error");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-lg p-6 space-y-4">
        <h3 className="text-white font-semibold text-lg">Import {label}</h3>
        <div className="space-y-2">
          <button onClick={() => importApi.downloadTemplate(module)}
            className="text-xs text-sky-400 hover:text-sky-300 underline">
            Download CSV template
          </button>
          <input type="file" accept=".csv"
            onChange={e => setFile(e.target.files?.[0] ?? null)}
            className="block text-sm text-slate-300" />
        </div>
        {err && <p className="text-red-400 text-sm">{err}</p>}
        {result && (
          <div className="text-sm space-y-1">
            <p className="text-slate-300">Rows: {result.total_rows} | Valid: {result.valid_rows} | Failed: {result.failed_rows}</p>
            {result.errors.slice(0, 5).map((e, i) => (
              <p key={i} className="text-red-400">Row {e.row}: {e.message}</p>
            ))}
            {result.imported && <p className="text-emerald-400 font-medium">Import complete.</p>}
          </div>
        )}
        <div className="flex gap-2 pt-2">
          <button disabled={!file || busy} onClick={() => run(false)}
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded disabled:opacity-40">
            {busy ? "…" : "Validate"}
          </button>
          <button disabled={!file || busy} onClick={() => run(true)}
            className="px-3 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 text-white rounded disabled:opacity-40">
            {busy ? "…" : "Import"}
          </button>
          <button onClick={onClose} className="ml-auto px-3 py-1.5 text-sm text-slate-400 hover:text-white">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CompressorPage() {
  const qc = useQueryClient();

  // ── Scope filters ────────────────────────────────────────────────────────
  const [dateFrom,    setDateFrom]    = useState("");
  const [dateTo,      setDateTo]      = useState("");
  const [assetId,     setAssetId]     = useState("");
  const [department,  setDepartment]  = useState("");
  const [shiftRef,    setShiftRef]    = useState("");
  const [prodLine,    setProdLine]    = useState("");

  const scope: Partial<CompressorFilters> = useMemo(() => ({
    ...(dateFrom   && { date_from:  dateFrom }),
    ...(dateTo     && { date_to:    dateTo }),
    ...(assetId    && { asset_id:   assetId }),
    ...(department && { department }),
    ...(shiftRef   && { shift_ref:  shiftRef }),
    ...(prodLine   && { prod_line:  prodLine }),
  }), [dateFrom, dateTo, assetId, department, shiftRef, prodLine]);

  // ── Data ─────────────────────────────────────────────────────────────────
  const { data: assets = [] } = useQuery({
    queryKey: ["cpr-assets"],
    queryFn:  () => compressorApi.listAssets(),
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["cpr-kpis", scope],
    queryFn:  () => compressorApi.kpis(scope),
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["cpr-trend", scope],
    queryFn:  () => compressorApi.dailyTrend(scope),
  });

  const { data: shifts = [] } = useQuery({
    queryKey: ["cpr-shifts", scope],
    queryFn:  () => compressorApi.shiftAnalysis(scope),
  });

  const [bdDim, setBdDim] = useState<
    "department" | "line" | "machine" | "building_area" | "shift"
  >("department");

  const { data: breakdown } = useQuery({
    queryKey: ["cpr-breakdown", bdDim, scope],
    queryFn:  () => compressorApi.breakdown(bdDim, scope),
  });

  // ── Records ───────────────────────────────────────────────────────────────
  const [recPage, setRecPage] = useState(0);
  const REC_LIMIT = 50;

  const { data: records = [], isLoading: recsLoading } = useQuery({
    queryKey: ["cpr-records", scope, recPage],
    queryFn:  () => compressorApi.listRecords({ ...scope, skip: recPage * REC_LIMIT, limit: REC_LIMIT }),
  });

  // ── Modals ────────────────────────────────────────────────────────────────
  const [viewRec,     setViewRec]     = useState<CompressorRecord | null>(null);
  const [editRec,     setEditRec]     = useState<CompressorRecord | null>(null);
  const [createOpen,  setCreateOpen]  = useState(false);
  const [deleteRec,   setDeleteRec]   = useState<CompressorRecord | null>(null);
  const [importModule, setImportModule] = useState<string | null>(null);

  // ── Mutations ─────────────────────────────────────────────────────────────
  const invAll = () => {
    qc.invalidateQueries({ queryKey: ["cpr-records"] });
    qc.invalidateQueries({ queryKey: ["cpr-kpis"] });
  };

  const createMut = useMutation({
    mutationFn: (d: CompressorRecordCreate) => compressorApi.createRecord(d),
    onSuccess: () => { invAll(); setCreateOpen(false); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CompressorRecordUpdate }) =>
      compressorApi.updateRecord(id, data),
    onSuccess: () => { invAll(); setEditRec(null); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => compressorApi.deleteRecord(id),
    onSuccess: () => { invAll(); setDeleteRec(null); },
  });

  // ── Form ──────────────────────────────────────────────────────────────────
  const emptyForm = (): Partial<CompressorRecordCreate> => ({
    asset_id: "",
    record_datetime: new Date().toISOString().slice(0, 16),
    air_unit: "Nm3",
    status: "RUNNING",
    source_method: "MANUAL",
    maintenance_flag: false,
    leak_test_done: false,
    is_anomaly: false,
  });

  const [form, setForm] = useState<Partial<CompressorRecordCreate>>(emptyForm());
  const fSet = (k: keyof CompressorRecordCreate, v: unknown) =>
    setForm(p => ({ ...p, [k]: v }));

  // ── Chart data prep ───────────────────────────────────────────────────────
  const trendData = useMemo(() =>
    trend.map(t => ({
      day:     t.date.slice(5),
      air:     +parseFloat(String(t.air_nm3)).toFixed(0),
      elec:    +parseFloat(String(t.electricity_kwh)).toFixed(1),
      se:      t.avg_specific_energy != null ? +parseFloat(String(t.avg_specific_energy)).toFixed(4) : null,
      idle:    +parseFloat(String(t.idle_hours)).toFixed(2),
      night:   +parseFloat(String(t.night_kwh)).toFixed(1),
    }))
  , [trend]);

  const shiftData = useMemo(() =>
    shifts.map(s => ({
      label: s.label,
      air:   +parseFloat(String(s.air_nm3)).toFixed(0),
      elec:  +parseFloat(String(s.electricity_kwh)).toFixed(1),
    }))
  , [shifts]);

  const bdData = useMemo(() =>
    (breakdown?.rows ?? []).slice(0, 8).map(r => ({
      label:    r.label.slice(0, 18),
      air:      +parseFloat(String(r.total_nm3)).toFixed(0),
      cost:     r.total_cost != null ? +parseFloat(String(r.total_cost)).toFixed(0) : null,
      pct:      r.pct_of_total != null ? +parseFloat(String(r.pct_of_total)).toFixed(1) : null,
    }))
  , [breakdown]);

  const K = kpis;

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0d1117] text-white space-y-6 p-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Compressor &amp; Compressed Air</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Operational records, KPI monitoring, and cost allocation for plant air systems
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setImportModule("compressor_records")}
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded text-slate-200">
            Import Records
          </button>
          <button onClick={() => setImportModule("air_transactions")}
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded text-slate-200">
            Import Transactions
          </button>
          <button onClick={() => { setForm(emptyForm()); setCreateOpen(true); }}
            className="px-3 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 rounded text-white">
            + Add Record
          </button>
        </div>
      </div>

      {/* Scope filters */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            ["Date From", "date", dateFrom, setDateFrom],
            ["Date To",   "date", dateTo,   setDateTo],
          ].map(([lbl, type, val, setter]) => (
            <div key={String(lbl)}>
              <label className="text-xs text-slate-400 block mb-1">{String(lbl)}</label>
              <input type={String(type)} value={String(val)}
                onChange={e => (setter as (v: string) => void)(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
            </div>
          ))}
          <div>
            <label className="text-xs text-slate-400 block mb-1">Compressor</label>
            <select value={assetId} onChange={e => setAssetId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white">
              <option value="">All</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Department</label>
            <input type="text" value={department} onChange={e => setDepartment(e.target.value)}
              placeholder="e.g. Utilities"
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white placeholder-slate-500" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Shift</label>
            <select value={shiftRef} onChange={e => setShiftRef(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white">
              <option value="">All</option>
              {["A","B","C","Day","Night"].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Line</label>
            <input type="text" value={prodLine} onChange={e => setProdLine(e.target.value)}
              placeholder="e.g. LINE-01"
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white placeholder-slate-500" />
          </div>
        </div>
      </div>

      {/* KPI strip */}
      {kpisLoading ? (
        <div className="text-slate-400 text-sm">Loading KPIs…</div>
      ) : K && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          <KPICard label="Air Generated"
            value={`${n(K.total_air_nm3, 0)} Nm³`}
            accent="border-sky-500/40" />
          <KPICard label="Electricity Used"
            value={`${n(K.total_electricity_kwh, 1)} kWh`}
            accent="border-yellow-500/40" />
          <KPICard label="Specific Energy"
            value={K.specific_energy_kwh_nm3 != null ? `${n(K.specific_energy_kwh_nm3, 4)} kWh/Nm³` : "—"}
            sub="Target: < 0.12 kWh/Nm³"
            flag={K.flag_poor_efficiency}
            flagMsg="Above 0.12 — check leaks/idle"
            accent="border-orange-500/40" />
          <KPICard label="Utilisation"
            value={K.utilization_pct != null ? `${n(K.utilization_pct, 1)}%` : "—"}
            sub={K.total_runtime_hours != null ? `${n(K.total_runtime_hours, 1)} h runtime` : undefined}
            accent="border-green-500/40" />
          <KPICard label="Idle Run Ratio"
            value={K.idle_run_ratio != null ? `${n(K.idle_run_ratio, 1)}%` : "—"}
            sub={K.total_idle_hours != null ? `${n(K.total_idle_hours, 1)} h idle` : undefined}
            flag={K.flag_high_idle}
            flagMsg="Above 20% — investigate demand"
            accent="border-amber-500/40" />
          <KPICard label="Discharge Pressure"
            value={K.avg_discharge_pressure_bar != null ? `${n(K.avg_discharge_pressure_bar, 2)} bar` : "—"}
            sub={K.avg_line_pressure_bar != null ? `Line: ${n(K.avg_line_pressure_bar, 2)} bar` : undefined}
            accent="border-blue-500/40" />
          <KPICard label="Pressure Drop"
            value={K.avg_pressure_drop_bar != null ? `${n(K.avg_pressure_drop_bar, 3)} bar` : "—"}
            flag={K.flag_pressure_drop}
            flagMsg="Above 0.3 bar — check distribution"
            accent="border-violet-500/40" />
          <KPICard label="Leak Estimate"
            value={K.avg_leak_pct != null ? `${n(K.avg_leak_pct, 1)}%` : "—"}
            sub={K.total_leak_nm3 != null ? `${n(K.total_leak_nm3, 0)} Nm³ lost` : undefined}
            flag={K.flag_leak_detected}
            flagMsg="Above 5% — schedule leak hunt"
            accent="border-red-500/40" />
          <KPICard label="Night Consumption"
            value={K.total_night_kwh != null ? `${n(K.total_night_kwh, 1)} kWh` : "—"}
            sub={K.night_pct != null ? `${n(K.night_pct, 1)}% of total` : undefined}
            flag={K.flag_high_night}
            flagMsg="Above 15% of total — check auto-stop"
            accent="border-teal-500/40" />
          <KPICard label="Air Cost / Nm³"
            value={K.air_cost_per_nm3 != null ? `$${n(K.air_cost_per_nm3, 4)}` : "—"}
            sub={K.air_cost_total != null ? `Total: $${n(K.air_cost_total, 0)}` : undefined}
            accent="border-emerald-500/40" />
          <KPICard label="Dryer Dew Point"
            value={K.avg_dryer_dew_point_c != null ? `${n(K.avg_dryer_dew_point_c, 1)} °C` : "—"}
            sub="Target: ≤ −20 °C PDP"
            accent="border-slate-600" />
          <KPICard label="Records / Anomalies"
            value={`${K.record_count}`}
            sub={`${K.anomaly_count} anomalies · ${K.maintenance_count} maint · ${K.start_stop_total} starts`}
            accent="border-slate-600" />
        </div>
      )}

      {/* Daily trend — air + electricity */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-medium text-slate-200">Daily Trend — Air Volume &amp; Electricity</h2>
        {trendData.length === 0 ? (
          <p className="text-slate-500 text-sm py-8 text-center">No data in selected range</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="airGrad"  x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={SKY}    stopOpacity={0.3} />
                  <stop offset="95%" stopColor={SKY}    stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="elecGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={AMBER}  stopOpacity={0.3} />
                  <stop offset="95%" stopColor={AMBER}  stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis yAxisId="left"  tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" Nm³" />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" kWh" />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                labelStyle={{ color: "#cbd5e1" }} itemStyle={{ color: "#e2e8f0" }} />
              <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
              <Area yAxisId="left"  type="monotone" dataKey="air"  name="Air (Nm³)" stroke={SKY}   fill="url(#airGrad)"  strokeWidth={2} dot={false} />
              <Area yAxisId="right" type="monotone" dataKey="elec" name="Electricity (kWh)" stroke={AMBER} fill="url(#elecGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Specific energy trend */}
      {trendData.some(t => t.se != null) && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-slate-200">Specific Energy — kWh/Nm³</h2>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                itemStyle={{ color: "#e2e8f0" }} />
              <Line type="monotone" dataKey="se" name="kWh/Nm³" stroke={ORANGE} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Shift + Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Shift */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-slate-200">Shift Analysis</h2>
          {shiftData.length === 0 ? (
            <p className="text-slate-500 text-sm py-6 text-center">No shift data</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={shiftData} layout="vertical" margin={{ top: 0, right: 16, left: 40, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" Nm³" />
                <YAxis dataKey="label" type="category" tick={{ fill: "#94a3b8", fontSize: 11 }} width={40} />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                  itemStyle={{ color: "#e2e8f0" }} />
                <Bar dataKey="air" name="Air (Nm³)" radius={[0, 4, 4, 0]}>
                  {shiftData.map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Breakdown */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-200">Air Consumption Breakdown</h2>
            <select value={bdDim} onChange={e => setBdDim(e.target.value as typeof bdDim)}
              className="text-xs bg-slate-700 border border-slate-600 rounded px-2 py-1 text-white">
              {(["department","line","machine","building_area","shift"] as const).map(d => (
                <option key={d} value={d}>{d.replace("_"," ")}</option>
              ))}
            </select>
          </div>
          {bdData.length === 0 ? (
            <p className="text-slate-500 text-sm py-6 text-center">No transaction data</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={bdData} layout="vertical" margin={{ top: 0, right: 16, left: 60, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" Nm³" />
                <YAxis dataKey="label" type="category" tick={{ fill: "#94a3b8", fontSize: 11 }} width={60} />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                  itemStyle={{ color: "#e2e8f0" }} />
                <Bar dataKey="air" name="Air (Nm³)" radius={[0, 4, 4, 0]}>
                  {bdData.map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {(breakdown?.rows ?? []).length > 0 && (
            <table className="w-full text-xs mt-2">
              <thead>
                <tr className="text-slate-400 text-left">
                  <th className="pb-1">Group</th>
                  <th className="pb-1 text-right">Nm³</th>
                  <th className="pb-1 text-right">%</th>
                  <th className="pb-1 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {(breakdown?.rows ?? []).map((r, i) => (
                  <tr key={i} className="border-t border-slate-700">
                    <td className="py-1 text-slate-300">{r.label}</td>
                    <td className="py-1 text-right text-slate-300">{n(r.total_nm3, 0)}</td>
                    <td className="py-1 text-right text-slate-400">{r.pct_of_total != null ? `${n(r.pct_of_total, 1)}%` : "—"}</td>
                    <td className="py-1 text-right text-slate-400">{r.total_cost != null ? `$${n(r.total_cost, 0)}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Records table */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <h2 className="text-sm font-medium text-slate-200">Compressor Operational Records</h2>
          <button
            onClick={() => downloadCompressorCsv(scope as Record<string, string | number | boolean | undefined>, "compressor_records.csv")}
            className="text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded">
            Export CSV
          </button>
        </div>

        {recsLoading ? (
          <div className="p-6 text-slate-400 text-sm">Loading records…</div>
        ) : records.length === 0 ? (
          <div className="p-6 text-slate-500 text-sm text-center">No records found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900/40">
                <tr className="text-xs text-slate-400 text-left">
                  <th className="px-4 py-2">Record No.</th>
                  <th className="px-4 py-2">Asset</th>
                  <th className="px-4 py-2">Date/Time</th>
                  <th className="px-4 py-2">Shift</th>
                  <th className="px-4 py-2 text-right">Air (Nm³)</th>
                  <th className="px-4 py-2 text-right">kWh</th>
                  <th className="px-4 py-2 text-right">SE (kWh/Nm³)</th>
                  <th className="px-4 py-2 text-right">Load %</th>
                  <th className="px-4 py-2 text-right">Idle %</th>
                  <th className="px-4 py-2">Dryer</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2 text-center">Flags</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {records.map(rec => {
                  const loadPct = rec.load_time_hours != null && rec.runtime_hours
                    ? (rec.load_time_hours / rec.runtime_hours * 100).toFixed(1)
                    : null;
                  const idlePct = rec.idle_time_hours != null && rec.runtime_hours
                    ? (rec.idle_time_hours / rec.runtime_hours * 100).toFixed(1)
                    : null;
                  return (
                    <tr key={rec.id}
                      className={`hover:bg-slate-700/30 cursor-pointer ${rec.is_anomaly ? "border-l-2 border-red-500" : ""}`}
                      onClick={() => setViewRec(rec)}>
                      <td className="px-4 py-2 font-mono text-xs text-slate-300">{rec.record_no}</td>
                      <td className="px-4 py-2 text-slate-300">{rec.asset_name ?? rec.asset_no ?? "—"}</td>
                      <td className="px-4 py-2 text-slate-400">{fmtDate(rec.record_datetime)}</td>
                      <td className="px-4 py-2 text-slate-400">{rec.shift_ref ?? "—"}</td>
                      <td className="px-4 py-2 text-right text-slate-300">{n(rec.air_generated_nm3, 0)}</td>
                      <td className="px-4 py-2 text-right text-slate-400">{n(rec.electricity_used_kwh, 1)}</td>
                      <td className="px-4 py-2 text-right">
                        {rec.specific_energy_kwh_m3 != null ? (
                          <span className={+rec.specific_energy_kwh_m3 > 0.12 ? "text-red-400" : "text-emerald-400"}>
                            {n(rec.specific_energy_kwh_m3, 4)}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-400">{loadPct != null ? `${loadPct}%` : "—"}</td>
                      <td className="px-4 py-2 text-right">
                        {idlePct != null ? (
                          <span className={+idlePct > 20 ? "text-red-400" : "text-slate-400"}>{idlePct}%</span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {rec.dryer_status ? (
                          <span className={`text-xs font-medium ${DRYER_STATUS_COLORS[rec.dryer_status] ?? "text-slate-400"}`}>
                            {rec.dryer_status}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-2">
                        <StatusBadge status={rec.status as CompressorStatus} />
                      </td>
                      <td className="px-4 py-2 text-center text-sm">
                        {rec.is_anomaly       && <span title="Anomaly" className="text-red-400 mr-1">⚠</span>}
                        {rec.leak_test_done   && <span title="Leak test done" className="text-amber-400 mr-1">🔍</span>}
                        {rec.maintenance_flag && <span title="Maintenance" className="text-violet-400">🔧</span>}
                      </td>
                      <td className="px-4 py-2" onClick={e => e.stopPropagation()}>
                        <div className="flex gap-2 justify-end">
                          <button onClick={() => { setForm({ ...rec }); setEditRec(rec); }}
                            className="text-xs text-sky-400 hover:text-sky-300">Edit</button>
                          <button onClick={() => setDeleteRec(rec)}
                            className="text-xs text-red-400 hover:text-red-300">Delete</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-700 text-xs text-slate-400">
          <span>Showing {recPage * REC_LIMIT + 1}–{recPage * REC_LIMIT + records.length}</span>
          <div className="flex gap-2">
            <button disabled={recPage === 0} onClick={() => setRecPage(p => p - 1)}
              className="px-2 py-1 bg-slate-700 rounded disabled:opacity-40">Prev</button>
            <button disabled={records.length < REC_LIMIT} onClick={() => setRecPage(p => p + 1)}
              className="px-2 py-1 bg-slate-700 rounded disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>

      {/* ══════════════ MODALS ══════════════ */}

      {/* View */}
      {viewRec && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-white font-semibold text-lg">{viewRec.record_no}</h3>
                <p className="text-xs text-slate-400">{viewRec.asset_name ?? viewRec.asset_no} · {fmtDate(viewRec.record_datetime)}</p>
              </div>
              <StatusBadge status={viewRec.status as CompressorStatus} />
            </div>
            {(viewRec.is_anomaly || viewRec.maintenance_flag || viewRec.leak_test_done) && (
              <div className="flex gap-2 flex-wrap">
                {viewRec.is_anomaly && (
                  <span className="px-2 py-0.5 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">
                    Anomaly: {viewRec.anomaly_note ?? "flagged"}
                  </span>
                )}
                {viewRec.maintenance_flag && (
                  <span className="px-2 py-0.5 bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs rounded">
                    Maintenance flag
                  </span>
                )}
                {viewRec.leak_test_done && (
                  <span className="px-2 py-0.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs rounded">
                    Leak test done
                    {viewRec.leak_estimation_pct != null ? ` — ${viewRec.leak_estimation_pct}% estimated` : ""}
                  </span>
                )}
              </div>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
              {[
                ["Shift",               viewRec.shift_ref],
                ["Department",          viewRec.department],
                ["Production Line",     viewRec.production_line],
                ["Period (h)",          viewRec.period_hours],
                ["Air Generated",       viewRec.air_generated_nm3 != null ? `${n(viewRec.air_generated_nm3, 0)} ${viewRec.air_unit ?? "Nm³"}` : null],
                ["Electricity Used",    viewRec.electricity_used_kwh != null ? `${viewRec.electricity_used_kwh} kWh` : null],
                ["Runtime (h)",         viewRec.runtime_hours],
                ["Load Time (h)",       viewRec.load_time_hours],
                ["Unload Time (h)",     viewRec.unload_time_hours],
                ["Idle Time (h)",       viewRec.idle_time_hours],
                ["Discharge (bar)",     viewRec.discharge_pressure_bar],
                ["System (bar)",        viewRec.system_pressure_bar],
                ["Receiver (bar)",      viewRec.receiver_tank_pressure_bar],
                ["Line (bar)",          viewRec.line_pressure_bar],
                ["Filter ΔP (bar)",     viewRec.filter_dp_bar],
                ["Dryer Status",        viewRec.dryer_status],
                ["Dryer Dew Point",     viewRec.dryer_dew_point_c != null ? `${viewRec.dryer_dew_point_c} °C` : null],
                ["Spec. Energy",        viewRec.specific_energy_kwh_m3 != null ? `${viewRec.specific_energy_kwh_m3} kWh/Nm³` : null],
                ["Leak Estimate",       viewRec.leak_estimation_pct != null ? `${viewRec.leak_estimation_pct}%` : null],
                ["Night Idle kWh",      viewRec.night_idle_kwh],
                ["Start-Stops",         viewRec.start_stop_count],
                ["Downtime (min)",      viewRec.downtime_minutes],
                ["Downtime Reason",     viewRec.downtime_reason],
                ["Notes",               viewRec.notes],
              ].map(([lbl, val]) =>
                val != null ? (
                  <div key={String(lbl)} className="flex flex-col">
                    <span className="text-xs text-slate-400">{lbl}</span>
                    <span className="text-slate-200">{String(val)}</span>
                  </div>
                ) : null
              )}
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => { setForm({ ...viewRec }); setEditRec(viewRec); setViewRec(null); }}
                className="px-3 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 text-white rounded">Edit</button>
              <button onClick={() => setViewRec(null)} className="px-3 py-1.5 text-sm text-slate-400 hover:text-white">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit form */}
      {(createOpen || editRec) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <h3 className="text-white font-semibold text-lg">
              {editRec ? "Edit Compressor Record" : "New Compressor Record"}
            </h3>

            {/* Identity */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Compressor Asset *</label>
                <select value={form.asset_id ?? ""}
                  onChange={e => fSet("asset_id", e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white">
                  <option value="">Select asset…</option>
                  {assets.map(a => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Record Date/Time *</label>
                <input type="datetime-local" value={(form.record_datetime ?? "").slice(0, 16)}
                  onChange={e => fSet("record_datetime", e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Shift</label>
                <select value={form.shift_ref ?? ""}
                  onChange={e => fSet("shift_ref", e.target.value || undefined)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white">
                  <option value="">—</option>
                  {["A","B","C","Day","Night"].map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Department</label>
                <input type="text" value={form.department ?? ""}
                  onChange={e => fSet("department", e.target.value || undefined)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white placeholder-slate-500"
                  placeholder="e.g. Utilities" />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Production Line</label>
                <input type="text" value={form.production_line ?? ""}
                  onChange={e => fSet("production_line", e.target.value || undefined)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white placeholder-slate-500"
                  placeholder="e.g. LINE-01" />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Status</label>
                <select value={form.status ?? "RUNNING"}
                  onChange={e => fSet("status", e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white">
                  {(["RUNNING","STANDBY","FAULT","MAINTENANCE"] as CompressorStatus[]).map(s => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Production & time */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Air Production &amp; Time Breakdown</legend>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["Period Hours",       "period_hours"],
                  ["Air Generated (Nm³)","air_generated_nm3"],
                  ["Electricity (kWh)",  "electricity_used_kwh"],
                  ["Runtime (h)",        "runtime_hours"],
                  ["Load Time (h)",      "load_time_hours"],
                  ["Unload Time (h)",    "unload_time_hours"],
                  ["Idle Time (h)",      "idle_time_hours"],
                  ["Start-Stops",        "start_stop_count"],
                  ["Downtime (min)",     "downtime_minutes"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof CompressorRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Pressure */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Pressure Points (bar)</legend>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["Inlet",          "inlet_pressure_bar"],
                  ["Discharge",      "discharge_pressure_bar"],
                  ["System/Header",  "system_pressure_bar"],
                  ["Receiver Tank",  "receiver_tank_pressure_bar"],
                  ["Line",           "line_pressure_bar"],
                  ["Filter ΔP",      "filter_dp_bar"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof CompressorRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Dryer & air quality */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Dryer &amp; Air Quality</legend>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Dryer Status</label>
                  <select value={form.dryer_status ?? ""}
                    onChange={e => fSet("dryer_status", e.target.value || undefined)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white">
                    <option value="">—</option>
                    {["ON","OFF","FAULT","BYPASS"].map(s => <option key={s}>{s}</option>)}
                  </select>
                </div>
                {[
                  ["Dryer Dew Point (°C)",     "dryer_dew_point_c"],
                  ["Compressor Dew Point (°C)","dew_point_c"],
                  ["PDP (°C)",                 "pressure_dew_point_c"],
                  ["Air Temp (°C)",             "air_temperature_c"],
                  ["Spec. Energy (kWh/Nm³)",   "specific_energy_kwh_m3"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof CompressorRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Leak & night */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Leak Testing &amp; Night Consumption</legend>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="flex items-center gap-2 col-span-1">
                  <input type="checkbox" id="leak_done" checked={!!form.leak_test_done}
                    onChange={e => fSet("leak_test_done", e.target.checked)} />
                  <label htmlFor="leak_done" className="text-sm text-slate-300">Leak test done</label>
                </div>
                {[
                  ["Leak Estimate (%)",   "leak_estimation_pct"],
                  ["Leak Volume (Nm³)",   "leak_volume_nm3"],
                  ["Night Idle kWh",      "night_idle_kwh"],
                  ["Night Idle Nm³",      "night_idle_nm3"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof CompressorRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Flags */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <input type="checkbox" id="maint" checked={!!form.maintenance_flag}
                  onChange={e => fSet("maintenance_flag", e.target.checked)} />
                <label htmlFor="maint" className="text-sm text-slate-300">Maintenance flag</label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="anomaly" checked={!!form.is_anomaly}
                  onChange={e => fSet("is_anomaly", e.target.checked)} />
                <label htmlFor="anomaly" className="text-sm text-slate-300">Anomaly</label>
              </div>
              <div className="col-span-2">
                <label className="text-xs text-slate-400 block mb-1">Notes / Remarks</label>
                <textarea value={form.notes ?? ""}
                  onChange={e => fSet("notes", e.target.value || undefined)}
                  rows={2}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white resize-none" />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  if (!form.asset_id || !form.record_datetime) return;
                  if (editRec) {
                    updateMut.mutate({ id: editRec.id, data: form as CompressorRecordUpdate });
                  } else {
                    createMut.mutate(form as CompressorRecordCreate);
                  }
                }}
                disabled={createMut.isPending || updateMut.isPending}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded text-sm disabled:opacity-40">
                {(createMut.isPending || updateMut.isPending) ? "Saving…" : editRec ? "Save Changes" : "Create Record"}
              </button>
              <button onClick={() => { setCreateOpen(false); setEditRec(null); }}
                className="px-4 py-2 text-slate-400 hover:text-white text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {deleteRec && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-white font-semibold">Delete Record</h3>
            <p className="text-sm text-slate-300">
              Delete <span className="font-mono">{deleteRec.record_no}</span>? This cannot be undone.
            </p>
            <div className="flex gap-2">
              <button onClick={() => deleteMut.mutate(deleteRec.id)} disabled={deleteMut.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm disabled:opacity-40">
                {deleteMut.isPending ? "Deleting…" : "Delete"}
              </button>
              <button onClick={() => setDeleteRec(null)}
                className="px-4 py-2 text-slate-400 hover:text-white text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Import modals */}
      {importModule === "compressor_records" && (
        <ImportModal module="compressor_records" label="Compressor Records" onClose={() => setImportModule(null)} />
      )}
      {importModule === "air_transactions" && (
        <ImportModal module="air_transactions" label="Air Consumption Transactions" onClose={() => setImportModule(null)} />
      )}
    </div>
  );
}
