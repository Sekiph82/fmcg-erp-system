"use client";

/**
 * Machine Utility Consumption Mapping Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Two-layer UI:
 *
 *   Tab 1 — Consumption Records
 *     Scope filters → KPI cards → trend chart → breakdown bar → records table
 *
 *   Tab 2 — Mapping Configuration
 *     Machine ↔ meter master: rated consumption, allocation share
 *
 * KPIs:
 *   electricity per runtime hour | water per batch | air per batch
 *   standby % | cost per batch | variance vs nominal
 *
 * Reporting readiness:
 *   flag_high_variance  avg deviation > 15 % from rated consumption
 *   flag_standby_waste  standby share > 20 % of total consumption
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import {
  machineUtilityApi,
  downloadMachineUtilityCsv,
  UTILITY_TYPE_LABELS,
  UTILITY_TYPE_COLORS,
  SOURCE_METHOD_LABELS,
  type MachineConsumptionRecord,
  type MachineConsumptionRecordCreate,
  type MachineUtilityMapping,
  type MachineUtilityMappingCreate,
  type MachineUtilityFilters,
  type UtilityType,
  type WorkCenterDropdown,
} from "@/lib/machineUtility";

// ── Palette ────────────────────────────────────────────────────────────────────
const CYAN   = "#22d3ee";
const ORANGE = "#fb923c";
const GREEN  = "#4ade80";
const AMBER  = "#fbbf24";
const RED    = "#f87171";
const BLUE   = "#60a5fa";
const VIOLET = "#a78bfa";

const BAR_COLORS = [
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
  "#f59e0b", "#10b981", "#ef4444", "#6366f1",
];

const UTILITY_TYPES: UtilityType[] = [
  "ELECTRICITY", "WATER", "SOFT_WATER", "PROCESS_WATER",
  "STEAM", "COMPRESSED_AIR", "NATURAL_GAS", "DIESEL", "OTHER",
];

// ── Helpers ────────────────────────────────────────────────────────────────────
const n = (v: number | string | null | undefined, dp = 2) =>
  v != null ? parseFloat(String(v)).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

// ── KPI Card ───────────────────────────────────────────────────────────────────
function KPICard({
  label, value, sub, accent = "border-slate-700", flag, flagMsg,
}: {
  label: string; value: React.ReactNode; sub?: React.ReactNode;
  accent?: string; flag?: boolean; flagMsg?: string;
}) {
  return (
    <div className={`bg-slate-800 border rounded-lg p-4 flex flex-col gap-1 ${flag ? "border-red-500/60" : accent}`}>
      <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
      <span className="text-xl font-semibold text-white">{value}</span>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
      {flag && flagMsg && <span className="text-xs text-red-400 font-medium">{flagMsg}</span>}
    </div>
  );
}

// ── Utility Badge ──────────────────────────────────────────────────────────────
function UtilityBadge({ type }: { type: UtilityType }) {
  const color = UTILITY_TYPE_COLORS[type] ?? "#6b7280";
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-medium"
      style={{ background: color + "22", color, border: `1px solid ${color}44` }}
    >
      {UTILITY_TYPE_LABELS[type] ?? type}
    </span>
  );
}

// ── Consumption Record Form ────────────────────────────────────────────────────
function RecordForm({
  workCenters, record, onClose,
}: {
  workCenters: WorkCenterDropdown[];
  record?: MachineConsumptionRecord | null;
  onClose: () => void;
}) {
  const qc  = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);

  const [form, setForm] = useState<Partial<MachineConsumptionRecordCreate>>({
    work_center_id:     record?.work_center_id      ?? (workCenters[0]?.id ?? ""),
    record_date:        record?.record_date          ?? today,
    utility_type:       record?.utility_type         ?? "ELECTRICITY",
    shift_ref:          record?.shift_ref            ?? "",
    department:         record?.department           ?? "",
    production_line:    record?.production_line      ?? "",
    source_method:      record?.source_method        ?? "MANUAL",
    is_estimated:       record?.is_estimated         ?? false,
    is_standby:         record?.is_standby           ?? false,
    runtime_hours:      record?.runtime_hours        ?? undefined,
    nominal_rate:       record?.nominal_rate         ?? undefined,
    nominal_unit:       record?.nominal_unit         ?? "",
    actual_consumption: record?.actual_consumption   ?? undefined,
    actual_unit:        record?.actual_unit          ?? "",
    batch_no:           record?.batch_no             ?? "",
    cost_rate:          record?.cost_rate            ?? undefined,
    total_cost:         record?.total_cost           ?? undefined,
    currency_code:      record?.currency_code        ?? "USD",
    is_anomaly:         record?.is_anomaly           ?? false,
    notes:              record?.notes                ?? "",
  });

  const set = (k: keyof MachineConsumptionRecordCreate, v: unknown) =>
    setForm(f => ({ ...f, [k]: v === "" ? undefined : v }));

  const createMut = useMutation({
    mutationFn: (d: MachineConsumptionRecordCreate) => machineUtilityApi.createRecord(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mu-records"] });
      qc.invalidateQueries({ queryKey: ["mu-kpis"] });
      qc.invalidateQueries({ queryKey: ["mu-trend"] });
      onClose();
    },
  });

  const updateMut = useMutation({
    mutationFn: (d: Partial<MachineConsumptionRecordCreate>) =>
      machineUtilityApi.updateRecord(record!.id, d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mu-records"] });
      qc.invalidateQueries({ queryKey: ["mu-kpis"] });
      onClose();
    },
  });

  const busy = createMut.isPending || updateMut.isPending;

  const handleSubmit = () => {
    const payload = { ...form } as MachineConsumptionRecordCreate;
    if (record) updateMut.mutate(payload);
    else createMut.mutate(payload);
  };

  const numField = (label: string, key: keyof MachineConsumptionRecordCreate, placeholder = "") => (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-slate-400">{label}</label>
      <input
        type="number" step="any" placeholder={placeholder}
        value={form[key] as number ?? ""}
        onChange={e => set(key, e.target.value === "" ? undefined : parseFloat(e.target.value))}
        className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
      />
    </div>
  );

  const textField = (label: string, key: keyof MachineConsumptionRecordCreate, placeholder = "") => (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-slate-400">{label}</label>
      <input
        type="text" placeholder={placeholder}
        value={form[key] as string ?? ""}
        onChange={e => set(key, e.target.value)}
        className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 overflow-y-auto p-4">
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 w-full max-w-3xl shadow-2xl">
        <h3 className="text-white font-semibold text-lg mb-5">
          {record ? "Edit Consumption Record" : "New Consumption Record"}
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Work center */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Machine / Work Center</label>
            <select
              value={form.work_center_id ?? ""}
              onChange={e => set("work_center_id", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {workCenters.map(wc => (
                <option key={wc.id} value={wc.id}>
                  {wc.work_center_id} — {wc.name}
                  {wc.department ? ` (${wc.department})` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Date */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Date</label>
            <input
              type="date"
              value={form.record_date ?? ""}
              onChange={e => set("record_date", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Utility type */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Utility Type</label>
            <select
              value={form.utility_type ?? "ELECTRICITY"}
              onChange={e => set("utility_type", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {UTILITY_TYPES.map(t => (
                <option key={t} value={t}>{UTILITY_TYPE_LABELS[t]}</option>
              ))}
            </select>
          </div>

          {/* Source method */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Source Method</label>
            <select
              value={form.source_method ?? "MANUAL"}
              onChange={e => set("source_method", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {Object.entries(SOURCE_METHOD_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          {textField("Shift", "shift_ref", "e.g. A")}
          {textField("Department", "department")}
          {textField("Production Line", "production_line")}
          {textField("Batch No", "batch_no")}

          {numField("Runtime Hours", "runtime_hours")}
          {numField("Nominal Rate (per h)", "nominal_rate")}
          {textField("Nominal Unit", "nominal_unit", "e.g. kWh/h")}

          {numField("Actual Consumption", "actual_consumption")}
          {textField("Actual Unit", "actual_unit", "e.g. kWh")}

          {numField("Cost Rate (per unit)", "cost_rate")}
          {numField("Total Cost", "total_cost")}
          {textField("Currency", "currency_code", "USD")}

          {/* Flags */}
          <div className="flex flex-col gap-2 col-span-4">
            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!form.is_estimated}
                  onChange={e => set("is_estimated", e.target.checked)}
                  className="accent-cyan-500"
                />
                Estimated (not metered)
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!form.is_standby}
                  onChange={e => set("is_standby", e.target.checked)}
                  className="accent-amber-500"
                />
                Standby / idle consumption
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!form.is_anomaly}
                  onChange={e => set("is_anomaly", e.target.checked)}
                  className="accent-red-500"
                />
                Flag as anomaly
              </label>
            </div>
          </div>

          <div className="flex flex-col gap-1 col-span-4">
            <label className="text-xs text-slate-400">Notes / Remarks</label>
            <textarea
              rows={2}
              value={form.notes ?? ""}
              onChange={e => set("notes", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {(createMut.error || updateMut.error) && (
          <p className="text-red-400 text-sm mt-3">
            {((createMut.error || updateMut.error) as Error)?.message ?? "An error occurred."}
          </p>
        )}

        <div className="flex gap-2 justify-end mt-5">
          <button onClick={onClose}
            className="px-4 py-2 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600">
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={busy}
            className="px-4 py-2 rounded bg-cyan-600 text-white text-sm hover:bg-cyan-500 disabled:opacity-50">
            {busy ? "Saving…" : record ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Mapping Config Form ────────────────────────────────────────────────────────
function MappingForm({
  workCenters, mapping, onClose,
}: {
  workCenters: WorkCenterDropdown[];
  mapping?: MachineUtilityMapping | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<MachineUtilityMappingCreate>>({
    machine_ref:      mapping?.machine_ref       ?? "",
    machine_name:     mapping?.machine_name      ?? "",
    work_center_id:   mapping?.work_center_id    ?? (workCenters[0]?.id ?? undefined),
    utility_type:     mapping?.utility_type      ?? "ELECTRICITY",
    department:       mapping?.department        ?? "",
    production_line:  mapping?.production_line   ?? "",
    allocation_pct:   mapping?.allocation_pct    ?? undefined,
    rated_consumption: mapping?.rated_consumption ?? undefined,
    rated_unit:       mapping?.rated_unit        ?? "",
    is_active:        mapping?.is_active         ?? true,
    notes:            mapping?.notes             ?? "",
  });

  const set = (k: keyof MachineUtilityMappingCreate, v: unknown) =>
    setForm(f => ({ ...f, [k]: v === "" ? undefined : v }));

  const createMut = useMutation({
    mutationFn: (d: MachineUtilityMappingCreate) => machineUtilityApi.createMapping(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["mu-mappings"] }); onClose(); },
  });

  const updateMut = useMutation({
    mutationFn: (d: Partial<MachineUtilityMappingCreate>) =>
      machineUtilityApi.updateMapping(mapping!.id, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["mu-mappings"] }); onClose(); },
  });

  const busy = createMut.isPending || updateMut.isPending;

  const handleSubmit = () => {
    const payload = { ...form } as MachineUtilityMappingCreate;
    if (mapping) updateMut.mutate(payload);
    else createMut.mutate(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 w-full max-w-2xl shadow-2xl">
        <h3 className="text-white font-semibold text-lg mb-5">
          {mapping ? "Edit Mapping Config" : "New Machine Utility Mapping"}
        </h3>

        <div className="grid grid-cols-2 gap-4">
          {/* Work center */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Work Center (machine/line)</label>
            <select
              value={form.work_center_id ?? ""}
              onChange={e => {
                const wc = workCenters.find(w => w.id === e.target.value);
                setForm(f => ({
                  ...f,
                  work_center_id: e.target.value,
                  machine_ref:    wc?.work_center_id ?? f.machine_ref,
                  machine_name:   wc?.name           ?? f.machine_name,
                  department:     wc?.department      ?? f.department,
                }));
              }}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="">— select —</option>
              {workCenters.map(wc => (
                <option key={wc.id} value={wc.id}>{wc.work_center_id} — {wc.name}</option>
              ))}
            </select>
          </div>

          {/* Utility type */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Utility Type</label>
            <select
              value={form.utility_type ?? "ELECTRICITY"}
              onChange={e => set("utility_type", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              {UTILITY_TYPES.map(t => (
                <option key={t} value={t}>{UTILITY_TYPE_LABELS[t]}</option>
              ))}
            </select>
          </div>

          {/* Allocation */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Allocation % (shared meter)</label>
            <input type="number" step="0.01" min="0" max="100"
              value={form.allocation_pct ?? ""}
              onChange={e => set("allocation_pct", e.target.value === "" ? undefined : parseFloat(e.target.value))}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Rated consumption */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Rated Consumption (nameplate)</label>
            <input type="number" step="any"
              value={form.rated_consumption ?? ""}
              onChange={e => set("rated_consumption", e.target.value === "" ? undefined : parseFloat(e.target.value))}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Rated unit */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Rated Unit (e.g. kW, m³/h)</label>
            <input type="text" placeholder="kW"
              value={form.rated_unit ?? ""}
              onChange={e => set("rated_unit", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Notes */}
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Notes</label>
            <textarea rows={2}
              value={form.notes ?? ""}
              onChange={e => set("notes", e.target.value)}
              className="bg-slate-900 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="col-span-2">
            <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
              <input type="checkbox" checked={!!form.is_active}
                onChange={e => set("is_active", e.target.checked)}
                className="accent-cyan-500"
              />
              Active mapping
            </label>
          </div>
        </div>

        <div className="flex gap-2 justify-end mt-5">
          <button onClick={onClose}
            className="px-4 py-2 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600">
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={busy}
            className="px-4 py-2 rounded bg-cyan-600 text-white text-sm hover:bg-cyan-500 disabled:opacity-50">
            {busy ? "Saving…" : mapping ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════════════

export default function MachineUtilityPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"records" | "mappings">("records");

  // ── Filters ────────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState<MachineUtilityFilters>({});
  const [breakdown, setBreakdown] = useState<"machine" | "utility" | "shift" | "line" | "department">("machine");

  // ── Modals ─────────────────────────────────────────────────────────────────
  const [showRecordForm,  setShowRecordForm]  = useState(false);
  const [showMappingForm, setShowMappingForm] = useState(false);
  const [editRecord,  setEditRecord]  = useState<MachineConsumptionRecord | null>(null);
  const [editMapping, setEditMapping] = useState<MachineUtilityMapping | null>(null);
  const [deleteId,    setDeleteId]    = useState<{ id: string; type: "record" | "mapping" } | null>(null);

  const setFilter = (k: keyof MachineUtilityFilters, v: unknown) =>
    setFilters(f => ({ ...f, [k]: v === "" ? undefined : v }));

  // ── Queries ────────────────────────────────────────────────────────────────
  const { data: workCenters = [] } = useQuery({
    queryKey: ["mu-work-centers"],
    queryFn:  machineUtilityApi.workCenters,
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["mu-kpis", filters],
    queryFn:  () => machineUtilityApi.kpis(filters),
    enabled:  activeTab === "records",
  });

  const { data: trend = [] } = useQuery({
    queryKey: ["mu-trend", filters],
    queryFn:  () => machineUtilityApi.dailyTrend(filters),
    enabled:  activeTab === "records",
  });

  const { data: bkd } = useQuery({
    queryKey: ["mu-breakdown", filters, breakdown],
    queryFn:  () => machineUtilityApi.breakdown(breakdown, filters),
    enabled:  activeTab === "records",
  });

  const { data: records = [], isLoading: recLoading } = useQuery({
    queryKey: ["mu-records", filters],
    queryFn:  () => machineUtilityApi.listRecords({ ...filters, limit: 300 }),
    enabled:  activeTab === "records",
  });

  const { data: mappings = [], isLoading: mapLoading } = useQuery({
    queryKey: ["mu-mappings"],
    queryFn:  () => machineUtilityApi.listMappings({ limit: 500 }),
    enabled:  activeTab === "mappings",
  });

  // ── Delete mutations ────────────────────────────────────────────────────────
  const deleteMut = useMutation({
    mutationFn: ({ id, type }: { id: string; type: "record" | "mapping" }) =>
      type === "record"
        ? machineUtilityApi.deleteRecord(id)
        : machineUtilityApi.deleteMapping(id),
    onSuccess: (_, { type }) => {
      qc.invalidateQueries({ queryKey: [type === "record" ? "mu-records" : "mu-mappings"] });
      if (type === "record") {
        qc.invalidateQueries({ queryKey: ["mu-kpis"] });
        qc.invalidateQueries({ queryKey: ["mu-trend"] });
      }
      setDeleteId(null);
    },
  });

  // ── Trend data keyed per utility type ──────────────────────────────────────
  const trendByDate = useMemo(() => {
    const map: Record<string, Record<string, number>> = {};
    for (const row of trend) {
      if (!map[row.date]) map[row.date] = { date: row.date as unknown as number };
      const ukey = row.utility_type ?? "OTHER";
      map[row.date][ukey] = (map[row.date][ukey] ?? 0) + parseFloat(String(row.total_consumption ?? 0));
    }
    return Object.values(map).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [trend]);

  const trendUtilityKeys = useMemo(() => {
    const keys = new Set<string>();
    trend.forEach(r => { if (r.utility_type) keys.add(r.utility_type); });
    return Array.from(keys);
  }, [trend]);

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-1">Machine Utility Consumption</h1>
      <p className="text-slate-400 text-sm mb-4">
        Map utility usage to machines — basis for machine-level costing and performance analysis.
      </p>

      {/* ── Tabs ── */}
      <div className="flex gap-1 mb-6 border-b border-slate-700">
        {(["records", "mappings"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium transition rounded-t-lg border-b-2 ${
              activeTab === tab
                ? "border-cyan-500 text-cyan-400 bg-slate-800"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab === "records" ? "Consumption Records" : "Mapping Configuration"}
          </button>
        ))}
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          TAB 1 — CONSUMPTION RECORDS
      ════════════════════════════════════════════════════════════════════ */}
      {activeTab === "records" && (
        <>
          {/* ── Filters ── */}
          <div className="flex flex-wrap gap-3 mb-5">
            <input type="date"
              value={filters.date_from ?? ""}
              onChange={e => setFilter("date_from", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
            <input type="date"
              value={filters.date_to ?? ""}
              onChange={e => setFilter("date_to", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            />
            <select
              value={filters.work_center_id ?? ""}
              onChange={e => setFilter("work_center_id", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Machines</option>
              {workCenters.map(wc => (
                <option key={wc.id} value={wc.id}>{wc.work_center_id} — {wc.name}</option>
              ))}
            </select>
            <select
              value={filters.utility_type ?? ""}
              onChange={e => setFilter("utility_type", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Utilities</option>
              {UTILITY_TYPES.map(t => (
                <option key={t} value={t}>{UTILITY_TYPE_LABELS[t]}</option>
              ))}
            </select>
            <input type="text" placeholder="Shift (e.g. A)"
              value={filters.shift_ref ?? ""}
              onChange={e => setFilter("shift_ref", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white w-28 focus:outline-none focus:border-cyan-500"
            />
            <input type="text" placeholder="Batch No"
              value={filters.batch_no ?? ""}
              onChange={e => setFilter("batch_no", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white w-36 focus:outline-none focus:border-cyan-500"
            />
            <input type="text" placeholder="Line"
              value={filters.production_line ?? ""}
              onChange={e => setFilter("production_line", e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white w-28 focus:outline-none focus:border-cyan-500"
            />
            <select
              value={filters.is_standby === undefined ? "" : String(filters.is_standby)}
              onChange={e => setFilter("is_standby", e.target.value === "" ? undefined : e.target.value === "true")}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="">All (standby+active)</option>
              <option value="true">Standby only</option>
              <option value="false">Active only</option>
            </select>
            <button onClick={() => setFilters({})}
              className="px-3 py-1.5 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600">
              Reset
            </button>
          </div>

          {/* ── KPI Cards ── */}
          {kpisLoading ? (
            <p className="text-slate-400 text-sm mb-5">Loading KPIs…</p>
          ) : kpis ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <KPICard
                label="Total Consumption"
                value={`${n(kpis.total_consumption, 2)} ${kpis.consumption_unit ?? ""}`}
                sub={`${kpis.record_count} records`}
                accent="border-cyan-700"
              />
              <KPICard
                label="Electricity / Runtime Hour"
                value={kpis.electricity_per_runtime_h != null ? `${n(kpis.electricity_per_runtime_h, 4)} kWh/h` : "—"}
                sub={`Runtime: ${n(kpis.total_runtime_hours, 1)} h`}
                accent="border-amber-700"
                flag={kpis.flag_high_variance}
                flagMsg={kpis.flag_high_variance ? `Variance ${n(kpis.avg_variance_pct)}% from nominal` : undefined}
              />
              <KPICard
                label="Water / Batch"
                value={kpis.water_per_batch != null ? `${n(kpis.water_per_batch, 3)} m³` : "—"}
                sub={`${kpis.batch_count} batches`}
                accent="border-blue-700"
              />
              <KPICard
                label="Compressed Air / Batch"
                value={kpis.air_per_batch != null ? `${n(kpis.air_per_batch, 3)} Nm³` : "—"}
                sub="Per distinct batch"
                accent="border-teal-700"
              />
              <KPICard
                label="Standby Consumption"
                value={kpis.total_standby_consumption != null ? n(kpis.total_standby_consumption) : "—"}
                sub={kpis.standby_pct != null ? `${n(kpis.standby_pct, 1)}% of total` : ""}
                accent="border-orange-700"
                flag={kpis.flag_standby_waste}
                flagMsg={kpis.flag_standby_waste ? "Standby > 20% of consumption" : undefined}
              />
              <KPICard
                label="Cost / Batch"
                value={kpis.cost_per_batch != null ? `$${n(kpis.cost_per_batch, 4)}` : "—"}
                sub={kpis.total_cost != null ? `Total $${n(kpis.total_cost, 2)}` : "No cost data"}
                accent="border-violet-700"
              />
              <KPICard
                label="Avg Variance vs Nominal"
                value={kpis.avg_variance_pct != null ? `${n(kpis.avg_variance_pct, 1)}%` : "—"}
                sub="Positive = overconsumption"
                accent={kpis.flag_high_variance ? "border-red-700" : "border-slate-700"}
                flag={kpis.flag_high_variance}
              />
              <KPICard
                label="Anomalies"
                value={kpis.anomaly_count}
                sub={`${kpis.order_count} orders linked`}
                accent={kpis.anomaly_count > 0 ? "border-red-700" : "border-slate-700"}
                flag={kpis.anomaly_count > 0}
                flagMsg={kpis.anomaly_count > 0 ? "Review anomaly records" : undefined}
              />
            </div>
          ) : null}

          {/* ── Charts ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            {/* Consumption trend */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm font-medium text-slate-300 mb-3">Daily Consumption by Utility Type</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={trendByDate} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickFormatter={d => String(d).slice(5)} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {trendUtilityKeys.map((utype, i) => (
                    <Bar key={utype} dataKey={utype}
                      name={UTILITY_TYPE_LABELS[utype as UtilityType] ?? utype}
                      fill={UTILITY_TYPE_COLORS[utype as UtilityType] ?? BAR_COLORS[i % BAR_COLORS.length]}
                      stackId="a"
                      radius={i === trendUtilityKeys.length - 1 ? [3, 3, 0, 0] : [0, 0, 0, 0]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Breakdown */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-slate-300">Consumption Breakdown</h3>
                <select
                  value={breakdown}
                  onChange={e => setBreakdown(e.target.value as typeof breakdown)}
                  className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-white focus:outline-none"
                >
                  <option value="machine">By Machine</option>
                  <option value="utility">By Utility Type</option>
                  <option value="shift">By Shift</option>
                  <option value="line">By Production Line</option>
                  <option value="department">By Department</option>
                </select>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={bkd?.rows ?? []}
                  layout="vertical"
                  margin={{ top: 4, right: 40, left: 8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis type="category" dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} width={90} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 6 }}
                    formatter={(v: unknown) => n(v as number | null | undefined, 2)}
                  />
                  <Bar dataKey="total_consumption" name="Consumption" radius={[0, 3, 3, 0]}>
                    {(bkd?.rows ?? []).map((_, i) => (
                      <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ── Records Table ── */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
              <span className="text-sm font-medium text-slate-300">
                Consumption Records {recLoading ? "— Loading…" : `— ${records.length}`}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => downloadMachineUtilityCsv({ ...filters })}
                  className="px-3 py-1.5 rounded bg-slate-700 text-slate-300 text-xs hover:bg-slate-600"
                >
                  Export CSV
                </button>
                <button
                  onClick={() => { setEditRecord(null); setShowRecordForm(true); }}
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
                    <th className="text-left px-3 py-2">Record No</th>
                    <th className="text-left px-3 py-2">Date</th>
                    <th className="text-left px-3 py-2">Machine</th>
                    <th className="text-left px-3 py-2">Utility</th>
                    <th className="text-left px-3 py-2">Shift</th>
                    <th className="text-right px-3 py-2">Nominal Rate</th>
                    <th className="text-right px-3 py-2">Actual</th>
                    <th className="text-right px-3 py-2">Variance %</th>
                    <th className="text-right px-3 py-2">Runtime h</th>
                    <th className="text-left px-3 py-2">Batch / Order</th>
                    <th className="text-right px-3 py-2">Cost</th>
                    <th className="text-left px-3 py-2">Flags</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {records.length === 0 ? (
                    <tr>
                      <td colSpan={13} className="text-center text-slate-500 py-10">
                        No records. Adjust filters or create a new consumption record.
                      </td>
                    </tr>
                  ) : records.map(rec => (
                    <tr
                      key={rec.id}
                      className={`border-b border-slate-700/50 hover:bg-slate-700/30 transition ${
                        rec.is_anomaly ? "bg-red-500/5" : rec.is_standby ? "bg-amber-500/5" : ""
                      }`}
                    >
                      <td className="px-3 py-2 font-mono text-xs text-slate-300">{rec.record_no}</td>
                      <td className="px-3 py-2 text-slate-300">{rec.record_date}</td>
                      <td className="px-3 py-2">
                        <div className="text-slate-200 text-xs font-medium">{rec.machine_ref}</div>
                        <div className="text-slate-500 text-xs">{rec.machine_name}</div>
                      </td>
                      <td className="px-3 py-2"><UtilityBadge type={rec.utility_type} /></td>
                      <td className="px-3 py-2 text-slate-400 text-xs">{rec.shift_ref ?? "—"}</td>
                      <td className="px-3 py-2 text-right text-slate-300 text-xs whitespace-nowrap">
                        {n(rec.nominal_rate)} {rec.nominal_unit ?? ""}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-200 text-xs font-medium whitespace-nowrap">
                        {n(rec.actual_consumption)} {rec.actual_unit ?? ""}
                      </td>
                      <td className="px-3 py-2 text-right text-xs">
                        {rec.variance_pct != null ? (
                          <span className={parseFloat(String(rec.variance_pct)) > 15 ? "text-red-400 font-medium" :
                                           parseFloat(String(rec.variance_pct)) > 0  ? "text-amber-400" : "text-emerald-400"}>
                            {n(rec.variance_pct, 1)}%
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-300 text-xs">{n(rec.runtime_hours, 1)}</td>
                      <td className="px-3 py-2 text-xs">
                        {rec.batch_no ? (
                          <div>
                            <div className="text-cyan-400">{rec.batch_no}</div>
                            {rec.production_order_no && (
                              <div className="text-slate-500">{rec.production_order_no}</div>
                            )}
                          </div>
                        ) : "—"}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-300 text-xs">
                        {rec.total_cost != null ? `$${n(rec.total_cost, 2)}` : "—"}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <div className="flex gap-1 flex-wrap">
                          {rec.is_standby && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                              Standby
                            </span>
                          )}
                          {rec.is_estimated && (
                            <span className="px-1.5 py-0.5 rounded bg-slate-600/60 text-slate-300 border border-slate-500/30">
                              Est
                            </span>
                          )}
                          {rec.is_anomaly && (
                            <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                              Anomaly
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => { setEditRecord(rec); setShowRecordForm(true); }}
                            className="text-xs text-cyan-400 hover:text-cyan-300"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => setDeleteId({ id: rec.id, type: "record" })}
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
        </>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          TAB 2 — MAPPING CONFIGURATION
      ════════════════════════════════════════════════════════════════════ */}
      {activeTab === "mappings" && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <span className="text-sm font-medium text-slate-300">
              Machine ↔ Utility Meter Mappings {mapLoading ? "— Loading…" : `— ${mappings.length}`}
            </span>
            <button
              onClick={() => { setEditMapping(null); setShowMappingForm(true); }}
              className="px-3 py-1.5 rounded bg-cyan-600 text-white text-xs hover:bg-cyan-500"
            >
              + New Mapping
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400 text-xs">
                  <th className="text-left px-4 py-2">Machine Ref</th>
                  <th className="text-left px-4 py-2">Machine Name</th>
                  <th className="text-left px-4 py-2">Utility</th>
                  <th className="text-left px-4 py-2">Department / Line</th>
                  <th className="text-right px-4 py-2">Allocation %</th>
                  <th className="text-right px-4 py-2">Rated Consumption</th>
                  <th className="text-left px-4 py-2">Meter / Device</th>
                  <th className="text-left px-4 py-2">Status</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {mappings.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center text-slate-500 py-10">
                      No mappings configured. Add machine-utility mappings to enable costing.
                    </td>
                  </tr>
                ) : mappings.map(m => (
                  <tr key={m.id} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition">
                    <td className="px-4 py-2 font-mono text-xs text-slate-200">{m.machine_ref}</td>
                    <td className="px-4 py-2 text-slate-300">{m.machine_name}</td>
                    <td className="px-4 py-2"><UtilityBadge type={m.utility_type} /></td>
                    <td className="px-4 py-2 text-xs text-slate-400">
                      {m.department ?? "—"} / {m.production_line ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-300 text-xs">
                      {m.allocation_pct != null ? `${n(m.allocation_pct, 1)}%` : "100%"}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-300 text-xs whitespace-nowrap">
                      {m.rated_consumption != null
                        ? `${n(m.rated_consumption)} ${m.rated_unit ?? ""}`
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-400">
                      {m.device_name ?? "—"}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                        m.is_active
                          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                          : "bg-slate-700/50 border-slate-600 text-slate-400"
                      }`}>
                        {m.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => { setEditMapping(m); setShowMappingForm(true); }}
                          className="text-xs text-cyan-400 hover:text-cyan-300"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => setDeleteId({ id: m.id, type: "mapping" })}
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
      )}

      {/* ── Modals ── */}
      {showRecordForm && (
        <RecordForm
          workCenters={workCenters}
          record={editRecord}
          onClose={() => { setShowRecordForm(false); setEditRecord(null); }}
        />
      )}

      {showMappingForm && (
        <MappingForm
          workCenters={workCenters}
          mapping={editMapping}
          onClose={() => { setShowMappingForm(false); setEditMapping(null); }}
        />
      )}

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-white font-semibold mb-3">
              Delete {deleteId.type === "record" ? "Consumption Record" : "Mapping"}?
            </h3>
            <p className="text-slate-400 text-sm mb-5">This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteId(null)}
                className="px-4 py-2 rounded bg-slate-700 text-slate-300 text-sm hover:bg-slate-600">
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
