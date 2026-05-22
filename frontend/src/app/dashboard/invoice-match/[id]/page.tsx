"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  imApi, MATCH_STATUS_COLOR, LINE_STATUS_COLOR, MatchHeaderOut, varColor, fmtVar,
} from "@/lib/invoice_match";

export default function MatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const [reviewer, setReviewer] = useState("");
  const [justification, setJustification] = useState("");
  const [showReviewForm, setShowReviewForm] = useState(false);

  const { data: match, isLoading, error } = useQuery<MatchHeaderOut>({
    queryKey: ["im-match", id],
    queryFn: () => imApi.get(id),
    enabled: !!id,
  });

  const approve = useMutation({
    mutationFn: () => imApi.approveException(id, reviewer, justification),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["im-match", id] }); setShowReviewForm(false); },
  });

  const reject = useMutation({
    mutationFn: () => imApi.reject(id, reviewer, justification),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["im-match", id] }); setShowReviewForm(false); },
  });

  const runAI = useMutation({
    mutationFn: () => imApi.runAIForMatch(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["im-match", id] }),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading…</div>;
  if (error || !match) return <div className="p-8 text-red-500">Match record not found.</div>;

  const matchLines = match.match_lines ?? [];
  const reviews    = match.reviews     ?? [];

  const canReview = match.review_required && !["APPROVED_EXCEPTION", "REJECTED"].includes(match.overall_status);

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{match.match_no}</h1>
          <p className="text-sm text-gray-500">
            Invoice: {match.invoice_no ?? "—"} · {match.invoice_date ?? "—"} · {match.currency}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${MATCH_STATUS_COLOR[match.overall_status]}`}>
            {match.overall_status.replace(/_/g, " ")}
          </span>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${match.is_payable ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
            {match.is_payable ? "✓ Payable" : "✗ Payment Hold"}
          </span>
          {match.duplicate_flag && (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-700">⚠ Duplicate Suspected</span>
          )}
          <button onClick={() => runAI.mutate()} disabled={runAI.isPending}
            className="px-3 py-1.5 text-xs border rounded-lg text-purple-600 hover:bg-purple-50 disabled:opacity-50">
            {runAI.isPending ? "…" : "Run AI"}
          </button>
          {canReview && (
            <button onClick={() => setShowReviewForm((v) => !v)}
              className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Review / Approve
            </button>
          )}
        </div>
      </div>

      {/* Payment hold reason */}
      {match.payment_hold_reason && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          <span className="font-medium">Payment Hold: </span>{match.payment_hold_reason}
        </div>
      )}

      {/* Review form */}
      {showReviewForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <h2 className="font-semibold text-gray-700">Exception Review</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Your Name</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Justification</label>
              <input className="border rounded-lg px-3 py-2 text-sm w-full"
                value={justification} onChange={(e) => setJustification(e.target.value)} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => approve.mutate()} disabled={!reviewer || approve.isPending}
              className="px-4 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50">
              Approve Exception
            </button>
            <button onClick={() => reject.mutate()} disabled={!reviewer || reject.isPending}
              className="px-4 py-1.5 border border-red-400 text-red-600 text-sm rounded-lg hover:bg-red-50 disabled:opacity-50">
              Reject Invoice
            </button>
            <button onClick={() => setShowReviewForm(false)}
              className="px-3 py-1.5 border text-sm rounded-lg hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Line-by-line comparison */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700">Line Comparison ({matchLines.length} lines)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-max">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Item", "PO Qty", "PO Price", "Recv'd", "Accepted", "Prev Billed", "Billable", "Inv Qty", "Inv Price", "Qty Var%", "Price Var%", "Status"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {matchLines.map((ml) => (
                <tr key={ml.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-xs font-medium max-w-[140px] truncate">{ml.material_name || ml.description || "—"}</td>
                  <td className="px-3 py-2">{ml.ordered_qty ?? "—"}</td>
                  <td className="px-3 py-2">{ml.ordered_unit_price != null ? Number(ml.ordered_unit_price).toFixed(4) : "—"}</td>
                  <td className="px-3 py-2">{ml.total_received_qty ?? "—"}</td>
                  <td className="px-3 py-2">{ml.total_accepted_qty ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-500">{Number(ml.prev_invoiced_qty).toFixed(2)}</td>
                  <td className="px-3 py-2 font-medium">{ml.billable_qty != null ? Number(ml.billable_qty).toFixed(2) : "—"}</td>
                  <td className="px-3 py-2 font-medium">{ml.invoiced_qty != null ? Number(ml.invoiced_qty).toFixed(2) : "—"}</td>
                  <td className="px-3 py-2">{ml.invoiced_unit_price != null ? Number(ml.invoiced_unit_price).toFixed(4) : "—"}</td>
                  <td className={`px-3 py-2 font-medium ${varColor(ml.qty_variance_pct)}`}>
                    {fmtVar(ml.qty_variance_pct, "%")}
                  </td>
                  <td className={`px-3 py-2 font-medium ${varColor(ml.price_variance_pct)}`}>
                    {fmtVar(ml.price_variance_pct, "%")}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${LINE_STATUS_COLOR[ml.match_status]}`}>
                      {ml.match_status.replace(/_/g, " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* GRN links for each line */}
      {matchLines.filter((ml) => (ml.grn_links ?? []).length > 0).length > 0 && (
        <div className="bg-white border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">GRN Links</h2>
          {matchLines.filter((ml) => (ml.grn_links ?? []).length > 0).map((ml) => (
            <div key={ml.id}>
              <p className="text-xs font-medium text-gray-600 mb-1">{ml.material_name || "Line"}</p>
              <table className="w-full text-xs border rounded">
                <thead className="bg-gray-50">
                  <tr>
                    {["GRN No", "Received", "Accepted", "Rejected", "Date"].map((h) => (
                      <th key={h} className="px-3 py-1.5 text-left text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(ml.grn_links ?? []).map((g) => (
                    <tr key={g.id}>
                      <td className="px-3 py-1.5 font-mono">{g.grn_no ?? "—"}</td>
                      <td className="px-3 py-1.5">{g.received_qty ?? "—"}</td>
                      <td className="px-3 py-1.5 text-green-700 font-medium">{g.accepted_qty ?? "—"}</td>
                      <td className="px-3 py-1.5 text-red-600">{g.rejected_qty ?? "—"}</td>
                      <td className="px-3 py-1.5 text-gray-500">{g.received_date ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* Review history */}
      {reviews.length > 0 && (
        <div className="bg-white border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700">Review History</h2>
          </div>
          <div className="divide-y">
            {reviews.map((r) => (
              <div key={r.id} className="px-5 py-3 space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-700">{r.reviewer_name}</span>
                  {r.reviewer_role && <span className="text-xs text-gray-400">({r.reviewer_role})</span>}
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    r.action === "APPROVED_EXCEPTION" ? "bg-green-100 text-green-700" :
                    r.action === "REJECTED" ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-600"
                  }`}>{r.action}</span>
                  <span className="text-xs text-gray-400 ml-auto">{new Date(r.created_at).toLocaleString()}</span>
                </div>
                {r.justification && <p className="text-xs text-gray-500">{r.justification}</p>}
                {r.previous_status && r.new_status && (
                  <p className="text-xs text-gray-400">{r.previous_status} → {r.new_status}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
