"use client";
import { useCallback, useEffect, useState } from "react";

interface AuditEntry {
  id: string;
  created_at: string;
  event_type: string;
  module: string | null;
  actor_email: string | null;
  actor_name: string | null;
  session_id: string | null;
  ip_address: string | null;
  target_type: string | null;
  target_id: string | null;
  target_name: string | null;
  before_value: Record<string, unknown> | null;
  after_value: Record<string, unknown> | null;
  details: Record<string, unknown> | null;
  row_hash: string | null;
}

interface AuditStats {
  period_days: number;
  total_events: number;
  security_alerts: number;
  by_event_type: Record<string, number>;
  by_module: Record<string, number>;
  top_actors: { email: string; count: number }[];
}

const EVENT_COLOR: Record<string, string> = {
  LOGIN_SUCCESS: "text-green-700 bg-green-100",
  LOGIN_FAILED: "text-red-700 bg-red-100",
  ACCOUNT_LOCKED: "text-red-700 bg-red-200",
  PERMISSION_DENIED: "text-red-700 bg-red-100",
  SUSPICIOUS_ACTIVITY: "text-red-800 bg-red-200",
  PO_APPROVED: "text-blue-700 bg-blue-100",
  INVOICE_APPROVED: "text-blue-700 bg-blue-100",
  PAYMENT_RECEIVED: "text-green-700 bg-green-100",
};

const DEFAULT_AUDIT_FILTERS = { event_type: "", target_type: "", module: "", limit: "200" };

function DiffView({ before, after }: { before: Record<string, unknown> | null; after: Record<string, unknown> | null }) {
  if (!before && !after) return null;
  const keysArr = Array.from(new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})]));
  const changed = keysArr.filter((k) => JSON.stringify((before ?? {})[k]) !== JSON.stringify((after ?? {})[k]));
  if (changed.length === 0) return <p className="text-xs text-gray-400">No field changes detected.</p>;
  return (
    <div className="space-y-1">
      {changed.map((k) => (
        <div key={k} className="grid grid-cols-3 gap-2 text-xs">
          <span className="text-gray-500 font-medium truncate">{k}</span>
          <span className="bg-red-50 text-red-700 rounded px-1 py-0.5 font-mono truncate">
            {JSON.stringify((before ?? {})[k]) ?? "—"}
          </span>
          <span className="bg-green-50 text-green-700 rounded px-1 py-0.5 font-mono truncate">
            {JSON.stringify((after ?? {})[k]) ?? "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ComplianceAuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filters, setFilters] = useState(DEFAULT_AUDIT_FILTERS);
  const [error, setError] = useState<string | null>(null);
  const [integrity, setIntegrity] = useState<{ status: string; verified: number; tampered_count: number } | null>(null);

  const buildParams = useCallback((source: typeof DEFAULT_AUDIT_FILTERS) => {
    const p = new URLSearchParams();
    if (source.event_type) p.set("event_type", source.event_type);
    if (source.target_type) p.set("target_type", source.target_type);
    if (source.module) p.set("module", source.module);
    p.set("limit", source.limit);
    return p.toString();
  }, []);

  const load = useCallback(async (source: typeof DEFAULT_AUDIT_FILTERS) => {
    setLoading(true);
    setError(null);
    try {
      const [logRes, statRes] = await Promise.all([
        fetch(`/api/v1/audit/?${buildParams(source)}`),
        fetch("/api/v1/audit/stats?days=30"),
      ]);
      if (!logRes.ok) throw new Error(await logRes.text());
      setLogs(await logRes.json());
      if (statRes.ok) setStats(await statRes.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  const runIntegrityCheck = async () => {
    const r = await fetch("/api/v1/audit/integrity-check?limit=1000");
    if (r.ok) setIntegrity(await r.json());
  };

  const exportCsv = () => {
    window.open(`/api/v1/audit/export?${buildParams(filters)}`, "_blank");
  };

  useEffect(() => { load(DEFAULT_AUDIT_FILTERS); }, [load]);

  const fmtDt = (iso: string) =>
    new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance Audit Trail</h1>
          <p className="text-sm text-gray-500 mt-0.5">Immutable event log with before/after tracking and tamper detection</p>
        </div>
        <div className="flex gap-2">
          <button onClick={runIntegrityCheck}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
            Integrity Check
          </button>
          <button onClick={exportCsv}
            className="border border-green-300 bg-green-50 rounded px-3 py-1.5 text-sm text-green-700 hover:bg-green-100">
            Export CSV
          </button>
          <button onClick={() => load(filters)} disabled={loading}
            className="border border-blue-300 bg-blue-50 rounded px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-100 disabled:opacity-50">
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {/* Integrity check result */}
      {integrity && (
        <div className={`border rounded-lg p-4 ${integrity.status === "CLEAN" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-300"}`}>
          <div className="flex items-center gap-3">
            <span className={`text-sm font-bold ${integrity.status === "CLEAN" ? "text-green-700" : "text-red-700"}`}>
              {integrity.status === "CLEAN" ? "✓ Integrity OK" : "⚠ Integrity Violation Detected"}
            </span>
            <span className="text-xs text-gray-600">
              {integrity.verified} rows verified · {integrity.tampered_count} tampered
            </span>
          </div>
        </div>
      )}

      {/* Stats strip */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Events (30d)", value: stats.total_events, color: "text-gray-800" },
            { label: "Security Alerts", value: stats.security_alerts, color: "text-red-600" },
            { label: "Event Types", value: Object.keys(stats.by_event_type).length, color: "text-blue-600" },
            { label: "Active Modules", value: Object.keys(stats.by_module).length, color: "text-green-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white border rounded-lg p-3 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white border rounded-lg p-3 shadow-sm">
        {[
          { label: "Event Type", key: "event_type", placeholder: "e.g. LOGIN_FAILED" },
          { label: "Target Type", key: "target_type", placeholder: "e.g. user" },
          { label: "Module", key: "module", placeholder: "e.g. finance" },
        ].map(({ label, key, placeholder }) => (
          <div key={key}>
            <label className="text-xs text-gray-500 block mb-1">{label}</label>
            <input
              type="text"
              placeholder={placeholder}
              value={(filters as Record<string, string>)[key]}
              onChange={(e) => setFilters((p) => ({ ...p, [key]: e.target.value }))}
              className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        ))}
        <div>
          <label className="text-xs text-gray-500 block mb-1">Limit</label>
          <select value={filters.limit} onChange={(e) => setFilters((p) => ({ ...p, limit: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none">
            <option value="100">100</option>
            <option value="200">200</option>
            <option value="500">500</option>
            <option value="1000">1000</option>
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={() => load(filters)} className="bg-blue-600 text-white text-xs px-3 py-1 rounded hover:bg-blue-700">
            Apply
          </button>
        </div>
      </div>

      {/* Log table */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">
            Audit Events
            <span className="ml-2 font-normal text-gray-400">{logs.length} records</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-gray-400 text-center">Loading…</div>
        ) : logs.length === 0 ? (
          <div className="p-6 text-sm text-gray-400 text-center">No audit events found.</div>
        ) : (
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {logs.map((lg) => (
              <div key={lg.id}>
                <div
                  className="px-4 py-3 flex items-center gap-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpanded(expanded === lg.id ? null : lg.id)}
                >
                  <div className="shrink-0 w-[130px]">
                    <p className="text-xs text-gray-400">{fmtDt(lg.created_at)}</p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs font-medium rounded-full px-2 py-0.5 ${EVENT_COLOR[lg.event_type] ?? "bg-gray-100 text-gray-600"}`}>
                        {lg.event_type}
                      </span>
                      {lg.module && <span className="text-xs text-gray-400">{lg.module}</span>}
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5 truncate">
                      {lg.actor_email ?? "—"} → {lg.target_type ?? ""} {lg.target_name ?? lg.target_id ?? ""}
                    </p>
                  </div>
                  <div className="text-xs text-gray-400 shrink-0">{lg.ip_address ?? ""}</div>
                  <div className="text-xs text-gray-300 shrink-0">
                    {lg.before_value || lg.after_value ? "Δ" : ""}
                  </div>
                </div>

                {expanded === lg.id && (
                  <div className="px-4 pb-4 bg-gray-50 border-t space-y-3">
                    {/* Before/After diff */}
                    {(lg.before_value || lg.after_value) && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-2">Change Diff</p>
                        <div className="grid grid-cols-3 gap-2 mb-1">
                          <span className="text-xs text-gray-400">Field</span>
                          <span className="text-xs text-red-500">Before</span>
                          <span className="text-xs text-green-600">After</span>
                        </div>
                        <DiffView before={lg.before_value} after={lg.after_value} />
                      </div>
                    )}
                    {/* Details */}
                    {lg.details && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Details</p>
                        <pre className="text-xs text-gray-600 bg-white rounded border p-2 overflow-auto max-h-32">
                          {JSON.stringify(lg.details, null, 2)}
                        </pre>
                      </div>
                    )}
                    {/* Meta */}
                    <div className="flex flex-wrap gap-4 text-xs text-gray-400">
                      <span>ID: {lg.id}</span>
                      {lg.session_id && <span>Session: {lg.session_id}</span>}
                      {lg.row_hash && <span>Hash: {lg.row_hash.slice(0, 16)}…</span>}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
