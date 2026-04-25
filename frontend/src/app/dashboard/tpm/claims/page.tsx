"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tpmApi, TPMClaim, TPMClaimStatus, fmtCurrency, CLAIM_STATUS_BADGE } from "@/lib/tpm";
import Link from "next/link";

export default function TPMClaimsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TPMClaimStatus | "">("");
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [approvedAmounts, setApprovedAmounts] = useState<Record<string, string>>({});
  const [settleAmounts, setSettleAmounts] = useState<Record<string, string>>({});

  const { data: claims = [], isLoading } = useQuery({
    queryKey: ["tpm-claims", statusFilter],
    queryFn: () => tpmApi.getClaims({ status: statusFilter || undefined }),
  });

  const review = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) =>
      tpmApi.reviewClaim(id, {
        approved,
        approved_amount: approved ? Number(approvedAmounts[id]) || undefined : undefined,
        reviewer_notes: reviewNotes[id],
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-claims"] }),
  });

  const settle = useMutation({
    mutationFn: (id: string) =>
      tpmApi.settleClaim(id, { settle_amount: Number(settleAmounts[id]) || 0 }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-claims"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Claim & Deduction Queue</h1>
          <p className="text-sm text-gray-500">Review, approve, and settle trade promotion claims.</p>
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TPMClaimStatus | "")}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {(["DRAFT","SUBMITTED","UNDER_REVIEW","APPROVED","PARTIALLY_SETTLED","SETTLED","REJECTED","CANCELLED"] as TPMClaimStatus[]).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="text-gray-400 text-center py-10">Loading…</div>
        ) : claims.length === 0 ? (
          <div className="liquid-glass p-8 text-center text-gray-400">No claims found.</div>
        ) : claims.map((c: TPMClaim) => (
          <div key={c.id} className="liquid-glass p-5 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs text-indigo-300">{c.claim_no}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CLAIM_STATUS_BADGE[c.status]}`}>{c.status.replace(/_/g, " ")}</span>
                  <span className="text-xs text-gray-400">{c.claim_type.replace(/_/g, " ")}</span>
                  <span className="text-xs text-gray-500">· {c.claimant_type}</span>
                </div>
                <div className="flex gap-4 text-xs text-gray-400">
                  <span>Claimed: <span className="text-orange-400 font-bold">{fmtCurrency(c.claimed_amount)}</span></span>
                  {c.approved_amount > 0 && <span>Approved: <span className="text-green-400 font-bold">{fmtCurrency(c.approved_amount)}</span></span>}
                  {c.settled_amount > 0 && <span>Settled: <span className="text-teal-400 font-bold">{fmtCurrency(c.settled_amount)}</span></span>}
                </div>
                <p className="text-xs text-gray-500">Date: {c.claim_date} · Ref: {c.reference_document_no || "—"}</p>
                {c.reviewer_notes && <p className="text-xs text-gray-400 italic">Reviewer: {c.reviewer_notes}</p>}
                {c.notes && <p className="text-xs text-gray-500">{c.notes}</p>}
              </div>
              <div className="text-right text-xs text-gray-500">
                {c.rejected_amount > 0 && <p className="text-red-400">Rejected: {fmtCurrency(c.rejected_amount)}</p>}
              </div>
            </div>

            {/* Review actions */}
            {(c.status === "SUBMITTED" || c.status === "UNDER_REVIEW") && (
              <div className="space-y-2 border-t border-blue-900/20 pt-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500">Approved Amount (leave blank = full)</label>
                    <input type="number" value={approvedAmounts[c.id] ?? ""}
                      onChange={(e) => setApprovedAmounts(a => ({ ...a, [c.id]: e.target.value }))}
                      placeholder={String(c.claimed_amount)}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500">Reviewer Notes</label>
                    <input type="text" value={reviewNotes[c.id] ?? ""}
                      onChange={(e) => setReviewNotes(n => ({ ...n, [c.id]: e.target.value }))}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => review.mutate({ id: c.id, approved: true })}
                    disabled={review.isPending} className="glow-button text-xs !py-1">Approve</button>
                  <button onClick={() => review.mutate({ id: c.id, approved: false })}
                    disabled={review.isPending} className="text-xs text-red-400 border border-red-200 rounded px-3 py-1">Reject</button>
                </div>
              </div>
            )}

            {/* Settle actions */}
            {(c.status === "APPROVED" || c.status === "PARTIALLY_SETTLED") && (
              <div className="space-y-2 border-t border-blue-900/20 pt-3">
                <div className="flex gap-3 items-end">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500">Settlement Amount</label>
                    <input type="number" value={settleAmounts[c.id] ?? ""}
                      onChange={(e) => setSettleAmounts(a => ({ ...a, [c.id]: e.target.value }))}
                      placeholder={String(c.approved_amount - c.settled_amount)}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm w-48" />
                  </div>
                  <button onClick={() => settle.mutate(c.id)}
                    disabled={settle.isPending || !settleAmounts[c.id]}
                    className="glow-button text-xs !py-2">
                    {settle.isPending ? "Settling…" : "Record Settlement"}
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
