"use client";

import { useQuery } from "@tanstack/react-query";
import { financeApi } from "@/lib/finance";
import { Badge } from "@/components/ui/Badge";

export default function ReceivablesPage() {
  const { data: receivables = [], isLoading } = useQuery({
    queryKey: ["finance-receivables"],
    queryFn: () => financeApi.receivables(),
  });

  const total = receivables.reduce((s, r) => s + r.outstanding, 0);
  const overdue = receivables.filter((r) => r.days_overdue && r.days_overdue > 0);
  const overdueAmount = overdue.reduce((s, r) => s + r.outstanding, 0);

  const agingBuckets = {
    "Current": receivables.filter((r) => !r.days_overdue || r.days_overdue <= 0),
    "1–30 days": receivables.filter((r) => r.days_overdue && r.days_overdue >= 1 && r.days_overdue <= 30),
    "31–60 days": receivables.filter((r) => r.days_overdue && r.days_overdue >= 31 && r.days_overdue <= 60),
    "61–90 days": receivables.filter((r) => r.days_overdue && r.days_overdue >= 61 && r.days_overdue <= 90),
    "90+ days": receivables.filter((r) => r.days_overdue && r.days_overdue > 90),
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Receivables</h1>
        <p className="text-sm text-gray-500 mt-1">Outstanding customer invoices and collections</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Outstanding</p>
          <p className="text-2xl font-bold mt-1 text-orange-600">KES {total.toLocaleString(undefined, { minimumFractionDigits: 0 })}</p>
          <p className="text-xs text-gray-400 mt-1">{receivables.length} invoices</p>
        </div>
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Overdue</p>
          <p className={`text-2xl font-bold mt-1 ${overdueAmount > 0 ? "text-red-600" : "text-gray-700"}`}>KES {overdueAmount.toLocaleString(undefined, { minimumFractionDigits: 0 })}</p>
          <p className="text-xs text-gray-400 mt-1">{overdue.length} invoices past due</p>
        </div>
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Severely Overdue</p>
          <p className="text-2xl font-bold mt-1 text-red-700">
            KES {agingBuckets["90+ days"].reduce((s, r) => s + r.outstanding, 0).toLocaleString(undefined, { minimumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-gray-400 mt-1">{agingBuckets["90+ days"].length} invoices 90+ days</p>
        </div>
        <div className="bg-white rounded-lg border p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Current (Not Due)</p>
          <p className="text-2xl font-bold mt-1 text-green-700">
            KES {agingBuckets["Current"].reduce((s, r) => s + r.outstanding, 0).toLocaleString(undefined, { minimumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-gray-400 mt-1">{agingBuckets["Current"].length} invoices current</p>
        </div>
      </div>

      {/* Aging buckets */}
      <div className="bg-white rounded-lg border p-5">
        <h2 className="font-semibold text-gray-800 mb-4">Aging Summary</h2>
        <div className="grid grid-cols-5 gap-4">
          {Object.entries(agingBuckets).map(([label, items]) => {
            const amount = items.reduce((s, r) => s + r.outstanding, 0);
            const pct = total > 0 ? (amount / total) * 100 : 0;
            const isOverdue = label !== "Current";
            return (
              <div key={label} className="text-center">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className={`text-lg font-bold ${isOverdue && amount > 0 ? "text-red-600" : "text-gray-700"}`}>
                  KES {amount.toLocaleString(undefined, { minimumFractionDigits: 0 })}
                </p>
                <p className="text-xs text-gray-400">{items.length} inv · {pct.toFixed(0)}%</p>
                <div className="mt-2 h-1.5 bg-gray-100 rounded overflow-hidden">
                  <div
                    className={`h-full rounded ${isOverdue ? "bg-red-400" : "bg-green-400"}`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Receivables table */}
      <div className="bg-white rounded-lg border">
        <div className="px-5 py-3 border-b">
          <h2 className="font-semibold text-gray-800">Outstanding Invoices</h2>
        </div>
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Invoice No</th>
                <th className="px-5 py-2 text-left">Customer</th>
                <th className="px-5 py-2 text-left">Invoice Date</th>
                <th className="px-5 py-2 text-left">Due Date</th>
                <th className="px-5 py-2 text-right">Total</th>
                <th className="px-5 py-2 text-right">Paid</th>
                <th className="px-5 py-2 text-right">Outstanding</th>
                <th className="px-5 py-2 text-left">Age</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {receivables.map((r) => {
                const overdue = r.days_overdue && r.days_overdue > 0;
                const severely = r.days_overdue && r.days_overdue > 60;
                return (
                  <tr key={r.invoice_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-mono text-xs font-medium">{r.invoice_no}</td>
                    <td className="px-5 py-3 font-medium text-gray-900">{r.customer_name}</td>
                    <td className="px-5 py-3 text-gray-600">{r.invoice_date}</td>
                    <td className="px-5 py-3 text-gray-600">{r.due_date}</td>
                    <td className="px-5 py-3 text-right">{Number(r.total_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="px-5 py-3 text-right text-green-600">{Number(r.paid_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-5 py-3 text-right font-semibold ${severely ? "text-red-600" : overdue ? "text-orange-600" : "text-gray-700"}`}>
                      {Number(r.outstanding).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-5 py-3">
                      {overdue ? (
                        <Badge label={`${r.days_overdue}d overdue`} variant={severely ? "red" : "yellow"} />
                      ) : (
                        <Badge label="Current" variant="green" />
                      )}
                    </td>
                  </tr>
                );
              })}
              {receivables.length === 0 && (
                <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-400">No outstanding receivables</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
