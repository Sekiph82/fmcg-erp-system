"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  logsApi,
  OperationalLog,
  SecurityLog,
  OperationalLogFilters,
} from "@/lib/logs";
import { RequirePermission } from "@/components/PermissionGuard";

type Tab = "operational" | "mpesa" | "security";

const MODULE_OPTIONS = [
  "", "inventory", "production", "sales", "finance", "mpesa",
  "procurement", "logistics", "quality", "maintenance",
];

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: "bg-emerald-100 text-emerald-800",
  FAILED: "bg-red-100 text-red-800",
  PENDING: "bg-amber-100 text-amber-800",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

function fmt(dt: string) {
  return new Date(dt).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

// ── Operational / M-Pesa tab ──────────────────────────────────────────────────
function OperationalTab({ mpesaOnly }: { mpesaOnly?: boolean }) {
  const [filters, setFilters] = useState<OperationalLogFilters>({ limit: 100, skip: 0 });
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["op-logs", mpesaOnly ? "mpesa" : "all", filters],
    queryFn: () =>
      mpesaOnly ? logsApi.listMpesa(filters) : logsApi.listOperational(filters),
  });

  const set = (k: keyof OperationalLogFilters, v: unknown) =>
    setFilters((f) => ({ ...f, [k]: v, skip: 0 }));

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg border p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {!mpesaOnly && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Module</label>
              <select
                className="w-full border rounded px-2 py-1.5 text-sm"
                value={filters.module_name ?? ""}
                onChange={(e) => set("module_name", e.target.value || undefined)}
              >
                {MODULE_OPTIONS.map((m) => (
                  <option key={m} value={m}>{m || "All Modules"}</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
            <select
              className="w-full border rounded px-2 py-1.5 text-sm"
              value={filters.status ?? ""}
              onChange={(e) => set("status", e.target.value || undefined)}
            >
              <option value="">All</option>
              <option value="SUCCESS">Success</option>
              <option value="FAILED">Failed</option>
              <option value="PENDING">Pending</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
            <input
              type="date"
              className="w-full border rounded px-2 py-1.5 text-sm"
              value={filters.date_from ?? ""}
              onChange={(e) => set("date_from", e.target.value || undefined)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
            <input
              type="date"
              className="w-full border rounded px-2 py-1.5 text-sm"
              value={filters.date_to ?? ""}
              onChange={(e) => set("date_to", e.target.value || undefined)}
            />
          </div>
        </div>
        <div className="flex items-center gap-4 mt-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.error_only ?? false}
              onChange={(e) => set("error_only", e.target.checked || undefined)}
            />
            Errors only
          </label>
          <span className="text-xs text-gray-400 ml-auto">
            {data?.total ?? 0} records
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-gray-400 text-sm">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Time</th>
                  {!mpesaOnly && <th className="px-4 py-2 text-left">Module</th>}
                  <th className="px-4 py-2 text-left">Entity</th>
                  <th className="px-4 py-2 text-left">Action</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">By</th>
                  <th className="px-4 py-2 text-left">Error</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {(data?.items ?? []).map((row: OperationalLog) => (
                  <>
                    <tr key={row.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">{fmt(row.created_at)}</td>
                      {!mpesaOnly && <td className="px-4 py-2 font-medium text-indigo-700 text-xs">{row.module_name}</td>}
                      <td className="px-4 py-2">
                        <span className="text-gray-700">{row.entity_type}</span>
                        {row.entity_id && (
                          <span className="block text-gray-400 text-xs font-mono truncate max-w-[120px]">{row.entity_id}</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-600 text-xs font-semibold">{row.action_type}</td>
                      <td className="px-4 py-2"><StatusBadge status={row.status} /></td>
                      <td className="px-4 py-2 text-gray-500 text-xs">{row.created_by_email ?? "—"}</td>
                      <td className="px-4 py-2 text-red-600 text-xs max-w-[180px] truncate">{row.error_message ?? ""}</td>
                      <td className="px-4 py-2">
                        {(row.request_payload || row.response_payload) && (
                          <button
                            className="text-xs text-indigo-600 hover:underline"
                            onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                          >
                            {expanded === row.id ? "Hide" : "Payload"}
                          </button>
                        )}
                      </td>
                    </tr>
                    {expanded === row.id && (
                      <tr key={`${row.id}-payload`} className="bg-gray-50">
                        <td colSpan={mpesaOnly ? 7 : 8} className="px-4 py-3">
                          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                            <div>
                              <p className="font-sans font-semibold text-gray-500 mb-1">Request</p>
                              <pre className="bg-white border rounded p-2 overflow-x-auto text-gray-700 max-h-40">
                                {JSON.stringify(row.request_payload, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <p className="font-sans font-semibold text-gray-500 mb-1">Response</p>
                              <pre className="bg-white border rounded p-2 overflow-x-auto text-gray-700 max-h-40">
                                {JSON.stringify(row.response_payload, null, 2)}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
                {(data?.items ?? []).length === 0 && (
                  <tr><td colSpan={mpesaOnly ? 7 : 8} className="p-8 text-center text-gray-400">No logs found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > (filters.limit ?? 100) && (
        <div className="flex items-center gap-3 justify-end text-sm">
          <button
            disabled={!filters.skip || filters.skip === 0}
            onClick={() => set("skip", Math.max(0, (filters.skip ?? 0) - (filters.limit ?? 100)))}
            className="px-3 py-1 border rounded disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-gray-500">
            {(filters.skip ?? 0) + 1}–{Math.min((filters.skip ?? 0) + (filters.limit ?? 100), data.total)} of {data.total}
          </span>
          <button
            disabled={(filters.skip ?? 0) + (filters.limit ?? 100) >= data.total}
            onClick={() => set("skip", (filters.skip ?? 0) + (filters.limit ?? 100))}
            className="px-3 py-1 border rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

// ── Security tab ──────────────────────────────────────────────────────────────
function SecurityTab() {
  const [eventType, setEventType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["security-logs", eventType, dateFrom, dateTo],
    queryFn: () =>
      logsApi.listSecurity({
        event_type: eventType || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 200,
      }),
  });

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Event Type</label>
            <input
              className="w-full border rounded px-2 py-1.5 text-sm"
              placeholder="e.g. LOGIN_SUCCESS"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
            <input type="date" className="w-full border rounded px-2 py-1.5 text-sm" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
            <input type="date" className="w-full border rounded px-2 py-1.5 text-sm" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-2">{logs.length} records</p>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-gray-400 text-sm">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-2 text-left">Time</th>
                <th className="px-4 py-2 text-left">Event</th>
                <th className="px-4 py-2 text-left">Actor</th>
                <th className="px-4 py-2 text-left">Target</th>
                <th className="px-4 py-2 text-left">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {logs.map((log: SecurityLog) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">{fmt(log.created_at)}</td>
                  <td className="px-4 py-2 font-semibold text-xs text-indigo-700">{log.event_type}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{log.actor_email ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">
                    {log.target_type ? (
                      <>
                        <span className="font-medium">{log.target_type}</span>
                        {log.target_name && <span className="text-gray-400"> · {log.target_name}</span>}
                      </>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-2 text-gray-400 text-xs font-mono">{log.ip_address ?? "—"}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={5} className="p-8 text-center text-gray-400">No security events</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
function LogsContent() {
  const [tab, setTab] = useState<Tab>("operational");

  const TABS: { key: Tab; label: string }[] = [
    { key: "operational", label: "Operational" },
    { key: "mpesa", label: "M-Pesa" },
    { key: "security", label: "Security" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Logs</h1>
          <p className="text-sm text-gray-500 mt-1">Operational, M-Pesa, and security audit trail</p>
        </div>
        <a
          href={logsApi.exportUrl({ limit: 5000 })}
          className="px-3 py-1.5 border rounded text-sm text-indigo-600 hover:border-indigo-300"
        >
          Export CSV
        </a>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "operational" && <OperationalTab />}
      {tab === "mpesa" && <OperationalTab mpesaOnly />}
      {tab === "security" && <SecurityTab />}
    </div>
  );
}

export default function LogsPage() {
  return (
    <RequirePermission permission="audit.view">
      <LogsContent />
    </RequirePermission>
  );
}
