"use client";
import { useEffect, useState } from "react";

interface Issuance {
  id: string;
  issuance_ref: string;
  customer_id: string;
  customer_name: string | null;
  container_type: string;
  qty_issued: number;
  qty_returned: number;
  qty_outstanding: number;
  deposit_charged: number;
  deposit_refunded: number;
  status: string;
  return_due_date: string | null;
  is_overdue: boolean;
  days_overdue: number;
  issued_at: string;
  notes: string | null;
}

const STATUS_COLOR: Record<string, string> = {
  OUTSTANDING: "bg-blue-100 text-blue-700",
  PARTIALLY_RETURNED: "bg-amber-100 text-amber-700",
  CLOSED: "bg-green-100 text-green-700",
  WRITTEN_OFF: "bg-red-100 text-red-600",
  OVERDUE: "bg-red-200 text-red-800",
};

interface ReturnForm {
  qty_returned: string;
  condition: string;
  notes: string;
  recorded_by: string;
}

export default function OutstandingContainersPage() {
  const [items, setItems] = useState<Issuance[]>([]);
  const [loading, setLoading] = useState(true);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [returnForm, setReturnForm] = useState<Record<string, ReturnForm>>({});
  const [returning, setReturning] = useState<string | null>(null);
  const [writingOff, setWritingOff] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "200" });
    if (overdueOnly) params.set("overdue_only", "true");
    else params.set("status", "OUTSTANDING");

    fetch(`/api/v1/containers/issuances?${params}`)
      .then((r) => r.json())
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [overdueOnly]);

  const initReturn = (id: string) => {
    setReturnForm((p) => ({ ...p, [id]: { qty_returned: "1", condition: "GOOD", notes: "", recorded_by: "" } }));
  };

  const submitReturn = async (issuanceId: string) => {
    const f = returnForm[issuanceId];
    if (!f) return;
    setReturning(issuanceId);
    setError(null);
    try {
      const r = await fetch("/api/v1/containers/return", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          issuance_id: issuanceId,
          qty_returned: Number(f.qty_returned),
          condition: f.condition,
          notes: f.notes || undefined,
          recorded_by: f.recorded_by || undefined,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setReturnForm((p) => { const n = { ...p }; delete n[issuanceId]; return n; });
      load();
    } catch (e) { setError(String(e)); }
    finally { setReturning(null); }
  };

  const writeOff = async (issuanceId: string) => {
    if (!confirm("Write off remaining outstanding containers for this issuance?")) return;
    setWritingOff(issuanceId);
    try {
      await fetch("/api/v1/containers/write-off", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ issuance_id: issuanceId, notes: "Written off from UI" }),
      });
      load();
    } finally { setWritingOff(null); }
  };

  const overdueCount = items.filter((i) => i.is_overdue).length;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Outstanding Containers</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {items.length} records · {overdueCount} overdue
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={overdueOnly} onChange={(e) => setOverdueOnly(e.target.checked)} className="h-3.5 w-3.5" />
            Overdue only
          </label>
          <button onClick={load} disabled={loading}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-700 font-semibold">All clear</p>
          <p className="text-green-600 text-sm mt-1">No outstanding containers.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const rf = returnForm[item.id];
            return (
              <div key={item.id} className={`bg-white border rounded-lg shadow-sm ${item.is_overdue ? "border-red-300" : ""}`}>
                <div className="px-4 py-3 flex items-start gap-4">
                  {item.is_overdue && (
                    <div className="shrink-0 bg-red-500 text-white text-xs font-bold rounded px-2 py-1 mt-0.5">
                      {item.days_overdue}d overdue
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-blue-600 font-medium">{item.issuance_ref}</span>
                      <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${STATUS_COLOR[item.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mt-0.5">{item.customer_name || item.customer_id}</p>
                    <div className="text-xs text-gray-500 mt-0.5 flex gap-4 flex-wrap">
                      <span>{item.container_type}</span>
                      <span>Issued: {item.qty_issued} · Returned: {item.qty_returned} · Outstanding: <strong>{item.qty_outstanding}</strong></span>
                      {item.return_due_date && <span>Due: {item.return_due_date}</span>}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      Deposit: KES {item.deposit_charged.toLocaleString()} charged · {item.deposit_refunded.toLocaleString()} refunded
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {!rf && item.qty_outstanding > 0 && (
                      <button onClick={() => initReturn(item.id)}
                        className="text-xs text-blue-600 hover:text-blue-800 border border-blue-300 rounded px-2 py-1">
                        Record Return
                      </button>
                    )}
                    {item.qty_outstanding > 0 && (
                      <button onClick={() => writeOff(item.id)} disabled={writingOff === item.id}
                        className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded px-2 py-1 disabled:opacity-50">
                        {writingOff === item.id ? "…" : "Write Off"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Return form */}
                {rf && (
                  <div className="px-4 pb-4 border-t bg-gray-50">
                    <div className="flex items-center gap-3 flex-wrap pt-3">
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">Qty Returned</label>
                        <input type="number" min={1} max={item.qty_outstanding} value={rf.qty_returned}
                          onChange={(e) => setReturnForm((p) => ({ ...p, [item.id]: { ...rf, qty_returned: e.target.value } }))}
                          className="border border-gray-300 rounded px-2 py-1 text-sm w-20 focus:outline-none" />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">Condition</label>
                        <select value={rf.condition}
                          onChange={(e) => setReturnForm((p) => ({ ...p, [item.id]: { ...rf, condition: e.target.value } }))}
                          className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none">
                          <option value="GOOD">Good</option>
                          <option value="DAMAGED">Damaged</option>
                          <option value="LOST">Lost</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">Notes</label>
                        <input type="text" value={rf.notes} placeholder="Optional"
                          onChange={(e) => setReturnForm((p) => ({ ...p, [item.id]: { ...rf, notes: e.target.value } }))}
                          className="border border-gray-300 rounded px-2 py-1 text-sm w-40 focus:outline-none" />
                      </div>
                      <div className="flex items-end gap-2">
                        <button onClick={() => submitReturn(item.id)} disabled={returning === item.id}
                          className="bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1.5 rounded disabled:opacity-50">
                          {returning === item.id ? "Saving…" : "Confirm Return"}
                        </button>
                        <button onClick={() => setReturnForm((p) => { const n = { ...p }; delete n[item.id]; return n; })}
                          className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
