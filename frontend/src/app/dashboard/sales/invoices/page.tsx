"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { salesApi, InvoiceStatus } from "@/lib/sales";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const statusVariant = (s: InvoiceStatus) =>
  s === "PAID" ? "green"
  : s === "OVERDUE" ? "red"
  : s === "PARTIALLY_PAID" ? "yellow"
  : s === "ISSUED" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = [
  { value: "", label: "All" },
  { value: "DRAFT", label: "Draft" },
  { value: "ISSUED", label: "Issued" },
  { value: "PARTIALLY_PAID", label: "Partially Paid" },
  { value: "PAID", label: "Paid" },
  { value: "OVERDUE", label: "Overdue" },
  { value: "CANCELLED", label: "Cancelled" },
];

export default function InvoicesPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [statusFilter, setStatusFilter] = useState("");

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ["sales-invoices", statusFilter],
    queryFn: () => salesApi.listInvoices(statusFilter ? { status: statusFilter as InvoiceStatus } : {}),
  });

  const { data: outstanding = [] } = useQuery({
    queryKey: ["sales-outstanding"],
    queryFn: () => salesApi.getOutstandingInvoices(),
  });

  const { data: summary } = useQuery({
    queryKey: ["sales-summary"],
    queryFn: () => salesApi.getSalesSummary(),
  });

  const syncMut = useMutation({
    mutationFn: () => salesApi.syncOverdue(),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["sales-invoices"] });
      qc.invalidateQueries({ queryKey: ["sales-outstanding"] });
      qc.invalidateQueries({ queryKey: ["sales-summary"] });
      toast("success", `${res.updated} invoice(s) marked overdue`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const columns = [
    { header: "Invoice No", accessor: (r: typeof invoices[0]) => (
      <button onClick={() => router.push(`/dashboard/sales/invoices/${r.id}`)} className="text-blue-600 hover:underline font-medium">
        {r.invoice_no}
      </button>
    )},
    { header: "Customer", accessor: (r: typeof invoices[0]) => r.customer_name || "—" },
    { header: "Sales Order", accessor: (r: typeof invoices[0]) => r.so_no || "—" },
    { header: "Invoice Date", accessor: (r: typeof invoices[0]) => r.invoice_date },
    { header: "Due Date", accessor: (r: typeof invoices[0]) => {
      const overdue = r.days_overdue;
      return <span className={overdue ? "text-red-600 font-medium" : ""}>{r.due_date}</span>;
    }},
    { header: "Total", accessor: (r: typeof invoices[0]) =>
      `${r.currency} ${Number(r.total_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
    },
    { header: "Paid", accessor: (r: typeof invoices[0]) =>
      `${r.currency} ${Number(r.paid_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
    },
    { header: "Outstanding", accessor: (r: typeof invoices[0]) => (
      <span className={Number(r.outstanding_balance) > 0 ? "text-orange-600 font-medium" : "text-green-600"}>
        {r.currency} {Number(r.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
      </span>
    )},
    { header: "Overdue", accessor: (r: typeof invoices[0]) =>
      r.days_overdue ? <span className="text-red-600 font-medium">{r.days_overdue}d</span> : "—"
    },
    { header: "Status", accessor: (r: typeof invoices[0]) => (
      <Badge label={r.status} variant={statusVariant(r.status)} />
    )},
  ];

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">{invoices.length} invoices</p>
        </div>
        <div className="flex gap-3">
          <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} />
          <Button variant="secondary" onClick={() => syncMut.mutate()} disabled={syncMut.isPending}>
            {syncMut.isPending ? "Syncing..." : "Sync Overdue"}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total Invoiced</p>
            <p className="text-xl font-bold text-gray-900 mt-1">
              ${Number(summary.total_invoiced).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Collected</p>
            <p className="text-xl font-bold text-green-700 mt-1">
              ${Number(summary.total_collected).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Outstanding</p>
            <p className="text-xl font-bold text-orange-600 mt-1">
              ${Number(summary.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Overdue Invoices</p>
            <p className={`text-xl font-bold mt-1 ${summary.overdue_invoices > 0 ? "text-red-600" : "text-gray-900"}`}>
              {summary.overdue_invoices}
            </p>
          </div>
        </div>
      )}

      {/* Overdue Alert */}
      {outstanding.filter((r) => r.days_overdue && r.days_overdue > 0).length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm font-medium text-red-800">
            {outstanding.filter((r) => r.days_overdue && r.days_overdue > 0).length} overdue invoice(s) require attention
          </p>
          <div className="mt-2 space-y-1">
            {outstanding
              .filter((r) => r.days_overdue && r.days_overdue > 0)
              .slice(0, 5)
              .map((r) => (
                <div key={r.invoice_id} className="text-xs text-red-700 flex justify-between">
                  <span>{r.invoice_no} — {r.customer_name}</span>
                  <span>{r.days_overdue}d overdue · ${Number(r.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : (
        <Table columns={columns} data={invoices} keyField="id" emptyMessage="No invoices found." />
      )}
    </div>
  );
}
