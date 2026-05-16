"use client";

import { useQuery } from "@tanstack/react-query";
import { aiApi, AILog } from "@/lib/aiApi";
import { RequirePermission } from "@/components/PermissionGuard";

const STATUS_PILL: Record<string, string> = {
  COMPLETED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
  PENDING: "bg-yellow-100 text-yellow-700",
  RUNNING: "bg-blue-100 text-blue-700",
};

export default function AILogsPage() {
  const { data = [], isLoading } = useQuery<AILog[]>({
    queryKey: ["ai-logs"],
    queryFn: () => aiApi.listLogs(100),
    refetchInterval: 15_000,
  });

  const totalTokens = data.reduce((s, l) => s + (l.prompt_tokens ?? 0) + (l.completion_tokens ?? 0), 0);
  const avgLatency = data.length > 0
    ? (data.reduce((s, l) => s + (l.latency_ms ?? 0), 0) / data.filter((l) => l.latency_ms).length).toFixed(0)
    : 0;
  const failCount = data.filter((l) => l.status === "FAILED").length;

  return (
    <RequirePermission permission="ai.view">
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Request Logs</h1>
        <p className="text-sm text-gray-500 mt-0.5">Audit trail of all AI API calls and responses</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Total Requests", value: data.length, color: "text-gray-900" },
          { label: "Total Tokens", value: totalTokens.toLocaleString(), color: "text-indigo-600" },
          { label: "Avg Latency", value: `${avgLatency} ms`, color: "text-teal-600" },
          { label: "Failed", value: failCount, color: failCount > 0 ? "text-red-600" : "text-gray-400" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">{s.label}</p>
            <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading logs…</p>
        ) : data.length === 0 ? (
          <p className="p-8 text-center text-gray-400">No AI requests logged yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Time</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Provider</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Model</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Prompt tkns</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Compl. tkns</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 font-medium text-gray-700 capitalize">
                      {log.request_type.toLowerCase().replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-2 text-gray-600 capitalize">{log.provider.toLowerCase()}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{log.model ?? "—"}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[log.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-gray-600">
                      {log.prompt_tokens?.toLocaleString() ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-gray-600">
                      {log.completion_tokens?.toLocaleString() ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-gray-600">
                      {log.latency_ms != null ? `${log.latency_ms}ms` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
    </RequirePermission>
  );
}
