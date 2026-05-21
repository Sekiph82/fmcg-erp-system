"use client";
import { useState, useEffect } from "react";
import { plApi, PLHeader, PL_TYPE_COLORS } from "@/lib/price_list";

export default function ApprovalQueue() {
  const [pending, setPending] = useState<PLHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    plApi.pendingApproval().then(setPending).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const act = async (id: string, action: "APPROVED" | "REJECTED") => {
    if (!reviewer) { alert("Enter reviewer name"); return; }
    setSaving(true);
    await plApi.reviewApproval(id, action, reviewer, notes);
    setReviewId(null);
    setReviewer("");
    setNotes("");
    setSaving(false);
    load();
  };

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Price List Approval Queue</h1>
        <p className="text-sm text-gray-500 mt-1">{pending.length} price list{pending.length !== 1 ? "s" : ""} awaiting approval</p>
      </div>

      {pending.length === 0 && !loading && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center text-green-800">
          All clear — no price lists pending approval.
        </div>
      )}

      <div className="space-y-4">
        {pending.map((hdr) => (
          <div key={hdr.id} className="bg-white rounded-xl border border-yellow-300 p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-gray-900">{hdr.price_list_name}</span>
                  <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-600">{hdr.price_list_code}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_TYPE_COLORS[hdr.pl_type]}`}>{hdr.pl_type.replace(/_/g, " ")}</span>
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  {hdr.currency} · {hdr.valid_from} → {hdr.valid_to || "open"} · Priority {hdr.priority_rank}
                  {hdr.minimum_margin_pct && ` · Min margin ${hdr.minimum_margin_pct}%`}
                </div>
                {hdr.created_by && <div className="text-xs text-gray-400 mt-0.5">Submitted by: {hdr.created_by}</div>}
                {hdr.notes && <div className="text-xs text-gray-500 mt-1 italic">{hdr.notes}</div>}
              </div>
              <div className="flex gap-2">
                <a href={`/dashboard/price-lists/${hdr.id}`} className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs text-gray-700 hover:bg-gray-50">Review Details</a>
                <button onClick={() => setReviewId(hdr.id)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium">
                  Approve / Reject
                </button>
              </div>
            </div>

            {reviewId === hdr.id && (
              <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
                <div>
                  <label className="text-xs font-medium text-gray-700">Reviewer Name</label>
                  <input value={reviewer} onChange={(e) => setReviewer(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Your name" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700">Notes (optional)</label>
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
                    rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div className="flex gap-3">
                  <button onClick={() => act(hdr.id, "APPROVED")} disabled={saving}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium">Approve</button>
                  <button onClick={() => act(hdr.id, "REJECTED")} disabled={saving}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium">Reject</button>
                  <button onClick={() => setReviewId(null)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
