"use client";

/**
 * Steam & Boiler Management Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Full operational view of plant boiler/steam system with KPIs, trend charts,
 * shift analysis, cost breakdown, and boiler records CRUD.
 *
 * Sections:
 *   1. Scope filters (date, asset, department, shift)
 *   2. KPI strip (steam, fuel, water, condensate, efficiency, cost, availability)
 *   3. Daily trend chart — steam generated + fuel consumed + efficiency %
 *   4. Shift analysis + cost breakdown by dimension
 *   5. Boiler records table (CRUD + export + import)
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import {
  boilerApi,
  downloadBoilerCsv,
  downloadSteamTxCsv,
  BOILER_STATUS_LABELS,
  BOILER_STATUS_COLORS,
  BOILER_STATUS_BG,
  type BoilerRecord,
  type BoilerRecordCreate,
  type BoilerRecordUpdate,
  type BoilerAsset,
  type SteamFilters,
  type BoilerStatus,
} from "@/lib/steam";
import { importApi, type ImportResult } from "@/lib/importApi";

// ── Palette ────────────────────────────────────────────────────────────────────
const CYAN   = "#22d3ee";
const ORANGE = "#fb923c";
const GREEN  = "#4ade80";
const AMBER  = "#fbbf24";
const RED    = "#f87171";
const BLUE   = "#60a5fa";
const VIOLET = "#a78bfa";
const SLATE  = "#94a3b8";

const BAR_COLORS = [
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
  "#f59e0b", "#10b981", "#ef4444", "#6366f1",
];

// ── Helpers ────────────────────────────────────────────────────────────────────
const n = (v: number | string | null | undefined, dp = 1) =>
  v != null ? parseFloat(String(v)).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

const fmtDate = (d: string) => {
  try { return new Date(d).toLocaleDateString(); } catch { return d; }
};

// ── KPI Card ───────────────────────────────────────────────────────────────────
interface KPICardProps {
  label:   string;
  value:   React.ReactNode;
  sub?:    React.ReactNode;
  accent?: string;
  flag?:   boolean;
  flagMsg?: string;
}
function KPICard({ label, value, sub, accent = "border-slate-700", flag, flagMsg }: KPICardProps) {
  return (
    <div className={`bg-slate-800 border rounded-lg p-4 flex flex-col gap-1 ${flag ? "border-red-500/60" : accent}`}>
      <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
      <span className="text-xl font-semibold text-white">{value}</span>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
      {flag && flagMsg && (
        <span className="text-xs text-red-400 font-medium">{flagMsg}</span>
      )}
    </div>
  );
}

// ── Status badge ───────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: BoilerStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${BOILER_STATUS_BG[status]} ${BOILER_STATUS_COLORS[status]}`}>
      {BOILER_STATUS_LABELS[status]}
    </span>
  );
}

// ── Import Modal ───────────────────────────────────────────────────────────────
function ImportModal({
  module, label, onClose,
}: { module: string; label: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (doImport: boolean) => {
    if (!file) return;
    setBusy(true); setErr(null); setResult(null);
    try {
      const r = doImport
        ? await importApi.runImport(module, file)
        : await importApi.validate(module, file);
      setResult(r);
      if (doImport && r.imported) {
        qc.invalidateQueries({ queryKey: ["steam-records"] });
        qc.invalidateQueries({ queryKey: ["steam-kpis"] });
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-lg p-6 space-y-4">
        <h3 className="text-white font-semibold text-lg">Import {label}</h3>
        <div className="space-y-2">
          <button
            onClick={() => importApi.downloadTemplate(module)}
            className="text-xs text-cyan-400 hover:text-cyan-300 underline"
          >
            Download CSV template
          </button>
          <input
            type="file" accept=".csv"
            onChange={e => setFile(e.target.files?.[0] ?? null)}
            className="block text-sm text-slate-300"
          />
        </div>
        {err && <p className="text-red-400 text-sm">{err}</p>}
        {result && (
          <div className="text-sm space-y-1">
            <p className="text-slate-300">
              Rows: {result.total_rows} | Valid: {result.valid_rows} | Failed: {result.failed_rows}
            </p>
            {result.errors.slice(0, 5).map((e, i) => (
              <p key={i} className="text-red-400">Row {e.row}: {e.message}</p>
            ))}
            {result.imported && <p className="text-emerald-400 font-medium">Import complete.</p>}
          </div>
        )}
        <div className="flex gap-2 pt-2">
          <button
            disabled={!file || busy}
            onClick={() => run(false)}
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded disabled:opacity-40"
          >
            {busy ? "…" : "Validate"}
          </button>
          <button
            disabled={!file || busy}
            onClick={() => run(true)}
            className="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-500 text-white rounded disabled:opacity-40"
          >
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

// ── Main page ──────────────────────────────────────────────────────────────────
export default function SteamPage() {
  const qc = useQueryClient();

  // ── Scope filters ────────────────────────────────────────────────────────────
  const [dateFrom,   setDateFrom]   = useState("");
  const [dateTo,     setDateTo]     = useState("");
  const [assetId,    setAssetId]    = useState("");
  const [department, setDepartment] = useState("");
  const [shiftRef,   setShiftRef]   = useState("");

  const scope: Partial<SteamFilters> = useMemo(() => ({
    ...(dateFrom   && { date_from: dateFrom }),
    ...(dateTo     && { date_to:   dateTo }),
    ...(assetId    && { asset_id:  assetId }),
    ...(department && { department }),
    ...(shiftRef   && { shift_ref: shiftRef }),
  }), [dateFrom, dateTo, assetId, department, shiftRef]);

  // ── Data ─────────────────────────────────────────────────────────────────────
  const { data: assets = [] } = useQuery({
    queryKey: ["steam-assets"],
    queryFn:  () => boilerApi.listAssets(),
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["steam-kpis", scope],
    queryFn:  () => boilerApi.kpis(scope),
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["steam-trend", scope],
    queryFn:  () => boilerApi.dailyTrend(scope),
  });

  const { data: shifts = [] } = useQuery({
    queryKey: ["steam-shifts", scope],
    queryFn:  () => boilerApi.shiftAnalysis(scope),
  });

  const [breakdownDim, setBreakdownDim] = useState<
    "department" | "line" | "machine" | "building_area" | "shift"
  >("department");

  const { data: breakdown } = useQuery({
    queryKey: ["steam-breakdown", breakdownDim, scope],
    queryFn:  () => boilerApi.breakdown(breakdownDim, scope),
  });

  // ── Records ───────────────────────────────────────────────────────────────────
  const [recPage, setRecPage] = useState(0);
  const REC_LIMIT = 50;

  const { data: records = [], isLoading: recsLoading } = useQuery({
    queryKey: ["steam-records", scope, recPage],
    queryFn:  () => boilerApi.listRecords({ ...scope, skip: recPage * REC_LIMIT, limit: REC_LIMIT }),
  });

  // ── Modals ────────────────────────────────────────────────────────────────────
  const [viewRec,   setViewRec]   = useState<BoilerRecord | null>(null);
  const [editRec,   setEditRec]   = useState<BoilerRecord | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteRec, setDeleteRec] = useState<BoilerRecord | null>(null);
  const [importModule, setImportModule] = useState<string | null>(null);

  // ── Mutations ─────────────────────────────────────────────────────────────────
  const createMut = useMutation({
    mutationFn: (d: BoilerRecordCreate) => boilerApi.createRecord(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steam-records"] });
      qc.invalidateQueries({ queryKey: ["steam-kpis"] });
      setCreateOpen(false);
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: BoilerRecordUpdate }) =>
      boilerApi.updateRecord(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steam-records"] });
      qc.invalidateQueries({ queryKey: ["steam-kpis"] });
      setEditRec(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => boilerApi.deleteRecord(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steam-records"] });
      qc.invalidateQueries({ queryKey: ["steam-kpis"] });
      setDeleteRec(null);
    },
  });

  // ── Record form state ─────────────────────────────────────────────────────────
  const emptyForm = (): Partial<BoilerRecordCreate> => ({
    asset_id: "",
    record_datetime: new Date().toISOString().slice(0, 16),
    status: "RUNNING",
    source_method: "MANUAL",
    maintenance_flag: false,
    is_anomaly: false,
  });

  const [form, setForm] = useState<Partial<BoilerRecordCreate>>(emptyForm());

  const fSet = (k: keyof BoilerRecordCreate, v: unknown) =>
    setForm(p => ({ ...p, [k]: v }));

  // ── Trend data prep ───────────────────────────────────────────────────────────
  const trendData = useMemo(() =>
    trend.map(t => ({
      day:      t.date.slice(5),          // MM-DD
      steam_t:  +(+t.steam_generated_kg / 1000).toFixed(2),
      fuel:     +parseFloat(String(t.fuel_consumed)).toFixed(1),
      eff:      t.avg_efficiency_pct != null ? +parseFloat(String(t.avg_efficiency_pct)).toFixed(1) : null,
      downtime: t.downtime_minutes,
    }))
  , [trend]);

  const shiftData = useMemo(() =>
    shifts.map(s => ({
      label:    s.label,
      steam_t:  +(+s.steam_generated_kg / 1000).toFixed(2),
      eff:      s.avg_efficiency_pct != null ? +parseFloat(String(s.avg_efficiency_pct)).toFixed(1) : null,
    }))
  , [shifts]);

  const breakdownData = useMemo(() =>
    (breakdown?.rows ?? []).slice(0, 8).map(r => ({
      label:    r.label.slice(0, 18),
      steam_t:  +(+r.total_kg / 1000).toFixed(2),
      cost:     r.total_cost != null ? +parseFloat(String(r.total_cost)).toFixed(0) : null,
      pct:      r.pct_of_total != null ? +parseFloat(String(r.pct_of_total)).toFixed(1) : null,
    }))
  , [breakdown]);

  // ── KPI aliases ───────────────────────────────────────────────────────────────
  const K = kpis;

  // ── Render ─────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0d1117] text-white space-y-6 p-6">

      {/* ── Header ────────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Steam &amp; Boiler Management</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Operational records, KPI monitoring, and cost allocation for plant steam systems
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setImportModule("boiler_records")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded text-slate-200"
          >
            Import Records
          </button>
          <button
            onClick={() => setImportModule("steam_transactions")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded text-slate-200"
          >
            Import Transactions
          </button>
          <button
            onClick={() => { setForm(emptyForm()); setCreateOpen(true); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-500 rounded text-white"
          >
            + Add Record
          </button>
        </div>
      </div>

      {/* ── Scope filters ─────────────────────────────────────────────────────── */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Date From</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Date To</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Boiler Asset</label>
            <select value={assetId} onChange={e => setAssetId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white">
              <option value="">All boilers</option>
              {assets.map(a => (
                <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>
              ))}
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
              <option value="">All shifts</option>
              {["A", "B", "C", "Day", "Night"].map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── KPI strip ─────────────────────────────────────────────────────────── */}
      {kpisLoading ? (
        <div className="text-slate-400 text-sm">Loading KPIs…</div>
      ) : K && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          <KPICard
            label="Steam Generated"
            value={`${n(K.total_steam_generated_tons, 1)} t`}
            sub={`${n(K.total_steam_generated_kg, 0)} kg`}
            accent="border-cyan-500/40"
          />
          <KPICard
            label="Fuel Consumed"
            value={`${n(K.total_fuel_consumed, 1)} ${K.fuel_unit ?? ""}`}
            sub={K.gas_per_ton_steam != null ? `${n(K.gas_per_ton_steam, 2)} ${K.fuel_unit ?? ""}/t steam` : undefined}
            accent="border-orange-500/40"
          />
          <KPICard
            label="Boiler Efficiency"
            value={K.avg_efficiency_pct != null ? `${n(K.avg_efficiency_pct, 1)}%` : "—"}
            sub={K.avg_boiler_load_pct != null ? `Load: ${n(K.avg_boiler_load_pct, 1)}%` : undefined}
            flag={K.flag_low_efficiency}
            flagMsg="Below 80% threshold"
            accent="border-green-500/40"
          />
          <KPICard
            label="Condensate Recovery"
            value={K.condensate_recovery_pct != null ? `${n(K.condensate_recovery_pct, 1)}%` : "—"}
            sub={`${n(K.total_condensate_m3, 2)} m³ returned`}
            flag={K.flag_low_condensate}
            flagMsg="Below 70% — check traps"
            accent="border-blue-500/40"
          />
          <KPICard
            label="Blowdown Loss"
            value={K.blowdown_loss_pct != null ? `${n(K.blowdown_loss_pct, 2)}%` : "—"}
            sub={`${n(K.total_blowdown_litres, 0)} L blown`}
            flag={K.flag_high_blowdown}
            flagMsg="Above 5% — check TDS"
            accent="border-amber-500/40"
          />
          <KPICard
            label="Feedwater Used"
            value={`${n(K.total_feedwater_m3, 2)} m³`}
            sub={K.water_per_ton_steam != null ? `${n(K.water_per_ton_steam, 3)} m³/t` : undefined}
            accent="border-sky-500/40"
          />
          <KPICard
            label="Availability"
            value={K.availability_pct != null ? `${n(K.availability_pct, 1)}%` : "—"}
            sub={K.total_burner_hours != null ? `${n(K.total_burner_hours, 1)} burner hrs` : undefined}
            accent="border-violet-500/40"
          />
          <KPICard
            label="Downtime"
            value={K.total_downtime_hours != null ? `${n(K.total_downtime_hours, 1)} h` : "—"}
            sub={`${K.total_start_stops} start-stops`}
            accent="border-slate-500/40"
          />
          <KPICard
            label="Steam Cost / Ton"
            value={K.steam_cost_per_ton != null ? `$${n(K.steam_cost_per_ton, 2)}` : "—"}
            sub={K.steam_cost_total != null ? `Total: $${n(K.steam_cost_total, 0)}` : undefined}
            accent="border-emerald-500/40"
          />
          <KPICard
            label="Records / Anomalies"
            value={`${K.record_count}`}
            sub={`${K.anomaly_count} anomalies · ${K.maintenance_count} maintenance`}
            accent="border-slate-600"
          />
        </div>
      )}

      {/* ── Trend chart ───────────────────────────────────────────────────────── */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-medium text-slate-200">Daily Trend — Steam &amp; Fuel</h2>
        {trendData.length === 0 ? (
          <p className="text-slate-500 text-sm py-8 text-center">No data in selected range</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="steamGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CYAN}   stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CYAN}  stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="fuelGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={ORANGE} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={ORANGE} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" t" />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" m³" />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                labelStyle={{ color: "#cbd5e1" }}
                itemStyle={{ color: "#e2e8f0" }}
              />
              <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
              <Area yAxisId="left" type="monotone" dataKey="steam_t" name="Steam (t)" stroke={CYAN}   fill="url(#steamGrad)" strokeWidth={2} dot={false} />
              <Area yAxisId="right" type="monotone" dataKey="fuel"    name="Fuel (m³/L/kg)" stroke={ORANGE} fill="url(#fuelGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Efficiency trend ──────────────────────────────────────────────────── */}
      {trendData.some(t => t.eff != null) && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-slate-200">Daily Boiler Efficiency %</h2>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} unit="%" domain={[60, 100]} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                labelStyle={{ color: "#cbd5e1" }}
                itemStyle={{ color: "#e2e8f0" }}
              />
              <Line type="monotone" dataKey="eff" name="Efficiency %" stroke={GREEN} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Shift analysis + Breakdown ────────────────────────────────────────── */}
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
                <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" t" />
                <YAxis dataKey="label" type="category" tick={{ fill: "#94a3b8", fontSize: 11 }} width={40} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                  itemStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="steam_t" name="Steam (t)" radius={[0, 4, 4, 0]}>
                  {shiftData.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Breakdown */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-200">Steam Consumption Breakdown</h2>
            <select
              value={breakdownDim}
              onChange={e => setBreakdownDim(e.target.value as typeof breakdownDim)}
              className="text-xs bg-slate-700 border border-slate-600 rounded px-2 py-1 text-white"
            >
              {(["department", "line", "machine", "building_area", "shift"] as const).map(d => (
                <option key={d} value={d}>{d.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          {breakdownData.length === 0 ? (
            <p className="text-slate-500 text-sm py-6 text-center">No transaction data for breakdown</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={breakdownData} layout="vertical" margin={{ top: 0, right: 16, left: 60, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} unit=" t" />
                <YAxis dataKey="label" type="category" tick={{ fill: "#94a3b8", fontSize: 11 }} width={60} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
                  itemStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="steam_t" name="Steam (t)" radius={[0, 4, 4, 0]}>
                  {breakdownData.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {(breakdown?.rows ?? []).length > 0 && (
            <table className="w-full text-xs mt-2">
              <thead>
                <tr className="text-slate-400 text-left">
                  <th className="pb-1">Group</th>
                  <th className="pb-1 text-right">Steam (t)</th>
                  <th className="pb-1 text-right">%</th>
                  <th className="pb-1 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {(breakdown?.rows ?? []).map((r, i) => (
                  <tr key={i} className="border-t border-slate-700">
                    <td className="py-1 text-slate-300">{r.label}</td>
                    <td className="py-1 text-right text-slate-300">{n(+r.total_kg / 1000, 2)}</td>
                    <td className="py-1 text-right text-slate-400">{r.pct_of_total != null ? `${n(r.pct_of_total, 1)}%` : "—"}</td>
                    <td className="py-1 text-right text-slate-400">{r.total_cost != null ? `$${n(r.total_cost, 0)}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Boiler records table ──────────────────────────────────────────────── */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <h2 className="text-sm font-medium text-slate-200">Boiler Operational Records</h2>
          <div className="flex gap-2">
            <button
              onClick={() => downloadBoilerCsv(scope as Record<string, string | number | boolean | undefined>, "boiler_records.csv")}
              className="text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded"
            >
              Export CSV
            </button>
          </div>
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
                  <th className="px-4 py-2 text-right">Steam (kg)</th>
                  <th className="px-4 py-2 text-right">Fuel</th>
                  <th className="px-4 py-2 text-right">Eff. %</th>
                  <th className="px-4 py-2 text-right">Load %</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2 text-center">Flags</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {records.map(rec => (
                  <tr
                    key={rec.id}
                    className={`hover:bg-slate-700/30 cursor-pointer ${
                      rec.is_anomaly ? "border-l-2 border-red-500" : ""
                    }`}
                    onClick={() => setViewRec(rec)}
                  >
                    <td className="px-4 py-2 font-mono text-xs text-slate-300">{rec.record_no}</td>
                    <td className="px-4 py-2 text-slate-300">{rec.asset_name ?? rec.asset_no ?? "—"}</td>
                    <td className="px-4 py-2 text-slate-400">{fmtDate(rec.record_datetime)}</td>
                    <td className="px-4 py-2 text-slate-400">{rec.shift_ref ?? "—"}</td>
                    <td className="px-4 py-2 text-right text-slate-300">{n(rec.steam_generated_kg, 0)}</td>
                    <td className="px-4 py-2 text-right text-slate-400">
                      {rec.fuel_consumption != null
                        ? `${n(rec.fuel_consumption, 1)} ${rec.fuel_unit ?? ""}`
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {rec.boiler_efficiency_pct != null ? (
                        <span className={+rec.boiler_efficiency_pct < 80 ? "text-red-400" : "text-emerald-400"}>
                          {n(rec.boiler_efficiency_pct, 1)}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-400">{rec.boiler_load_pct != null ? `${n(rec.boiler_load_pct, 1)}%` : "—"}</td>
                    <td className="px-4 py-2">
                      <StatusBadge status={rec.status as BoilerStatus} />
                    </td>
                    <td className="px-4 py-2 text-center text-sm">
                      {rec.is_anomaly        && <span title="Anomaly" className="text-red-400 mr-1">⚠</span>}
                      {rec.maintenance_flag  && <span title="Maintenance" className="text-amber-400">🔧</span>}
                    </td>
                    <td className="px-4 py-2" onClick={e => e.stopPropagation()}>
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => { setForm({ ...rec }); setEditRec(rec); }}
                          className="text-xs text-cyan-400 hover:text-cyan-300"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => setDeleteRec(rec)}
                          className="text-xs text-red-400 hover:text-red-300"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
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

      {/* ════════════════════════════════════════════════════════════════════════
          MODALS
          ══════════════════════════════════════════════════════════════════════ */}

      {/* View record */}
      {viewRec && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-white font-semibold text-lg">{viewRec.record_no}</h3>
                <p className="text-xs text-slate-400">{viewRec.asset_name ?? viewRec.asset_no} · {fmtDate(viewRec.record_datetime)}</p>
              </div>
              <StatusBadge status={viewRec.status as BoilerStatus} />
            </div>

            {/* Flags */}
            {(viewRec.is_anomaly || viewRec.maintenance_flag) && (
              <div className="flex gap-2 flex-wrap">
                {viewRec.is_anomaly && (
                  <span className="px-2 py-0.5 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">
                    Anomaly: {viewRec.anomaly_note ?? "flagged"}
                  </span>
                )}
                {viewRec.maintenance_flag && (
                  <span className="px-2 py-0.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs rounded">
                    Maintenance flag
                  </span>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
              {[
                ["Shift",          viewRec.shift_ref],
                ["Department",     viewRec.department],
                ["Period (h)",     viewRec.period_hours],
                ["Steam Pressure", viewRec.steam_pressure_bar != null ? `${viewRec.steam_pressure_bar} bar` : null],
                ["Steam Temp",     viewRec.steam_temp_c != null ? `${viewRec.steam_temp_c} °C` : null],
                ["Steam Flow",     viewRec.steam_flow_kgh != null ? `${viewRec.steam_flow_kgh} kg/h` : null],
                ["Steam Quality",  viewRec.steam_quality_pct != null ? `${viewRec.steam_quality_pct}%` : null],
                ["Steam Generated",viewRec.steam_generated_kg != null ? `${n(viewRec.steam_generated_kg, 0)} kg` : null],
                ["Feedwater",      viewRec.feedwater_consumed_m3 != null ? `${viewRec.feedwater_consumed_m3} m³` : null],
                ["Condensate",     viewRec.condensate_returned_m3 != null ? `${viewRec.condensate_returned_m3} m³` : null],
                ["Blowdown %",     viewRec.blowdown_pct != null ? `${viewRec.blowdown_pct}%` : null],
                ["Blowdown Vol.",  viewRec.blowdown_volume_litres != null ? `${viewRec.blowdown_volume_litres} L` : null],
                ["Fuel Type",      viewRec.fuel_type],
                ["Fuel Consumed",  viewRec.fuel_consumption != null ? `${viewRec.fuel_consumption} ${viewRec.fuel_unit ?? ""}` : null],
                ["Efficiency",     viewRec.boiler_efficiency_pct != null ? `${viewRec.boiler_efficiency_pct}%` : null],
                ["Flue Temp",      viewRec.flue_gas_temp_c != null ? `${viewRec.flue_gas_temp_c} °C` : null],
                ["O₂ %",           viewRec.o2_pct],
                ["CO₂ %",          viewRec.co2_pct],
                ["Boiler Load",    viewRec.boiler_load_pct != null ? `${viewRec.boiler_load_pct}%` : null],
                ["Burner Hours",   viewRec.burner_runtime_hours],
                ["Start-Stops",    viewRec.start_stop_count],
                ["Downtime (min)", viewRec.downtime_minutes],
                ["Chemical",       viewRec.chemical_dosing_amount != null ? `${viewRec.chemical_dosing_amount} ${viewRec.chemical_dosing_unit ?? ""}` : null],
                ["Source",         viewRec.source_method],
                ["Notes",          viewRec.notes],
              ].map(([label, val]) =>
                val != null ? (
                  <div key={String(label)} className="flex flex-col">
                    <span className="text-xs text-slate-400">{label}</span>
                    <span className="text-slate-200">{String(val)}</span>
                  </div>
                ) : null
              )}
            </div>

            <div className="flex justify-end pt-2 gap-2">
              <button
                onClick={() => { setForm({ ...viewRec }); setEditRec(viewRec); setViewRec(null); }}
                className="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-500 text-white rounded"
              >
                Edit
              </button>
              <button onClick={() => setViewRec(null)} className="px-3 py-1.5 text-sm text-slate-400 hover:text-white">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit record form */}
      {(createOpen || editRec) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <h3 className="text-white font-semibold text-lg">
              {editRec ? "Edit Boiler Record" : "New Boiler Record"}
            </h3>

            {/* Asset + datetime */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Boiler Asset *</label>
                <select value={form.asset_id ?? ""}
                  onChange={e => fSet("asset_id", e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white">
                  <option value="">Select asset…</option>
                  {assets.map(a => (
                    <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>
                  ))}
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
                  {["A", "B", "C", "Day", "Night"].map(s => <option key={s}>{s}</option>)}
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
                <label className="text-xs text-slate-400 block mb-1">Period Hours</label>
                <input type="number" step="0.01" value={form.period_hours ?? ""}
                  onChange={e => fSet("period_hours", e.target.value ? +e.target.value : undefined)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Status</label>
                <select value={form.status ?? "RUNNING"}
                  onChange={e => fSet("status", e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white">
                  {(["RUNNING", "STANDBY", "SHUTDOWN", "FAULT"] as BoilerStatus[]).map(s => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Steam */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Steam Parameters</legend>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["Steam Generated (kg)",   "steam_generated_kg"],
                  ["Steam Pressure (bar)",   "steam_pressure_bar"],
                  ["Steam Temp (°C)",        "steam_temp_c"],
                  ["Steam Flow (kg/h)",      "steam_flow_kgh"],
                  ["Steam Quality (%)",      "steam_quality_pct"],
                  ["Period Hours",           "period_hours"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof BoilerRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Water */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Water Consumption</legend>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["Feedwater (m³)",         "feedwater_consumed_m3"],
                  ["Condensate Return (m³)", "condensate_returned_m3"],
                  ["Blowdown %",             "blowdown_pct"],
                  ["Blowdown Volume (L)",    "blowdown_volume_litres"],
                  ["Feed Water Temp (°C)",   "feed_water_temp_c"],
                  ["Feed Water TDS (ppm)",   "feed_water_tds_ppm"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof BoilerRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Fuel & combustion */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Fuel &amp; Combustion</legend>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Fuel Type</label>
                  <select value={form.fuel_type ?? ""}
                    onChange={e => fSet("fuel_type", e.target.value || undefined)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white">
                    <option value="">—</option>
                    {["NATURAL_GAS", "LPG", "DIESEL", "HFO", "BIOMASS", "COAL"].map(f => (
                      <option key={f}>{f}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Fuel Consumed</label>
                  <input type="number" step="any" value={form.fuel_consumption ?? ""}
                    onChange={e => fSet("fuel_consumption", e.target.value ? +e.target.value : undefined)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Fuel Unit</label>
                  <select value={form.fuel_unit ?? ""}
                    onChange={e => fSet("fuel_unit", e.target.value || undefined)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white">
                    <option value="">—</option>
                    {["m3", "L", "kg", "ton"].map(u => <option key={u}>{u}</option>)}
                  </select>
                </div>
                {[
                  ["Efficiency (%)",    "boiler_efficiency_pct"],
                  ["Boiler Load (%)",   "boiler_load_pct"],
                  ["Flue Temp (°C)",    "flue_gas_temp_c"],
                  ["O₂ (%)",            "o2_pct"],
                  ["CO₂ (%)",           "co2_pct"],
                  ["CO (ppm)",          "co_ppm"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step="any"
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof BoilerRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Operational */}
            <fieldset className="border border-slate-700 rounded p-3 space-y-3">
              <legend className="text-xs text-slate-400 px-1">Operational</legend>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["Burner Runtime (h)",     "burner_runtime_hours"],
                  ["Start-Stop Count",       "start_stop_count"],
                  ["Cumul. Running Hrs",     "running_hours_cumulative"],
                  ["Downtime (min)",         "downtime_minutes"],
                  ["Chemical Amount",        "chemical_dosing_amount"],
                ].map(([lbl, key]) => (
                  <div key={key}>
                    <label className="text-xs text-slate-400 block mb-1">{lbl}</label>
                    <input type="number" step={key === "start_stop_count" || key === "downtime_minutes" ? "1" : "any"}
                      value={(form as Record<string, unknown>)[key] as number ?? ""}
                      onChange={e => fSet(key as keyof BoilerRecordCreate, e.target.value ? +e.target.value : undefined)}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white" />
                  </div>
                ))}
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Chemical Unit</label>
                  <input type="text" value={form.chemical_dosing_unit ?? ""}
                    onChange={e => fSet("chemical_dosing_unit", e.target.value || undefined)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white"
                    placeholder="kg / L / ppm" />
                </div>
                <div className="col-span-3">
                  <label className="text-xs text-slate-400 block mb-1">Downtime Reason</label>
                  <input type="text" value={form.downtime_reason ?? ""}
                    onChange={e => fSet("downtime_reason", e.target.value || undefined)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white"
                    placeholder="e.g. Tube scaling, Safety valve test…" />
                </div>
              </div>
            </fieldset>

            {/* Flags & notes */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <input type="checkbox" id="maint_flag" checked={!!form.maintenance_flag}
                  onChange={e => fSet("maintenance_flag", e.target.checked)} />
                <label htmlFor="maint_flag" className="text-sm text-slate-300">Maintenance flag</label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="anomaly_flag" checked={!!form.is_anomaly}
                  onChange={e => fSet("is_anomaly", e.target.checked)} />
                <label htmlFor="anomaly_flag" className="text-sm text-slate-300">Anomaly</label>
              </div>
              <div className="col-span-2">
                <label className="text-xs text-slate-400 block mb-1">Notes</label>
                <textarea value={form.notes ?? ""}
                  onChange={e => fSet("notes", e.target.value || undefined)}
                  rows={2}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white resize-none" />
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  if (!form.asset_id || !form.record_datetime) return;
                  if (editRec) {
                    updateMut.mutate({ id: editRec.id, data: form as BoilerRecordUpdate });
                  } else {
                    createMut.mutate(form as BoilerRecordCreate);
                  }
                }}
                disabled={createMut.isPending || updateMut.isPending}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-sm disabled:opacity-40"
              >
                {(createMut.isPending || updateMut.isPending) ? "Saving…" : editRec ? "Save Changes" : "Create Record"}
              </button>
              <button
                onClick={() => { setCreateOpen(false); setEditRec(null); }}
                className="px-4 py-2 text-slate-400 hover:text-white text-sm"
              >
                Cancel
              </button>
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
              Delete <span className="font-mono text-slate-200">{deleteRec.record_no}</span>? This cannot be undone.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => deleteMut.mutate(deleteRec.id)}
                disabled={deleteMut.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm disabled:opacity-40"
              >
                {deleteMut.isPending ? "Deleting…" : "Delete"}
              </button>
              <button onClick={() => setDeleteRec(null)} className="px-4 py-2 text-slate-400 hover:text-white text-sm">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import modals */}
      {importModule === "boiler_records" && (
        <ImportModal
          module="boiler_records"
          label="Boiler Operational Records"
          onClose={() => setImportModule(null)}
        />
      )}
      {importModule === "steam_transactions" && (
        <ImportModal
          module="steam_transactions"
          label="Steam Consumption Transactions"
          onClose={() => setImportModule(null)}
        />
      )}

    </div>
  );
}
