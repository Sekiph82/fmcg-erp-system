"use client";

/**
 * UtilityTransactionTable
 * ──────────────────────────────────────────────────────────────────────────────
 * Reusable transaction table that can be embedded in any utility-specific
 * section or used standalone on the full /transactions page.
 *
 * Props
 *   deviceId      — pre-filter by meter/device
 *   assetId       — pre-filter by asset
 *   department    — pre-filter by department
 *   utilityType   — pre-filter by utility type
 *   showFilters   — render the filter bar (default true)
 *   compact       — reduce row padding / hide secondary columns (default false)
 *   onSelectRow   — optional callback when a row is clicked
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  UtilityTransaction,
  TransactionFilters,
  utilityTransactionsApi,
  UTILITY_TYPE_OPTIONS,
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

// ── Main component ─────────────────────────────────────────────────────────────

interface Props {
  deviceId?: string;
  assetId?: string;
  department?: string;
  utilityType?: UtilityType;
  showFilters?: boolean;
  compact?: boolean;
  onSelectRow?: (tx: UtilityTransaction) => void;
}

export default function UtilityTransactionTable({
  deviceId,
  assetId,
  department: deptProp,
  utilityType: utilityTypeProp,
  showFilters = true,
  compact = false,
  onSelectRow,
}: Props) {
  const [filters, setFilters] = useState<TransactionFilters>({
    utility_type: utilityTypeProp,
    department: deptProp,
    source_meter_id: deviceId,
    source_asset_id: assetId,
  });

  const { data: rows = [], isLoading, refetch } = useQuery({
    queryKey: ["utility-transactions", filters],
    queryFn: () => utilityTransactionsApi.list({ ...filters, limit: 200 }),
  });

  function setFilter<K extends keyof TransactionFilters>(key: K, val: TransactionFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: val || undefined }));
  }

  const anomalyCount = rows.filter((r) => r.anomaly_flag).length;

  async function handleExport() {
    const params = new URLSearchParams();
    if (filters.utility_type) params.set("utility_type", filters.utility_type);
    if (filters.department)    params.set("department", filters.department);
    if (filters.date_from)     params.set("date_from", filters.date_from);
    if (filters.date_to)       params.set("date_to", filters.date_to);
    if (filters.source_meter_id) params.set("source_meter_id", filters.source_meter_id);
    const qs = params.toString();
    await downloadAuthenticatedCsvTransactions(
      `/api/v1/utility-management/transactions/export/csv${qs ? `?${qs}` : ""}`,
      `utility-transactions-${new Date().toISOString().slice(0, 10)}.csv`
    );
  }

  const tdCls = compact
    ? "px-3 py-1.5 text-xs text-slate-300 whitespace-nowrap"
    : "px-4 py-2.5 text-xs text-slate-300 whitespace-nowrap";

  return (
    <div className="flex flex-col gap-3">
      {/* Filter bar */}
      {showFilters && (
        <div className="flex flex-wrap gap-2 items-center">
          {/* Utility type */}
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

          {/* Source method */}
          <select
            value={filters.source_method ?? ""}
            onChange={(e) => setFilter("source_method", e.target.value as SourceMethod || undefined)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All sources</option>
            {Object.entries(SOURCE_METHOD_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>

          {/* Anomaly filter */}
          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={filters.is_anomaly === true}
              onChange={(e) => setFilter("is_anomaly", e.target.checked ? true : undefined)}
              className="accent-red-500"
            />
            Anomalies only
          </label>

          {/* Date from */}
          <input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => setFilter("date_from", e.target.value || undefined)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
          />
          <span className="text-slate-600 text-xs">–</span>
          {/* Date to */}
          <input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => setFilter("date_to", e.target.value || undefined)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
          />

          {/* Department */}
          {!deptProp && (
            <input
              type="text"
              placeholder="Department…"
              value={filters.department ?? ""}
              onChange={(e) => setFilter("department", e.target.value || undefined)}
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 w-28"
            />
          )}

          {/* Batch */}
          <input
            type="text"
            placeholder="Batch ID…"
            value={filters.batch_id ?? ""}
            onChange={(e) => setFilter("batch_id", e.target.value || undefined)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 w-24"
          />

          <div className="ml-auto flex items-center gap-2">
            {anomalyCount > 0 && (
              <span className="text-xs text-red-400 font-medium">
                {anomalyCount} anomal{anomalyCount === 1 ? "y" : "ies"}
              </span>
            )}
            <span className="text-xs text-slate-500">{rows.length} row{rows.length !== 1 ? "s" : ""}</span>
            <button
              onClick={handleExport}
              className="px-2.5 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
            >
              Export CSV
            </button>
          </div>
        </div>
      )}

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
              {!compact && (
                <>
                  <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Source</th>
                  <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Dept / Line</th>
                  <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Ref.</th>
                </>
              )}
              <th className="px-4 py-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Quality</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/30">
            {isLoading && (
              <tr>
                <td colSpan={compact ? 5 : 9} className="px-4 py-8 text-center text-xs text-slate-500">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={compact ? 5 : 9} className="px-4 py-8 text-center text-xs text-slate-500">
                  No transactions found.
                </td>
              </tr>
            )}
            {rows.map((tx) => (
              <tr
                key={tx.id}
                onClick={() => onSelectRow?.(tx)}
                className={`hover:bg-slate-800/40 transition-colors ${onSelectRow ? "cursor-pointer" : ""} ${tx.anomaly_flag ? "border-l-2 border-l-red-500/60" : ""}`}
              >
                <td className={tdCls}>
                  <span className="font-mono text-slate-200">{tx.transaction_no}</span>
                  {tx.anomaly_flag && (
                    <span className="ml-1.5 inline-flex items-center px-1 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                      ANOM
                    </span>
                  )}
                </td>
                <td className={tdCls}>{tx.transaction_date}</td>
                <td className={tdCls}>
                  <UtilityTypeBadge t={tx.utility_type} />
                </td>
                <td className={tdCls}>
                  <span className="font-medium text-slate-200">{parseFloat(tx.quantity).toLocaleString()}</span>
                  <span className="text-slate-500 ml-1">{tx.uom}</span>
                  {tx.variance_from_standard != null && parseFloat(tx.variance_from_standard) !== 0 && (
                    <span className={`ml-1.5 text-[10px] ${parseFloat(tx.variance_from_standard) > 0 ? "text-red-400" : "text-emerald-400"}`}>
                      {parseFloat(tx.variance_from_standard) > 0 ? "▲" : "▼"}
                      {Math.abs(parseFloat(tx.variance_from_standard)).toFixed(2)}
                    </span>
                  )}
                </td>
                <td className={tdCls}>
                  {tx.total_cost != null ? (
                    <span className="text-slate-200">
                      {tx.currency_code ?? ""} {parseFloat(tx.total_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                {!compact && (
                  <>
                    <td className={tdCls}>
                      <SourceBadge s={tx.source_method} />
                    </td>
                    <td className={tdCls}>
                      <div className="flex flex-col gap-0.5">
                        {tx.department && <span className="text-slate-300">{tx.department}</span>}
                        {tx.line_id && <span className="text-slate-500 text-[10px]">Line: {tx.line_id}</span>}
                        {tx.machine_id && <span className="text-slate-500 text-[10px]">Machine: {tx.machine_id}</span>}
                        {!tx.department && !tx.line_id && !tx.machine_id && (
                          <span className="text-slate-600">—</span>
                        )}
                      </div>
                    </td>
                    <td className={tdCls}>
                      {tx.reference_type ? (
                        <span className="text-slate-400 text-[10px]">
                          {TX_REFERENCE_TYPE_LABELS[tx.reference_type]}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                  </>
                )}
                <td className={tdCls}>
                  <QualityBadge q={tx.quality} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
