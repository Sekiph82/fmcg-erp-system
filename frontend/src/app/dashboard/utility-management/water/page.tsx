"use client";

/**
 * Water Management Dashboard
 * ──────────────────────────
 * KPIs: water_in, process, wastewater, balance, loss %, recovery %
 * Charts: daily trend (3 series area), breakdown by dept/line/machine
 * Transactions: tabbed by type (WATER / PROCESS_WATER / WASTEWATER)
 * CRUD: create / edit / delete utility_transactions for water types
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from "recharts";
import {
  waterApi,
  downloadWaterCsv,
  type WaterScope,
  type WaterKPIs,
  type WaterTrendPoint,
  type WaterBreakdown,
  WATER_TYPE_LABELS,
  WATER_TYPE_COLORS,
  type WaterUtilityType,
} from "@/lib/water";
import type { UtilityTransaction, UtilityTransactionCreate } from "@/lib/utilityTransactions";
import { importApi } from "@/lib/importApi";
import type { ImportResult } from "@/lib/importApi";

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: string | number | null | undefined, dec = 2) =>
  v == null ? "—" : Number(v).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec });

const fmtDate = (s: string) => s.slice(0, 10);

// ── Small components ──────────────────────────────────────────────────────────

function KPICard({
  label, value, sub, alert = false,
}: { label: string; value: string; sub?: string; alert?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${alert ? "border-red-500/40 bg-red-500/5" : "border-white/10 bg-white/5"}`}>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-semibold ${alert ? "text-red-400" : "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function Section({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-3 mt-6 mb-3">
      <div className="w-1 h-5 rounded-full bg-sky-400" />
      <span className="text-sm font-medium text-gray-200">{title}</span>
    </div>
  );
}

type BreakdownDim = "department" | "line" | "machine" | "building_area" | "shift";
const DIM_LABELS: Record<BreakdownDim, string> = {
  department: "Department", line: "Production Line",
  machine: "Machine", building_area: "Building/Area", shift: "Shift",
};

const BAR_COLORS = ["#38bdf8", "#34d399", "#a78bfa", "#fb923c", "#f472b6", "#facc15"];

// ── Transaction form ──────────────────────────────────────────────────────────

function TxForm({
  initial, onSubmit, onCancel, loading,
}: {
  initial?: Partial<UtilityTransactionCreate>;
  onSubmit: (d: UtilityTransactionCreate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [f, setF] = useState<UtilityTransactionCreate>({
    utility_type: "WATER" as unknown as UtilityTransactionCreate["utility_type"],
    transaction_date: new Date().toISOString().slice(0, 10),
    quantity: 0,
    uom: "m3",
    source_method: "MANUAL" as UtilityTransactionCreate["source_method"],
    quality: "GOOD" as UtilityTransactionCreate["quality"],
    estimated_or_actual: false,
    anomaly_flag: false,
    ...initial,
  });

  const set = (k: keyof typeof f, v: unknown) => setF(p => ({ ...p, [k]: v }));

  return (
    <form
      onSubmit={e => { e.preventDefault(); onSubmit(f); }}
      className="space-y-4"
    >
      {/* Type + Date */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Water Type *</span>
          <select
            required
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.utility_type as unknown as string}
            onChange={e => set("utility_type", e.target.value as unknown as UtilityTransactionCreate["utility_type"])}
          >
            {(["WATER", "PROCESS_WATER", "WASTEWATER"] as WaterUtilityType[]).map(t => (
              <option key={t} value={t}>{WATER_TYPE_LABELS[t]}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Date *</span>
          <input required type="date" className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.transaction_date} onChange={e => set("transaction_date", e.target.value)} />
        </label>
      </div>

      {/* Volume + UoM */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Volume (m³) *</span>
          <input required type="number" step="0.001" min="0"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.quantity} onChange={e => set("quantity", parseFloat(e.target.value))} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Unit</span>
          <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.uom} onChange={e => set("uom", e.target.value)} />
        </label>
      </div>

      {/* Allocation */}
      <div className="grid grid-cols-3 gap-3">
        {(["department", "building_area", "line_id"] as (keyof UtilityTransactionCreate)[]).map(k => (
          <label key={k} className="flex flex-col gap-1">
            <span className="text-xs text-gray-400 capitalize">{String(k).replace(/_/g, " ").replace(" id", "")}</span>
            <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
              value={(f[k] as string) ?? ""}
              onChange={e => set(k, e.target.value || null)} />
          </label>
        ))}
        {(["machine_id", "shift_id", "batch_id"] as (keyof UtilityTransactionCreate)[]).map(k => (
          <label key={k} className="flex flex-col gap-1">
            <span className="text-xs text-gray-400 capitalize">{String(k).replace(/_/g, " ").replace(" id", "")}</span>
            <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
              value={(f[k] as string) ?? ""}
              onChange={e => set(k, e.target.value || null)} />
          </label>
        ))}
      </div>

      {/* Cost */}
      <div className="grid grid-cols-3 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Cost Rate</span>
          <input type="number" step="0.0001" className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={(f.cost_rate as number) ?? ""}
            onChange={e => set("cost_rate", e.target.value ? parseFloat(e.target.value) : null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Total Cost</span>
          <input type="number" step="0.01" className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={(f.total_cost as number) ?? ""}
            onChange={e => set("total_cost", e.target.value ? parseFloat(e.target.value) : null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Currency</span>
          <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.currency_code ?? "USD"}
            onChange={e => set("currency_code", e.target.value)} />
        </label>
      </div>

      {/* Quality flags */}
      <div className="grid grid-cols-3 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Source Method</span>
          <select className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.source_method} onChange={e => set("source_method", e.target.value as UtilityTransactionCreate["source_method"])}>
            {["MANUAL", "IMPORTED", "IOT", "API", "CALCULATED", "ESTIMATED"].map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Quality</span>
          <select className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.quality} onChange={e => set("quality", e.target.value as UtilityTransactionCreate["quality"])}>
            {["GOOD", "ESTIMATED", "SUSPECT", "MISSING"].map(q => (
              <option key={q} value={q}>{q}</option>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-2 pt-4">
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={!!f.estimated_or_actual} onChange={e => set("estimated_or_actual", e.target.checked)} />
            Estimated
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={!!f.anomaly_flag} onChange={e => set("anomaly_flag", e.target.checked)} />
            Anomaly
          </label>
        </div>
      </div>

      {f.anomaly_flag && (
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Anomaly Note</span>
          <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.anomaly_note ?? ""}
            onChange={e => set("anomaly_note", e.target.value || null)} />
        </label>
      )}

      <label className="flex flex-col gap-1">
        <span className="text-xs text-gray-400">Notes</span>
        <textarea rows={2} className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white resize-none"
          value={f.notes ?? ""}
          onChange={e => set("notes", e.target.value || null)} />
      </label>

      <div className="flex gap-2 justify-end pt-2">
        <button type="button" onClick={onCancel}
          className="px-3 py-1.5 rounded text-sm text-gray-400 border border-white/10 hover:bg-white/5">
          Cancel
        </button>
        <button type="submit" disabled={loading}
          className="px-4 py-1.5 rounded text-sm bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-50">
          {loading ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

// ── Import modal ──────────────────────────────────────────────────────────────

function ImportModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (doImport: boolean) => {
    if (!file) return;
    setLoading(true); setError(null);
    try {
      const r = doImport
        ? await importApi.runImport("water_transactions", file, "import_valid_only")
        : await importApi.validate("water_transactions", file);
      setResult(r);
      if (doImport && r.imported) onDone();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-md space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-white font-semibold">Import Water Transactions</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        <div>
          <button onClick={() => importApi.downloadTemplate("water_transactions")}
            className="text-xs text-sky-400 hover:underline">
            Download template CSV
          </button>
        </div>

        <input type="file" accept=".csv"
          className="block w-full text-sm text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:bg-white/10 file:text-white"
          onChange={e => { setFile(e.target.files?.[0] ?? null); setResult(null); }} />

        {result && (
          <div className={`p-3 rounded text-sm border ${result.imported ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-blue-500/10 border-blue-500/20 text-blue-400"}`}>
            <p>{result.imported ? "Import complete" : "Validation result"}</p>
            <p className="text-xs mt-1">
              {result.valid_rows} valid / {result.failed_rows} failed / {result.total_rows} total
            </p>
            {result.errors.slice(0, 5).map((e, i) => (
              <p key={i} className="text-xs text-red-400 mt-0.5">Row {e.row}: {e.message}</p>
            ))}
          </div>
        )}
        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="flex gap-2 justify-end">
          <button onClick={() => run(false)} disabled={!file || loading}
            className="px-3 py-1.5 text-xs rounded border border-white/10 text-gray-300 hover:bg-white/5 disabled:opacity-40">
            Validate
          </button>
          <button onClick={() => run(true)} disabled={!file || loading}
            className="px-3 py-1.5 text-xs rounded bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-40">
            {loading ? "Running…" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type ModalState =
  | { type: "none" }
  | { type: "create" }
  | { type: "edit"; tx: UtilityTransaction }
  | { type: "delete"; tx: UtilityTransaction }
  | { type: "import" };

export default function WaterPage() {
  const qc = useQueryClient();
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["water-kpis"] });
    qc.invalidateQueries({ queryKey: ["water-trend"] });
    qc.invalidateQueries({ queryKey: ["water-breakdown"] });
    qc.invalidateQueries({ queryKey: ["water-tx"] });
  };

  // Scope + filters
  const [scope, setScope] = useState<WaterScope>({});
  const [txType, setTxType] = useState<WaterUtilityType>("WATER");
  const [breakdownDim, setBreakdownDim] = useState<BreakdownDim>("department");
  const [modal, setModal] = useState<ModalState>({ type: "none" });

  const setS = (k: keyof WaterScope, v: string) =>
    setScope(p => ({ ...p, [k]: v || undefined }));

  // Queries
  const { data: kpis } = useQuery<WaterKPIs>({
    queryKey: ["water-kpis", scope],
    queryFn: () => waterApi.kpis(scope),
  });
  const { data: trend = [] } = useQuery<WaterTrendPoint[]>({
    queryKey: ["water-trend", scope],
    queryFn: () => waterApi.dailyTrend(scope),
  });
  const { data: breakdown } = useQuery<WaterBreakdown>({
    queryKey: ["water-breakdown", breakdownDim, txType, scope],
    queryFn: () => waterApi.breakdown(breakdownDim, txType, scope),
  });
  const { data: txList = [] } = useQuery<UtilityTransaction[]>({
    queryKey: ["water-tx", txType, scope],
    queryFn: () => waterApi.listTransactions({ utility_type: txType, ...scope, limit: 200 }),
  });

  // Mutations
  const createMut = useMutation({
    mutationFn: (d: UtilityTransactionCreate) => waterApi.createTransaction(d),
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, d }: { id: string; d: Partial<UtilityTransactionCreate> }) =>
      waterApi.updateTransaction(id, d),
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => waterApi.deleteTransaction(id),
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });

  const trendData = trend.map(r => ({
    date: r.date.slice(5),
    "Raw Water":  parseFloat(r.water_in_m3),
    "Process":    parseFloat(r.process_m3),
    "Wastewater": parseFloat(r.wastewater_m3),
  }));

  const bkData = (breakdown?.rows ?? []).map(r => ({
    name: r.label,
    m3: parseFloat(r.total_m3),
  }));

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Water Management</h1>
          <p className="text-sm text-gray-400 mt-1">
            Raw intake · Process consumption · Wastewater · Water balance
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadWaterCsv({ utility_type: txType, ...scope }, `water-${txType.toLowerCase()}-${new Date().toISOString().slice(0,10)}.csv`)}
            className="px-3 py-1.5 text-xs rounded border border-white/10 text-gray-300 hover:bg-white/5"
          >
            Export CSV
          </button>
          <button onClick={() => setModal({ type: "import" })}
            className="px-3 py-1.5 text-xs rounded border border-sky-500/30 text-sky-400 hover:bg-sky-500/10">
            Import
          </button>
          <button onClick={() => setModal({ type: "create" })}
            className="px-3 py-1.5 text-xs rounded bg-sky-600 hover:bg-sky-500 text-white">
            + Add Record
          </button>
        </div>
      </div>

      {/* Scope filter bar */}
      <div className="flex flex-wrap gap-2">
        {([
          ["date_from", "date", "From"],
          ["date_to", "date", "To"],
          ["department", "text", "Department"],
          ["building_area", "text", "Building/Area"],
          ["line_id", "text", "Line"],
          ["machine_id", "text", "Machine"],
          ["shift_id", "text", "Shift"],
        ] as [keyof WaterScope, string, string][]).map(([k, type, ph]) => (
          <input
            key={k}
            type={type}
            placeholder={ph}
            className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-300 w-28"
            value={scope[k] ?? ""}
            onChange={e => setS(k, e.target.value)}
          />
        ))}
      </div>

      {/* KPI Cards */}
      <Section title="Water Balance KPIs" />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPICard label="Raw Water In" value={`${fmt(kpis?.water_in_m3)} m³`} />
        <KPICard label="Process Water" value={`${fmt(kpis?.process_m3)} m³`} />
        <KPICard label="Wastewater" value={`${fmt(kpis?.wastewater_m3)} m³`} />
        <KPICard label="Balance" value={`${fmt(kpis?.balance_m3)} m³`}
          sub="In − Waste" />
        <KPICard
          label="Water Loss"
          value={kpis?.loss_pct ? `${fmt(kpis.loss_pct, 1)}%` : "—"}
          sub={kpis?.loss_m3 ? `${fmt(kpis.loss_m3)} m³` : undefined}
          alert={parseFloat(kpis?.loss_pct ?? "0") > 10}
        />
        <KPICard
          label="Recovery Rate"
          value={kpis?.recovery_pct ? `${fmt(kpis.recovery_pct, 1)}%` : "—"}
          sub="Process / In"
        />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard label="Avg m³/Day" value={`${fmt(kpis?.avg_m3_per_day)} m³`} />
        <KPICard label="Total Cost" value={kpis?.total_cost ? `$${fmt(kpis.total_cost)}` : "—"} />
        <KPICard label="Anomalies" value={String(kpis?.anomaly_count ?? 0)}
          alert={(kpis?.anomaly_count ?? 0) > 0} />
        <KPICard label="Records" value={String(kpis?.tx_count ?? 0)} />
      </div>

      {/* Daily Trend Chart */}
      <Section title="Daily Water Trend" />
      <div className="bg-white/5 border border-white/10 rounded-xl p-4" style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trendData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 10 }} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} tickFormatter={v => `${v}m³`} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1a1f2e", border: "1px solid #ffffff20", borderRadius: 8 }}
              labelStyle={{ color: "#e5e7eb" }}
              formatter={(v: unknown) => [`${Number(v).toLocaleString()} m³`]}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
            <Area type="monotone" dataKey="Raw Water"  stroke="#38bdf8" fill="#38bdf820" strokeWidth={2} />
            <Area type="monotone" dataKey="Process"    stroke="#34d399" fill="#34d39920" strokeWidth={2} />
            <Area type="monotone" dataKey="Wastewater" stroke="#f87171" fill="#f8717120" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Breakdown */}
      <Section title="Consumption Breakdown" />
      <div className="flex gap-3 flex-wrap mb-2">
        <select
          value={txType}
          onChange={e => setTxType(e.target.value as WaterUtilityType)}
          className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-300"
        >
          {(["WATER", "PROCESS_WATER", "WASTEWATER"] as WaterUtilityType[]).map(t => (
            <option key={t} value={t}>{WATER_TYPE_LABELS[t]}</option>
          ))}
        </select>
        <select
          value={breakdownDim}
          onChange={e => setBreakdownDim(e.target.value as BreakdownDim)}
          className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-300"
        >
          {(Object.keys(DIM_LABELS) as BreakdownDim[]).map(d => (
            <option key={d} value={d}>{DIM_LABELS[d]}</option>
          ))}
        </select>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Bar chart */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4" style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bkData} layout="vertical" margin={{ top: 5, right: 20, left: 60, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 10 }} tickFormatter={v => `${v}m³`} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#9ca3af", fontSize: 10 }} width={60} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1f2e", border: "1px solid #ffffff20", borderRadius: 8 }}
                formatter={(v: unknown) => [`${Number(v).toLocaleString()} m³`]}
              />
              <Bar dataKey="m3">
                {bkData.map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        {/* Summary table */}
        <div className="bg-white/5 border border-white/10 rounded-xl overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left px-3 py-2 text-gray-400">{DIM_LABELS[breakdownDim]}</th>
                <th className="text-right px-3 py-2 text-gray-400">m³</th>
                <th className="text-right px-3 py-2 text-gray-400">%</th>
                <th className="text-right px-3 py-2 text-gray-400">Cost</th>
              </tr>
            </thead>
            <tbody>
              {(breakdown?.rows ?? []).map((r, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                  <td className="px-3 py-2 text-gray-300">{r.label}</td>
                  <td className="px-3 py-2 text-right text-white">{fmt(r.total_m3)}</td>
                  <td className="px-3 py-2 text-right text-gray-400">{r.pct_of_total ? `${fmt(r.pct_of_total, 1)}%` : "—"}</td>
                  <td className="px-3 py-2 text-right text-gray-400">{r.total_cost ? `$${fmt(r.total_cost)}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction list */}
      <Section title="Transactions" />
      <div className="flex gap-2 mb-2">
        {(["WATER", "PROCESS_WATER", "WASTEWATER"] as WaterUtilityType[]).map(t => (
          <button
            key={t}
            onClick={() => setTxType(t)}
            className={`px-3 py-1 text-xs rounded-full border transition-colors ${
              txType === t
                ? "border-sky-500 bg-sky-500/20 text-sky-300"
                : "border-white/10 text-gray-400 hover:bg-white/5"
            }`}
          >
            {WATER_TYPE_LABELS[t]}
          </button>
        ))}
      </div>
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10">
              {["Tx No", "Date", "Quantity", "Department", "Line", "Machine", "Shift",
                "Cost", "Source", "Quality", "Flags", ""].map(h => (
                <th key={h} className="text-left px-3 py-2 text-gray-400 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {txList.map(tx => (
              <tr
                key={tx.id}
                className={`border-b border-white/5 hover:bg-white/5 ${tx.anomaly_flag ? "border-l-2 border-red-500/60" : ""}`}
              >
                <td className="px-3 py-2 font-mono text-gray-300">{tx.transaction_no}</td>
                <td className="px-3 py-2 text-gray-300">{fmtDate(tx.transaction_date)}</td>
                <td className="px-3 py-2 text-white">{fmt(tx.quantity)} {tx.uom}</td>
                <td className="px-3 py-2 text-gray-400">{tx.department ?? "—"}</td>
                <td className="px-3 py-2 text-gray-400">{tx.line_id ?? "—"}</td>
                <td className="px-3 py-2 text-gray-400">{tx.machine_id ?? "—"}</td>
                <td className="px-3 py-2 text-gray-400">{tx.shift_id ?? "—"}</td>
                <td className="px-3 py-2 text-gray-400">{tx.total_cost ? `$${fmt(tx.total_cost)}` : "—"}</td>
                <td className="px-3 py-2 text-gray-500">{tx.source_method}</td>
                <td className="px-3 py-2 text-gray-500">{tx.quality}</td>
                <td className="px-3 py-2">
                  {tx.anomaly_flag && <span className="text-red-400 mr-1">⚠</span>}
                  {tx.estimated_or_actual && <span className="text-amber-400">~</span>}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-2">
                    <button onClick={() => setModal({ type: "edit", tx })}
                      className="text-sky-400 hover:text-sky-300 text-xs">Edit</button>
                    <button onClick={() => setModal({ type: "delete", tx })}
                      className="text-red-400 hover:text-red-300 text-xs">Del</button>
                  </div>
                </td>
              </tr>
            ))}
            {txList.length === 0 && (
              <tr>
                <td colSpan={12} className="px-3 py-8 text-center text-gray-500">
                  No {WATER_TYPE_LABELS[txType]} records found for the selected scope.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modals */}
      {modal.type === "create" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-2xl">
            <h3 className="text-white font-semibold mb-4">Add Water Record</h3>
            <TxForm
              onSubmit={d => createMut.mutate(d)}
              onCancel={() => setModal({ type: "none" })}
              loading={createMut.isPending}
            />
          </div>
        </div>
      )}

      {modal.type === "edit" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-2xl">
            <h3 className="text-white font-semibold mb-4">Edit Water Record</h3>
            <TxForm
              initial={modal.tx as unknown as Partial<UtilityTransactionCreate>}
              onSubmit={d => updateMut.mutate({ id: modal.tx.id, d })}
              onCancel={() => setModal({ type: "none" })}
              loading={updateMut.isPending}
            />
          </div>
        </div>
      )}

      {modal.type === "delete" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-sm text-center">
            <p className="text-white mb-2">Delete this record?</p>
            <p className="text-gray-400 text-sm mb-4">{modal.tx.transaction_no}</p>
            <div className="flex gap-2 justify-center">
              <button onClick={() => setModal({ type: "none" })}
                className="px-4 py-1.5 rounded border border-white/10 text-gray-300 text-sm hover:bg-white/5">Cancel</button>
              <button onClick={() => deleteMut.mutate(modal.tx.id)}
                disabled={deleteMut.isPending}
                className="px-4 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white text-sm disabled:opacity-50">
                {deleteMut.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {modal.type === "import" && (
        <ImportModal
          onClose={() => setModal({ type: "none" })}
          onDone={() => { inv(); setModal({ type: "none" }); }}
        />
      )}
    </div>
  );
}
