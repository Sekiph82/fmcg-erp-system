"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UtilityTransaction,
  UtilityTransactionCreate,
  UtilityTransactionUpdate,
  TransactionFilters,
  UtilityTransactionSummary,
  utilityTransactionsApi,
  UTILITY_TYPE_OPTIONS,
  TX_REFERENCE_TYPE_OPTIONS,
  SOURCE_METHOD_OPTIONS,
  DATA_QUALITY_OPTIONS,
  SOURCE_METHOD_LABELS,
  DATA_QUALITY_LABELS,
  TX_REFERENCE_TYPE_LABELS,
  downloadAuthenticatedCsvTransactions,
} from "@/lib/utilityTransactions";
import { UTILITY_TYPE_LABELS } from "@/lib/utilityManagement";
import type { UtilityType } from "@/lib/utilityManagement";
import type { TxReferenceType, SourceMethod, DataQuality } from "@/lib/utilityTransactions";

// ── Badge helpers ─────────────────────────────────────────────────────────────

function QualityBadge({ q }: { q: DataQuality }) {
  const cls: Record<DataQuality, string> = {
    GOOD:      "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    ESTIMATED: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    SUSPECT:   "bg-orange-500/15 text-orange-400 border-orange-500/20",
    MISSING:   "bg-red-500/15 text-red-400 border-red-500/20",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${cls[q]}`}>
      {DATA_QUALITY_LABELS[q]}
    </span>
  );
}

function SourceBadge({ s }: { s: SourceMethod }) {
  const cls: Record<SourceMethod, string> = {
    MANUAL:     "bg-slate-500/15 text-slate-400 border-slate-500/20",
    IMPORTED:   "bg-blue-500/15 text-blue-400 border-blue-500/20",
    API:        "bg-purple-500/15 text-purple-400 border-purple-500/20",
    IOT:        "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
    CALCULATED: "bg-indigo-500/15 text-indigo-400 border-indigo-500/20",
    ESTIMATED:  "bg-amber-500/15 text-amber-400 border-amber-500/20",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${cls[s]}`}>
      {SOURCE_METHOD_LABELS[s]}
    </span>
  );
}

function UtilityTypeBadge({ t }: { t: UtilityType }) {
  const colors: Partial<Record<UtilityType, string>> = {
    ELECTRICITY:    "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
    WATER:          "bg-blue-500/15 text-blue-400 border-blue-500/20",
    SOFT_WATER:     "bg-sky-500/15 text-sky-400 border-sky-500/20",
    PROCESS_WATER:  "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
    STEAM:          "bg-orange-500/15 text-orange-400 border-orange-500/20",
    COMPRESSED_AIR: "bg-slate-500/15 text-slate-300 border-slate-500/20",
    SOLAR:          "bg-amber-500/15 text-amber-400 border-amber-500/20",
    NATURAL_GAS:    "bg-red-500/15 text-red-400 border-red-500/20",
    WASTEWATER:     "bg-teal-500/15 text-teal-400 border-teal-500/20",
    DIESEL:         "bg-zinc-500/15 text-zinc-400 border-zinc-500/20",
    CHILLED_WATER:  "bg-indigo-500/15 text-indigo-400 border-indigo-500/20",
    OTHER:          "bg-gray-500/15 text-gray-400 border-gray-500/20",
  };
  const cls = colors[t] ?? "bg-gray-500/15 text-gray-400 border-gray-500/20";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${cls}`}>
      {UTILITY_TYPE_LABELS[t] ?? t}
    </span>
  );
}

// ── Section title ─────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-bold uppercase tracking-widest text-blue-400 border-b border-slate-700/50 pb-1 mb-3">
      {children}
    </div>
  );
}

// ── Transaction Form ──────────────────────────────────────────────────────────

interface TxFormProps {
  initial?: Partial<UtilityTransaction>;
  onSubmit: (data: UtilityTransactionCreate) => void;
  isLoading?: boolean;
  error?: string | null;
  submitLabel?: string;
}

function TransactionForm({ initial, onSubmit, isLoading, error, submitLabel = "Save" }: TxFormProps) {
  const [form, setForm] = useState<UtilityTransactionCreate>({
    utility_type: (initial?.utility_type as UtilityType) ?? "ELECTRICITY",
    transaction_date: initial?.transaction_date ?? new Date().toISOString().slice(0, 10),
    quantity: initial?.quantity ?? "",
    uom: initial?.uom ?? "",
    transaction_time: initial?.transaction_time ?? null,
    period_start: initial?.period_start ?? null,
    period_end: initial?.period_end ?? null,
    department: initial?.department ?? null,
    building_area: initial?.building_area ?? null,
    line_id: initial?.line_id ?? null,
    machine_id: initial?.machine_id ?? null,
    shift_id: initial?.shift_id ?? null,
    batch_id: initial?.batch_id ?? null,
    reference_type: (initial?.reference_type as TxReferenceType) ?? null,
    reference_id: initial?.reference_id ?? null,
    cost_rate: initial?.cost_rate ?? null,
    total_cost: initial?.total_cost ?? null,
    currency_code: initial?.currency_code ?? "USD",
    variance_from_standard: initial?.variance_from_standard ?? null,
    source_method: (initial?.source_method as SourceMethod) ?? "MANUAL",
    quality: (initial?.quality as DataQuality) ?? "GOOD",
    estimated_or_actual: initial?.estimated_or_actual ?? false,
    anomaly_flag: initial?.anomaly_flag ?? false,
    anomaly_note: initial?.anomaly_note ?? null,
    notes: initial?.notes ?? null,
  });

  function set<K extends keyof UtilityTransactionCreate>(k: K, v: UtilityTransactionCreate[K]) {
    setForm((prev) => ({ ...prev, [k]: v }));
  }

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(form); }}
      className="flex flex-col gap-5"
    >
      {/* Core */}
      <div>
        <SectionTitle>Transaction Details</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Utility Type *</label>
            <select
              required
              value={form.utility_type}
              onChange={(e) => set("utility_type", e.target.value as UtilityType)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {UTILITY_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Transaction Date *</label>
            <input
              required
              type="date"
              value={form.transaction_date}
              onChange={(e) => set("transaction_date", e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Transaction Time</label>
            <input
              type="datetime-local"
              value={form.transaction_time?.slice(0, 16) ?? ""}
              onChange={(e) => set("transaction_time", e.target.value ? e.target.value + ":00" : null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Quantity *</label>
            <input
              required
              type="number"
              step="any"
              min="0"
              value={form.quantity as string}
              onChange={(e) => set("quantity", e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Unit of Measure *</label>
            <input
              required
              type="text"
              value={form.uom}
              onChange={(e) => set("uom", e.target.value)}
              placeholder="kWh, m³, kg…"
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Source Method</label>
            <select
              value={form.source_method}
              onChange={(e) => set("source_method", e.target.value as SourceMethod)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {SOURCE_METHOD_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Cost */}
      <div>
        <SectionTitle>Cost</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Cost Rate</label>
            <input
              type="number"
              step="any"
              min="0"
              value={form.cost_rate as string ?? ""}
              onChange={(e) => set("cost_rate", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Total Cost</label>
            <input
              type="number"
              step="any"
              min="0"
              value={form.total_cost as string ?? ""}
              onChange={(e) => set("total_cost", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Currency</label>
            <input
              type="text"
              value={form.currency_code ?? "USD"}
              onChange={(e) => set("currency_code", e.target.value.toUpperCase())}
              maxLength={3}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 uppercase"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Variance from Standard</label>
            <input
              type="number"
              step="any"
              value={form.variance_from_standard as string ?? ""}
              onChange={(e) => set("variance_from_standard", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Allocation */}
      <div>
        <SectionTitle>Allocation</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Department</label>
            <input
              type="text"
              value={form.department ?? ""}
              onChange={(e) => set("department", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Building / Area</label>
            <input
              type="text"
              value={form.building_area ?? ""}
              onChange={(e) => set("building_area", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Production Line</label>
            <input
              type="text"
              value={form.line_id ?? ""}
              onChange={(e) => set("line_id", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Machine</label>
            <input
              type="text"
              value={form.machine_id ?? ""}
              onChange={(e) => set("machine_id", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Shift</label>
            <input
              type="text"
              value={form.shift_id ?? ""}
              onChange={(e) => set("shift_id", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Batch ID</label>
            <input
              type="text"
              value={form.batch_id ?? ""}
              onChange={(e) => set("batch_id", e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Reference linkage */}
      <div>
        <SectionTitle>Reference Linkage</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Reference Type</label>
            <select
              value={form.reference_type ?? ""}
              onChange={(e) => set("reference_type", (e.target.value as TxReferenceType) || null)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">— None —</option>
              {TX_REFERENCE_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Reference ID</label>
            <input
              type="text"
              value={form.reference_id ?? ""}
              onChange={(e) => set("reference_id", e.target.value || null)}
              placeholder="UUID or external reference"
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Quality / flags */}
      <div>
        <SectionTitle>Quality & Flags</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-slate-400">Data Quality</label>
            <select
              value={form.quality}
              onChange={(e) => set("quality", e.target.value as DataQuality)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {DATA_QUALITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-3 pt-5">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={form.estimated_or_actual}
                onChange={(e) => set("estimated_or_actual", e.target.checked)}
                className="accent-amber-500"
              />
              Estimated (not actual)
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={form.anomaly_flag}
                onChange={(e) => set("anomaly_flag", e.target.checked)}
                className="accent-red-500"
              />
              Anomaly
            </label>
          </div>
          {form.anomaly_flag && (
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-slate-400">Anomaly Note</label>
              <input
                type="text"
                value={form.anomaly_note ?? ""}
                onChange={(e) => set("anomaly_note", e.target.value || null)}
                className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Notes */}
      <div className="flex flex-col gap-1">
        <label className="text-[11px] text-slate-400">Notes</label>
        <textarea
          rows={2}
          value={form.notes ?? ""}
          onChange={(e) => set("notes", e.target.value || null)}
          className="bg-slate-800 border border-slate-700 rounded px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 resize-none"
        />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
        >
          {isLoading ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

// ── View Modal ─────────────────────────────────────────────────────────────────

function ViewModal({ tx, onClose }: { tx: UtilityTransaction; onClose: () => void }) {
  const Row = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
      <span className="text-xs text-slate-200">{value ?? <span className="text-slate-600">—</span>}</span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 font-mono">{tx.transaction_no}</h2>
            <p className="text-xs text-slate-500 mt-0.5">{tx.transaction_date}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
        </div>
        <div className="overflow-y-auto flex-1 px-5 py-4 flex flex-col gap-5">
          {/* Classification */}
          <div>
            <SectionTitle>Classification</SectionTitle>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Row label="Utility Type" value={<UtilityTypeBadge t={tx.utility_type} />} />
              <Row label="Source Method" value={<SourceBadge s={tx.source_method} />} />
              <Row label="Quality" value={<QualityBadge q={tx.quality} />} />
              <Row label="Estimated?" value={tx.estimated_or_actual ? "Yes" : "No"} />
              <Row label="Anomaly?" value={
                tx.anomaly_flag
                  ? <span className="text-red-400 font-medium">Yes{tx.anomaly_note ? ` — ${tx.anomaly_note}` : ""}</span>
                  : "No"
              } />
            </div>
          </div>

          {/* Consumption */}
          <div>
            <SectionTitle>Consumption</SectionTitle>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Row label="Quantity" value={`${parseFloat(tx.quantity).toLocaleString()} ${tx.uom}`} />
              <Row label="Variance from Std" value={
                tx.variance_from_standard
                  ? <span className={parseFloat(tx.variance_from_standard) > 0 ? "text-red-400" : "text-emerald-400"}>
                      {parseFloat(tx.variance_from_standard) > 0 ? "▲" : "▼"} {Math.abs(parseFloat(tx.variance_from_standard)).toFixed(4)}
                    </span>
                  : null
              } />
            </div>
          </div>

          {/* Cost */}
          <div>
            <SectionTitle>Cost</SectionTitle>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Row label="Cost Rate" value={tx.cost_rate ? `${tx.currency_code} ${parseFloat(tx.cost_rate).toFixed(4)}` : null} />
              <Row label="Total Cost" value={
                tx.total_cost
                  ? `${tx.currency_code} ${parseFloat(tx.total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                  : null
              } />
              <Row label="Currency" value={tx.currency_code} />
            </div>
          </div>

          {/* Allocation */}
          <div>
            <SectionTitle>Allocation</SectionTitle>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Row label="Department" value={tx.department} />
              <Row label="Building / Area" value={tx.building_area} />
              <Row label="Production Line" value={tx.line_id} />
              <Row label="Machine" value={tx.machine_id} />
              <Row label="Shift" value={tx.shift_id} />
              <Row label="Batch ID" value={tx.batch_id} />
            </div>
          </div>

          {/* Reference */}
          <div>
            <SectionTitle>Reference</SectionTitle>
            <div className="grid grid-cols-2 gap-3">
              <Row label="Reference Type" value={tx.reference_type ? TX_REFERENCE_TYPE_LABELS[tx.reference_type] : null} />
              <Row label="Reference ID" value={<span className="font-mono text-[11px]">{tx.reference_id}</span>} />
              <Row label="Device" value={tx.device_code ? `${tx.device_code} — ${tx.device_name}` : null} />
              <Row label="Asset" value={tx.asset_no ? `${tx.asset_no} — ${tx.asset_name}` : null} />
            </div>
          </div>

          {tx.notes && (
            <div>
              <SectionTitle>Notes</SectionTitle>
              <p className="text-xs text-slate-300 whitespace-pre-wrap">{tx.notes}</p>
            </div>
          )}

          <div className="text-[10px] text-slate-600">Created: {tx.created_at ? new Date(tx.created_at).toLocaleString() : "—"}</div>
        </div>
      </div>
    </div>
  );
}

// ── Summary cards ─────────────────────────────────────────────────────────────

function SummaryCards({ summary }: { summary: UtilityTransactionSummary }) {
  return (
    <div className="flex flex-col gap-3">
      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Total Transactions</div>
          <div className="text-xl font-bold text-slate-200">{summary.grand_total_tx.toLocaleString()}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Total Cost</div>
          <div className="text-xl font-bold text-emerald-400">
            {summary.grand_total_cost
              ? parseFloat(summary.grand_total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })
              : "—"}
          </div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Utility Types</div>
          <div className="text-xl font-bold text-slate-200">{summary.by_utility_type.length}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Anomalies</div>
          <div className={`text-xl font-bold ${summary.by_utility_type.reduce((a, r) => a + r.anomaly_count, 0) > 0 ? "text-red-400" : "text-slate-200"}`}>
            {summary.by_utility_type.reduce((a, r) => a + r.anomaly_count, 0)}
          </div>
        </div>
      </div>

      {/* By utility type */}
      {summary.by_utility_type.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          {summary.by_utility_type.map((row) => (
            <div key={row.group_key} className="bg-slate-800/40 border border-slate-700/40 rounded-lg p-2.5">
              <div className="text-[10px] text-slate-400 font-medium mb-1">{row.label}</div>
              <div className="text-sm font-semibold text-slate-200">
                {parseFloat(row.total_quantity).toLocaleString()} <span className="text-slate-500 text-[10px]">{row.uom}</span>
              </div>
              {row.total_cost && (
                <div className="text-xs text-emerald-400 mt-0.5">
                  {parseFloat(row.total_cost).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
              )}
              <div className="text-[10px] text-slate-600 mt-0.5">{row.tx_count} tx</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type ModalState =
  | { type: "none" }
  | { type: "create" }
  | { type: "view"; tx: UtilityTransaction }
  | { type: "edit"; tx: UtilityTransaction }
  | { type: "delete"; tx: UtilityTransaction };

export default function TransactionsPage() {
  const qc = useQueryClient();

  const [filters, setFilters] = useState<TransactionFilters>({ limit: 200 });
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [formError, setFormError] = useState<string | null>(null);

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["utility-transactions", filters],
    queryFn: () => utilityTransactionsApi.list(filters),
  });

  const { data: summary } = useQuery({
    queryKey: ["utility-tx-summary", filters.date_from, filters.date_to, filters.utility_type, filters.department],
    queryFn: () =>
      utilityTransactionsApi.summary({
        date_from: filters.date_from,
        date_to: filters.date_to,
        utility_type: filters.utility_type,
        department: filters.department,
      }),
  });

  const createMut = useMutation({
    mutationFn: utilityTransactionsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["utility-transactions"] }); qc.invalidateQueries({ queryKey: ["utility-tx-summary"] }); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create transaction."),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityTransactionUpdate }) =>
      utilityTransactionsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["utility-transactions"] }); qc.invalidateQueries({ queryKey: ["utility-tx-summary"] }); setModal({ type: "none" }); setFormError(null); },
    onError: (e: unknown) => setFormError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to update transaction."),
  });

  const deleteMut = useMutation({
    mutationFn: utilityTransactionsApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["utility-transactions"] }); qc.invalidateQueries({ queryKey: ["utility-tx-summary"] }); setModal({ type: "none" }); },
  });

  function setFilter<K extends keyof TransactionFilters>(key: K, val: TransactionFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: val || undefined }));
  }

  async function handleExport() {
    const params = new URLSearchParams();
    if (filters.utility_type) params.set("utility_type", filters.utility_type);
    if (filters.department)    params.set("department", filters.department!);
    if (filters.date_from)     params.set("date_from", filters.date_from!);
    if (filters.date_to)       params.set("date_to", filters.date_to!);
    if (filters.source_method) params.set("source_method", filters.source_method!);
    if (filters.is_anomaly)    params.set("is_anomaly", "true");
    const qs = params.toString();
    await downloadAuthenticatedCsvTransactions(
      `/api/v1/utility-management/transactions/export/csv${qs ? `?${qs}` : ""}`,
      `utility-transactions-${new Date().toISOString().slice(0, 10)}.csv`
    );
  }

  const anomalyCount = rows.filter((r) => r.anomaly_flag).length;

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6 flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-200">Utility Transactions</h1>
          <p className="text-xs text-slate-500 mt-0.5">Unified consumption & cost event log</p>
        </div>
        <button
          onClick={() => { setFormError(null); setModal({ type: "create" }); }}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded font-medium transition-colors"
        >
          <span className="text-base leading-none">+</span> Record Transaction
        </button>
      </div>

      {/* Summary cards */}
      {summary && <SummaryCards summary={summary} />}

      {/* Stats bar */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span>{rows.length} transaction{rows.length !== 1 ? "s" : ""}</span>
        {anomalyCount > 0 && (
          <span className="text-red-400 font-medium">{anomalyCount} anomal{anomalyCount === 1 ? "y" : "ies"}</span>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={filters.utility_type ?? ""}
          onChange={(e) => setFilter("utility_type", e.target.value as UtilityType || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All utilities</option>
          {UTILITY_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <select
          value={filters.source_method ?? ""}
          onChange={(e) => setFilter("source_method", e.target.value as SourceMethod || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All sources</option>
          {SOURCE_METHOD_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <select
          value={filters.reference_type ?? ""}
          onChange={(e) => setFilter("reference_type", e.target.value as TxReferenceType || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All ref. types</option>
          {TX_REFERENCE_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <select
          value={filters.quality ?? ""}
          onChange={(e) => setFilter("quality", e.target.value as DataQuality || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All quality</option>
          {DATA_QUALITY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={filters.is_anomaly === true}
            onChange={(e) => setFilter("is_anomaly", e.target.checked ? true : undefined)}
            className="accent-red-500"
          />
          Anomalies
        </label>

        <input
          type="date"
          value={filters.date_from ?? ""}
          onChange={(e) => setFilter("date_from", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
        />
        <span className="text-slate-600 text-xs">–</span>
        <input
          type="date"
          value={filters.date_to ?? ""}
          onChange={(e) => setFilter("date_to", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
        />

        <input
          type="text"
          placeholder="Department…"
          value={filters.department ?? ""}
          onChange={(e) => setFilter("department", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 w-28"
        />
        <input
          type="text"
          placeholder="Line…"
          value={filters.line_id ?? ""}
          onChange={(e) => setFilter("line_id", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 w-20"
        />
        <input
          type="text"
          placeholder="Batch…"
          value={filters.batch_id ?? ""}
          onChange={(e) => setFilter("batch_id", e.target.value || undefined)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 w-20"
        />

        <button
          onClick={handleExport}
          className="ml-auto px-2.5 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
        >
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-700/50">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-700/60 bg-slate-800/60">
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Tx No.</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Date</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Utility</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Qty / UOM</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Cost</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Source</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Dept / Line</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Ref.</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Quality</th>
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/30">
            {isLoading && (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-xs text-slate-500">Loading…</td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-xs text-slate-500">
                  No transactions found.
                </td>
              </tr>
            )}
            {rows.map((tx) => (
              <tr
                key={tx.id}
                className={`hover:bg-slate-800/40 transition-colors ${tx.anomaly_flag ? "border-l-2 border-l-red-500/60" : ""}`}
              >
                <td className="px-4 py-2.5 text-xs whitespace-nowrap">
                  <button
                    onClick={() => setModal({ type: "view", tx })}
                    className="font-mono text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    {tx.transaction_no}
                  </button>
                  {tx.anomaly_flag && (
                    <span className="ml-1.5 inline-flex items-center px-1 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                      ANOM
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-300 whitespace-nowrap">{tx.transaction_date}</td>
                <td className="px-4 py-2.5 text-xs whitespace-nowrap">
                  <UtilityTypeBadge t={tx.utility_type} />
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-300 whitespace-nowrap">
                  <span className="font-medium text-slate-200">{parseFloat(tx.quantity).toLocaleString()}</span>
                  <span className="text-slate-500 ml-1">{tx.uom}</span>
                  {tx.variance_from_standard != null && parseFloat(tx.variance_from_standard) !== 0 && (
                    <span className={`ml-1.5 text-[10px] ${parseFloat(tx.variance_from_standard) > 0 ? "text-red-400" : "text-emerald-400"}`}>
                      {parseFloat(tx.variance_from_standard) > 0 ? "▲" : "▼"}
                      {Math.abs(parseFloat(tx.variance_from_standard)).toFixed(2)}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-300 whitespace-nowrap">
                  {tx.total_cost != null ? (
                    <span className="text-slate-200">
                      {tx.currency_code ?? ""} {parseFloat(tx.total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-xs whitespace-nowrap">
                  <SourceBadge s={tx.source_method} />
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-300 whitespace-nowrap">
                  <div className="flex flex-col gap-0.5">
                    {tx.department && <span>{tx.department}</span>}
                    {tx.line_id && <span className="text-slate-500 text-[10px]">Line: {tx.line_id}</span>}
                    {!tx.department && !tx.line_id && <span className="text-slate-600">—</span>}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-500 whitespace-nowrap">
                  {tx.reference_type ? TX_REFERENCE_TYPE_LABELS[tx.reference_type] : "—"}
                </td>
                <td className="px-4 py-2.5 text-xs whitespace-nowrap">
                  <QualityBadge q={tx.quality} />
                </td>
                <td className="px-4 py-2.5 text-xs whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setModal({ type: "view", tx })}
                      className="text-slate-400 hover:text-slate-200 transition-colors text-[11px]"
                    >
                      View
                    </button>
                    <button
                      onClick={() => { setFormError(null); setModal({ type: "edit", tx }); }}
                      className="text-blue-400 hover:text-blue-300 transition-colors text-[11px]"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setModal({ type: "delete", tx })}
                      className="text-red-400 hover:text-red-300 transition-colors text-[11px]"
                    >
                      Del
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Create modal ─────────────────────────────────────────────────────── */}
      {modal.type === "create" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
              <h2 className="text-sm font-semibold text-slate-200">Record Transaction</h2>
              <button onClick={() => setModal({ type: "none" })} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="overflow-y-auto flex-1 px-5 py-4">
              <TransactionForm
                onSubmit={(data) => createMut.mutate(data)}
                isLoading={createMut.isPending}
                error={formError}
                submitLabel="Record Transaction"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Edit modal ───────────────────────────────────────────────────────── */}
      {modal.type === "edit" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
              <h2 className="text-sm font-semibold text-slate-200">Edit Transaction</h2>
              <button onClick={() => setModal({ type: "none" })} className="text-slate-500 hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="overflow-y-auto flex-1 px-5 py-4">
              <TransactionForm
                initial={modal.tx}
                onSubmit={(data) => updateMut.mutate({ id: modal.tx.id, data })}
                isLoading={updateMut.isPending}
                error={formError}
                submitLabel="Save Changes"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── View modal ───────────────────────────────────────────────────────── */}
      {modal.type === "view" && (
        <ViewModal tx={modal.tx} onClose={() => setModal({ type: "none" })} />
      )}

      {/* ── Delete modal ─────────────────────────────────────────────────────── */}
      {modal.type === "delete" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-sm p-5 flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-slate-200">Delete Transaction</h2>
            <p className="text-xs text-slate-400">
              Delete <span className="font-mono text-slate-200">{modal.tx.transaction_no}</span>? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setModal({ type: "none" })}
                className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMut.mutate(modal.tx.id)}
                disabled={deleteMut.isPending}
                className="px-3 py-1.5 text-xs bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded transition-colors"
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
