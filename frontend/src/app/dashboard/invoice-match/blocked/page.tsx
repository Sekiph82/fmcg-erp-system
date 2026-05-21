"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { imApi, MATCH_STATUS_COLOR, MatchHeaderSummary } from "@/lib/invoice_match";

export default function BlockedInvoicesPage() {
  const { data = [], isLoading } = useQuery<MatchHeaderSummary[]>({
    queryKey: ["im-blocked"],
    queryFn: () => imApi.getBlockedInvoices(),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Blocked Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Invoices on payment hold — requires resolution</p>
        </div>
        <span className={`text-xl font-bold ${data.length > 0 ? "text-red-600" : "text-green-600"}`}>
          {data.length} on hold
        </span>
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading…</p>
      ) : data.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <p className="text-green-700 font-medium">✓ No blocked invoices. All matched invoices are payable.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Match No", "Invoice No", "Date", "Total", "Status", "Hold Reason", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs font-medium">{m.match_no}</td>
                  <td className="px-4 py-2 text-gray-600">{m.invoice_no ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{m.invoice_date ?? "—"}</td>
                  <td className="px-4 py-2 font-medium">
                    {Number(m.invoice_total).toLocaleString(undefined, { minimumFractionDigits: 2 })} {m.currency}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${MATCH_STATUS_COLOR[m.overall_status]}`}>
                      {m.overall_status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-red-600 max-w-xs truncate" title={m.payment_hold_reason ?? undefined}>
                    {m.payment_hold_reason ?? "—"}
                  </td>
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/invoice-match/${m.id}`} className="text-blue-600 hover:underline text-xs">
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
