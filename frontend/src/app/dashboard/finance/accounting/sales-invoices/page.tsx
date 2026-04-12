"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { financeApi, SalesInvoice, InvoiceStatus } from "@/lib/finance";

function fmtKES(n: number) {
  return `KES ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STATUS_CONFIG: Record<InvoiceStatus, { label: string; cls: string }> = {
  DRAFT:          { label: "Draft",          cls: "bg-gray-100 text-gray-500" },
  ISSUED:         { label: "Issued",         cls: "bg-blue-100 text-blue-700" },
  PARTIALLY_PAID: { label: "Partial",        cls: "bg-yellow-100 text-yellow-700" },
  PAID:           { label: "Paid",           cls: "bg-green-100 text-green-700" },
  OVERDUE:        { label: "Overdue",        cls: "bg-red-100 text-red-700" },
  CANCELLED:      { label: "Cancelled",      cls: "bg-gray-100 text-gray-400" },
};

const STATUSES: Array<InvoiceStatus | ""> = ["", "ISSUED", "PARTIALLY_PAID", "PAID", "OVERDUE", "DRAFT", "CANCELLED"];

export default function SalesInvoicesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");

  const { data = [], isLoading } = useQuery<SalesInvoice[]>({
    queryKey: ["accounting-sales-invoices", statusFilter],
    queryFn: () => financeApi.listSalesInvoices({ status: statusFilter || undefined, limit: 300 }),
    staleTime: 30_000,
  });

  const filtered = search
    ? data.filter(
        (inv) =>
          inv.invoice_no.toLowerCase().includes(search.toLowerCase()) ||
          (inv.customer_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : data;

  const totalInvoiced = filtered.reduce((s, r) => s + r.total_amount, 0);
  const totalPaid = filtered.reduce((s, r) => s + r.paid_amount, 0);
  const totalOutstanding = filtered.reduce((s, r) => s + r.outstanding, 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sales Invoices</h1>
          <p className="text-sm text-gray-400 mt-0.5">Customer invoices — amounts, payments, and balances</p>
        </div>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Invoiced</p>
          <p className="text-lg font-bold text-indigo-700">{fmtKES(totalInvoiced)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Paid</p>
          <p className="text-lg font-bold text-green-600">{fmtKES(totalPaid)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Outstanding</p>
          <p className={`text-lg font-bold ${totalOutstanding > 0 ? "text-orange-600" : "text-green-600"}`}>
            {fmtKES(totalOutstanding)}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search invoice # or customer..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 w-64"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s === "" ? "All Statuses" : STATUS_CONFIG[s as InvoiceStatus]?.label ?? s}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-widest">
                <th className="px-5 py-3 text-left font-semibold">Invoice #</th>
                <th className="px-5 py-3 text-left font-semibold">Customer</th>
                <th className="px-5 py-3 text-center font-semibold">Date</th>
                <th className="px-5 py-3 text-center font-semibold">Due</th>
                <th className="px-5 py-3 text-right font-semibold">Total</th>
                <th className="px-5 py-3 text-right font-semibold">Paid</th>
                <th className="px-5 py-3 text-right font-semibold">Outstanding</th>
                <th className="px-5 py-3 text-center font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="px-5 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-gray-400">
                    No invoices found.
                  </td>
                </tr>
              )}
              {filtered.map((inv) => {
                const cfg = STATUS_CONFIG[inv.status as InvoiceStatus];
                return (
                  <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-600">
                      {inv.invoice_no}
                    </td>
                    <td className="px-5 py-3 text-gray-900">
                      <div>{inv.customer_name ?? "—"}</div>
                      {inv.customer_code && (
                        <div className="text-xs text-gray-400">{inv.customer_code}</div>
                      )}
                    </td>
                    <td className="px-5 py-3 text-center text-gray-500">{inv.invoice_date}</td>
                    <td className="px-5 py-3 text-center text-gray-500">{inv.due_date}</td>
                    <td className="px-5 py-3 text-right font-medium text-gray-800">{fmtKES(inv.total_amount)}</td>
                    <td className="px-5 py-3 text-right text-green-600">{fmtKES(inv.paid_amount)}</td>
                    <td className={`px-5 py-3 text-right font-semibold ${inv.outstanding > 0 ? "text-orange-600" : "text-gray-400"}`}>
                      {fmtKES(inv.outstanding)}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg?.cls ?? "bg-gray-100 text-gray-500"}`}>
                        {cfg?.label ?? inv.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            {filtered.length > 0 && (
              <tfoot>
                <tr className="bg-gray-50 font-semibold text-sm border-t-2 border-gray-200">
                  <td className="px-5 py-3" colSpan={4}>Total ({filtered.length})</td>
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
