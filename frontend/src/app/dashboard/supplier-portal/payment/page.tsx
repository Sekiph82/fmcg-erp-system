"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { spApi } from "@/lib/supplier_portal";

const PAYMENT_COLORS: Record<string, string> = {
  SUBMITTED: "bg-gray-100 text-gray-700",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
  MATCHED: "bg-blue-100 text-blue-800",
  BLOCKED: "bg-red-100 text-red-800",
  APPROVED_PAYMENT: "bg-green-100 text-green-800",
  PAID: "bg-emerald-100 text-emerald-800",
  PARTIALLY_PAID: "bg-orange-100 text-orange-800",
  DISPUTED: "bg-red-100 text-red-800",
};

function PaymentContent() {
  const sp = useSearchParams();
  const accountId = sp.get("account") || "";
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!accountId) { setLoading(false); return; }
    spApi.getPaymentStatus(accountId).then(setData).finally(() => setLoading(false));
  }, [accountId]);

  const totalPaid = data.filter((d) => d.status === "PAID").reduce((s, d) => s + (d.total_amount || 0), 0);
  const totalPending = data.filter((d) => !["PAID", "REJECTED"].includes(d.status)).reduce((s, d) => s + (d.total_amount || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Payment Status</h1>
        <p className="text-sm text-gray-500 mt-1">Invoice payment tracking — read-only where policy permits</p>
      </div>

      {!accountId ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800">
          Select a supplier account to view payment status.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="text-2xl font-bold text-gray-900">{data.length}</div>
              <div className="text-xs text-gray-500 mt-1">Total Invoices</div>
            </div>
            <div className="bg-white border border-green-200 rounded-xl p-4">
              <div className="text-2xl font-bold text-green-700">{data[0]?.currency || "KES"} {totalPaid.toLocaleString()}</div>
              <div className="text-xs text-gray-500 mt-1">Total Paid</div>
            </div>
            <div className="bg-white border border-yellow-200 rounded-xl p-4">
              <div className="text-2xl font-bold text-yellow-700">{data[0]?.currency || "KES"} {totalPending.toLocaleString()}</div>
              <div className="text-xs text-gray-500 mt-1">Pending / In Progress</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["Invoice #", "Date", "Currency", "Amount", "Status", "Due Date"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
                ) : data.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No payment data available, or payment visibility is disabled for this account.</td></tr>
                ) : data.map((d) => (
                  <tr key={d.invoice_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-blue-700">{d.invoice_number}</td>
                    <td className="px-4 py-3 text-gray-500">{d.invoice_date || "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{d.currency}</td>
                    <td className="px-4 py-3 font-mono">{d.total_amount?.toLocaleString() || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PAYMENT_COLORS[d.status] || "bg-gray-100 text-gray-700"}`}>
                        {d.status?.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{d.due_date || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default function PaymentPage() {
  return <Suspense fallback={<div className="p-6 text-gray-400">Loading…</div>}><PaymentContent /></Suspense>;
}
