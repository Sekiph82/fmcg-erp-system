"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { imApi, MATCH_STATUS_COLOR, MatchHeaderSummary, MatchOverallStatus } from "@/lib/invoice_match";

const STATUSES: { value: MatchOverallStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "FULLY_MATCHED", label: "Matched" },
  { value: "MATCHED_WITHIN_TOLERANCE", label: "In Tolerance" },
  { value: "PENDING_REVIEW", label: "Pending Review" },
  { value: "PRICE_MISMATCH", label: "Price Mismatch" },
  { value: "QUANTITY_MISMATCH", label: "Qty Mismatch" },
  { value: "BLOCKED", label: "Blocked" },
  { value: "DUPLICATE_SUSPECTED", label: "Duplicate" },
  { value: "REJECTED", label: "Rejected" },
];

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
      setRunMsg(`Match created: ${result.match_no} — ${result.overall_status}`);
      setInvoiceId("");
      qc.invalidateQueries({ queryKey: ["im-list"] });
    },
    onError: (e: Error) => setRunMsg(`Error: ${e.message}`),
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Invoice Match Results</h1>
        <div className="flex gap-2">
          <input
            className="border rounded-lg px-3 py-1.5 text-sm w-72"
            placeholder="Invoice ID (UUID) to run match…"
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
          />
          <button
            onClick={() => invoiceId && runMatch.mutate(invoiceId)}
            disabled={!invoiceId || runMatch.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {runMatch.isPending ? "Running…" : "Run Match"}
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
              {["Match No", "Invoice No", "Date", "Total", "Status", "Review", "Payable", "Dup", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">No matches found.</td></tr>
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
                      ? <span className="text-xs text-yellow-600 font-medium">⚠ Required</span>
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
                    <Link href={`/dashboard/invoice-match/${m.id}`} className="text-blue-600 hover:underline text-xs">View</Link>
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
