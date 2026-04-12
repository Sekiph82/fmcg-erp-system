"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  integrationsApi,
  IntegrationLog,
  IntegrationProvider,
  IntegrationLogStatus,
} from "@/lib/integrations";

const PROVIDERS: (IntegrationProvider | "")[] = [
  "", "MPESA", "CRM", "SHOPIFY", "WOOCOMMERCE", "BARCODE", "IOT", "GENERIC",
];
const STATUSES: (IntegrationLogStatus | "")[] = ["", "SUCCESS", "FAILED", "PENDING", "RETRYING"];

const STATUS_CFG: Record<string, string> = {
  SUCCESS: "bg-emerald-100 text-emerald-800",
  FAILED: "bg-red-100 text-red-800",
  PENDING: "bg-amber-100 text-amber-800",
  RETRYING: "bg-blue-100 text-blue-700",
};

const PROVIDER_ICONS: Record<string, string> = {
  MPESA: "📱", CRM: "👥", SHOPIFY: "🛒", WOOCOMMERCE: "🛍️",
  BARCODE: "📷", IOT: "🏭", GENERIC: "🔌",
};

function LogDetailModal({ log, onClose }: { log: IntegrationLog; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center p-4 pt-16 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Log Detail</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ["Provider", log.provider],
            ["Type", log.integration_type],
            ["Endpoint", log.endpoint ?? "—"],
            ["Status", log.status],
            ["HTTP", log.http_status ?? "—"],
            ["Duration", log.duration_ms ? `${log.duration_ms}ms` : "—"],
            ["Time", new Date(log.created_at).toLocaleString()],
            ["Error", log.error_message ?? "none"],
          ].map(([k, v]) => (
            <div key={k}>
              <p className="text-xs text-gray-500 font-medium">{k}</p>
              <p className="text-gray-900 font-mono text-xs break-all">{String(v)}</p>
            </div>
          ))}
        </div>

        {log.request_payload && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Request Payload</p>
            <pre className="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto text-gray-800 max-h-40">
              {(() => { try { return JSON.stringify(JSON.parse(log.request_payload!), null, 2); } catch { return log.request_payload; } })()}
            </pre>
          </div>
        )}

        {log.response_payload && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Response Payload</p>
            <pre className="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto text-gray-800 max-h-40">
              {(() => { try { return JSON.stringify(JSON.parse(log.response_payload!), null, 2); } catch { return log.response_payload; } })()}
            </pre>
          </div>
        )}

        <button
          onClick={onClose}
          className="w-full px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200"
        >
          Close
        </button>
      </div>
    </div>
  );
}

export default function IntegrationLogsPage() {
  const [provider, setProvider] = useState<IntegrationProvider | "">("");
  const [status, setStatus] = useState<IntegrationLogStatus | "">("");
  const [selectedLog, setSelectedLog] = useState<IntegrationLog | null>(null);

  const { data: logs = [], isLoading, refetch } = useQuery({
    queryKey: ["integration-logs", provider, status],
    queryFn: () =>
      integrationsApi.listLogs({
        provider: provider || undefined,
        status: status || undefined,
        limit: 100,
      }),
    refetchInterval: 60_000,
  });

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {selectedLog && (
        <LogDetailModal log={selectedLog} onClose={() => setSelectedLog(null)} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📋 Integration Logs</h1>
          <p className="text-gray-500 text-sm mt-0.5">Audit trail of all external API calls</p>
        </div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 bg-white border border-gray-200 rounded-xl p-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Provider</label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as IntegrationProvider | "")}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {p || "All Providers"}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as IntegrationLogStatus | "")}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s || "All Statuses"}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <span className="text-sm text-gray-500">{logs.length} records</span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading logs...</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No logs found for selected filters</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["Provider", "Type", "Endpoint", "Status", "HTTP", "Duration", "Time", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.map((log: IntegrationLog) => (
                  <tr
                    key={log.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="px-4 py-3">
                      <span className="mr-1">{PROVIDER_ICONS[log.provider] ?? "🔌"}</span>
                      <span className="text-xs font-medium text-gray-700">{log.provider}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{log.integration_type}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                      {log.endpoint ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_CFG[log.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{log.http_status ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {log.duration_ms ? `${log.duration_ms}ms` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      {log.status === "FAILED" && log.error_message && (
                        <span className="text-xs text-red-500 max-w-xs truncate block">
                          {log.error_message.slice(0, 40)}...
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
