"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { imApi, MATCH_STATUS_COLOR, MatchHeaderSummary } from "@/lib/invoice_match";
import { tx } from "@/lib/i18n/core";

export default function ReviewQueuePage() {
  const qc = useQueryClient();
  const [justification, setJustification] = useState("");
  const [actionTarget, setActionTarget] = useState<string | null>(null);

  const { data = [], isLoading } = useQuery<MatchHeaderSummary[]>({
    queryKey: ["im-review-queue"],
    queryFn: () => imApi.list({ review_required: true }),
  });

  const approve = useMutation({
    mutationFn: (match: MatchHeaderSummary) => imApi.approveException(match.id, match.run_at ?? "", justification),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["im-review-queue"] }); setActionTarget(null); },
  });

  const reject = useMutation({
    mutationFn: (match: MatchHeaderSummary) => imApi.reject(match.id, match.run_at ?? "", justification),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["im-review-queue"] }); setActionTarget(null); },
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Mismatch Review Queue")}</h1>
          <p className="text-sm text-gray-500 mt-1">{tx("Invoices requiring human review before payment")}</p>
        </div>
        <span className="text-lg font-bold text-yellow-600">{data.length} {tx("pending")}</span>
      </div>

      {/* Review justification */}
      <div className="bg-white border rounded-xl p-4 flex gap-3 items-end flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">{tx("Justification")}</label>
          <input className="border rounded-lg px-3 py-1.5 text-sm w-72"
            placeholder={tx("Reason for approval/rejection")}
            value={justification} onChange={(e) => setJustification(e.target.value)} />
        </div>
      </div>

      {/* Queue */}
      {isLoading ? (
        <p className="text-gray-400">{tx("Loading…")}</p>
      ) : data.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <p className="text-green-700 font-medium">{tx("✓ Review queue is empty — all invoices are matched or resolved.")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((m) => (
            <div key={m.id} className="bg-white border rounded-xl p-5 space-y-3">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium">{m.match_no}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${MATCH_STATUS_COLOR[m.overall_status]}`}>
                      {m.overall_status.replace(/_/g, " ")}
                    </span>
                    {m.duplicate_flag && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-700">{tx("⚠ Duplicate")}</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {tx("Invoice:")} {m.invoice_no ?? "—"} {tx("· Date:")} {m.invoice_date ?? "—"} {tx("· Total:")} {Number(m.invoice_total).toLocaleString(undefined, { minimumFractionDigits: 2 })} {m.currency}
                  </p>
                  {m.payment_hold_reason && (
                    <p className="text-xs text-red-600 mt-1">{tx("Hold:")} {m.payment_hold_reason}</p>
                  )}
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Link href={`/dashboard/invoice-match/${m.id}`}
                    className="px-3 py-1.5 text-xs border rounded-lg hover:bg-gray-50">
                    {tx("View Detail")}
                  </Link>
                  <button
                    onClick={() => { setActionTarget(m.id); approve.mutate(m); }}
                    disabled={!m.run_at || approve.isPending}
                    className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    {approve.isPending && actionTarget === m.id ? "…" : tx("Approve Exception")}
                  </button>
                  <button
                    onClick={() => { setActionTarget(m.id); reject.mutate(m); }}
                    disabled={!m.run_at || reject.isPending}
                    className="px-3 py-1.5 text-xs border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                  >
                    {reject.isPending && actionTarget === m.id ? "…" : tx("Reject")}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
