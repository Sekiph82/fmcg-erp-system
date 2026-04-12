"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { procurementApi } from "@/lib/procurement";
import { suppliersApi } from "@/lib/suppliers";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const statusVariant = (s: string) =>
  s === "APPROVED" || s === "CONVERTED" ? "green"
  : s === "PENDING_APPROVAL" ? "blue"
  : s === "REJECTED" || s === "CANCELLED" ? "red"
  : "blue";

export default function PRDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [convertOpen, setConvertOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [convertForm, setConvertForm] = useState({
    po_no: "", supplier_id: "", order_date: "", expected_delivery_date: "",
    payment_terms: "", currency: "USD", notes: "",
  });

  const { data: pr, isLoading } = useQuery({
    queryKey: ["pr", id],
    queryFn: () => procurementApi.getPR(id),
    enabled: !!id,
  });

  const { data: suppliers = [] } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => suppliersApi.list(0, 200),
    enabled: convertOpen,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["pr", id] });

  const submit = useMutation({
    mutationFn: () => procurementApi.submitPR(id),
    onSuccess: () => { invalidate(); toast("success", "Submitted", "PR pending approval."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const approve = useMutation({
    mutationFn: () => procurementApi.approvePR(id, true),
    onSuccess: () => { invalidate(); toast("success", "Approved", "PR approved."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const reject = useMutation({
    mutationFn: () => procurementApi.approvePR(id, false, rejectionReason),
    onSuccess: () => { invalidate(); setRejectOpen(false); toast("success", "Rejected", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const convert = useMutation({
    mutationFn: () => procurementApi.convertPRToPO(id, {
      ...convertForm,
      exchange_rate: 1.0,
      line_prices: {},
    }),
    onSuccess: (po) => {
      invalidate();
      setConvertOpen(false);
      toast("success", "PO created", `${po.po_no} created from this PR.`);
      router.push(`/dashboard/procurement/orders/${po.id}`);
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  if (isLoading) return <div className="flex justify-center py-24"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>;
  if (!pr) return <div className="text-center py-16 text-gray-500">PR not found.</div>;

  const isDraft = pr.status === "DRAFT";
  const isPending = pr.status === "PENDING_APPROVAL";
  const isApproved = pr.status === "APPROVED";

  const totalEstimated = pr.lines.reduce((sum, l) =>
    sum + (l.quantity * (l.estimated_unit_cost ?? 0)), 0
  );

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button className="text-sm text-indigo-600 hover:underline mb-2 block" onClick={() => router.push("/dashboard/procurement")}>
              ← Back to Requisitions
            </button>
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{pr.pr_no}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {pr.requester_name && `Requested by ${pr.requester_name}`}
              {pr.department && ` · ${pr.department}`}
              {` · Required by ${new Date(pr.required_date).toLocaleDateString()}`}
            </p>
            {pr.rejection_reason && (
              <p className="text-sm text-red-600 mt-1">Rejected: {pr.rejection_reason}</p>
            )}
          </div>
          <div className="flex flex-col items-end gap-3">
            <Badge label={pr.status.replace(/_/g, " ")} variant={statusVariant(pr.status)} />
            <div className="flex gap-2 flex-wrap justify-end">
              {isDraft && (
                <Button onClick={() => submit.mutate()} loading={submit.isPending}>Submit for Approval</Button>
              )}
              {isPending && (
                <>
                  <Button onClick={() => approve.mutate()} loading={approve.isPending}>Approve</Button>
                  <Button variant="secondary" onClick={() => setRejectOpen(true)}>Reject</Button>
                </>
              )}
              {isApproved && (
                <Button onClick={() => setConvertOpen(true)}>Convert to PO</Button>
              )}
            </div>
          </div>
        </div>

        {totalEstimated > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs text-gray-500">Estimated Total</p>
            <p className="text-xl font-bold">{totalEstimated.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          </div>
        )}
      </div>

      {/* Lines */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Requested Items</h2>
        <Table
          keyField="id"
          data={pr.lines}
          emptyMessage="No lines."
          columns={[
            { header: "#", accessor: "line_no", className: "w-10 text-gray-400 text-xs" },
            {
              header: "Material",
              accessor: (l) => (
                <span>
                  {l.material_code && <span className="font-mono text-xs text-gray-400 mr-1">{l.material_code}</span>}
                  {l.material_name || l.product_name || l.description || "—"}
                </span>
              ),
            },
            { header: "Quantity", accessor: (l) => `${Number(l.quantity).toFixed(3)} ${l.unit}` },
            {
              header: "Est. Unit Cost",
              accessor: (l) => l.estimated_unit_cost != null
                ? Number(l.estimated_unit_cost).toFixed(4)
                : "—",
            },
            {
              header: "Est. Total",
              accessor: (l) => l.estimated_unit_cost != null
                ? (l.quantity * l.estimated_unit_cost).toFixed(2)
                : "—",
            },
            { header: "Preferred Supplier", accessor: (l) => l.preferred_supplier_name ?? "—" },
            { header: "Notes", accessor: (l) => l.notes ?? "—" },
          ]}
        />
      </div>

      {/* Reject Modal */}
      <Modal open={rejectOpen} onClose={() => setRejectOpen(false)} title="Reject PR">
        <form onSubmit={(e) => { e.preventDefault(); reject.mutate(); }} className="space-y-4">
          <Input label="Rejection Reason *" value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)} required />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" type="button" onClick={() => setRejectOpen(false)}>Cancel</Button>
            <Button type="submit" loading={reject.isPending} disabled={!rejectionReason}>Reject PR</Button>
          </div>
        </form>
      </Modal>

      {/* Convert to PO Modal */}
      <Modal open={convertOpen} onClose={() => setConvertOpen(false)} title="Convert PR to Purchase Order">
        <form onSubmit={(e) => { e.preventDefault(); convert.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="PO No *" value={convertForm.po_no} onChange={(e) => setConvertForm((f) => ({ ...f, po_no: e.target.value }))} placeholder="e.g. PO-2026-001" required />
            <Input label="Currency" value={convertForm.currency} onChange={(e) => setConvertForm((f) => ({ ...f, currency: e.target.value }))} />
          </div>
          <Select
            label="Supplier *"
            options={[{ value: "", label: "Select…" }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))]}
            value={convertForm.supplier_id}
            onChange={(e) => setConvertForm((f) => ({ ...f, supplier_id: e.target.value }))}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Order Date *" type="date" onChange={(e) => setConvertForm((f) => ({ ...f, order_date: e.target.value }))} required />
            <Input label="Expected Delivery *" type="date" onChange={(e) => setConvertForm((f) => ({ ...f, expected_delivery_date: e.target.value }))} required />
          </div>
          <Input label="Payment Terms" value={convertForm.payment_terms} onChange={(e) => setConvertForm((f) => ({ ...f, payment_terms: e.target.value }))} placeholder="e.g. Net 30" />
          <Input label="Notes" value={convertForm.notes} onChange={(e) => setConvertForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-700">
            All {pr.lines.length} PR line(s) will be copied to the PO using estimated unit costs. Prices can be adjusted on the PO.
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setConvertOpen(false)}>Cancel</Button>
            <Button type="submit" loading={convert.isPending} disabled={!convertForm.po_no || !convertForm.supplier_id || !convertForm.order_date || !convertForm.expected_delivery_date}>
              Create PO
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
