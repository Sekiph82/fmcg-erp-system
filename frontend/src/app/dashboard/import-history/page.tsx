"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  importApi,
  MODULE_LABELS,
  STATUS_BG,
  STATUS_COLORS,
  type ImportHistoryEntry,
} from "@/lib/importApi";

const ALL_MODULES = Object.keys(MODULE_LABELS);

function fmt(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-KE", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function ImportHistoryPage() {
  const [module,   setModule]    = useState("");
  const [username, setUsername]  = useState("");
  const [dateFrom, setDateFrom]  = useState("");
  const [dateTo,   setDateTo]    = useState("");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["import-history", module, username, dateFrom, dateTo],
    queryFn: () =>
      importApi.getHistory({
        module:    module || undefined,
        username:  username || undefined,
        date_from: dateFrom || undefined,
        date_to:   dateTo   || undefined,
        limit: 100,
      }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Import History</h1>
        <p className="text-sm text-slate-500 mt-1">Audit trail of all bulk import runs.</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={module}
          onChange={e => setModule(e.target.value)}
          className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50"
        >
          <option value="">All modules</option>
          {ALL_MODULES.map(m => (
            <option key={m} value={m}>{MODULE_LABELS[m]}</option>
          ))}
        </select>

        <input
          value={username}
          onChange={e => setUsername(e.target.value)}
          placeholder="Filter by user…"
          className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 placeholder-slate-600 outline-none focus:border-indigo-500/50"
        />

        <input
          type="date"
          value={dateFrom}
          onChange={e => setDateFrom(e.target.value)}
          className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50"
        />
        <span className="self-center text-slate-600 text-xs">to</span>
        <input
          type="date"
          value={dateTo}
          onChange={e => setDateTo(e.target.value)}
          className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-indigo-500/50"
        />

        <button
          onClick={() => { setModule(""); setUsername(""); setDateFrom(""); setDateTo(""); }}
          className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 rounded-xl bg-white/[0.02] animate-pulse border border-white/[0.04]" />
          ))}
        </div>
      ) : !data?.length ? (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-10 text-center">
          <p className="text-slate-500 text-sm">No import history found.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-white/[0.06] overflow-hidden">
          <table className="w-full text-left text-[13px]">
            <thead className="border-b border-white/[0.06]">
              <tr>
                {["Module", "File", "Mode", "Total", "Success", "Failed", "Status", "User", "When", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {data.map(row => (
                <HistoryRow key={row.id} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function HistoryRow({ row }: { row: ImportHistoryEntry }) {
  const modeName: Record<string, string> = {
    validate_only:       "Validate only",
    import_valid_only:   "Valid rows",
    strict:              "Strict",
  };

  return (
    <tr className="hover:bg-white/[0.02] transition-colors">
      <td className="px-4 py-3 text-slate-300 font-medium">
        {MODULE_LABELS[row.module] ?? row.module}
      </td>
      <td className="px-4 py-3 text-slate-500 max-w-[160px] truncate" title={row.file_name ?? ""}>
        {row.file_name ?? "—"}
      </td>
      <td className="px-4 py-3 text-slate-500">
        {modeName[row.import_mode] ?? row.import_mode}
      </td>
      <td className="px-4 py-3 text-slate-400 font-mono">{row.total_rows}</td>
      <td className="px-4 py-3 text-emerald-400 font-mono">{row.success_count}</td>
      <td className="px-4 py-3 font-mono">
        <span className={row.failure_count > 0 ? "text-red-400" : "text-slate-600"}>
          {row.failure_count}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-medium uppercase ${STATUS_BG[row.status] ?? ""}`}>
          <span className={STATUS_COLORS[row.status] ?? "text-slate-400"}>{row.status}</span>
        </span>
      </td>
      <td className="px-4 py-3 text-slate-500">{row.username ?? "—"}</td>
      <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{fmt(row.created_at)}</td>
      <td className="px-4 py-3">
        {row.failure_count > 0 && (
          <button
            onClick={() => importApi.downloadErrors(row.id)}
            className="text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors whitespace-nowrap"
          >
            ↓ Errors
          </button>
        )}
      </td>
    </tr>
  );
}
