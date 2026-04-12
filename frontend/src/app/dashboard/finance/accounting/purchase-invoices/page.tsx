"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { financeApi, PurchaseInvoice, PurchaseInvoiceStatus } from "@/lib/finance";

function fmtKES(n: number) {
  return `KES ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STATUS_CONFIG: Record<PurchaseInvoiceStatus, { label: string; cls: string }> = {
  DRAFT:          { label: "Draft",     cls: "bg-gray-100 text-gray-500" },
  RECEIVED:       { label: "Received",  cls: "bg-blue-100 text-blue-700" },
  PARTIALLY_PAID: { label: "Partial",   cls: "bg-yellow-100 text-yellow-700" },
  PAID:           { label: "Paid",      cls: "bg-green-100 text-green-700" },
  OVERDUE:        { label: "Overdue",   cls: "bg-red-100 text-red-700" },
  CANCELLED:      { label: "Cancelled", cls: "bg-gray-100 text-gray-400" },
};

const STATUSES: Array<PurchaseInvoiceStatus | ""> = [
  "", "RECEIVED", "PARTIALLY_PAID", "PAID", "OVERDUE", "DRAFT", "CANCELLED",
];

function PaymentModal({
  invoice,
  onClose,
  onSuccess,
}: {
  invoice: PurchaseInvoice;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    payment_date: new Date().toISOString().split("T")[0],
    amount: "",
    method: "bank",
    reference: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      financeApi.createPurchasePayment(invoice.id, {
        invoice_id: invoice.id,
        payment_date: form.payment_date,
        amount: parseFloat(form.amount),
        method: form.method,
        reference: form.reference || undefined,
        notes: form.notes || undefined,
      }),
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail ?? "Failed to record payment"),
  });

  const outstanding = invoice.total_amount - invoice.paid_amount;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-bold text-gray-900">Record Payment</h3>
        <p className="text-sm text-gray-500">
          Invoice <strong>{invoice.invoice_no}</strong> · Outstanding: <strong>{fmtKES(outstanding)}</strong>
        </p>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Payment Date</label>
            <input type="date" value={form.payment_date}
              onChange={(e) => setForm(f => ({ ...f, payment_date: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Amount (KES)</label>
            <input type="number" step="0.01" value={form.amount} placeholder={`Max: ${outstanding.toFixed(2)}`}
              onChange={(e) => setForm(f => ({ ...f, amount: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Method</label>
            <select value={form.method} onChange={(e) => setForm(f => ({ ...f, method: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
              <option value="cash">Cash</option>
              <option value="bank">Bank Transfer</option>
              <option value="mpesa">M-Pesa</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Reference</label>
            <input type="text" value={form.reference} placeholder="Bank ref / M-Pesa receipt"
              onChange={(e) => setForm(f => ({ ...f, reference: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            Cancel
          </button>
          <button
            disabled={mutation.isPending || !form.amount}
            onClick={() => mutation.mutate()}
            className="px-4 py-2 text-sm font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors">
            {mutation.isPending ? "Saving…" : "Record Payment"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PurchaseInvoicesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [payingInvoice, setPayingInvoice] = useState<PurchaseInvoice | null>(null);
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<PurchaseInvoice[]>({
    queryKey: ["accounting-purchase-invoices", statusFilter],
    queryFn: () => financeApi.listPurchaseInvoices({ status: statusFilter || undefined, limit: 300 }),
    staleTime: 30_000,
  });

  const filtered = search
    ? data.filter(
        (inv) =>
          inv.invoice_no.toLowerCase().includes(search.toLowerCase()) ||
          (inv.supplier_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : data;

  const totalPurchases = filtered.reduce((s, r) => s + r.total_amount, 0);
  const totalPaid = filtered.reduce((s, r) => s + r.paid_amount, 0);
  const totalPayable = filtered.reduce((s, r) => s + (r.total_amount - r.paid_amount), 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      {payingInvoice && (
        <PaymentModal
          invoice={payingInvoice}
          onClose={() => setPayingInvoice(null)}
          onSuccess={() => qc.invalidateQueries({ queryKey: ["accounting-purchase-invoices"] })}
        />
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Purchase Invoices</h1>
        <p className="text-sm text-gray-400 mt-0.5">Supplier invoices for materials and goods received</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Total Purchases</p>
          <p className="text-lg font-bold text-indigo-700">{fmtKES(totalPurchases)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Paid</p>
          <p className="text-lg font-bold text-green-600">{fmtKES(totalPaid)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest">Outstanding Payable</p>
          <p className={`text-lg font-bold ${totalPayable > 0 ? "text-red-600" : "text-green-600"}`}>
            {fmtKES(totalPayable)}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search invoice # or supplier..."
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
            <option key={s} value={s}>
              {s === "" ? "All Statuses" : STATUS_CONFIG[s as PurchaseInvoiceStatus]?.label ?? s}
            </option>
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
                <th className="px-5 py-3 text-left font-semibold">Supplier</th>
                <th className="px-5 py-3 text-center font-semibold">Date</th>
                <th className="px-5 py-3 text-center font-semibold">Due</th>
                <th className="px-5 py-3 text-right font-semibold">Total</th>
                <th className="px-5 py-3 text-right font-semibold">Paid</th>
                <th className="px-5 py-3 text-right font-semibold">Payable</th>
                <th className="px-5 py-3 text-center font-semibold">Status</th>
                <th className="px-5 py-3 text-center font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 9 }).map((_, j) => (
                      <td key={j} className="px-5 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-5 py-8 text-center text-gray-400">
                    No purchase invoices found.
                  </td>
                </tr>
              )}
              {filtered.map((inv) => {
                const cfg = STATUS_CONFIG[inv.status as PurchaseInvoiceStatus];
                const payable = inv.total_amount - inv.paid_amount;
                const canPay = !["PAID", "CANCELLED"].includes(inv.status) && payable > 0;
                return (
                  <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-600">{inv.invoice_no}</td>
                    <td className="px-5 py-3 text-gray-900">
                      <div>{inv.supplier_name ?? "—"}</div>
                      {inv.po_no && <div className="text-xs text-gray-400">PO: {inv.po_no}</div>}
                    </td>
                    <td className="px-5 py-3 text-center text-gray-500">{inv.invoice_date}</td>
                    <td className="px-5 py-3 text-center text-gray-500">{inv.due_date}</td>
                    <td className="px-5 py-3 text-right font-medium text-gray-800">{fmtKES(inv.total_amount)}</td>
                    <td className="px-5 py-3 text-right text-green-600">{fmtKES(inv.paid_amount)}</td>
                    <td className={`px-5 py-3 text-right font-semibold ${payable > 0 ? "text-red-600" : "text-gray-400"}`}>
                      {fmtKES(payable)}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg?.cls ?? "bg-gray-100 text-gray-500"}`}>
                        {cfg?.label ?? inv.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      {canPay && (
                        <button
                          onClick={() => setPayingInvoice(inv)}
                          className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
                        >
                          Pay
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            {filtered.length > 0 && (
              <tfoot>
                <tr className="bg-gray-50 font-semibold text-sm border-t-2 border-gray-200">
                  <td className="px-5 py-3" colSpan={4}>Total ({filtered.length})</td>
                  <td className="px-5 py-3 text-right text-indigo-700">{fmtKES(totalPurchases)}</td>
                  <td className="px-5 py-3 text-right text-green-600">{fmtKES(totalPaid)}</td>
                  <td className={`px-5 py-3 text-right ${totalPayable > 0 ? "text-red-600" : "text-green-600"}`}>
                    {fmtKES(totalPayable)}
                  </td>
                  <td colSpan={2} />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  );
}
