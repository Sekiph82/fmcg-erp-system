"use client";

import { useQuery } from "@tanstack/react-query";
import { financeApi, CustomerLedgerRow } from "@/lib/finance";

function fmtKES(n: number) {
  return `KES ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function CustomersLedgerPage() {
  const { data = [], isLoading } = useQuery<CustomerLedgerRow[]>({
    queryKey: ["customer-ledger"],
    queryFn: financeApi.customerLedger,
    staleTime: 30_000,
  });

  const totalInvoiced = data.reduce((s, r) => s + r.total_invoiced, 0);
  const totalPaid = data.reduce((s, r) => s + r.total_paid, 0);
  const totalOutstanding = data.reduce((s, r) => s + r.outstanding_balance, 0);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Customers Ledger</h1>
        <p className="text-sm text-gray-400 mt-0.5">Total sales, payments, and outstanding balances per customer</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">Total Invoiced</p>
          <p className="text-xl font-bold text-indigo-700">{fmtKES(totalInvoiced)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">Total Paid</p>
          <p className="text-xl font-bold text-green-600">{fmtKES(totalPaid)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">Outstanding Balance</p>
          <p className={`text-xl font-bold ${totalOutstanding > 0 ? "text-orange-600" : "text-green-600"}`}>
            {fmtKES(totalOutstanding)}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-50">
          <h2 className="font-semibold text-gray-800">{data.length} Customers</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-widest">
                <th className="px-5 py-3 text-left font-semibold">Code</th>
                <th className="px-5 py-3 text-left font-semibold">Customer</th>
                <th className="px-5 py-3 text-right font-semibold">Total Invoiced</th>
                <th className="px-5 py-3 text-right font-semibold">Total Paid</th>
                <th className="px-5 py-3 text-right font-semibold">Outstanding</th>
                <th className="px-5 py-3 text-center font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-5 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              )}
              {!isLoading && data.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-400">
                    No customer records found.
                  </td>
                </tr>
              )}
              {data.map((row) => {
                const outstanding = row.outstanding_balance;
                return (
                  <tr key={row.customer_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-gray-500">{row.customer_code}</td>
                    <td className="px-5 py-3 font-medium text-gray-900">{row.customer_name}</td>
                    <td className="px-5 py-3 text-right text-gray-700">{fmtKES(row.total_invoiced)}</td>
                    <td className="px-5 py-3 text-right text-green-600 font-medium">{fmtKES(row.total_paid)}</td>
                    <td className={`px-5 py-3 text-right font-semibold ${outstanding > 0 ? "text-orange-600" : "text-gray-400"}`}>
                      {fmtKES(outstanding)}
                    </td>
                    <td className="px-5 py-3 text-center">
                      {outstanding <= 0 ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">Settled</span>
                      ) : row.total_invoiced === 0 ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-400 font-medium">No Invoices</span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium">Outstanding</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            {data.length > 0 && (
              <tfoot>
                <tr className="bg-gray-50 font-semibold text-sm border-t-2 border-gray-200">
                  <td className="px-5 py-3" colSpan={2}>Total</td>
                  <td className="px-5 py-3 text-right text-indigo-700">{fmtKES(totalInvoiced)}</td>
                  <td className="px-5 py-3 text-right text-green-600">{fmtKES(totalPaid)}</td>
                  <td className={`px-5 py-3 text-right ${totalOutstanding > 0 ? "text-orange-600" : "text-green-600"}`}>
                    {fmtKES(totalOutstanding)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  );
}
