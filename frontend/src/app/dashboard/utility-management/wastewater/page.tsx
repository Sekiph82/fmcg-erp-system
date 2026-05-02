"use client";

/**
 * Biological / Wastewater Treatment Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Full operational view of the biological/physico-chemical WWTP with:
 *   1. Scope filters (date, asset, treatment stage, compliance)
 *   2. Alarm banner — six alarm types, color-coded by severity
 *   3. KPI strip — 8 KPIs including removal efficiency, compliance %, cost
 *   4. Daily trend charts — COD/BOD removal, DO, pH, flow
 *   5. Stage analysis + compliance donut
 *   6. Records table — CRUD, export CSV, import
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from "recharts";
import {
  wastewaterApi,
  downloadWastewaterCsv,
  PROCESS_STAGE_LABELS,
  PROCESS_STAGE_COLORS,
  PROCESS_STAGE_BG,
  COMPLIANCE_LABELS,
  COMPLIANCE_COLORS,
  COMPLIANCE_BG,
  type WastewaterRecord,
  type WastewaterRecordCreate,
  type WastewaterRecordUpdate,
  type WastewaterAsset,
  type WastewaterFilters,
  type WastewaterProcess,
  type ComplianceStatus,
} from "@/lib/wastewater";
import { importApi, type ImportResult } from "@/lib/importApi";

// ── Palette ────────────────────────────────────────────────────────────────────
const CYAN   = "#22d3ee";
const ORANGE = "#fb923c";
const GREEN  = "#4ade80";
const AMBER  = "#fbbf24";
const RED    = "#f87171";
const BLUE   = "#60a5fa";
const VIOLET = "#a78bfa";
const TEAL   = "#2dd4bf";

const BAR_COLORS = [
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
  "#f59e0b", "#10b981", "#ef4444", "#6366f1",
];

const COMPLIANCE_CHART_COLORS: Record<string, string> = {
  COMPLIANT:     "#4ade80",
  NON_COMPLIANT: "#f87171",
  BORDERLINE:    "#fbbf24",
  NOT_TESTED:    "#94a3b8",
};

// ── Helpers ────────────────────────────────────────────────────────────────────
const n = (v: number | string | null | undefined, dp = 1) =>
  v != null ? parseFloat(String(v)).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

const fmtDate = (d: string) => {
  try { return new Date(d).toLocaleDateString(); } catch { return d; }
};

const fmtDatetime = (d: string) => {
  try { return new Date(d).toLocaleString(); } catch { return d; }
};

// ── KPI Card ───────────────────────────────────────────────────────────────────
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

// ── Alarm Banner ───────────────────────────────────────────────────────────────
interface AlarmItem {
  key:      string;
  active:   boolean;
  severity: string;
  label:    string;
  detail:   string;
}

function AlarmBanner({ alarms }: { alarms: AlarmItem[] }) {
  const active = alarms.filter(a => a.active);
  if (active.length === 0) return null;

  const severityStyle = (s: string) => {
    if (s === "CRITICAL") return "bg-red-500/10 border-red-500/40 text-red-300";
    if (s === "ALERT")    return "bg-orange-500/10 border-orange-500/40 text-orange-300";
    return "bg-amber-500/10 border-amber-500/40 text-amber-300";
  };

  return (
    <div className="flex flex-col gap-2 mb-4">
      {active.map(a => (
        <div key={a.key} className={`flex items-start gap-3 border rounded-lg px-4 py-3 ${severityStyle(a.severity)}`}>
          <span className="text-lg mt-0.5">
            {a.severity === "CRITICAL" ? "🔴" : a.severity === "ALERT" ? "🟠" : "🟡"}
          </span>
          <div>
            <span className="font-semibold text-sm">{a.label}</span>
            <span className="text-xs ml-2 opacity-80">{a.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Compliance Badge ───────────────────────────────────────────────────────────
function ComplianceBadge({ status }: { status: ComplianceStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${COMPLIANCE_BG[status]} ${COMPLIANCE_COLORS[status]}`}>
      {COMPLIANCE_LABELS[status]}
    </span>
  );
}

// ── Stage Badge ────────────────────────────────────────────────────────────────
function StageBadge({ stage }: { stage: WastewaterProcess }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${PROCESS_STAGE_BG[stage]} ${PROCESS_STAGE_COLORS[stage]}`}>
      {PROCESS_STAGE_LABELS[stage]}
    </span>
  );
}

// ── Import Modal ───────────────────────────────────────────────────────────────
function ImportModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);

  const handleImport = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const res = await importApi.upload("wastewater", file);
      setResult(res);
      qc.invalidateQueries({ queryKey: ["ww-records"] });
      qc.invalidateQueries({ queryKey: ["ww-kpis"] });
    } catch (e: unknown) {
      setResult({ success: false, message: String(e), inserted: 0, errors: [], total_rows: 0, valid_rows: 0, failed_rows: 0, imported: false, import_mode: "", module: "wastewater" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 w-full max-w-md shadow-2xl">
        <h3 className="text-white font-semibold text-lg mb-4">Import Wastewater Records (CSV)</h3>
        <input
          type="file" accept=".csv"
          onChange={e => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-300 mb-4"
        />
        {result && (
          <div className={`text-sm mb-4 p-3 rounded ${result.success ? "bg-emerald-900/40 text-emerald-300" : "bg-red-900/40 text-red-300"}`}>
            {result.message} {result.success ? `(${result.inserted} inserted)` : ""}
          </div>
        )}
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600">
            Close
          </button>
          <button
            onClick={handleImport}
            disabled={!file || busy}
            className="px-4 py-2 rounded bg-cyan-600 text-white text-sm hover:bg-cyan-500 disabled:opacity-50"
          >
            {busy ? "Importing…" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Record Form Modal ──────────────────────────────────────────────────────────
function RecordModal({
  assets,
  record,
  onClose,
}: {
  assets: WastewaterAsset[];
  record?: WastewaterRecord | null;
  onClose: () => void;
}) {
  const qc  = useQueryClient();
  const now = new Date().toISOString().slice(0, 16);

  const [form, setForm] = useState<Partial<WastewaterRecordCreate>>({
    asset_id:          record?.asset_id        ?? (assets[0]?.id ?? ""),
    record_datetime:   record?.record_datetime  ? record.record_datetime.slice(0, 16) : now,
    process_stage:     record?.process_stage    ?? "SECONDARY",
    shift_ref:         record?.shift_ref        ?? "",
    influent_flow_m3h: record?.influent_flow_m3h ?? undefined,
    effluent_flow_m3h: record?.effluent_flow_m3h ?? undefined,
    influent_ph:       record?.influent_ph       ?? undefined,
    effluent_ph:       record?.effluent_ph       ?? undefined,
    influent_cod_mgl:  record?.influent_cod_mgl  ?? undefined,
    effluent_cod_mgl:  record?.effluent_cod_mgl  ?? undefined,
    influent_bod_mgl:  record?.influent_bod_mgl  ?? undefined,
    effluent_bod_mgl:  record?.effluent_bod_mgl  ?? undefined,
    influent_tss_mgl:  record?.influent_tss_mgl  ?? undefined,
    effluent_tss_mgl:  record?.effluent_tss_mgl  ?? undefined,
    conductivity_us_cm: record?.conductivity_us_cm ?? undefined,
    temperature_c:     record?.temperature_c     ?? undefined,
    do_mgl:            record?.do_mgl            ?? undefined,
    mlss_mgl:          record?.mlss_mgl          ?? undefined,
    aeration_runtime_hours: record?.aeration_runtime_hours ?? undefined,
    blower_power_kw:   record?.blower_power_kw   ?? undefined,
    nutrient_dose_kg:  record?.nutrient_dose_kg  ?? undefined,
    antifoam_dose_kg:  record?.antifoam_dose_kg  ?? undefined,
    sludge_produced_kg:    record?.sludge_produced_kg    ?? undefined,
    sludge_volume_m3:      record?.sludge_volume_m3      ?? undefined,
    sludge_disposal_qty_kg: record?.sludge_disposal_qty_kg ?? undefined,
    compliance_status: record?.compliance_status ?? "COMPLIANT",
    permit_limit_ref:  record?.permit_limit_ref  ?? "",
    deviation_reason:  record?.deviation_reason  ?? "",
    corrective_action: record?.corrective_action ?? "",
    notes:             record?.notes             ?? "",
    source_method:     "MANUAL",
    is_anomaly:        record?.is_anomaly        ?? false,
  });

  const set = (k: keyof WastewaterRecordCreate, v: unknown) =>
    setForm(f => ({ ...f, [k]: v === "" ? undefined : v }));

  const createMut = useMutation({
    mutationFn: (d: WastewaterRecordCreate) => wastewaterApi.createRecord(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ww-records"] });
      qc.invalidateQueries({ queryKey: ["ww-kpis"] });
      qc.invalidateQueries({ queryKey: ["ww-trend"] });
      onClose();
    },
  });

  const updateMut = useMutation({
    mutationFn: (d: WastewaterRecordUpdate) => wastewaterApi.updateRecord(record!.id, d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ww-records"] });
      qc.invalidateQueries({ queryKey: ["ww-kpis"] });
      onClose();
    },
  });

  const busy = createMut.isPending || updateMut.isPending;
  const err  = createMut.error || updateMut.error;

  const handleSubmit = () => {
    const payload = {
      ...form,
      record_datetime: form.record_datetime ? new Date(form.record_datetime).toISOString() : new Date().toISOString(),
    } as WastewaterRecordCreate;
    if (record) {
      updateMut.mutate(payload as WastewaterRecordUpdate);
    } else {
      createMut.mutate(payload);
    }
  };

  const field = (label: string, key: keyof WastewaterRecordCreate, type = "number", placeholder = "") => (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-slate-400">{label}</label>
      <input
        type={type}
        step="any"
        placeholder={placeholder}
        value={form[key] as string ?? ""}
        onChange={e => set(key, type === "number" ? (e.target.value === "" ? undefined : parseFloat(e.target.value)) : e.target.value)}
        className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 overflow-y-auto p-4">
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 w-full max-w-4xl shadow-2xl">
        <h3 className="text-white font-semibold text-lg mb-5">
          {record ? "Edit Wastewater Record" : "New Wastewater Record"}
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Asset */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Asset / WWTP Unit</label>
            <select
              value={form.asset_id ?? ""}
              onChange={e => set("asset_id", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {assets.map(a => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
            </select>
          </div>

          {/* Datetime */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Date / Time</label>
            <input
              type="datetime-local"
              value={form.record_datetime ?? ""}
              onChange={e => set("record_datetime", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Stage */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Treatment Stage</label>
            <select
              value={form.process_stage ?? "SECONDARY"}
              onChange={e => set("process_stage", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {(["PRIMARY", "SECONDARY", "TERTIARY", "SLUDGE_HANDLING"] as WastewaterProcess[]).map(s => (
                <option key={s} value={s}>{PROCESS_STAGE_LABELS[s]}</option>
              ))}
            </select>
          </div>

          {/* Compliance Status */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Compliance Status</label>
            <select
              value={form.compliance_status ?? "COMPLIANT"}
              onChange={e => set("compliance_status", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {(["COMPLIANT", "NON_COMPLIANT", "BORDERLINE", "NOT_TESTED"] as ComplianceStatus[]).map(s => (
                <option key={s} value={s}>{COMPLIANCE_LABELS[s]}</option>
              ))}
            </select>
          </div>

          {/* Flow */}
          {field("Influent Flow (m³/h)", "influent_flow_m3h")}
          {field("Effluent Flow (m³/h)", "effluent_flow_m3h")}

          {/* pH */}
          {field("Influent pH", "influent_ph")}
          {field("Effluent pH", "effluent_ph")}

          {/* COD */}
          {field("Influent COD (mg/L)", "influent_cod_mgl")}
          {field("Effluent COD (mg/L)", "effluent_cod_mgl")}

          {/* BOD */}
          {field("Influent BOD (mg/L)", "influent_bod_mgl")}
          {field("Effluent BOD (mg/L)", "effluent_bod_mgl")}

          {/* TSS */}
          {field("Influent TSS (mg/L)", "influent_tss_mgl")}
          {field("Effluent TSS (mg/L)", "effluent_tss_mgl")}

          {/* Other process */}
          {field("Conductivity (µS/cm)", "conductivity_us_cm")}
          {field("Temperature (°C)", "temperature_c")}
          {field("Dissolved Oxygen (mg/L)", "do_mgl")}
          {field("MLSS (mg/L)", "mlss_mgl")}

          {/* Blower */}
          {field("Blower Runtime (h)", "aeration_runtime_hours")}
          {field("Blower Power (kW)", "blower_power_kw")}

          {/* Dosing */}
          {field("Nutrient Dose (kg)", "nutrient_dose_kg")}
          {field("Antifoam Dose (kg)", "antifoam_dose_kg")}

          {/* Sludge */}
          {field("Sludge Produced (kg)", "sludge_produced_kg")}
          {field("Sludge Volume (m³)", "sludge_volume_m3")}
          {field("Sludge Disposal (kg)", "sludge_disposal_qty_kg")}

          {/* Permit */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Permit Limit Reference</label>
            <input
              type="text"
              value={form.permit_limit_ref ?? ""}
              onChange={e => set("permit_limit_ref", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Deviation */}
          <div className="flex flex-col gap-1 col-span-4">
            <label className="text-xs text-slate-400">Deviation Reason</label>
            <textarea
              rows={2}
              value={form.deviation_reason ?? ""}
              onChange={e => set("deviation_reason", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Corrective action */}
          <div className="flex flex-col gap-1 col-span-4">
            <label className="text-xs text-slate-400">Corrective Action</label>
            <textarea
              rows={2}
              value={form.corrective_action ?? ""}
              onChange={e => set("corrective_action", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Notes */}
          <div className="flex flex-col gap-1 col-span-4">
            <label className="text-xs text-slate-400">Notes</label>
            <textarea
              rows={2}
              value={form.notes ?? ""}
              onChange={e => set("notes", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {err && (
          <p className="text-red-400 text-sm mt-3">
            {(err as Error)?.message ?? "An error occurred."}
          </p>
        )}

        <div className="flex gap-2 justify-end mt-5">
          <button onClick={onClose} className="px-4 py-2 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={busy}
            className="px-4 py-2 rounded bg-cyan-600 text-white text-sm hover:bg-cyan-500 disabled:opacity-50"
          >
            {busy ? "Saving…" : record ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════════════

export default function WastewaterPage() {
  const qc = useQueryClient();

  // ── Filters ────────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState<WastewaterFilters>({});
  const [showImport, setShowImport] = useState(false);
  const [showForm,   setShowForm]   = useState(false);
  const [editRecord, setEditRecord] = useState<WastewaterRecord | null>(null);
  const [deleteId,   setDeleteId]   = useState<string | null>(null);

  const setFilter = (k: keyof WastewaterFilters, v: unknown) =>
    setFilters(f => ({ ...f, [k]: v === "" ? undefined : v }));

  // ── Queries ────────────────────────────────────────────────────────────────
  const { data: assets = [] } = useQuery({
    queryKey: ["ww-assets"],
    queryFn:  wastewaterApi.listAssets,
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["ww-kpis", filters],
    queryFn:  () => wastewaterApi.kpis(filters),
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["ww-trend", filters],
    queryFn:  () => wastewaterApi.dailyTrend(filters),
  });

  const { data: stages = [] } = useQuery({
    queryKey: ["ww-stages", filters],
    queryFn:  () => wastewaterApi.stageAnalysis(filters),
  });

  const { data: compliance } = useQuery({
    queryKey: ["ww-compliance", filters],
    queryFn:  () => wastewaterApi.complianceSummary(filters),
  });

  const { data: records = [], isLoading: recLoading } = useQuery({
    queryKey: ["ww-records", filters],
    queryFn:  () => wastewaterApi.listRecords({ ...filters, limit: 300 }),
  });

  // ── Delete mutation ────────────────────────────────────────────────────────
  const deleteMut = useMutation({
    mutationFn: (id: string) => wastewaterApi.deleteRecord(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ww-records"] });
      qc.invalidateQueries({ queryKey: ["ww-kpis"] });
      setDeleteId(null);
    },
  });

  // ── Alarm items ────────────────────────────────────────────────────────────
  const alarmItems = useMemo(() => {
    if (!kpis) return [];
    return [
      {
        key: "ph", active: kpis.alarm_ph_out_of_range, severity: "ALERT",
        label: "pH Out of Range",
        detail: `Effluent pH outside [6.0 – 9.0]. Avg: ${n(kpis.avg_effluent_ph, 2)}`,
      },
      {
        key: "cod", active: kpis.alarm_cod_high, severity: "CRITICAL",
        label: "COD Exceedance",
        detail: `Avg effluent COD ${n(kpis.avg_effluent_cod)} mg/L exceeds 150 mg/L limit.`,
      },
      {
        key: "do", active: kpis.alarm_low_do, severity: "WARNING",
        label: "Low Dissolved Oxygen",
        detail: `Avg DO ${n(kpis.avg_do_mgl)} mg/L is below 1.5 mg/L minimum.`,
      },
      {
        key: "blower", active: kpis.alarm_blower_failure, severity: "CRITICAL",
        label: "Blower Failure",
        detail: "One or more records show zero aeration runtime.",
      },
      {
        key: "overflow", active: kpis.alarm_overflow_risk, severity: "ALERT",
        label: "Overflow Risk",
        detail: "Influent flow exceeded overflow threshold (500 m³/h).",
      },
      {
        key: "nc", active: kpis.alarm_non_compliant_discharge, severity: "CRITICAL",
        label: "Non-Compliant Discharge",
        detail: `${kpis.non_compliant_count} non-compliant record(s) in selected period.`,
      },
    ];
  }, [kpis]);

  // ── Compliance donut data ──────────────────────────────────────────────────
  const compliancePieData = useMemo(() => {
    if (!compliance) return [];
    return [
      { name: "Compliant",     value: compliance.compliant,     fill: COMPLIANCE_CHART_COLORS.COMPLIANT },
      { name: "Non-Compliant", value: compliance.non_compliant, fill: COMPLIANCE_CHART_COLORS.NON_COMPLIANT },
      { name: "Borderline",    value: compliance.borderline,    fill: COMPLIANCE_CHART_COLORS.BORDERLINE },
      { name: "Not Tested",    value: compliance.not_tested,    fill: COMPLIANCE_CHART_COLORS.NOT_TESTED },
    ].filter(d => d.value > 0);
  }, [compliance]);

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-1">Biological / Wastewater Treatment</h1>
      <p className="text-slate-400 text-sm mb-6">Influent quality, treatment efficiency, compliance monitoring, and sludge management.</p>

      {/* ── Filters ── */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="date"
          value={filters.date_from ?? ""}
          onChange={e => setFilter("date_from", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        />
        <input
          type="date"
          value={filters.date_to ?? ""}
          onChange={e => setFilter("date_to", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        />
        <select
          value={filters.asset_id ?? ""}
          onChange={e => setFilter("asset_id", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Assets</option>
          {assets.map(a => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
        </select>
        <select
          value={filters.process_stage ?? ""}
          onChange={e => setFilter("process_stage", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Stages</option>
          {(["PRIMARY", "SECONDARY", "TERTIARY", "SLUDGE_HANDLING"] as WastewaterProcess[]).map(s => (
            <option key={s} value={s}>{PROCESS_STAGE_LABELS[s]}</option>
          ))}
        </select>
        <select
          value={filters.compliance_status ?? ""}
          onChange={e => setFilter("compliance_status", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Compliance</option>
          {(["COMPLIANT", "NON_COMPLIANT", "BORDERLINE", "NOT_TESTED"] as ComplianceStatus[]).map(s => (
            <option key={s} value={s}>{COMPLIANCE_LABELS[s]}</option>
          ))}
        </select>
        <button
          onClick={() => setFilters({})}
          className="px-3 py-1.5 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600"
        >
          Reset
        </button>
      </div>

      {/* ── Alarm Banner ── */}
      <AlarmBanner alarms={alarmItems} />

      {/* ── KPI Cards ── */}
      {kpisLoading ? (
        <p className="text-slate-400 text-sm mb-6">Loading KPIs…</p>
      ) : kpis ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <KPICard
            label="COD Removal"
            value={kpis.cod_removal_pct != null ? `${n(kpis.cod_removal_pct)}%` : "—"}
            sub={`Influent ${n(kpis.avg_influent_cod)} → Effluent ${n(kpis.avg_effluent_cod)} mg/L`}
            accent="border-cyan-700"
          />
          <KPICard
            label="BOD Removal"
            value={kpis.bod_removal_pct != null ? `${n(kpis.bod_removal_pct)}%` : "—"}
            sub={`Influent ${n(kpis.avg_influent_bod)} → Effluent ${n(kpis.avg_effluent_bod)} mg/L`}
            accent="border-teal-700"
          />
          <KPICard
            label="Compliance"
            value={kpis.compliance_pct != null ? `${n(kpis.compliance_pct)}%` : "—"}
            sub={`${kpis.compliant_count} compliant / ${kpis.record_count} records`}
            accent="border-emerald-700"
            flag={kpis.non_compliant_count > 0}
            flagMsg={kpis.non_compliant_count > 0 ? `${kpis.non_compliant_count} non-compliant` : undefined}
          />
          <KPICard
            label="Treatment Cost / m³"
            value={kpis.treatment_cost_per_m3 != null ? `$${n(kpis.treatment_cost_per_m3, 4)}` : "—"}
            sub={kpis.treatment_cost_total != null ? `Total $${n(kpis.treatment_cost_total, 2)}` : "No cost data"}
            accent="border-orange-700"
          />
          <KPICard
            label="Blower Energy / m³"
            value={kpis.blower_energy_per_m3 != null ? `${n(kpis.blower_energy_per_m3, 4)} kWh` : "—"}
            sub={`Total power: ${n(kpis.total_power_kwh, 1)} kWh`}
            accent="border-blue-700"
            flag={kpis.alarm_blower_failure}
            flagMsg={kpis.alarm_blower_failure ? "Blower failure detected" : undefined}
          />
          <KPICard
            label="Sludge Generation Rate"
            value={kpis.sludge_gen_rate != null ? `${n(kpis.sludge_gen_rate, 3)} kg/m³` : "—"}
            sub={`Total: ${n(kpis.total_sludge_produced_kg, 0)} kg`}
            accent="border-amber-700"
          />
          <KPICard
            label="Avg Dissolved Oxygen"
            value={kpis.avg_do_mgl != null ? `${n(kpis.avg_do_mgl, 2)} mg/L` : "—"}
            sub="Aeration tank"
            accent="border-violet-700"
            flag={kpis.alarm_low_do}
            flagMsg={kpis.alarm_low_do ? "Below 1.5 mg/L minimum" : undefined}
          />
          <KPICard
            label="Non-Compliance Risk"
            value={kpis.non_compliance_risk ? "HIGH" : "LOW"}
            sub="Based on last 7 days"
            accent={kpis.non_compliance_risk ? "border-red-700" : "border-slate-700"}
            flag={kpis.non_compliance_risk}
            flagMsg={kpis.non_compliance_risk ? "Recent non-compliant trend" : undefined}
          />
        </div>
      ) : null}

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* COD / BOD Trend */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">COD / BOD — Daily Trend (mg/L)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }}
                formatter={(v: unknown) => n(v as number | null | undefined, 1)}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="avg_cod_influent" name="COD In"  stroke={RED}    strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="avg_cod_effluent" name="COD Out" stroke={ORANGE} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="avg_bod_influent" name="BOD In"  stroke={BLUE}   strokeWidth={2} dot={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="avg_bod_effluent" name="BOD Out" stroke={CYAN}   strokeWidth={2} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* DO & pH Trend */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Dissolved Oxygen & Effluent pH — Daily</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={d => d.slice(5)} />
              <YAxis yAxisId="do"  tick={{ fill: "#94a3b8", fontSize: 11 }} domain={[0, 10]} />
              <YAxis yAxisId="ph"  orientation="right" tick={{ fill: "#94a3b8", fontSize: 11 }} domain={[4, 12]} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }}
                formatter={(v: unknown) => n(v as number | null | undefined, 2)}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="do" type="monotone" dataKey="avg_do"          name="DO (mg/L)"   stroke={GREEN}  strokeWidth={2} dot={false} />
              <Line yAxisId="ph" type="monotone" dataKey="avg_ph_effluent" name="Eff pH"       stroke={VIOLET} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Flow Trend */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Flow — Influent vs Effluent (m³/h avg)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gradInf" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={BLUE}  stopOpacity={0.3} />
                  <stop offset="95%" stopColor={BLUE}  stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradEff" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={CYAN}  stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CYAN}  stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }}
                formatter={(v: unknown) => n(v as number | null | undefined, 1)}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="influent_flow_m3h" name="Influent" stroke={BLUE} fill="url(#gradInf)" strokeWidth={2} />
              <Area type="monotone" dataKey="effluent_flow_m3h" name="Effluent" stroke={CYAN} fill="url(#gradEff)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Compliance Donut + Stage Bar */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Compliance Distribution</h3>
          <div className="flex gap-6 items-center">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie
                  data={compliancePieData}
                  cx="50%" cy="50%"
                  innerRadius={40} outerRadius={70}
                  dataKey="value"
                  paddingAngle={2}
                >
                  {compliancePieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col gap-2 text-sm">
              {compliancePieData.map(d => (
                <div key={d.name} className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-full" style={{ background: d.fill }} />
                  <span className="text-slate-300">{d.name}</span>
                  <span className="text-white font-medium ml-auto pl-4">{d.value}</span>
                </div>
              ))}
              {compliance && (
                <div className="mt-2 pt-2 border-t border-slate-700 text-slate-400">
                  Compliance rate: <span className="text-white font-semibold">{n(compliance.compliance_pct)}%</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Stage Analysis ── */}
      {stages.length > 0 && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Treatment Stage Analysis</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={stages} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="record_count"    name="Records"          fill={BLUE}   radius={[3, 3, 0, 0]} />
              <Bar dataKey="non_compliant_cnt" name="Non-Compliant" fill={RED}    radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Records Table ── */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <span className="text-sm font-medium text-slate-300">
            Wastewater Records
            {recLoading ? " — Loading…" : ` — ${records.length}`}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => downloadWastewaterCsv({ ...filters })}
              className="px-3 py-1.5 rounded bg-slate-700 text-slate-300 text-xs hover:bg-slate-600"
            >
              Export CSV
            </button>
            <button
              onClick={() => setShowImport(true)}
              className="px-3 py-1.5 rounded bg-slate-700 text-slate-300 text-xs hover:bg-slate-600"
            >
              Import CSV
            </button>
            <button
              onClick={() => { setEditRecord(null); setShowForm(true); }}
              className="px-3 py-1.5 rounded bg-cyan-600 text-white text-xs hover:bg-cyan-500"
            >
              + New Record
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 text-xs">
                <th className="text-left px-4 py-2">Record No</th>
                <th className="text-left px-4 py-2">Date / Time</th>
                <th className="text-left px-4 py-2">Stage</th>
                <th className="text-right px-4 py-2">Inf Flow</th>
                <th className="text-right px-4 py-2">Eff pH</th>
                <th className="text-right px-4 py-2">COD In/Out</th>
                <th className="text-right px-4 py-2">DO</th>
                <th className="text-right px-4 py-2">Blower (h)</th>
                <th className="text-right px-4 py-2">Sludge (kg)</th>
                <th className="text-left px-4 py-2">Compliance</th>
                <th className="text-left px-4 py-2">Permit Ref</th>
                <th className="text-left px-4 py-2">Operator</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan={13} className="text-center text-slate-500 py-10">
                    No records found. Adjust filters or create a new record.
                  </td>
                </tr>
              ) : records.map(rec => (
                <tr
                  key={rec.id}
                  className={`border-b border-slate-700/50 hover:bg-slate-700/30 transition ${
                    rec.compliance_status === "NON_COMPLIANT" ? "bg-red-500/5" :
                    rec.compliance_status === "BORDERLINE"    ? "bg-amber-500/5" : ""
                  }`}
                >
                  <td className="px-4 py-2 font-mono text-xs text-slate-300">{rec.record_no}</td>
                  <td className="px-4 py-2 text-slate-300 whitespace-nowrap">{fmtDatetime(rec.record_datetime)}</td>
                  <td className="px-4 py-2"><StageBadge stage={rec.process_stage} /></td>
                  <td className="px-4 py-2 text-right text-slate-300">{n(rec.influent_flow_m3h)} m³/h</td>
                  <td className="px-4 py-2 text-right">
                    <span className={
                      rec.effluent_ph != null && (rec.effluent_ph < 6 || rec.effluent_ph > 9)
                        ? "text-red-400 font-medium" : "text-slate-300"
                    }>
                      {n(rec.effluent_ph, 2)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right text-slate-300 whitespace-nowrap">
                    {n(rec.influent_cod_mgl)} / <span className={
                      rec.effluent_cod_mgl != null && rec.effluent_cod_mgl > 150
                        ? "text-red-400 font-medium" : ""
                    }>{n(rec.effluent_cod_mgl)}</span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className={
                      rec.do_mgl != null && rec.do_mgl < 1.5
                        ? "text-red-400 font-medium" : "text-slate-300"
                    }>
                      {n(rec.do_mgl, 2)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right text-slate-300">{n(rec.aeration_runtime_hours, 1)}</td>
                  <td className="px-4 py-2 text-right text-slate-300">{n(rec.sludge_produced_kg, 0)}</td>
                  <td className="px-4 py-2"><ComplianceBadge status={rec.compliance_status} /></td>
                  <td className="px-4 py-2 text-xs text-slate-400 max-w-[120px] truncate" title={rec.permit_limit_ref ?? ""}>
                    {rec.permit_limit_ref ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-400">{rec.operator_name ?? "—"}</td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => { setEditRecord(rec); setShowForm(true); }}
                        className="text-xs text-cyan-400 hover:text-cyan-300"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteId(rec.id)}
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
      </div>

      {/* ── Modals ── */}
      {showImport && <ImportModal onClose={() => setShowImport(false)} />}

      {showForm && (
        <RecordModal
          assets={assets}
          record={editRecord}
          onClose={() => { setShowForm(false); setEditRecord(null); }}
        />
      )}

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-white font-semibold mb-3">Delete Record?</h3>
            <p className="text-slate-400 text-sm mb-5">This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteId(null)}
                className="px-4 py-2 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMut.mutate(deleteId)}
                disabled={deleteMut.isPending}
                className="px-4 py-2 rounded bg-red-600 text-white text-sm hover:bg-red-500 disabled:opacity-50"
              >
                {deleteMut.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
