"use client";

/**
 * Solar Energy Management Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Solar PV monitoring with KPIs, generation trends, breakdown analysis,
 * inverter operational records, and full transaction management.
 *
 * Sections:
 *   1. Global scope filters (date, dept, line, building, asset)
 *   2. KPI card strip (generated, self-consumed, grid export, PR ratio, cost savings, anomalies)
 *   3. Daily generation trend chart (AreaChart: generated + self-consumed + grid export)
 *   4. Performance metrics chart (PR ratio trend)
 *   5. Breakdown tabs (Dept / Line / Machine / Building / Shift)
 *   6. Operational records (SolarRecord — inverter data)
 *   7. Transactions table (create / edit / delete / export)
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import {
  solarApi,
  downloadSolarCsv,
  type SolarScope,
  type SolarTxFilters,
  type UtilityTransaction,
  type UtilityTransactionCreate,
  type UtilityTransactionUpdate,
  type SolarRecord,
  type SolarRecordCreate,
} from "@/lib/solar";
import { SOURCE_METHOD_LABELS, DATA_QUALITY_LABELS } from "@/lib/utilityTransactions";
import type { SourceMethod, DataQuality } from "@/lib/utilityTransactions";

// ── Palette ────────────────────────────────────────────────────────────────────
const AMBER  = "#f59e0b";
const GOLD   = "#fbbf24";
const TEAL   = "#2dd4bf";
const GREEN  = "#10b981";
const ORANGE = "#fb923c";
const RED    = "#f87171";

const BAR_COLORS = [
  "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6",
  "#ec4899", "#14b8a6", "#ef4444", "#6366f1",
];

// ── Number helpers ─────────────────────────────────────────────────────────────
const n = (v: string | null | undefined, dp = 1) =>
  v != null ? parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

const pct = (v: string | null | undefined) =>
  v != null ? `${parseFloat(v).toFixed(1)}%` : "—";

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

function Section({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-bold uppercase tracking-widest text-amber-500 border-b border-slate-700/50 pb-1 mb-3">
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
    utility_type:    "SOLAR",
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

  const inp = "bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 w-full";
  const lbl = "text-[11px] text-slate-400";

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(f); }} className="flex flex-col gap-5">
      <div>
        <Section>Generation</Section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1">
            <label className={lbl}>Date *</label>
            <input required type="date" value={f.transaction_date}
              onChange={(e) => s("transaction_date", e.target.value)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>kWh Generated *</label>
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
        <Section>Cost / Savings</Section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1">
            <label className={lbl}>Tariff (feed-in / avoided cost)</label>
            <select value={f.tariff_id ?? ""} onChange={(e) => s("tariff_id", e.target.value || null)} className={inp}>
              <option value="">— No tariff —</option>
              {tariffs.map((t) => (
                <option key={t.id} value={t.id}>{t.tariff_code} — {t.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Rate (/kWh)</label>
            <input type="number" step="any" min="0" value={f.cost_rate as string ?? ""}
              onChange={(e) => s("cost_rate", e.target.value || null)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Total Cost Offset</label>
            <input type="number" step="any" min="0" value={f.total_cost as string ?? ""}
              onChange={(e) => s("total_cost", e.target.value || null)} className={inp} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Currency</label>
            <input type="text" maxLength={3} value={f.currency_code ?? "USD"}
              onChange={(e) => s("currency_code", e.target.value.toUpperCase())} className={inp + " uppercase"} />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Variance from Expected</label>
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
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors">
          {isPending ? "Saving…" : label}
        </button>
      </div>
    </form>
  );
}

// ── Solar Record Form ─────────────────────────────────────────────────────────
function SolarRecordForm({
  onSubmit,
  isPending,
  error,
}: {
  onSubmit: (d: SolarRecordCreate) => void;
  isPending: boolean;
  error?: string | null;
}) {
  const [f, setF] = useState<SolarRecordCreate>({
    asset_id:        "",
    record_datetime: new Date().toISOString().slice(0, 16),
    source_method:   "IOT",
    is_anomaly:      false,
  });

  const s = <K extends keyof SolarRecordCreate>(k: K, v: SolarRecordCreate[K]) =>
    setF((p) => ({ ...p, [k]: v }));

  const inp = "bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 w-full";
  const lbl = "text-[11px] text-slate-400";

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(f); }} className="flex flex-col gap-5">
      <div>
        <Section>Identification</Section>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <label className={lbl}>Asset ID (Solar Panel / Inverter) *</label>
            <input required type="text" value={f.asset_id}
              onChange={(e) => s("asset_id", e.target.value)} className={inp}
              placeholder="UUID of solar asset" />
          </div>
          <div className="flex flex-col gap-1">
            <label className={lbl}>Record Datetime *</label>
            <input required type="datetime-local" value={f.record_datetime}
              onChange={(e) => s("record_datetime", e.target.value)} className={inp} />
          </div>
        </div>
      </div>

      <div>
        <Section>Environmental</Section>
        <div className="grid grid-cols-3 gap-3">
          {([
            ["Irradiance (W/m²)", "irradiance_wm2"],
            ["Panel Temp (°C)",   "panel_temp_c"],
            ["Ambient Temp (°C)", "ambient_temp_c"],
          ] as [string, keyof SolarRecordCreate][]).map(([fl, fk]) => (
            <div key={fk} className="flex flex-col gap-1">
              <label className={lbl}>{fl}</label>
              <input type="number" step="any"
                value={(f[fk] as string | null | undefined) ?? ""}
                onChange={(e) => s(fk, e.target.value || null)}
                className={inp} />
            </div>
          ))}
        </div>
      </div>

      <div>
        <Section>DC / AC Output</Section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {([
            ["DC Voltage (V)",     "dc_voltage_v"],
            ["DC Current (A)",     "dc_current_a"],
            ["DC Power (kW)",      "dc_power_kw"],
            ["AC Power (kW)",      "ac_power_kw"],
            ["Generated (kWh)",    "energy_generated_kwh"],
            ["Grid Export (kWh)",  "grid_export_kwh"],
            ["Self-Consumed (kWh)","self_consumption_kwh"],
          ] as [string, keyof SolarRecordCreate][]).map(([fl, fk]) => (
            <div key={fk} className="flex flex-col gap-1">
              <label className={lbl}>{fl}</label>
              <input type="number" step="any"
                value={(f[fk] as string | null | undefined) ?? ""}
                onChange={(e) => s(fk, e.target.value || null)}
                className={inp} />
            </div>
          ))}
        </div>
      </div>

      <div>
        <Section>Performance</Section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {([
            ["Inverter Efficiency (%)", "inverter_efficiency_pct"],
            ["PR Ratio",                "pr_ratio"],
            ["Availability (%)",        "availability_pct"],
            ["Capacity Factor (%)",     "capacity_factor_pct"],
          ] as [string, keyof SolarRecordCreate][]).map(([fl, fk]) => (
            <div key={fk} className="flex flex-col gap-1">
              <label className={lbl}>{fl}</label>
              <input type="number" step="any" min="0"
                value={(f[fk] as string | null | undefined) ?? ""}
                onChange={(e) => s(fk, e.target.value || null)}
                className={inp} />
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input type="checkbox" checked={f.is_anomaly ?? false}
            onChange={(e) => s("is_anomaly", e.target.checked)} className="accent-red-500" />
          Anomaly / Fault
        </label>
        {f.is_anomaly && (
          <input type="text" placeholder="Anomaly note…" value={f.anomaly_note ?? ""}
            onChange={(e) => s("anomaly_note", e.target.value || null)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-red-500 flex-1" />
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex justify-end">
        <button type="submit" disabled={isPending}
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors">
          {isPending ? "Saving…" : "Log Record"}
        </button>
      </div>
    </form>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type ModalState =
  | { type: "none" }
  | { type: "create" }
  | { type: "edit"; tx: UtilityTransaction }
  | { type: "view"; tx: UtilityTransaction }
  | { type: "delete"; tx: UtilityTransaction }
  | { type: "addRecord" }
  | { type: "deleteRecord"; rec: SolarRecord };

type BreakdownDim = "department" | "line" | "machine" | "building_area" | "shift";

const DIM_LABELS: Record<BreakdownDim, string> = {
  department:    "Department",
  line:          "Production Line",
  machine:       "Machine",
  building_area: "Building / Area",
  shift:         "Shift",
};

export default function SolarPage() {
  const qc = useQueryClient();

  // ── Scope filters ───────────────────────────────────────────────────────────
  const [scope, setScope] = useState<SolarScope>({});
  const [txFilters, setTxFilters] = useState<SolarTxFilters>({ limit: 200 });
  const [breakdownDim, setBreakdownDim] = useState<BreakdownDim>("department");
  const [activeTab, setActiveTab] = useState<"transactions" | "records">("transactions");
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [formError, setFormError] = useState<string | null>(null);

  function setS<K extends keyof SolarScope>(k: K, v: SolarScope[K]) {
    setScope((p) => ({ ...p, [k]: v || undefined }));
    setTxFilters((p) => ({ ...p, [k]: v || undefined }));
  }

  // ── Data queries ─────────────────────────────────────────────────────────────
  const { data: kpis } = useQuery({
    queryKey: ["solar-kpis", scope],
    queryFn:  () => solarApi.kpis(scope),
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["solar-trend", scope],
    queryFn:  () => solarApi.dailyTrend(scope),
  });

  const { data: breakdown } = useQuery({
    queryKey: ["solar-breakdown", breakdownDim, scope],
    queryFn:  () => solarApi.breakdown(breakdownDim, scope),
  });

  const { data: txRows = [], isLoading: txLoading } = useQuery({
    queryKey: ["solar-tx", txFilters],
    queryFn:  () => solarApi.listTransactions(txFilters),
  });

  const { data: solarRecords = [], isLoading: recLoading } = useQuery({
    queryKey: ["solar-records", scope.asset_id, scope.date_from, scope.date_to],
    queryFn:  () => solarApi.listRecords({
      asset_id: scope.asset_id,
      date_from: scope.date_from,
      date_to: scope.date_to,
    }),
  });

  const { data: tariffs = [] } = useQuery({
    queryKey: ["solar-tariffs"],
    queryFn:  () => solarApi.tariffs(true),
  });

  // ── Mutations ────────────────────────────────────────────────────────────────
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["solar-kpis"] });
    qc.invalidateQueries({ queryKey: ["solar-trend"] });
    qc.invalidateQueries({ queryKey: ["solar-breakdown"] });
    qc.invalidateQueries({ queryKey: ["solar-tx"] });
    qc.invalidateQueries({ queryKey: ["solar-records"] });
  };

  const createMut = useMutation({
    mutationFn: solarApi.createTransaction,
    onSuccess: () => { inv(); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save."),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityTransactionUpdate }) =>
      solarApi.updateTransaction(id, data),
    onSuccess: () => { inv(); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save."),
  });

  const deleteMut = useMutation({
    mutationFn: solarApi.deleteTransaction,
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });

  const addRecordMut = useMutation({
    mutationFn: solarApi.createRecord,
    onSuccess: () => { inv(); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save."),
  });

  const deleteRecordMut = useMutation({
    mutationFn: solarApi.deleteRecord,
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });

  // ── Chart data prep ──────────────────────────────────────────────────────────
  const trendData = useMemo(() => trend.map((p) => ({
    date:     p.date.slice(5),
    generated: parseFloat(p.total_generated_kwh),
    selfConsumed: p.self_consumption_kwh ? parseFloat(p.self_consumption_kwh) : null,
    exported: p.grid_export_kwh ? parseFloat(p.grid_export_kwh) : null,
    cost:     p.total_cost ? parseFloat(p.total_cost) : null,
    anom:     p.anomaly_count,
  })), [trend]);

  const prTrendData = useMemo(() => trend
    .filter((p) => p.avg_pr_ratio != null)
    .map((p) => ({
      date:    p.date.slice(5),
      pr:      parseFloat(p.avg_pr_ratio!),
    })),
    [trend]
  );

  const breakdownData = useMemo(
    () => (breakdown?.rows ?? []).slice(0, 12).map((r) => ({
      name: r.label,
      kwh:  parseFloat(r.total_generated_kwh),
      pct:  r.pct_of_total ? parseFloat(r.pct_of_total) : 0,
    })),
    [breakdown]
  );

  async function handleExport() {
    await downloadSolarCsv(
      { ...scope, is_anomaly: txFilters.is_anomaly },
      `solar-${new Date().toISOString().slice(0, 10)}.csv`
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6 flex flex-col gap-6">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                d="M12 3v1m0 16v1m8.66-9h-1M4.34 12h-1m15.07-5.66l-.71.71M6.34 17.66l-.71.71m12.73 0l-.71-.71M6.34 6.34l-.71-.71M12 7a5 5 0 100 10A5 5 0 0012 7z" />
            </svg>
            <h1 className="text-lg font-semibold text-slate-200">Solar Energy Management</h1>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 ml-7">
            Generation · self-consumption · grid export · PR ratio · inverter performance
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={handleExport}
            className="px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
            Export CSV
          </button>
          <button onClick={() => { setFormError(null); setModal({ type: "addRecord" }); }}
            className="px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
            + Operational Record
          </button>
          <button onClick={() => { setFormError(null); setModal({ type: "create" }); }}
            className="flex items-center gap-1.5 px-3 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm rounded font-medium transition-colors">
            <span className="text-base leading-none">+</span> Generation Record
          </button>
        </div>
      </div>

      {/* ── Scope filter bar ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 items-center bg-slate-800/40 border border-slate-700/40 rounded-lg p-3">
        <span className="text-[10px] text-slate-500 uppercase tracking-wider mr-1">Scope:</span>
        <input type="date" value={scope.date_from ?? ""} onChange={(e) => setS("date_from", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500" />
        <span className="text-slate-600 text-xs">–</span>
        <input type="date" value={scope.date_to ?? ""} onChange={(e) => setS("date_to", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500" />
        {[
          ["dept…",     "department"],
          ["line…",     "line_id"],
          ["building…", "building_area"],
          ["asset id…", "asset_id"],
        ].map(([ph, k]) => (
          <input key={k} type="text" placeholder={ph}
            value={(scope as Record<string, string | undefined>)[k] ?? ""}
            onChange={(e) => setS(k as keyof SolarScope, e.target.value || undefined)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 w-28" />
        ))}
        <button onClick={() => { setScope({}); setTxFilters({ limit: 200 }); }}
          className="ml-auto text-xs text-slate-500 hover:text-slate-300 transition-colors">
          Clear
        </button>
      </div>

      {/* ── KPI cards ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <KPICard label="Total Generated"   value={`${n(kpis?.total_generated_kwh)} kWh`}   sub={`${kpis?.tx_count ?? 0} records`} accent="text-amber-400" />
        <KPICard label="Avg kWh/Day"       value={`${n(kpis?.avg_generated_kwh_per_day)} kWh`} />
        <KPICard label="Peak Generation"   value={`${n(kpis?.peak_generation_kwh)} kWh`}   sub="max single record" accent="text-gold-400" />
        <KPICard label="Self-Consumed"     value={`${n(kpis?.total_self_consumption_kwh)} kWh`}
          sub={kpis?.self_consumption_ratio ? `Self-ratio: ${pct(kpis.self_consumption_ratio)}` : undefined}
          accent="text-green-400" />
        <KPICard label="Grid Export"       value={`${n(kpis?.total_grid_export_kwh)} kWh`} accent="text-teal-400" />
        <KPICard label="Avg PR Ratio"      value={kpis?.avg_pr_ratio ? n(kpis.avg_pr_ratio, 3) : "—"}
          sub={kpis?.avg_inverter_efficiency_pct ? `Inverter: ${pct(kpis.avg_inverter_efficiency_pct)}` : undefined}
          accent="text-amber-300" />
        <KPICard label="Cost Savings"      value={currency(kpis?.total_cost_offset)}
          sub={kpis?.avg_cost_per_kwh ? `${n(kpis.avg_cost_per_kwh, 4)}/kWh` : undefined}
          accent="text-emerald-400" />
        <KPICard label="Anomalies"         value={kpis?.anomaly_count ?? 0}
          accent={kpis?.anomaly_count ? "text-red-400" : "text-slate-200"}
          alert={!!kpis?.anomaly_count} />
      </div>

      {/* ── Generation trend chart ────────────────────────────────────────────── */}
      <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-4">
        <div className="text-xs font-semibold text-slate-300 mb-4">Daily Generation Trend</div>
        {trendData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-xs text-slate-500">
            No data for selected scope.
          </div>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gen-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={AMBER} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={AMBER} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="self-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={GREEN} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={GREEN} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="exp-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={TEAL} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={TEAL} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="generated"    name="Generated kWh"    stroke={AMBER} fill="url(#gen-grad)"  strokeWidth={1.5} dot={false} />
                <Area type="monotone" dataKey="selfConsumed" name="Self-Consumed kWh" stroke={GREEN} fill="url(#self-grad)" strokeWidth={1.5} dot={false} />
                <Area type="monotone" dataKey="exported"     name="Grid Export kWh"  stroke={TEAL}  fill="url(#exp-grad)"  strokeWidth={1.5} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* ── PR Ratio trend + Breakdown ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* PR Ratio trend */}
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-4 flex flex-col gap-3">
          <span className="text-xs font-semibold text-slate-300">Performance Ratio (PR) Trend</span>
          {prTrendData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-xs text-slate-500">
              No PR ratio data. Add solar operational records.
            </div>
          ) : (
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={prTrendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#64748b" }}
                    tickFormatter={(v) => v.toFixed(2)} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 11 }}
                    formatter={(v: unknown) => [Number(v).toFixed(3), "PR Ratio"]}
                  />
                  <Line type="monotone" dataKey="pr" name="PR Ratio"
                    stroke={GOLD} strokeWidth={2} dot={{ r: 2, fill: GOLD }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Breakdown by dimension */}
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">Generation Breakdown</span>
            <div className="flex gap-1 ml-auto flex-wrap">
              {(Object.keys(DIM_LABELS) as BreakdownDim[]).map((d) => (
                <button key={d} onClick={() => setBreakdownDim(d)}
                  className={`px-2 py-1 text-[10px] rounded transition-colors ${breakdownDim === d ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
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
                    <Bar dataKey="kwh" name="Generated kWh" radius={[0, 3, 3, 0]}>
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
                    <span className="text-slate-500 tabular-nums">{n(r.total_generated_kwh)} kWh</span>
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
      </div>

      {/* ── Data tabs: Transactions / Operational Records ────────────────────── */}
      <div className="flex gap-1 border-b border-slate-700/50">
        {(["transactions", "records"] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px ${activeTab === tab ? "border-amber-500 text-amber-400" : "border-transparent text-slate-500 hover:text-slate-300"}`}>
            {tab === "transactions" ? "Generation Records" : "Operational Logs (Inverter)"}
          </button>
        ))}
      </div>

      {/* ── Transactions table ────────────────────────────────────────────────── */}
      {activeTab === "transactions" && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">Generation Records</span>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
                <input type="checkbox" checked={txFilters.is_anomaly === true}
                  onChange={(e) => setTxFilters((p) => ({ ...p, is_anomaly: e.target.checked ? true : undefined }))}
                  className="accent-red-500" />
                Anomalies only
              </label>
              <input type="text" placeholder="Search…"
                value={txFilters.search ?? ""}
                onChange={(e) => setTxFilters((p) => ({ ...p, search: e.target.value || undefined }))}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 w-32" />
              <span className="text-xs text-slate-600">{txRows.length} rows</span>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-700/50">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-700/60 bg-slate-800/60">
                  {["Tx No.", "Date", "Generated kWh", "Cost Offset", "Dept / Line", "Shift", "Source", "Quality", "Actions"].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {txLoading && (
                  <tr><td colSpan={9} className="px-4 py-8 text-center text-xs text-slate-500">Loading…</td></tr>
                )}
                {!txLoading && txRows.length === 0 && (
                  <tr><td colSpan={9} className="px-4 py-8 text-center text-xs text-slate-500">No records found.</td></tr>
                )}
                {txRows.map((tx) => (
                  <tr key={tx.id} className={`hover:bg-slate-800/40 transition-colors ${tx.anomaly_flag ? "border-l-2 border-l-red-500/60" : ""}`}>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">
                      <button onClick={() => setModal({ type: "view", tx })}
                        className="font-mono text-amber-400 hover:text-amber-300 transition-colors">{tx.transaction_no}</button>
                      {tx.anomaly_flag && <span className="ml-1 inline-flex px-1 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">ANOM</span>}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-300 whitespace-nowrap">{tx.transaction_date}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">
                      <span className="font-medium text-slate-200">{parseFloat(tx.quantity).toLocaleString()}</span>
                      <span className="text-slate-500 ml-1 text-[10px]">{tx.uom}</span>
                      {tx.variance_from_standard != null && parseFloat(tx.variance_from_standard) !== 0 && (
                        <span className={`ml-1 text-[10px] ${parseFloat(tx.variance_from_standard) > 0 ? "text-emerald-400" : "text-red-400"}`}>
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
                    <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">{tx.shift_id ?? "—"}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap"><SrcBadge s={tx.source_method} /></td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap"><QBadge q={tx.quality} /></td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <button onClick={() => setModal({ type: "view", tx })} className="text-slate-400 hover:text-slate-200 transition-colors text-[11px]">View</button>
                        <button onClick={() => { setFormError(null); setModal({ type: "edit", tx }); }} className="text-amber-400 hover:text-amber-300 transition-colors text-[11px]">Edit</button>
                        <button onClick={() => setModal({ type: "delete", tx })} className="text-red-400 hover:text-red-300 transition-colors text-[11px]">Del</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Operational Records table ─────────────────────────────────────────── */}
      {activeTab === "records" && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">Inverter / Panel Operational Logs</span>
            <span className="text-xs text-slate-600">{solarRecords.length} rows</span>
          </div>
          <div className="overflow-x-auto rounded-lg border border-slate-700/50">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-700/60 bg-slate-800/60">
                  {["Record No.", "Asset", "Datetime", "Generated kWh", "Self-Consumed", "Grid Export", "PR Ratio", "Inv. Eff.", "Irradiance", "Anomaly", "Actions"].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {recLoading && (
                  <tr><td colSpan={11} className="px-4 py-8 text-center text-xs text-slate-500">Loading…</td></tr>
                )}
                {!recLoading && solarRecords.length === 0 && (
                  <tr><td colSpan={11} className="px-4 py-8 text-center text-xs text-slate-500">No operational records. Use "+ Operational Record" to log inverter data.</td></tr>
                )}
                {solarRecords.map((rec) => (
                  <tr key={rec.id} className={`hover:bg-slate-800/40 transition-colors ${rec.is_anomaly ? "border-l-2 border-l-red-500/60" : ""}`}>
                    <td className="px-3 py-2 text-xs font-mono text-amber-400 whitespace-nowrap">{rec.record_no}</td>
                    <td className="px-3 py-2 text-xs text-slate-300 whitespace-nowrap">{rec.asset_name ?? rec.asset_no ?? rec.asset_id.slice(0, 8)}</td>
                    <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">{rec.record_datetime.replace("T", " ").slice(0, 16)}</td>
                    <td className="px-3 py-2 text-xs font-medium text-slate-200 whitespace-nowrap">{rec.energy_generated_kwh ? n(rec.energy_generated_kwh) : "—"}</td>
                    <td className="px-3 py-2 text-xs text-green-400 whitespace-nowrap">{rec.self_consumption_kwh ? n(rec.self_consumption_kwh) : "—"}</td>
                    <td className="px-3 py-2 text-xs text-teal-400 whitespace-nowrap">{rec.grid_export_kwh ? n(rec.grid_export_kwh) : "—"}</td>
                    <td className="px-3 py-2 text-xs text-amber-300 whitespace-nowrap">{rec.pr_ratio ? n(rec.pr_ratio, 3) : "—"}</td>
                    <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">{rec.inverter_efficiency_pct ? pct(rec.inverter_efficiency_pct) : "—"}</td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{rec.irradiance_wm2 ? `${n(rec.irradiance_wm2, 1)} W/m²` : "—"}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">
                      {rec.is_anomaly
                        ? <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">FAULT</span>
                        : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">
                      <button onClick={() => setModal({ type: "deleteRecord", rec })} className="text-red-400 hover:text-red-300 transition-colors text-[11px]">Del</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Modals ───────────────────────────────────────────────────────────── */}
      {(modal.type === "create" || modal.type === "edit") && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
              <h2 className="text-sm font-semibold text-slate-200">
                {modal.type === "create" ? "Record Solar Generation" : "Edit Generation Record"}
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
                label={modal.type === "create" ? "Record Generation" : "Save Changes"}
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
                <p className="text-xs text-slate-500 mt-0.5">{modal.tx.transaction_date} · Solar Generation</p>
              </div>
              <button onClick={() => setModal({ type: "none" })} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="overflow-y-auto flex-1 px-5 py-4">
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-xs">
                {[
                  ["Generated", `${parseFloat(modal.tx.quantity).toLocaleString()} ${modal.tx.uom}`],
                  ["Cost Offset", currency(modal.tx.total_cost, modal.tx.currency_code ?? "USD")],
                  ["Rate", modal.tx.cost_rate ? `${modal.tx.currency_code} ${parseFloat(modal.tx.cost_rate).toFixed(4)}/kWh` : "—"],
                  ["Variance", modal.tx.variance_from_standard ? `${parseFloat(modal.tx.variance_from_standard).toFixed(2)} kWh` : "—"],
                  ["Department", modal.tx.department ?? "—"],
                  ["Building / Area", modal.tx.building_area ?? "—"],
                  ["Production Line", modal.tx.line_id ?? "—"],
                  ["Machine", modal.tx.machine_id ?? "—"],
                  ["Shift", modal.tx.shift_id ?? "—"],
                  ["Batch", modal.tx.batch_id ?? "—"],
                  ["Asset", modal.tx.asset_no ?? "—"],
                  ["Source Method", SOURCE_METHOD_LABELS[modal.tx.source_method]],
                  ["Tariff", modal.tx.tariff_code ?? "—"],
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

      {modal.type === "addRecord" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
              <h2 className="text-sm font-semibold text-slate-200">Log Inverter / Panel Operational Record</h2>
              <button onClick={() => setModal({ type: "none" })} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="overflow-y-auto flex-1 px-5 py-4">
              <SolarRecordForm
                onSubmit={(data) => addRecordMut.mutate(data)}
                isPending={addRecordMut.isPending}
                error={formError}
              />
            </div>
          </div>
        </div>
      )}

      {modal.type === "deleteRecord" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-sm p-5 flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-slate-200">Delete Operational Record</h2>
            <p className="text-xs text-slate-400">Delete <span className="font-mono text-slate-200">{modal.rec.record_no}</span>? This cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setModal({ type: "none" })}
                className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors">
                Cancel
              </button>
              <button onClick={() => deleteRecordMut.mutate(modal.rec.id)} disabled={deleteRecordMut.isPending}
                className="px-3 py-1.5 text-xs bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded transition-colors">
                {deleteRecordMut.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
