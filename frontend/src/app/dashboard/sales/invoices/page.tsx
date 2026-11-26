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
import { tx, lx } from "@/lib/i18n/core";

const statusVariant = (s: InvoiceStatus) =>
  s === "PAID" ? "green"
  : s === "OVERDUE" ? "red"
  : s === "PARTIALLY_PAID" ? "yellow"
  : s === "ISSUED" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = lx(() => [
  { value: "", label: tx("All") },
  { value: "DRAFT", label: tx("Draft") },
  { value: "ISSUED", label: tx("Issued") },
  { value: "PARTIALLY_PAID", label: tx("Partially Paid") },
  { value: "PAID", label: tx("Paid") },
  { value: "OVERDUE", label: tx("Overdue") },
  { value: "CANCELLED", label: tx("Cancelled") },
]);

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
      toast("success", tx("{updated} invoice(s) marked overdue", { updated: res.updated }));
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const columns = [
    { header: tx("Invoice No"), accessor: (r: typeof invoices[0]) => (
      <button onClick={() => router.push(`/dashboard/sales/invoices/${r.id}`)} className="text-blue-600 hover:underline font-medium">
        {r.invoice_no}
      </button>
    )},
    { header: tx("Customer"), accessor: (r: typeof invoices[0]) => r.customer_name || "—" },
    { header: tx("Sales Order"), accessor: (r: typeof invoices[0]) => r.so_no || "—" },
    { header: tx("Invoice Date"), accessor: (r: typeof invoices[0]) => r.invoice_date },
    { header: tx("Due Date"), accessor: (r: typeof invoices[0]) => {
      const overdue = r.days_overdue;
      return <span className={overdue ? "text-red-600 font-medium" : ""}>{r.due_date}</span>;
    }},
    { header: tx("Total"), accessor: (r: typeof invoices[0]) =>
      `${r.currency} ${Number(r.total_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
    },
    { header: tx("Paid"), accessor: (r: typeof invoices[0]) =>
      `${r.currency} ${Number(r.paid_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
    },
    { header: tx("Outstanding"), accessor: (r: typeof invoices[0]) => (
      <span className={Number(r.outstanding_balance) > 0 ? "text-orange-600 font-medium" : "text-green-600"}>
        {r.currency} {Number(r.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
      </span>
    )},
    { header: tx("Overdue"), accessor: (r: typeof invoices[0]) =>
      r.days_overdue ? <span className="text-red-600 font-medium">{r.days_overdue}{tx("d")}</span> : "—"
    },
    { header: tx("Status"), accessor: (r: typeof invoices[0]) => (
      <Badge label={r.status} variant={statusVariant(r.status)} />
    )},
  ];

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Invoices")}</h1>
          <p className="text-sm text-gray-500 mt-1">{invoices.length} {tx("invoices")}</p>
        </div>
        <div className="flex gap-3">
          <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} />
          <Button variant="secondary" onClick={() => syncMut.mutate()} disabled={syncMut.isPending}>
            {syncMut.isPending ? tx("Syncing...") : tx("Sync Overdue")}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tx("Total Invoiced")}</p>
            <p className="text-xl font-bold text-gray-900 mt-1">
              ${Number(summary.total_invoiced).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tx("Collected")}</p>
            <p className="text-xl font-bold text-green-700 mt-1">
              ${Number(summary.total_collected).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tx("Outstanding")}</p>
            <p className="text-xl font-bold text-orange-600 mt-1">
              ${Number(summary.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tx("Overdue Invoices")}</p>
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
            {outstanding.filter((r) => r.days_overdue && r.days_overdue > 0).length} {tx("overdue invoice(s) require attention")}
          </p>
          <div className="mt-2 space-y-1">
            {outstanding
              .filter((r) => r.days_overdue && r.days_overdue > 0)
              .slice(0, 5)
              .map((r) => (
                <div key={r.invoice_id} className="text-xs text-red-700 flex justify-between">
                  <span>{r.invoice_no} — {r.customer_name}</span>
                  <span>{r.days_overdue}{tx("d overdue · $")}{Number(r.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">{tx("Loading...")}</div>
      ) : (
        <Table columns={columns} data={invoices} keyField="id" emptyMessage="No invoices found." />
      )}
    </div>
  );
}
