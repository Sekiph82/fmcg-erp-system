"use client";

/**
 * Soft Water Management Dashboard
 * ─────────────────────────────────
 * KPIs: volume treated, salt, efficiency %, compliance %, regen frequency,
 *       hardness removal %, loss ratio
 * Charts: daily volume + salt trend, efficiency trend
 * Records CRUD: create/edit/delete soft_water_records
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
  softWaterApi,
  downloadSoftWaterCsv,
  type SoftWaterKPIs,
  type SoftWaterTrendPoint,
  type SoftWaterRecord,
  type SoftWaterRecordCreate,
  type SoftWaterFilters,
  type SoftenerAsset,
  SOFTENER_STATUS_LABELS,
  SOFTENER_STATUS_COLORS,
  type SoftenerStatus,
} from "@/lib/water";
import { importApi } from "@/lib/importApi";
import type { ImportResult } from "@/lib/importApi";

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: string | number | null | undefined, dec = 2) =>
  v == null ? "—" : Number(v).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec });

const fmtDt = (s: string | null) => s ? s.slice(0, 16).replace("T", " ") : "—";

// ── Small components ──────────────────────────────────────────────────────────

function KPICard({
  label, value, sub, alert = false, ok = false,
}: { label: string; value: string; sub?: string; alert?: boolean; ok?: boolean }) {
  const border = alert ? "border-red-500/40 bg-red-500/5"
                : ok    ? "border-emerald-500/40 bg-emerald-500/5"
                : "border-white/10 bg-white/5";
  const color  = alert ? "text-red-400" : ok ? "text-emerald-400" : "text-white";
  return (
    <div className={`rounded-lg border p-4 ${border}`}>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function Section({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-3 mt-6 mb-3">
      <div className="w-1 h-5 rounded-full bg-cyan-400" />
      <span className="text-sm font-medium text-gray-200">{title}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: SoftenerStatus }) {
  return (
    <span className={`text-xs font-medium ${SOFTENER_STATUS_COLORS[status]}`}>
      {SOFTENER_STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ── Record form ───────────────────────────────────────────────────────────────

function RecordForm({
  initial, assets, onSubmit, onCancel, loading,
}: {
  initial?: Partial<SoftWaterRecordCreate>;
  assets: SoftenerAsset[];
  onSubmit: (d: SoftWaterRecordCreate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [f, setF] = useState<SoftWaterRecordCreate>({
    asset_id: assets[0]?.id ?? "",
    record_datetime: new Date().toISOString().slice(0, 16),
    status: "ONLINE",
    source_method: "MANUAL",
    is_anomaly: false,
    maintenance_flag: false,
    ...initial,
  });

  const set = (k: keyof typeof f, v: unknown) => setF(p => ({ ...p, [k]: v }));

  return (
    <form onSubmit={e => { e.preventDefault(); onSubmit(f); }} className="space-y-4">
      {/* Asset + datetime */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Softener Asset *</span>
          <select required
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.asset_id} onChange={e => set("asset_id", e.target.value)}>
            {assets.map(a => (
              <option key={a.id} value={a.id}>{a.name} ({a.asset_no})</option>
            ))}
            {assets.length === 0 && <option value="">No SOFT_WATER assets found</option>}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Record DateTime *</span>
          <input required type="datetime-local"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.record_datetime} onChange={e => set("record_datetime", e.target.value)} />
        </label>
      </div>

      {/* Water quality */}
      <p className="text-xs text-gray-500 border-t border-white/5 pt-3">Water Quality</p>
      <div className="grid grid-cols-3 gap-3">
        {([
          ["feed_water_hardness_ppm",    "Feed Hardness (ppm)"],
          ["product_water_hardness_ppm", "Product Hardness (ppm)"],
          ["feed_water_tds_ppm",         "Feed TDS (ppm)"],
          ["product_water_tds_ppm",      "Product TDS (ppm)"],
          ["conductivity_feed_uscm",     "Feed Cond. (µS/cm)"],
          ["conductivity_product_uscm",  "Product Cond. (µS/cm)"],
          ["feed_ph",                    "Feed pH"],
          ["product_ph",                 "Product pH"],
        ] as [keyof SoftWaterRecordCreate, string][]).map(([k, label]) => (
          <label key={k} className="flex flex-col gap-1">
            <span className="text-xs text-gray-400">{label}</span>
            <input type="number" step="0.01"
              className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
              value={(f[k] as number) ?? ""}
              onChange={e => set(k, e.target.value ? parseFloat(e.target.value) : null)} />
          </label>
        ))}
      </div>

      {/* Volume + flow */}
      <p className="text-xs text-gray-500 border-t border-white/5 pt-3">Volume & Flow</p>
      <div className="grid grid-cols-3 gap-3">
        {([
          ["raw_water_input_m3",  "Raw Input (m³)"],
          ["volume_treated_m3",   "Treated Output (m³)"],
          ["flow_rate_lpm",       "Flow Rate (L/min)"],
          ["salt_consumed_kg",    "Salt Consumed (kg)"],
          ["resin_volume_litres", "Resin Volume (L)"],
          ["efficiency_pct",      "Efficiency (%)"],
        ] as [keyof SoftWaterRecordCreate, string][]).map(([k, label]) => (
          <label key={k} className="flex flex-col gap-1">
            <span className="text-xs text-gray-400">{label}</span>
            <input type="number" step="0.01"
              className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
              value={(f[k] as number) ?? ""}
              onChange={e => set(k, e.target.value ? parseFloat(e.target.value) : null)} />
          </label>
        ))}
      </div>

      {/* Regeneration */}
      <p className="text-xs text-gray-500 border-t border-white/5 pt-3">Regeneration Cycle</p>
      <div className="grid grid-cols-3 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Regen Start</span>
          <input type="datetime-local"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.regen_start ?? ""}
            onChange={e => set("regen_start", e.target.value || null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Regen End</span>
          <input type="datetime-local"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.regen_end ?? ""}
            onChange={e => set("regen_end", e.target.value || null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Regen Count</span>
          <input type="number" step="1"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.regeneration_count ?? ""}
            onChange={e => set("regeneration_count", e.target.value ? parseInt(e.target.value) : null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Service Run Hours</span>
          <input type="number" step="0.01"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.service_run_hours ?? ""}
            onChange={e => set("service_run_hours", e.target.value ? parseFloat(e.target.value) : null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Downtime (min)</span>
          <input type="number" step="1"
            className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.downtime_minutes ?? ""}
            onChange={e => set("downtime_minutes", e.target.value ? parseInt(e.target.value) : null)} />
        </label>
      </div>

      {/* Operational */}
      <p className="text-xs text-gray-500 border-t border-white/5 pt-3">Operational</p>
      <div className="grid grid-cols-3 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Status</span>
          <select className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.status} onChange={e => set("status", e.target.value)}>
            {(["ONLINE", "REGENERATING", "STANDBY", "FAULT"] as SoftenerStatus[]).map(s => (
              <option key={s} value={s}>{SOFTENER_STATUS_LABELS[s]}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Destination Tag</span>
          <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            placeholder="e.g. Boiler Feed, CIP"
            value={f.destination_tag ?? ""}
            onChange={e => set("destination_tag", e.target.value || null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Department</span>
          <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.department ?? ""}
            onChange={e => set("department", e.target.value || null)} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-400">Shift</span>
          <input className="bg-white/5 border border-white/10 rounded px-2 py-1.5 text-sm text-white"
            value={f.shift_ref ?? ""}
            onChange={e => set("shift_ref", e.target.value || null)} />
        </label>
        <div className="flex flex-col gap-2 pt-4">
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={!!f.maintenance_flag}
              onChange={e => set("maintenance_flag", e.target.checked)} />
            Maintenance Required
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={!!f.is_anomaly}
              onChange={e => set("is_anomaly", e.target.checked)} />
            Anomaly
          </label>
        </div>
      </div>

      {f.is_anomaly && (
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
          className="px-3 py-1.5 rounded text-sm text-gray-400 border border-white/10 hover:bg-white/5">Cancel</button>
        <button type="submit" disabled={loading}
          className="px-4 py-1.5 rounded text-sm bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-50">
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
        ? await importApi.runImport("soft_water_records", file, "import_valid_only")
        : await importApi.validate("soft_water_records", file);
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
          <h3 className="text-white font-semibold">Import Soft Water Records</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>
        <button onClick={() => importApi.downloadTemplate("soft_water_records")}
          className="text-xs text-cyan-400 hover:underline">Download template CSV</button>
        <input type="file" accept=".csv"
          className="block w-full text-sm text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:bg-white/10 file:text-white"
          onChange={e => { setFile(e.target.files?.[0] ?? null); setResult(null); }} />
        {result && (
          <div className={`p-3 rounded text-sm border ${result.imported ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-blue-500/10 border-blue-500/20 text-blue-400"}`}>
            <p>{result.imported ? "Import complete" : "Validation result"}</p>
            <p className="text-xs mt-1">{result.valid_rows} valid / {result.failed_rows} failed / {result.total_rows} total</p>
            {result.errors.slice(0, 5).map((e, i) => (
              <p key={i} className="text-xs text-red-400 mt-0.5">Row {e.row}: {e.message}</p>
            ))}
          </div>
        )}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button onClick={() => run(false)} disabled={!file || loading}
            className="px-3 py-1.5 text-xs rounded border border-white/10 text-gray-300 hover:bg-white/5 disabled:opacity-40">Validate</button>
          <button onClick={() => run(true)} disabled={!file || loading}
            className="px-3 py-1.5 text-xs rounded bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-40">
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
  | { type: "edit"; rec: SoftWaterRecord }
  | { type: "view"; rec: SoftWaterRecord }
  | { type: "delete"; rec: SoftWaterRecord }
  | { type: "import" };

export default function SoftWaterPage() {
  const qc = useQueryClient();
  const inv = () => {
    qc.invalidateQueries({ queryKey: ["sw-kpis"] });
    qc.invalidateQueries({ queryKey: ["sw-trend"] });
    qc.invalidateQueries({ queryKey: ["sw-records"] });
  };

  const [filters, setFilters] = useState<SoftWaterFilters>({});
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const setF = (k: keyof SoftWaterFilters, v: string | boolean | undefined) =>
    setFilters(p => ({ ...p, [k]: v || undefined }));

  const kpiParams = {
    date_from: filters.date_from,
    date_to:   filters.date_to,
    asset_id:  filters.asset_id,
    department: filters.department,
    shift_ref:  filters.shift_ref,
  };

  const { data: kpis } = useQuery<SoftWaterKPIs>({
    queryKey: ["sw-kpis", kpiParams],
    queryFn: () => softWaterApi.kpis(kpiParams),
  });
  const { data: trend = [] } = useQuery<SoftWaterTrendPoint[]>({
    queryKey: ["sw-trend", kpiParams],
    queryFn: () => softWaterApi.dailyTrend({ date_from: filters.date_from, date_to: filters.date_to, asset_id: filters.asset_id, department: filters.department }),
  });
  const { data: records = [] } = useQuery<SoftWaterRecord[]>({
    queryKey: ["sw-records", filters],
    queryFn: () => softWaterApi.listRecords({ ...filters, limit: 200 }),
  });
  const { data: assets = [] } = useQuery<SoftenerAsset[]>({
    queryKey: ["sw-assets"],
    queryFn: () => softWaterApi.listAssets(),
    staleTime: 300_000,
  });

  const createMut = useMutation({
    mutationFn: (d: SoftWaterRecordCreate) => softWaterApi.createRecord(d),
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, d }: { id: string; d: Partial<SoftWaterRecordCreate> }) =>
      softWaterApi.updateRecord(id, d),
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => softWaterApi.deleteRecord(id),
    onSuccess: () => { inv(); setModal({ type: "none" }); },
  });

  const trendData = trend.map(r => ({
    date: r.date.slice(5),
    "Treated (m³)": parseFloat(r.volume_treated_m3),
    "Salt (kg)":    parseFloat(r.salt_consumed_kg),
    "Eff %":        r.avg_efficiency_pct ? parseFloat(r.avg_efficiency_pct) : null,
  }));

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Soft Water Management</h1>
          <p className="text-sm text-gray-400 mt-1">
            Softener operations · Hardness/TDS/conductivity · Regeneration cycles · Salt consumption
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              const { skip: _s, limit: _l, ...exportParams } = filters;
              downloadSoftWaterCsv(exportParams as Record<string, string | boolean | undefined>, `soft-water-${new Date().toISOString().slice(0,10)}.csv`);
            }}
            className="px-3 py-1.5 text-xs rounded border border-white/10 text-gray-300 hover:bg-white/5"
          >
            Export CSV
          </button>
          <button onClick={() => setModal({ type: "import" })}
            className="px-3 py-1.5 text-xs rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10">
            Import
          </button>
          <button onClick={() => setModal({ type: "create" })}
            className="px-3 py-1.5 text-xs rounded bg-cyan-600 hover:bg-cyan-500 text-white">
            + Log Record
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {([
          ["date_from", "date", "From"],
          ["date_to",   "date", "To"],
          ["department","text", "Department"],
          ["shift_ref", "text", "Shift"],
        ] as [keyof SoftWaterFilters, string, string][]).map(([k, type, ph]) => (
          <input key={k} type={type} placeholder={ph}
            className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-300 w-28"
            value={String(filters[k] ?? "")}
            onChange={e => setF(k, e.target.value)} />
        ))}
        <select
          className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-300"
          value={filters.asset_id ?? ""}
          onChange={e => setF("asset_id", e.target.value)}
        >
          <option value="">All Assets</option>
          {assets.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-xs text-gray-400">
          <input type="checkbox" checked={filters.is_anomaly === true}
            onChange={e => setF("is_anomaly", e.target.checked ? true : undefined)} />
          Anomalies only
        </label>
        <label className="flex items-center gap-1.5 text-xs text-gray-400">
          <input type="checkbox" checked={filters.maintenance_flag === true}
            onChange={e => setF("maintenance_flag", e.target.checked ? true : undefined)} />
          Maintenance flagged
        </label>
      </div>

      {/* KPIs */}
      <Section title="Soft Water KPIs" />
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <KPICard label="Volume Treated" value={`${fmt(kpis?.total_volume_m3)} m³`} />
        <KPICard label="Raw Input" value={`${fmt(kpis?.total_raw_input_m3)} m³`} />
        <KPICard label="Salt Consumed" value={`${fmt(kpis?.total_salt_kg)} kg`} />
        <KPICard label="Salt / m³" value={kpis?.salt_per_m3 ? `${fmt(kpis.salt_per_m3, 3)} kg` : "—"} />
        <KPICard
          label="Conversion Eff."
          value={kpis?.conversion_eff_pct ? `${fmt(kpis.conversion_eff_pct, 1)}%` : "—"}
          ok={parseFloat(kpis?.conversion_eff_pct ?? "0") >= 95}
          alert={parseFloat(kpis?.conversion_eff_pct ?? "100") < 90}
        />
        <KPICard
          label="Hardness Removal"
          value={kpis?.hardness_removal_pct ? `${fmt(kpis.hardness_removal_pct, 1)}%` : "—"}
          ok={parseFloat(kpis?.hardness_removal_pct ?? "0") >= 90}
        />
        <KPICard
          label="Compliance"
          value={kpis?.compliance_pct ? `${fmt(kpis.compliance_pct, 1)}%` : "—"}
          sub="Product ≤ 50 ppm"
          ok={parseFloat(kpis?.compliance_pct ?? "0") >= 95}
          alert={parseFloat(kpis?.compliance_pct ?? "100") < 80}
        />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard label="Regen Count" value={String(kpis?.regen_count ?? 0)} />
        <KPICard label="Regen Frequency" value={kpis?.regen_frequency ? `${fmt(kpis.regen_frequency, 2)}/day` : "—"} />
        <KPICard
          label="Loss Ratio"
          value={kpis?.loss_ratio ? `${fmt(kpis.loss_ratio, 1)}%` : "—"}
          alert={parseFloat(kpis?.loss_ratio ?? "0") > 5}
        />
        <KPICard label="Avg Downtime" value={kpis?.avg_downtime_min ? `${fmt(kpis.avg_downtime_min, 0)} min` : "—"}
          alert={parseFloat(kpis?.avg_downtime_min ?? "0") > 30} />
      </div>
      {(kpis?.anomaly_count ?? 0) > 0 && (
        <div className="flex gap-4">
          <KPICard label="Anomalies" value={String(kpis?.anomaly_count ?? 0)} alert />
          <KPICard label="Maintenance Flags" value={String(kpis?.maintenance_count ?? 0)} alert={(kpis?.maintenance_count ?? 0) > 0} />
        </div>
      )}

      {/* Trend Charts */}
      <Section title="Daily Trend" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Volume + Salt */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4" style={{ height: 240 }}>
          <p className="text-xs text-gray-400 mb-2">Volume Treated vs Salt Consumed</p>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={trendData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
              <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 10 }} />
              <YAxis yAxisId="vol" orientation="left" tick={{ fill: "#9ca3af", fontSize: 10 }} tickFormatter={v => `${v}m³`} />
              <YAxis yAxisId="salt" orientation="right" tick={{ fill: "#9ca3af", fontSize: 10 }} tickFormatter={v => `${v}kg`} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1f2e", border: "1px solid #ffffff20", borderRadius: 8 }}
                formatter={(v: unknown) => [Number(v).toLocaleString()]}
              />
              <Legend wrapperStyle={{ fontSize: 10, color: "#9ca3af" }} />
              <Bar yAxisId="vol"  dataKey="Treated (m³)" fill="#22d3ee" />
              <Bar yAxisId="salt" dataKey="Salt (kg)"    fill="#a78bfa" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {/* Efficiency */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4" style={{ height: 240 }}>
          <p className="text-xs text-gray-400 mb-2">Efficiency % Trend</p>
          <ResponsiveContainer width="100%" height="90%">
            <AreaChart data={trendData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
              <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 10 }} />
              <YAxis domain={[0, 100]} tick={{ fill: "#9ca3af", fontSize: 10 }} tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1f2e", border: "1px solid #ffffff20", borderRadius: 8 }}
                formatter={(v: unknown) => [`${Number(v).toFixed(1)}%`]}
              />
              <Area type="monotone" dataKey="Eff %" stroke="#34d399" fill="#34d39920" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Records table */}
      <Section title="Operational Records" />
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10">
              {["Record No", "DateTime", "Asset", "Vol (m³)", "Raw In",
                "Salt (kg)", "Hard Feed/Prod", "Eff %", "Regen",
                "Status", "Flags", ""].map(h => (
                <th key={h} className="text-left px-3 py-2 text-gray-400 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.map(rec => (
              <tr
                key={rec.id}
                className={`border-b border-white/5 hover:bg-white/5 cursor-pointer ${
                  rec.is_anomaly ? "border-l-2 border-red-500/60" : ""
                }`}
                onClick={() => setModal({ type: "view", rec })}
              >
                <td className="px-3 py-2 font-mono text-gray-300">{rec.record_no}</td>
                <td className="px-3 py-2 text-gray-300 whitespace-nowrap">{fmtDt(rec.record_datetime)}</td>
                <td className="px-3 py-2 text-gray-400">{rec.asset_name ?? rec.asset_no ?? "—"}</td>
                <td className="px-3 py-2 text-white">{fmt(rec.volume_treated_m3)}</td>
                <td className="px-3 py-2 text-gray-400">{fmt(rec.raw_water_input_m3)}</td>
                <td className="px-3 py-2 text-gray-400">{fmt(rec.salt_consumed_kg)}</td>
                <td className="px-3 py-2 text-gray-400">
                  {rec.feed_water_hardness_ppm != null ? fmt(rec.feed_water_hardness_ppm, 0) : "—"}
                  {" / "}
                  {rec.product_water_hardness_ppm != null
                    ? <span className={rec.product_water_hardness_ppm > 50 ? "text-red-400" : "text-emerald-400"}>
                        {fmt(rec.product_water_hardness_ppm, 0)}
                      </span>
                    : "—"}
                </td>
                <td className="px-3 py-2">
                  {rec.efficiency_pct != null ? (
                    <span className={parseFloat(String(rec.efficiency_pct)) < 90 ? "text-amber-400" : "text-emerald-400"}>
                      {fmt(rec.efficiency_pct, 1)}%
                    </span>
                  ) : "—"}
                </td>
                <td className="px-3 py-2 text-gray-400">{rec.regeneration_count ?? "—"}</td>
                <td className="px-3 py-2"><StatusBadge status={rec.status} /></td>
                <td className="px-3 py-2">
                  {rec.is_anomaly && <span className="text-red-400 mr-1" title="Anomaly">⚠</span>}
                  {rec.maintenance_flag && <span className="text-amber-400" title="Maintenance required">🔧</span>}
                </td>
                <td className="px-3 py-2" onClick={e => e.stopPropagation()}>
                  <div className="flex gap-2">
                    <button onClick={() => setModal({ type: "edit", rec })}
                      className="text-cyan-400 hover:text-cyan-300 text-xs">Edit</button>
                    <button onClick={() => setModal({ type: "delete", rec })}
                      className="text-red-400 hover:text-red-300 text-xs">Del</button>
                  </div>
                </td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr>
                <td colSpan={12} className="px-3 py-8 text-center text-gray-500">
                  No soft water records found for the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modals */}
      {modal.type === "create" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-auto">
            <h3 className="text-white font-semibold mb-4">Log Soft Water Record</h3>
            <RecordForm
              assets={assets}
              onSubmit={d => createMut.mutate(d)}
              onCancel={() => setModal({ type: "none" })}
              loading={createMut.isPending}
            />
          </div>
        </div>
      )}

      {modal.type === "edit" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-auto">
            <h3 className="text-white font-semibold mb-4">Edit Soft Water Record — {modal.rec.record_no}</h3>
            <RecordForm
              initial={modal.rec as unknown as Partial<SoftWaterRecordCreate>}
              assets={assets}
              onSubmit={d => updateMut.mutate({ id: modal.rec.id, d })}
              onCancel={() => setModal({ type: "none" })}
              loading={updateMut.isPending}
            />
          </div>
        </div>
      )}

      {modal.type === "view" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-white font-semibold">Record — {modal.rec.record_no}</h3>
              <button onClick={() => setModal({ type: "none" })} className="text-gray-400 hover:text-white">✕</button>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              {([
                ["Asset",     modal.rec.asset_name ?? modal.rec.asset_no],
                ["DateTime",  fmtDt(modal.rec.record_datetime)],
                ["Status",    modal.rec.status],
                ["Volume Treated", modal.rec.volume_treated_m3 != null ? `${fmt(modal.rec.volume_treated_m3)} m³` : "—"],
                ["Raw Input", modal.rec.raw_water_input_m3 != null ? `${fmt(modal.rec.raw_water_input_m3)} m³` : "—"],
                ["Salt Consumed", modal.rec.salt_consumed_kg != null ? `${fmt(modal.rec.salt_consumed_kg)} kg` : "—"],
                ["Feed Hardness", modal.rec.feed_water_hardness_ppm != null ? `${fmt(modal.rec.feed_water_hardness_ppm, 0)} ppm` : "—"],
                ["Product Hardness", modal.rec.product_water_hardness_ppm != null ? `${fmt(modal.rec.product_water_hardness_ppm, 0)} ppm` : "—"],
                ["Feed TDS",    modal.rec.feed_water_tds_ppm != null ? `${fmt(modal.rec.feed_water_tds_ppm, 0)} ppm` : "—"],
                ["Product TDS", modal.rec.product_water_tds_ppm != null ? `${fmt(modal.rec.product_water_tds_ppm, 0)} ppm` : "—"],
                ["Feed Cond.",    modal.rec.conductivity_feed_uscm != null ? `${fmt(modal.rec.conductivity_feed_uscm)} µS/cm` : "—"],
                ["Product Cond.", modal.rec.conductivity_product_uscm != null ? `${fmt(modal.rec.conductivity_product_uscm)} µS/cm` : "—"],
                ["Efficiency", modal.rec.efficiency_pct != null ? `${fmt(modal.rec.efficiency_pct, 1)}%` : "—"],
                ["Regen Count", modal.rec.regeneration_count ?? "—"],
                ["Regen Start", fmtDt(modal.rec.regen_start)],
                ["Regen End",   fmtDt(modal.rec.regen_end)],
                ["Downtime",    modal.rec.downtime_minutes != null ? `${modal.rec.downtime_minutes} min` : "—"],
                ["Destination", modal.rec.destination_tag ?? "—"],
                ["Department",  modal.rec.department ?? "—"],
                ["Shift",       modal.rec.shift_ref ?? "—"],
              ] as [string, unknown][]).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <span className="text-gray-500 w-32 shrink-0">{k}</span>
                  <span className="text-gray-200">{String(v ?? "—")}</span>
                </div>
              ))}
              {modal.rec.notes && (
                <div className="col-span-2 flex gap-2">
                  <span className="text-gray-500 w-32 shrink-0">Notes</span>
                  <span className="text-gray-200">{modal.rec.notes}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {modal.type === "delete" && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-xl p-6 w-full max-w-sm text-center">
            <p className="text-white mb-2">Delete this record?</p>
            <p className="text-gray-400 text-sm mb-4">{modal.rec.record_no}</p>
            <div className="flex gap-2 justify-center">
              <button onClick={() => setModal({ type: "none" })}
                className="px-4 py-1.5 rounded border border-white/10 text-gray-300 text-sm hover:bg-white/5">Cancel</button>
              <button onClick={() => deleteMut.mutate(modal.rec.id)}
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
