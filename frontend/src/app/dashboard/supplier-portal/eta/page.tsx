"use client";
import { useCallback, useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { spApi, SPETALog, SPETAStatus } from "@/lib/supplier_portal";

const ETA_STATUS_COLORS: Record<SPETAStatus, string> = {
  ORIGINAL: "bg-gray-100 text-gray-700",
  REVISED: "bg-yellow-100 text-yellow-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
};

function ETAContent() {
  const sp = useSearchParams();
  const accountId = sp.get("account") || "";
  const [history, setHistory] = useState<SPETALog[]>([]);
  const [poId, setPoId] = useState(sp.get("po") || "");
  const [loading, setLoading] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [form, setForm] = useState({ po_id: poId, proposed_date: "", supplier_reason: "" });
  const [reviewing, setReviewing] = useState<SPETALog | null>(null);
  const [reviewForm, setReviewForm] = useState({ eta_status: "APPROVED", buyer_notes: "", reviewed_by: "" });

  const loadHistory = useCallback(() => {
    if (!accountId || !poId) return;
    setLoading(true);
    spApi.getETAHistory(accountId, poId).then(setHistory).finally(() => setLoading(false));
  }, [accountId, poId]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const propose = async () => {
    await spApi.proposeETA(accountId, { po_id: form.po_id, proposed_date: form.proposed_date, supplier_reason: form.supplier_reason || undefined });
    setProposing(false);
    setPoId(form.po_id);
    loadHistory();
  };

  const review = async () => {
    if (!reviewing) return;
    await spApi.reviewETA(reviewing.id, reviewForm as any);
    setReviewing(null);
    loadHistory();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Delivery ETA Management</h1>
        <button onClick={() => setProposing(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + Propose ETA
        </button>
      </div>

      <div className="flex gap-3">
        <input value={poId} onChange={(e) => setPoId(e.target.value)} placeholder="Enter PO ID to view history…"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-72" />
        <button onClick={loadHistory} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm">Load</button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["PO ID", "Rev #", "Proposed Date", "Original Date", "Reason", "Status", "Buyer Notes", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : history.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No ETA history found. Enter a PO ID above.</td></tr>
            ) : history.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{e.po_id.slice(0, 8)}…</td>
                <td className="px-4 py-3 font-medium">Rev {e.revision_no}</td>
                <td className="px-4 py-3 font-medium text-blue-700">{e.proposed_date}</td>
                <td className="px-4 py-3 text-gray-500">{e.original_date || "—"}</td>
                <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{e.supplier_reason || "—"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ETA_STATUS_COLORS[e.eta_status]}`}>{e.eta_status}</span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{e.buyer_notes || "—"}</td>
                <td className="px-4 py-3">
                  {e.eta_status === "REVISED" && (
                    <button onClick={() => setReviewing(e)} className="text-blue-600 hover:underline text-xs">Review</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {proposing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Propose Revised ETA</h2>
            <div>
              <label className="text-xs font-medium text-gray-700">PO ID</label>
              <input value={form.po_id} onChange={(e) => setForm({ ...form, po_id: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Proposed Date</label>
              <input type="date" value={form.proposed_date} onChange={(e) => setForm({ ...form, proposed_date: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Reason</label>
              <textarea value={form.supplier_reason} onChange={(e) => setForm({ ...form, supplier_reason: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setProposing(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={propose} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Submit</button>
            </div>
          </div>
        </div>
      )}

      {reviewing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Review ETA Revision #{reviewing.revision_no}</h2>
            <p className="text-sm text-gray-600">Supplier proposes: <strong>{reviewing.proposed_date}</strong></p>
            <div>
              <label className="text-xs font-medium text-gray-700">Decision</label>
              <select value={reviewForm.eta_status} onChange={(e) => setReviewForm({ ...reviewForm, eta_status: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="APPROVED">Approve</option>
                <option value="REJECTED">Reject</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Reviewer Name</label>
              <input value={reviewForm.reviewed_by} onChange={(e) => setReviewForm({ ...reviewForm, reviewed_by: e.target.value })}
                className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Buyer Notes</label>
              <textarea value={reviewForm.buyer_notes} onChange={(e) => setReviewForm({ ...reviewForm, buyer_notes: e.target.value })}
                rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setReviewing(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button onClick={review} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">Submit Review</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ETAPage() {
  return <Suspense fallback={<div className="p-6 text-gray-400">Loading…</div>}><ETAContent /></Suspense>;
}
