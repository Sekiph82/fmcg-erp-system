"use client";

/**
 * Electricity Management Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Plant-wide electricity monitoring with KPIs, trend chart, consumption
 * breakdown, shift analysis, and full transaction management.
 *
 * Sections:
 *   1. Global scope filters (date, dept, line, machine, shift, building)
 *   2. KPI card strip (kWh, cost, peak, base load, idle, solar, anomalies)
 *   3. Daily trend chart (recharts AreaChart)
 *   4. Breakdown + Shift Analysis (tabs: Dept / Line / Machine / Building / Shift)
 *   5. Transactions table (create / edit / delete / export / import)
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import {
  electricityApi,
  downloadElectricityCsv,
  type ElectricityScope,
  type ElectricityTxFilters,
  type UtilityTransaction,
  type UtilityTransactionCreate,
  type UtilityTransactionUpdate,
} from "@/lib/electricity";
import { SOURCE_METHOD_LABELS, DATA_QUALITY_LABELS } from "@/lib/utilityTransactions";
import type { SourceMethod, DataQuality } from "@/lib/utilityTransactions";
import { importApi, type ImportResult } from "@/lib/importApi";

// ── Palette ────────────────────────────────────────────────────────────────────
const YELLOW = "#facc15";
const ORANGE = "#fb923c";
const TEAL   = "#2dd4bf";
const RED    = "#f87171";
const SLATE  = "#94a3b8";

const BAR_COLORS = [
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
  "#f59e0b", "#10b981", "#ef4444", "#6366f1",
];

// ── Number helpers ─────────────────────────────────────────────────────────────
const n = (v: string | null | undefined, dp = 1) =>
  v != null ? parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

const currency = (v: string | null | undefined, code = "USD") =>
  v != null ? `${code} ${parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "—";

// ── KPI Card ───────────────────────────────────────────────────────────────────
interface KPICardProps {
  label:   string;
  value:   React.ReactNode;
  sub?:    React.ReactNode;
  accent?: string;
  alert?:  boolean;
}
function KPICard({ label, value, sub, accent = "text-slate-200", alert }: KPICardProps) {
  return (
    <div className={`bg-slate-800/60 border rounded-lg p-3.5 flex flex-col gap-1 ${alert ? "border-red-500/40" : "border-slate-700/50"}`}>
      <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
      <div className={`text-xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}

// ── Badge helpers ──────────────────────────────────────────────────────────────
function QBadge({ q }: { q: DataQuality }) {
  const cls: Record<DataQuality, string> = {
    GOOD: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    ESTIMATED: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    SUSPECT: "bg-orange-500/15 text-orange-400 border-orange-500/20",
    MISSING: "bg-red-500/15 text-red-400 border-red-500/20",
  };
  return <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium border ${cls[q]}`}>{DATA_QUALITY_LABELS[q]}</span>;
}

function SrcBadge({ s }: { s: SourceMethod }) {
  const cls: Record<SourceMethod, string> = {
    MANUAL: "bg-slate-500/15 text-slate-400 border-slate-500/20",
    IMPORTED: "bg-blue-500/15 text-blue-400 border-blue-500/20",
    API: "bg-purple-500/15 text-purple-400 border-purple-500/20",
    IOT: "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
    CALCULATED: "bg-indigo-500/15 text-indigo-400 border-indigo-500/20",
    ESTIMATED: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  };
  return <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium border ${cls[s]}`}>{SOURCE_METHOD_LABELS[s]}</span>;
}

// ── Section label ─────────────────────────────────────────────────────────────
function Section({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-bold uppercase tracking-widest text-yellow-500 border-b border-slate-700/50 pb-1 mb-3">
      {children}
    </div>
  );
}

// ── Transaction Form ──────────────────────────────────────────────────────────
interface TxFormProps {
  initial?: Partial<UtilityTransaction>;
  tariffs:  Array<{ id: string; tariff_code: string; name: string; currency_code: string }>;
  onSubmit: (d: UtilityTransactionCreate) => void;
  isPending: boolean;
  error?:   string | null;
  label?:   string;
}

function TxForm({ initial, tariffs, onSubmit, isPending, error, label = "Save" }: TxFormProps) {
  const [f, setF] = useState<UtilityTransactionCreate>({
    utility_type:    "ELECTRICITY",
    transaction_date: initial?.transaction_date ?? new Date().toISOString().slice(0, 10),
    quantity:         initial?.quantity ?? "",
    uom:              initial?.uom ?? "kWh",
    department:       initial?.department ?? null,
    building_area:    initial?.building_area ?? null,
    line_id:          initial?.line_id ?? null,
    machine_id:       initial?.machine_id ?? null,
    shift_id:         initial?.shift_id ?? null,
    batch_id:         initial?.batch_id ?? null,
    tariff_id:        initial?.tariff_id ?? null,
    cost_rate:        initial?.cost_rate ?? null,
    total_cost:       initial?.total_cost ?? null,
    currency_code:    initial?.currency_code ?? "USD",
    variance_from_standard: initial?.variance_from_standard ?? null,
    source_method:    (initial?.source_method as SourceMethod) ?? "MANUAL",
    quality:          (initial?.quality as DataQuality) ?? "GOOD",
    estimated_or_actual: initial?.estimated_or_actual ?? false,
    anomaly_flag:     initial?.anomaly_flag ?? false,
    anomaly_note:     initial?.anomaly_note ?? null,
    notes:            initial?.notes ?? null,
  });

  const s = <K extends keyof UtilityTransactionCreate>(k: K, v: UtilityTransactionCreate[K]) =>
    setF((p) => ({ ...p, [k]: v }));

  const inp = "bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-yellow-500 w-full";
  const lbl = "text-[11px] text-slate-400";

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(f); }} className="flex flex-col gap-5">
      <div>
        <Section>Consumption</Section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1">
            <label className={lbl}>Date *</label>
            <input required type="date" value={f.transaction_date}
              onChange={(e) => s("transaction_date", e.target.value)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>kWh Consumed *</label>
            <input required type="number" step="any" min="0" value={f.quantity as string}
              onChange={(e) => s("quantity", e.target.value)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>UOM</label>
            <input type="text" value={f.uom} onChange={(e) => s("uom", e.target.value)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Source</label>
            <select value={f.source_method} onChange={(e) => s("source_method", e.target.value as SourceMethod)} className={inp}>
              {Object.entries(SOURCE_METHOD_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div>
        <Section>Allocation</Section>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {(
            [
              ["Department",      "department"],
              ["Building / Area", "building_area"],
              ["Production Line", "line_id"],
              ["Machine",         "machine_id"],
              ["Shift",           "shift_id"],
              ["Batch",           "batch_id"],
            ] as [string, keyof UtilityTransactionCreate][]
          ).map(([fieldLabel, field]) => (
            <div key={field} className="flex flex-col gap-1">
              <label className={lbl}>{fieldLabel}</label>
              <input type="text"
                value={(f[field] as string | null | undefined) ?? ""}
                onChange={(e) => s(field, e.target.value || null)}
                className={inp} />
            </div>
          ))}
        </div>
      </div>

      <div>
        <Section>Cost</Section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1">
            <label className={lbl}>Tariff</label>
            <select value={f.tariff_id ?? ""} onChange={(e) => s("tariff_id", e.target.value || null)} className={inp}>
              <option value="">— No tariff —</option>
              {tariffs.map((t) => (
                <option key={t.id} value={t.id}>{t.tariff_code} — {t.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Cost Rate (/kWh)</label>
            <input type="number" step="any" min="0" value={f.cost_rate as string ?? ""}
              onChange={(e) => s("cost_rate", e.target.value || null)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Total Cost</label>
            <input type="number" step="any" min="0" value={f.total_cost as string ?? ""}
              onChange={(e) => s("total_cost", e.target.value || null)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Currency</label>
            <input type="text" maxLength={3} value={f.currency_code ?? "USD"}
              onChange={(e) => s("currency_code", e.target.value.toUpperCase())} className={inp + " uppercase"} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Variance from Standard</label>
            <input type="number" step="any" value={f.variance_from_standard as string ?? ""}
              onChange={(e) => s("variance_from_standard", e.target.value || null)} className={inp} />
          </div>
        </div>
      </div>

      <div>
        <Section>Quality & Flags</Section>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className={lbl}>Data Quality</label>
            <select value={f.quality} onChange={(e) => s("quality", e.target.value as DataQuality)} className={inp}>
              {Object.entries(DATA_QUALITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-4 pt-5">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" checked={f.estimated_or_actual}
                onChange={(e) => s("estimated_or_actual", e.target.checked)} className="accent-amber-500" />
              Estimated
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input type="checkbox" checked={f.anomaly_flag}
                onChange={(e) => s("anomaly_flag", e.target.checked)} className="accent-red-500" />
              Anomaly
            </label>
          </div>
          {f.anomaly_flag && (
            <div className="flex flex-col gap-1">
              <label className={lbl}>Anomaly Note</label>
              <input type="text" value={f.anomaly_note ?? ""}
                onChange={(e) => s("anomaly_note", e.target.value || null)} className={inp} />
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className={lbl}>Notes</label>
        <textarea rows={2} value={f.notes ?? ""}
          onChange={(e) => s("notes", e.target.value || null)}
          className={inp + " resize-none"} />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex justify-end">
        <button type="submit" disabled={isPending}
          className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors">
          {isPending ? "Saving…" : label}
        </button>
      </div>
    </form>
  );
}

// ── Import Modal ──────────────────────────────────────────────────────────────
function ImportModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"idle" | "validating" | "validated" | "importing" | "done">("idle");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleTemplate() {
    try { await importApi.downloadTemplate("electricity_transactions"); }
    catch { setError("Template download failed."); }
  }

  async function handleValidate() {
    if (!file) return;
    setStep("validating"); setError(null);
    try {
      const r = await importApi.validate("electricity_transactions", file);
      setResult(r); setStep("validated");
    } catch (e: unknown) {
      setError((e as { message?: string })?.message ?? "Validation failed.");
      setStep("idle");
    }
  }

  async function handleImport() {
    if (!file) return;
    setStep("importing"); setError(null);
    try {
      const r = await importApi.runImport("electricity_transactions", file, "import_valid_only");
      setResult(r); setStep("done"); onDone();
    } catch (e: unknown) {
      setError((e as { message?: string })?.message ?? "Import failed.");
      setStep("validated");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Import Electricity Records</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
        </div>

        <button onClick={handleTemplate}
          className="text-xs text-yellow-400 hover:text-yellow-300 text-left transition-colors">
          Download CSV template →
        </button>

        <div>
          <label className="text-[11px] text-slate-400 block mb-1">CSV File</label>
          <input type="file" accept=".csv"
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setStep("idle"); setResult(null); }}
            className="text-xs text-slate-300 file:mr-3 file:px-3 file:py-1.5 file:rounded file:bg-slate-700 file:border-0 file:text-slate-200 file:text-xs cursor-pointer" />
        </div>

        {result && (
          <div className="text-xs space-y-1">
            <div className="flex gap-4 text-slate-300">
              <span>Valid rows: <strong className="text-emerald-400">{result.valid_rows}</strong></span>
              <span>Failed rows: <strong className="text-red-400">{result.failed_rows}</strong></span>
              <span>Total: <strong className="text-slate-400">{result.total_rows}</strong></span>
            </div>
            {result.errors.length > 0 && (
              <div className="max-h-32 overflow-y-auto text-red-400 bg-red-500/10 border border-red-500/20 rounded p-2 space-y-0.5">
                {result.errors.slice(0, 20).map((e, i) => (
                  <div key={i}>Row {e.row}: {e.field} — {e.message}</div>
                ))}
                {result.errors.length > 20 && <div>… and {result.errors.length - 20} more</div>}
              </div>
            )}
          </div>
        )}

        {error && <p className="text-xs text-red-400">{error}</p>}

        <div className="flex justify-end gap-2">
          <button onClick={onClose}
            className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
            Close
          </button>
          {step === "idle" && (
            <button onClick={handleValidate} disabled={!file}
              className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition-colors">
              Validate
            </button>
          )}
          {step === "validating" && (
            <span className="text-xs text-slate-400 px-3 py-1.5">Validating…</span>
          )}
          {step === "validated" && (
            <button onClick={handleImport}
              className="px-3 py-1.5 text-xs bg-yellow-600 hover:bg-yellow-500 text-white rounded transition-colors">
              Import
            </button>
          )}
          {step === "importing" && (
            <span className="text-xs text-slate-400 px-3 py-1.5">Importing…</span>
          )}
          {step === "done" && (
            <span className="text-xs text-emerald-400 px-3 py-1.5">Done ✓</span>
          )}
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
  | { type: "view"; tx: UtilityTransaction }
  | { type: "delete"; tx: UtilityTransaction }
  | { type: "import" };

type BreakdownDim = "department" | "line" | "machine" | "building_area" | "shift";

const DIM_LABELS: Record<BreakdownDim, string> = {
  department:    "Department",
  line:          "Production Line",
  machine:       "Machine",
  building_area: "Building / Area",
  shift:         "Shift",
};

export default function ElectricityPage() {
  const qc = useQueryClient();

  // ── Scope filters ───────────────────────────────────────────────────────────
  const [scope, setScope] = useState<ElectricityScope>({});
  const [txFilters, setTxFilters] = useState<ElectricityTxFilters>({ limit: 200 });
  const [breakdownDim, setBreakdownDim] = useState<BreakdownDim>("department");
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [formError, setFormError] = useState<string | null>(null);

  function setS<K extends keyof ElectricityScope>(k: K, v: ElectricityScope[K]) {
    setScope((p) => ({ ...p, [k]: v || undefined }));
    setTxFilters((p) => ({ ...p, [k]: v || undefined }));
  }

  // ── Data queries ─────────────────────────────────────────────────────────────
  const { data: kpis } = useQuery({
    queryKey: ["elec-kpis", scope],
    queryFn:  () => electricityApi.kpis(scope),
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["elec-trend", scope],
    queryFn:  () => electricityApi.dailyTrend(scope),
  });

  const { data: shiftData = [] } = useQuery({
    queryKey: ["elec-shift", scope.date_from, scope.date_to, scope.department, scope.line_id],
    queryFn:  () => electricityApi.shiftTrend({
      date_from: scope.date_from, date_to: scope.date_to,
      department: scope.department, line_id: scope.line_id,
    }),
  });

  const { data: breakdown } = useQuery({
    queryKey: ["elec-breakdown", breakdownDim, scope],
    queryFn:  () => electricityApi.breakdown(breakdownDim, scope),
  });

  const { data: txRows = [], isLoading: txLoading } = useQuery({
    queryKey: ["elec-tx", txFilters],
    queryFn:  () => electricityApi.listTransactions(txFilters),
  });

  const { data: tariffs = [] } = useQuery({
    queryKey: ["elec-tariffs"],
    queryFn:  () => electricityApi.tariffs(true),
  });

  // ── Mutations ────────────────────────────────────────────────────────────────
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["elec-kpis"] });
    qc.invalidateQueries({ queryKey: ["elec-trend"] });
    qc.invalidateQueries({ queryKey: ["elec-shift"] });
    qc.invalidateQueries({ queryKey: ["elec-breakdown"] });
    qc.invalidateQueries({ queryKey: ["elec-tx"] });
  };

  const createMut = useMutation({
    mutationFn: electricityApi.createTransaction,
    onSuccess: () => { inv(); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save."),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityTransactionUpdate }) =>
      electricityApi.updateTransaction(id, data),
    onSuccess: () => { inv(); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save."),
  });

  const deleteMut = useMutation({
    mutationFn: electricityApi.deleteTransaction,
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });

  // ── Chart data prep ──────────────────────────────────────────────────────────
  const trendData = useMemo(() => trend.map((p) => ({
    date:  p.date.slice(5),   // MM-DD
    kwh:   parseFloat(p.total_kwh),
    cost:  p.total_cost ? parseFloat(p.total_cost) : null,
    anom:  p.anomaly_count,
  })), [trend]);

  const breakdownData = useMemo(
    () => (breakdown?.rows ?? []).slice(0, 12).map((r) => ({
      name: r.label,
      kwh:  parseFloat(r.total_kwh),
      pct:  r.pct_of_total ? parseFloat(r.pct_of_total) : 0,
    })),
    [breakdown]
  );

  async function handleExport() {
    await downloadElectricityCsv(
      { ...scope, is_anomaly: txFilters.is_anomaly },
      `electricity-${new Date().toISOString().slice(0, 10)}.csv`
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6 flex flex-col gap-6">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-yellow-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h1 className="text-lg font-semibold text-slate-200">Electricity Management</h1>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 ml-7">
            Plant-wide · department · line · machine · shift · solar · peak demand
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={() => setModal({ type: "import" })}
            className="px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
            Import CSV
          </button>
          <button onClick={handleExport}
            className="px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
            Export CSV
          </button>
          <button onClick={() => { setFormError(null); setModal({ type: "create" }); }}
            className="flex items-center gap-1.5 px-3 py-2 bg-yellow-600 hover:bg-yellow-500 text-white text-sm rounded font-medium transition-colors">
            <span className="text-base leading-none">+</span> Record
          </button>
        </div>
      </div>

      {/* ── Scope filter bar ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 items-center bg-slate-800/40 border border-slate-700/40 rounded-lg p-3">
        <span className="text-[10px] text-slate-500 uppercase tracking-wider mr-1">Scope:</span>
        <input type="date" value={scope.date_from ?? ""} onChange={(e) => setS("date_from", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-yellow-500" />
        <span className="text-slate-600 text-xs">–</span>
        <input type="date" value={scope.date_to ?? ""} onChange={(e) => setS("date_to", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-yellow-500" />
        {[
          ["dept…",     "department"],
          ["line…",     "line_id"],
          ["machine…",  "machine_id"],
          ["building…", "building_area"],
          ["shift…",    "shift_id"],
        ].map(([ph, k]) => (
          <input key={k} type="text" placeholder={ph}
            value={(scope as Record<string, string | undefined>)[k] ?? ""}
            onChange={(e) => setS(k as keyof ElectricityScope, e.target.value || undefined)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-yellow-500 w-24" />
        ))}
        <button onClick={() => { setScope({}); setTxFilters({ limit: 200 }); }}
          className="ml-auto text-xs text-slate-500 hover:text-slate-300 transition-colors">
          Clear
        </button>
      </div>

      {/* ── KPI cards ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <KPICard label="Total kWh" value={n(kpis?.total_kwh)} sub={`${kpis?.tx_count ?? 0} records`} accent="text-yellow-400" />
        <KPICard label="Avg kWh/Day" value={n(kpis?.avg_kwh_per_day)} />
        <KPICard label="Peak Demand" value={n(kpis?.peak_demand_kwh) + " kWh"} sub="max single record" accent="text-orange-400" />
        <KPICard label="Base Load" value={n(kpis?.base_load_kwh) + " kWh"} sub="avg bottom 20%" />
        <KPICard label="Idle / Non-Prod" value={n(kpis?.idle_kwh) + " kWh"} sub="no production linkage" />
        <KPICard label="Solar Offset" value={n(kpis?.solar_offset_kwh) + " kWh"}
          sub={kpis?.net_kwh ? `Net: ${n(kpis.net_kwh)} kWh` : undefined} accent="text-teal-400" />
        <KPICard label="Total Cost" value={currency(kpis?.total_cost)} sub={kpis?.avg_cost_per_kwh ? `${n(kpis.avg_cost_per_kwh, 4)}/kWh` : undefined} accent="text-emerald-400" />
        <KPICard label="Anomalies" value={kpis?.anomaly_count ?? 0} accent={kpis?.anomaly_count ? "text-red-400" : "text-slate-200"} alert={!!kpis?.anomaly_count} />
      </div>

      {/* Estimated warning strip */}
      {kpis?.estimated_pct && parseFloat(kpis.estimated_pct) > 20 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-400">
          <span className="font-medium">Estimated data:</span>
          {kpis.estimated_pct}% of records are estimated ({kpis.estimated_count} of {kpis.tx_count}).
          Verify meter readings or add actual measurements.
        </div>
      )}

      {/* ── Trend chart ──────────────────────────────────────────────────────── */}
      <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-4">
        <div className="text-xs font-semibold text-slate-300 mb-4">Daily Consumption Trend</div>
        {trendData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-xs text-slate-500">
            No data for selected scope.
          </div>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="kwh-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={YELLOW} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={YELLOW} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="cost-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={TEAL} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={TEAL} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis yAxisId="kwh" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis yAxisId="cost" orientation="right" tick={{ fontSize: 10, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area
                  yAxisId="kwh" type="monotone" dataKey="kwh" name="kWh"
                  stroke={YELLOW} fill="url(#kwh-grad)" strokeWidth={1.5} dot={false}
                />
                <Area
                  yAxisId="cost" type="monotone" dataKey="cost" name="Cost"
                  stroke={TEAL} fill="url(#cost-grad)" strokeWidth={1.5} dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* ── Breakdown + Shift Analysis ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Breakdown */}
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">Consumption Breakdown</span>
            <div className="flex gap-1 ml-auto flex-wrap">
              {(Object.keys(DIM_LABELS) as BreakdownDim[]).map((d) => (
                <button key={d} onClick={() => setBreakdownDim(d)}
                  className={`px-2 py-1 text-[10px] rounded transition-colors ${breakdownDim === d ? "bg-yellow-600 text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
                  {DIM_LABELS[d]}
                </button>
              ))}
            </div>
          </div>

          {breakdownData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-xs text-slate-500">No data.</div>
          ) : (
            <>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={breakdownData} layout="vertical" margin={{ top: 0, right: 40, left: 60, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: "#64748b" }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: "#94a3b8" }} width={60} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 11 }}
                      formatter={(v: unknown) => [`${Number(v).toLocaleString()} kWh`]}
                    />
                    <Bar dataKey="kwh" name="kWh" radius={[0, 3, 3, 0]}>
                      {breakdownData.map((_, i) => (
                        <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(breakdown?.rows ?? []).map((r, i) => (
                  <div key={r.group_key ?? i} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 truncate max-w-[140px]">{r.label}</span>
                    <span className="text-slate-500 tabular-nums">{n(r.total_kwh)} kWh</span>
                    <span className="text-slate-600 tabular-nums">{r.pct_of_total ? n(r.pct_of_total, 1) : "—"}%</span>
                    {r.anomaly_count > 0 && (
                      <span className="text-red-400 text-[10px]">{r.anomaly_count} anom.</span>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Shift analysis */}
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-4 flex flex-col gap-3">
          <span className="text-xs font-semibold text-slate-300">Shift / Time-of-Use Analysis</span>
          {shiftData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-xs text-slate-500">
              No shift data. Add shift references to transactions.
            </div>
          ) : (
            <>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={shiftData.map((s) => ({ name: s.label, kwh: parseFloat(s.total_kwh), cost: s.total_cost ? parseFloat(s.total_cost) : 0 }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 11 }}
                    />
                    <Bar dataKey="kwh" name="kWh" fill={ORANGE} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-700/50">
                      <th className="py-1.5 text-left text-[10px] text-slate-500 uppercase font-semibold tracking-wider">Shift</th>
                      <th className="py-1.5 text-right text-[10px] text-slate-500 uppercase font-semibold tracking-wider">kWh</th>
                      <th className="py-1.5 text-right text-[10px] text-slate-500 uppercase font-semibold tracking-wider">Cost</th>
                      <th className="py-1.5 text-right text-[10px] text-slate-500 uppercase font-semibold tracking-wider">Tx</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/30">
                    {shiftData.map((s, i) => (
                      <tr key={i} className="hover:bg-slate-800/30">
                        <td className="py-1.5 text-slate-200">{s.label}</td>
                        <td className="py-1.5 text-right text-slate-300 tabular-nums">{n(s.total_kwh)}</td>
                        <td className="py-1.5 text-right text-slate-400 tabular-nums">{currency(s.total_cost)}</td>
                        <td className="py-1.5 text-right text-slate-500">{s.tx_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Transaction table ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300">Electricity Records</span>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
              <input type="checkbox" checked={txFilters.is_anomaly === true}
                onChange={(e) => setTxFilters((p) => ({ ...p, is_anomaly: e.target.checked ? true : undefined }))}
                className="accent-red-500" />
              Anomalies only
            </label>
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
              <input type="checkbox" checked={txFilters.is_estimated === true}
                onChange={(e) => setTxFilters((p) => ({ ...p, is_estimated: e.target.checked ? true : undefined }))}
                className="accent-amber-500" />
              Estimated
            </label>
            <input type="text" placeholder="Search…"
              value={txFilters.search ?? ""}
              onChange={(e) => setTxFilters((p) => ({ ...p, search: e.target.value || undefined }))}
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-yellow-500 w-32" />
            <span className="text-xs text-slate-600">{txRows.length} rows</span>
          </div>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-700/50">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-700/60 bg-slate-800/60">
                {["Tx No.", "Date", "kWh", "Cost", "Dept / Line", "Machine", "Shift", "Batch", "Source", "Quality", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {txLoading && (
                <tr><td colSpan={11} className="px-4 py-8 text-center text-xs text-slate-500">Loading…</td></tr>
              )}
              {!txLoading && txRows.length === 0 && (
                <tr><td colSpan={11} className="px-4 py-8 text-center text-xs text-slate-500">No records found.</td></tr>
              )}
              {txRows.map((tx) => (
                <tr key={tx.id} className={`hover:bg-slate-800/40 transition-colors ${tx.anomaly_flag ? "border-l-2 border-l-red-500/60" : ""}`}>
                  <td className="px-3 py-2 text-xs whitespace-nowrap">
                    <button onClick={() => setModal({ type: "view", tx })}
                      className="font-mono text-yellow-400 hover:text-yellow-300 transition-colors">{tx.transaction_no}</button>
                    {tx.anomaly_flag && <span className="ml-1 inline-flex px-1 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">ANOM</span>}
                    {tx.estimated_or_actual && <span className="ml-1 inline-flex px-1 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">EST</span>}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-300 whitespace-nowrap">{tx.transaction_date}</td>
                  <td className="px-3 py-2 text-xs whitespace-nowrap">
                    <span className="font-medium text-slate-200">{parseFloat(tx.quantity).toLocaleString()}</span>
                    <span className="text-slate-500 ml-1 text-[10px]">{tx.uom}</span>
                    {tx.variance_from_standard != null && parseFloat(tx.variance_from_standard) !== 0 && (
                      <span className={`ml-1 text-[10px] ${parseFloat(tx.variance_from_standard) > 0 ? "text-red-400" : "text-emerald-400"}`}>
                        {parseFloat(tx.variance_from_standard) > 0 ? "▲" : "▼"}{Math.abs(parseFloat(tx.variance_from_standard)).toFixed(1)}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-300 whitespace-nowrap">
                    {tx.total_cost ? (
                      <span>{tx.currency_code} {parseFloat(tx.total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-300 whitespace-nowrap">
                    <div className="flex flex-col gap-0.5">
                      {tx.department && <span>{tx.department}</span>}
                      {tx.line_id && <span className="text-slate-500 text-[10px]">{tx.line_id}</span>}
                      {!tx.department && !tx.line_id && <span className="text-slate-600">—</span>}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">{tx.machine_id ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">{tx.shift_id ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap font-mono">{tx.batch_id ?? "—"}</td>
                  <td className="px-3 py-2 text-xs whitespace-nowrap"><SrcBadge s={tx.source_method} /></td>
                  <td className="px-3 py-2 text-xs whitespace-nowrap"><QBadge q={tx.quality} /></td>
                  <td className="px-3 py-2 text-xs whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <button onClick={() => setModal({ type: "view", tx })} className="text-slate-400 hover:text-slate-200 transition-colors text-[11px]">View</button>
                      <button onClick={() => { setFormError(null); setModal({ type: "edit", tx }); }} className="text-yellow-400 hover:text-yellow-300 transition-colors text-[11px]">Edit</button>
                      <button onClick={() => setModal({ type: "delete", tx })} className="text-red-400 hover:text-red-300 transition-colors text-[11px]">Del</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Modals ───────────────────────────────────────────────────────────── */}
      {(modal.type === "create" || modal.type === "edit") && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
              <h2 className="text-sm font-semibold text-slate-200">
                {modal.type === "create" ? "Record Electricity Consumption" : "Edit Record"}
              </h2>
              <button onClick={() => setModal({ type: "none" })} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="overflow-y-auto flex-1 px-5 py-4">
              <TxForm
                initial={modal.type === "edit" ? modal.tx : undefined}
                tariffs={tariffs}
                onSubmit={(data) => modal.type === "create"
                  ? createMut.mutate(data)
                  : updateMut.mutate({ id: (modal as { tx: UtilityTransaction }).tx.id, data })}
                isPending={createMut.isPending || updateMut.isPending}
                error={formError}
                label={modal.type === "create" ? "Record Consumption" : "Save Changes"}
              />
            </div>
          </div>
        </div>
      )}

      {modal.type === "view" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
              <div>
                <h2 className="text-sm font-semibold text-slate-200 font-mono">{modal.tx.transaction_no}</h2>
                <p className="text-xs text-slate-500 mt-0.5">{modal.tx.transaction_date} · Electricity</p>
              </div>
              <button onClick={() => setModal({ type: "none" })} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="overflow-y-auto flex-1 px-5 py-4">
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-xs">
                {[
                  ["kWh Consumed", `${parseFloat(modal.tx.quantity).toLocaleString()} ${modal.tx.uom}`],
                  ["Total Cost", currency(modal.tx.total_cost, modal.tx.currency_code ?? "USD")],
                  ["Cost Rate", modal.tx.cost_rate ? `${modal.tx.currency_code} ${parseFloat(modal.tx.cost_rate).toFixed(4)}/kWh` : "—"],
                  ["Variance", modal.tx.variance_from_standard ? `${parseFloat(modal.tx.variance_from_standard).toFixed(2)} kWh` : "—"],
                  ["Department", modal.tx.department ?? "—"],
                  ["Building / Area", modal.tx.building_area ?? "—"],
                  ["Production Line", modal.tx.line_id ?? "—"],
                  ["Machine", modal.tx.machine_id ?? "—"],
                  ["Shift", modal.tx.shift_id ?? "—"],
                  ["Batch", modal.tx.batch_id ?? "—"],
                  ["Device", modal.tx.device_code ?? "—"],
                  ["Asset", modal.tx.asset_no ?? "—"],
                  ["Source Method", SOURCE_METHOD_LABELS[modal.tx.source_method]],
                  ["Tariff", modal.tx.tariff_code ?? "—"],
                  ["Estimated?", modal.tx.estimated_or_actual ? "Yes" : "No"],
                  ["Anomaly?", modal.tx.anomaly_flag ? `Yes — ${modal.tx.anomaly_note ?? ""}` : "No"],
                ].map(([l, v]) => (
                  <div key={l} className="flex flex-col gap-0.5">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">{l}</span>
                    <span className="text-slate-200">{v}</span>
                  </div>
                ))}
                {modal.tx.notes && (
                  <div className="col-span-2 flex flex-col gap-0.5">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">Notes</span>
                    <span className="text-slate-300 whitespace-pre-wrap">{modal.tx.notes}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {modal.type === "delete" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-sm p-5 flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-slate-200">Delete Record</h2>
            <p className="text-xs text-slate-400">Delete <span className="font-mono text-slate-200">{modal.tx.transaction_no}</span>? This cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setModal({ type: "none" })}
                className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
                Cancel
              </button>
              <button onClick={() => deleteMut.mutate(modal.tx.id)} disabled={deleteMut.isPending}
                className="px-3 py-1.5 text-xs bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded transition-colors">
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
