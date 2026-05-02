"use client";

import { useEffect, useState } from "react";
import { listDeadLetter, replayEvents, retryDelivery, DeliveryAttempt, STATUS_BADGE } from "@/lib/webhooks";
import { Button } from "@/components/ui/Button";

export default function DeadLetterPage() {
  const [items, setItems] = useState<DeliveryAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [retrying, setRetrying] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => { load(); }, []);
  async function load() {
    setLoading(true);
    try { setItems(await listDeadLetter(200)); } catch {}
    setLoading(false);
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleRetrySelected() {
    setRetrying(true);
    try {
      for (const id of Array.from(selected)) {
        await retryDelivery(id);
      }
      setMsg(`Retried ${selected.size} item(s)`);
      setSelected(new Set());
      await load();
    } catch { setMsg("Retry failed"); }
    setRetrying(false);
  }

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dead-Letter Queue</h1>
          <p className="text-sm text-gray-500 mt-1">{items.length} undeliverable event(s)</p>
        </div>
        {selected.size > 0 && (
          <Button onClick={handleRetrySelected} loading={retrying}>
            Retry Selected ({selected.size})
          </Button>
        )}
      </div>

      {msg && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 text-sm rounded-lg px-4 py-2">{msg}</div>
      )}

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-4xl mb-2">✓</div>
          <div>Dead-letter queue is empty</div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3">
                  <input type="checkbox" onChange={(e) => {
                    if (e.target.checked) setSelected(new Set(items.map((i) => i.id)));
                    else setSelected(new Set());
                  }} />
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Delivery ID</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Attempts</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">HTTP Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Error</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Last Attempt</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item) => (
                <tr key={item.id} className={`hover:bg-gray-50 ${selected.has(item.id) ? "bg-amber-50" : ""}`}>
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={selected.has(item.id)} onChange={() => toggleSelect(item.id)} />
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs text-gray-600">{item.id.slice(0, 8)}...</code>
                  </td>
                  <td className="px-4 py-3 text-gray-600">#{item.attempt_no}</td>
                  <td className="px-4 py-3">
                    {item.response_status ? (
                      <span className="font-mono font-bold text-red-700">{item.response_status}</span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-red-600 text-xs max-w-xs truncate">
                    {item.error_message || item.response_body?.slice(0, 80) || "Unknown error"}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {item.attempted_at ? new Date(item.attempted_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => retryDelivery(item.id).then(() => load())} className="text-xs text-indigo-600 hover:underline">
                      Retry
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
