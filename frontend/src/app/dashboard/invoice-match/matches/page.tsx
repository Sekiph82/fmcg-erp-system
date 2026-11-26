"use client";
import { EntityPicker } from "@/components/EntityPicker";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { imApi, MATCH_STATUS_COLOR, MatchHeaderSummary, MatchOverallStatus } from "@/lib/invoice_match";
import { tx, lx } from "@/lib/i18n/core";

const STATUSES: { value: MatchOverallStatus | ""; label: string }[] = lx(() => [
  { value: "", label: tx("All") },
  { value: "FULLY_MATCHED", label: tx("Matched") },
  { value: "MATCHED_WITHIN_TOLERANCE", label: tx("In Tolerance") },
  { value: "PENDING_REVIEW", label: tx("Pending Review") },
  { value: "PRICE_MISMATCH", label: tx("Price Mismatch") },
  { value: "QUANTITY_MISMATCH", label: tx("Qty Mismatch") },
  { value: "BLOCKED", label: tx("Blocked") },
  { value: "DUPLICATE_SUSPECTED", label: tx("Duplicate") },
  { value: "REJECTED", label: tx("Rejected") },
]);

export default function MatchListPage() {
  const [statusFilter, setStatusFilter] = useState<MatchOverallStatus | "">("");
  const [invoiceId, setInvoiceId] = useState("");
  const [runMsg, setRunMsg] = useState("");
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<MatchHeaderSummary[]>({
    queryKey: ["im-list", statusFilter],
    queryFn: () => imApi.list(statusFilter ? { status: statusFilter } : undefined),
  });

  const runMatch = useMutation({
    mutationFn: (id: string) => imApi.runMatch(id),
    onSuccess: (result) => {
      setRunMsg(tx("Match created: {match_no} — {overall_status}", { match_no: result.match_no, overall_status: result.overall_status }));
      setInvoiceId("");
      qc.invalidateQueries({ queryKey: ["im-list"] });
    },
    onError: (e: Error) => setRunMsg(tx("Error: {message}", { message: e.message })),
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{tx("Invoice Match Results")}</h1>
        <div className="flex gap-2">
          <EntityPicker kind="purchase_invoice" label={tx("Supplier invoice to match")} placeholder={tx("Supplier invoice to match…")}
            className="w-72 max-w-full" value={invoiceId} onChange={setInvoiceId} />
          <button
            onClick={() => invoiceId && runMatch.mutate(invoiceId)}
            disabled={!invoiceId || runMatch.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {runMatch.isPending ? tx("Running…") : tx("Run Match")}
          </button>
        </div>
      </div>

      {runMsg && (
        <p className={`text-sm px-3 py-2 rounded ${runMsg.startsWith("Error") ? "bg-red-50 text-red-600" : "bg-green-50 text-green-700"}`}>
          {runMsg}
        </p>
      )}

      {/* Status filters */}
      <div className="flex flex-wrap gap-1">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(s.value)}
            className={`px-3 py-1 text-xs rounded-lg border ${
              statusFilter === s.value ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {[tx("Match No"), tx("Invoice No"), tx("Date"), tx("Total"), tx("Status"), tx("Review"), tx("Payable"), tx("Dup"), ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">{tx("Loading…")}</td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">{tx("No matches found.")}</td></tr>
            ) : (
              data.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs font-medium">{m.match_no}</td>
                  <td className="px-4 py-2 text-gray-600">{m.invoice_no ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{m.invoice_date ?? "—"}</td>
                  <td className="px-4 py-2 font-medium">{Number(m.invoice_total).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${MATCH_STATUS_COLOR[m.overall_status]}`}>
                      {m.overall_status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {m.review_required
                      ? <span className="text-xs text-yellow-600 font-medium">{tx("⚠ Required")}</span>
                      : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`text-xs font-medium ${m.is_payable ? "text-green-600" : "text-red-600"}`}>
                      {m.is_payable ? "✓" : "✗"}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {m.duplicate_flag && <span className="text-xs text-purple-600 font-medium">⚠</span>}
                  </td>
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/invoice-match/${m.id}`} className="text-blue-600 hover:underline text-xs">{tx("View")}</Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
