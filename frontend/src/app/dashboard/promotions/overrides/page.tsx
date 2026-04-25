"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { promoApi, OverrideRequest, OverrideStatus } from "@/lib/promotions";

export default function OverridesPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<OverrideStatus | "">("");
  const [approverNotes, setApproverNotes] = useState<Record<string, string>>({});

  const { data: requests = [], isLoading } = useQuery({
    queryKey: ["promo-overrides", statusFilter],
    queryFn: () => promoApi.getOverrideRequests(statusFilter || undefined),
  });

  const approve = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) =>
      promoApi.approveOverride(id, { approved, approver_notes: approverNotes[id] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-overrides"] }),
  });

  const STATUS_COLORS: Record<OverrideStatus, string> = {
    PENDING:  "bg-yellow-100 text-yellow-700",
    APPROVED: "bg-green-100 text-green-700",
    REJECTED: "bg-red-100 text-red-700",
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Promotion Override Approval Queue</h1>
          <p className="text-sm text-gray-500">Review and approve requests for manual promotion exceptions.</p>
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as OverrideStatus | "")}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="text-gray-400 text-center py-10">Loading…</div>
        ) : requests.length === 0 ? (
          <div className="liquid-glass p-8 text-center text-gray-400">No override requests found.</div>
        ) : requests.map((req) => (
          <div key={req.id} className="liquid-glass p-5 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-indigo-300">Order: {req.sales_order_id.slice(0, 8)}…</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[req.status]}`}>
                    {req.status}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-200">{req.reason}</p>
                <div className="flex gap-4 text-xs text-gray-400">
                  {req.requested_discount_pct != null && <span>Discount: {req.requested_discount_pct}%</span>}
                  {req.requested_free_qty != null && <span>Free Qty: {req.requested_free_qty}</span>}
                </div>
                {req.approver_notes && (
                  <p className="text-xs text-gray-500">Approver: {req.approver_notes}</p>
                )}
              </div>
            </div>

            {req.status === "PENDING" && (
              <div className="space-y-2">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Approver Notes (optional)</label>
                  <input type="text" value={approverNotes[req.id] ?? ""}
                    onChange={(e) => setApproverNotes((n) => ({ ...n, [req.id]: e.target.value }))}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => approve.mutate({ id: req.id, approved: true })}
                    disabled={approve.isPending} className="glow-button text-xs !py-1">Approve</button>
                  <button onClick={() => approve.mutate({ id: req.id, approved: false })}
                    disabled={approve.isPending} className="text-xs text-red-400 hover:text-red-600 px-3 py-1 border border-red-200 rounded-lg">
                    Reject
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
