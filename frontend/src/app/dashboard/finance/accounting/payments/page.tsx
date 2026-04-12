"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { financeApi, CombinedPayment } from "@/lib/finance";

function fmtKES(n: number) {
  return `KES ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const METHOD_PILL: Record<string, string> = {
  cash:  "bg-green-100 text-green-700",
  bank:  "bg-blue-100 text-blue-700",
  mpesa: "bg-emerald-100 text-emerald-700",
};

const TYPE_PILL: Record<string, string> = {
  customer: "bg-indigo-100 text-indigo-700",
  supplier: "bg-orange-100 text-orange-700",
};

export default function PaymentsPage() {
  const [typeFilter, setTypeFilter] = useState<"" | "customer" | "supplier">("");
  const [methodFilter, setMethodFilter] = useState("");
  const [search, setSearch] = useState("");

  const { data = [], isLoading } = useQuery<CombinedPayment[]>({
    queryKey: ["accounting-payments", typeFilter],
    queryFn: () => financeApi.listAllPayments({
      payment_type: typeFilter || undefined,
      limit: 500,
    }),
    staleTime: 30_000,
  });

  const filtered = data.filter((p) => {
    if (methodFilter && p.method !== methodFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        (p.invoice_no ?? "").toLowerCase().includes(q) ||
        (p.party_name ?? "").toLowerCase().includes(q) ||
        (p.reference ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const customerTotal = filtered.filter(p => p.type === "customer").reduce((s, p) => s + p.amount, 0);
  const supplierTotal = filtered.filter(p => p.type === "supplier").reduce((s, p) => s + p.amount, 0);
  const grandTotal = filtered.reduce((s, p) => s + p.amount, 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Payments</h1>
        <p className="text-sm text-gray-400 mt-0.5">All customer and supplier payments in one view</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Customer Receipts</p>
          <p className="text-lg font-bold text-indigo-700">{fmtKES(customerTotal)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Supplier Payments</p>
          <p className="text-lg font-bold text-orange-600">{fmtKES(supplierTotal)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Total Volume</p>
          <p className="text-lg font-bold text-gray-800">{fmtKES(grandTotal)}</p>
          <p className="text-xs text-gray-400">{filtered.length} transactions</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search invoice, party, reference..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 w-64"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as "" | "customer" | "supplier")}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All Types</option>
          <option value="customer">Customer</option>
          <option value="supplier">Supplier</option>
        </select>
        <select
          value={methodFilter}
          onChange={(e) => setMethodFilter(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All Methods</option>
          <option value="cash">Cash</option>
          <option value="bank">Bank</option>
          <option value="mpesa">M-Pesa</option>
        </select>
      </div>

      {/* Method breakdown */}
      {filtered.length > 0 && (
        <div className="flex gap-4 flex-wrap">
          {(["cash", "bank", "mpesa"] as const).map((m) => {
            const total = filtered.filter(p => p.method === m).reduce((s, p) => s + p.amount, 0);
            if (total === 0) return null;
            return (
              <div key={m} className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${METHOD_PILL[m]}`}>
                <span className="capitalize">{m}</span>
                <span>{fmtKES(total)}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-widest">
                <th className="px-5 py-3 text-center font-semibold">Type</th>
                <th className="px-5 py-3 text-center font-semibold">Date</th>
                <th className="px-5 py-3 text-left font-semibold">Party</th>
                <th className="px-5 py-3 text-left font-semibold">Invoice</th>
                <th className="px-5 py-3 text-right font-semibold">Amount</th>
                <th className="px-5 py-3 text-center font-semibold">Method</th>
                <th className="px-5 py-3 text-left font-semibold">Reference</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-5 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-gray-400">
                    No payment records found.
                  </td>
                </tr>
              )}
              {filtered.map((p) => (
                <tr key={`${p.type}-${p.id}`} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${TYPE_PILL[p.type]}`}>
                      {p.type}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-center text-gray-500">{p.payment_date}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{p.party_name ?? "—"}</td>
                  <td className="px-5 py-3 font-mono text-xs text-indigo-600">{p.invoice_no ?? "—"}</td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-800">{fmtKES(p.amount)}</td>
                  <td className="px-5 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${METHOD_PILL[p.method] ?? "bg-gray-100 text-gray-500"}`}>
                      {p.method}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-400">{p.reference ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
