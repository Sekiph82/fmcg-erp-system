"use client";
import { useEffect, useState } from "react";
import { mobileApi, MobileApprovalItem } from "@/lib/mobile_api";

const API_BASE = "/api/v1/approvals";

async function actionApproval(requestId: string, action: "approve" | "reject", comment: string) {
  const endpoint = action === "approve" ? `${API_BASE}/${requestId}/approve` : `${API_BASE}/${requestId}/reject`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function MobileApprovalsPage() {
  const [items, setItems] = useState<MobileApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [comment, setComment] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    mobileApi.getApprovals()
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handle = async (requestId: string, action: "approve" | "reject") => {
    setActing(requestId + action);
    setError(null);
    try {
      await actionApproval(requestId, action, comment[requestId] ?? "");
      setItems((prev) => prev.filter((i) => i.request_id !== requestId));
    } catch (e) {
      setError(String(e));
    } finally {
      setActing(null);
    }
  };

  const fmtAmt = (amt: number | null, cur: string) =>
    amt !== null ? `${cur} ${amt.toLocaleString()}` : "";

  const fmtDate = (iso: string) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  };

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Approval Inbox</h1>
        <button
          onClick={load}
          disabled={loading}
          className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading approvals…</p>
      ) : items.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-700 font-semibold">All clear</p>
          <p className="text-green-600 text-sm mt-1">No pending approvals in your inbox.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.request_id} className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-gray-900 text-sm leading-snug">{item.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {item.reference_type} · Requested by {item.requested_by}
                  </p>
                </div>
                {item.amount !== null && (
                  <span className="text-sm font-bold text-gray-800 shrink-0 bg-gray-100 rounded px-2 py-0.5">
                    {fmtAmt(item.amount, item.currency)}
                  </span>
                )}
              </div>

              <p className="text-xs text-gray-400">{fmtDate(item.created_at)}</p>

              {/* Comment input */}
              <input
                type="text"
                placeholder="Comment (optional)"
                value={comment[item.request_id] ?? ""}
                onChange={(e) =>
                  setComment((prev) => ({ ...prev, [item.request_id]: e.target.value }))
                }
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />

              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handle(item.request_id, "approve")}
                  disabled={acting !== null}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-2 rounded disabled:opacity-50"
                >
                  {acting === item.request_id + "approve" ? "Approving…" : "Approve"}
                </button>
                <button
                  onClick={() => handle(item.request_id, "reject")}
                  disabled={acting !== null}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm font-medium py-2 rounded disabled:opacity-50"
                >
                  {acting === item.request_id + "reject" ? "Rejecting…" : "Reject"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 text-center">
        {items.length} pending · Mobile Approvals View
      </p>
    </div>
  );
}
