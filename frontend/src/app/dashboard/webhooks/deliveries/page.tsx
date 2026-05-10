"use client";

import { useCallback, useEffect, useState } from "react";
import { listDeliveries, DeliveryAttempt, DeliveryStatus, STATUS_BADGE, retryDelivery } from "@/lib/webhooks";

const STATUSES: DeliveryStatus[] = ["pending", "sent", "failed", "retrying", "dead_letter"];

export default function DeliveriesPage() {
  const [deliveries, setDeliveries] = useState<DeliveryAttempt[]>([]);
  const [statusFilter, setStatusFilter] = useState<DeliveryStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDeliveries(await listDeliveries({
        delivery_status: statusFilter === "all" ? undefined : statusFilter,
        limit: 200,
      }));
    } catch {}
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  async function handleRetry(id: string) {
    setRetrying(id);
    try { await retryDelivery(id); await load(); } catch {}
    setRetrying(null);
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Delivery Attempts</h1>
          <p className="text-sm text-gray-500 mt-1">{deliveries.length} record(s)</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setStatusFilter("all")} className={`text-sm px-3 py-1.5 rounded-lg ${statusFilter === "all" ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
            All
          </button>
          {STATUSES.map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`text-sm px-3 py-1.5 rounded-lg capitalize ${statusFilter === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-gray-500 py-8 text-center">Loading...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Attempt</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">HTTP</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Duration</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Error</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Time</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {deliveries.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${STATUS_BADGE[d.status]}`}>
                      {d.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">#{d.attempt_no}</td>
                  <td className="px-4 py-3">
                    {d.response_status ? (
                      <span className={`text-xs font-mono font-bold ${d.response_status < 300 ? "text-green-700" : "text-red-700"}`}>
                        {d.response_status}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{d.duration_ms ? `${d.duration_ms}ms` : "—"}</td>
                  <td className="px-4 py-3 text-red-600 text-xs max-w-xs truncate">{d.error_message || "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {d.attempted_at ? new Date(d.attempted_at).toLocaleString() : new Date(d.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    {(d.status === "failed" || d.status === "dead_letter") && (
                      <button
                        onClick={() => handleRetry(d.id)}
                        disabled={retrying === d.id}
                        className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                      >
                        {retrying === d.id ? "..." : "Retry"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {deliveries.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No delivery records</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
