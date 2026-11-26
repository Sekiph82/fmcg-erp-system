"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { procurementApi, PRStatus } from "@/lib/procurement";
import { materialsApi } from "@/lib/materials";
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
import { tx, lx } from "@/lib/i18n/core";

const statusVariant = (s: PRStatus) =>
  s === "APPROVED" || s === "CONVERTED" ? "green"
  : s === "PENDING_APPROVAL" ? "blue"
  : s === "REJECTED" || s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = lx(() => [
  { value: "", label: tx("All") },
  { value: "DRAFT", label: tx("Draft") },
  { value: "PENDING_APPROVAL", label: tx("Pending Approval") },
  { value: "APPROVED", label: tx("Approved") },
  { value: "CONVERTED", label: tx("Converted to PO") },
  { value: "REJECTED", label: tx("Rejected") },
  { value: "CANCELLED", label: tx("Cancelled") },
]);

const UNIT_OPTS = ["KG", "G", "L", "ML", "PCS", "BOX", "CARTON", "PALLET"].map((u) => ({ value: u, label: u }));

type LineForm = {
  line_no: number;
  material_id: string;
  quantity: string;
  unit: string;
  estimated_unit_cost: string;
  preferred_supplier_id: string;
  notes: string;
};

const emptyLine = (n: number): LineForm => ({
  line_no: n, material_id: "", quantity: "", unit: "KG",
  estimated_unit_cost: "", preferred_supplier_id: "", notes: "",
});

function ProcurementPRsTab() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<PRStatus | "">("");
  const [form, setForm] = useState({
    pr_no: "", department: "", required_date: "", notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine(1)]);
  // PR workflow (M40.S02.T001): submit → approve/reject → convert to a purchase order
  const [convertPr, setConvertPr] = useState<{ id: string; pr_no: string } | null>(null);
  const [conv, setConv] = useState({ po_no: "", supplier_id: "", order_date: new Date().toISOString().slice(0, 10), expected_delivery_date: "", currency: "KES" });
  const act = useMutation({
    mutationFn: ({ id, step, reason }: { id: string; step: "submit" | "approve" | "reject"; reason?: string }) =>
      step === "submit" ? procurementApi.submitPR(id) : procurementApi.approvePR(id, step === "approve", reason),
    onSuccess: (pr, v) => {
      qc.invalidateQueries({ queryKey: ["prs"] });
      toast("success", v.step === "submit" ? tx("Sent for approval") : v.step === "approve" ? tx("Approved") : tx("Rejected"), pr.pr_no);
    },
    onError: (e) => toast("error", tx("Failed"), extractApiError(e)),
  });
  const convert = useMutation({
    mutationFn: () => procurementApi.convertPRToPO(convertPr!.id, conv),
    onSuccess: (po) => {
      qc.invalidateQueries({ queryKey: ["prs"] });
      qc.invalidateQueries({ queryKey: ["pos"] });
      setConvertPr(null);
      toast("success", tx("Purchase order created"), tx("{po_no} is a draft in Purchase Orders, waiting for approval.", { po_no: po.po_no }));
    },
    onError: (e) => toast("error", tx("Failed"), extractApiError(e)),
  });

  const { data: prs = [], isLoading } = useQuery({
    queryKey: ["prs", statusFilter],
    queryFn: () => procurementApi.listPRs(statusFilter ? { status: statusFilter } : undefined),
  });

  const { data: materials = [] } = useQuery({
    queryKey: ["materials"],
    queryFn: () => materialsApi.list(0, 200),
    enabled: open,
  });

  const { data: suppliers = [] } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => suppliersApi.list(0, 200),
    enabled: open || !!convertPr,
  });

  const matOpts = [{ value: "", label: tx("Select material…") }, ...materials.map((m) => ({ value: m.id, label: `${m.code} — ${m.name}` }))];
  const suppOpts = [{ value: "", label: tx("Any supplier") }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))];

  const create = useMutation({
    mutationFn: () =>
      procurementApi.createPR({
        ...form,
        lines: lines
          .filter((l) => l.material_id && l.quantity)
          .map((l) => ({
            line_no: l.line_no,
            material_id: l.material_id || undefined,
            quantity: parseFloat(l.quantity),
            unit: l.unit,
            estimated_unit_cost: l.estimated_unit_cost ? parseFloat(l.estimated_unit_cost) : undefined,
            preferred_supplier_id: l.preferred_supplier_id || undefined,
            notes: l.notes || undefined,
          })),
      }),
    onSuccess: (pr) => {
      qc.invalidateQueries({ queryKey: ["prs"] });
      setOpen(false);
      toast("success", tx("PR created"), tx("{pr_no} created.", { pr_no: pr.pr_no }));
    },
    onError: (e) => toast("error", tx("Failed"), extractApiError(e)),
  });

  const updateLine = (i: number, field: keyof LineForm, val: string) =>
    setLines((ls) => ls.map((l, idx) => idx === i ? { ...l, [field]: val } : l));

  return (
    <div data-testid="procurement-page">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Purchase Requisitions")}</h1>
          <p className="text-sm text-gray-500 mt-1">{prs.length} {tx("total")}</p>
        </div>
        <Button onClick={() => setOpen(true)} data-testid="procurement-create-pr-button">{tx("+ New PR")}</Button>
      </div>

      <div className="mb-4">
        <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as PRStatus | "")} className="w-52" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <div data-testid="procurement-pr-list">
          <Table
            keyField="id"
            data={prs}
            emptyMessage="No purchase requisitions yet."
            columns={[
            {
              header: tx("PR No"),
              accessor: (p) => (
                <span className="font-mono text-xs font-medium text-gray-900">{p.pr_no}</span>
              ),
            },
            { header: tx("Requester"), accessor: (p) => p.requester_name ?? "—" },
            { header: tx("Department"), accessor: (p) => p.department ?? "—" },
            { header: tx("Required By"), accessor: (p) => new Date(p.required_date).toLocaleDateString() },
            { header: tx("Lines"), accessor: (p) => p.line_count },
            { header: tx("Status"), accessor: (p) => <Badge label={p.status.replace(/_/g, " ")} variant={statusVariant(p.status)} /> },
            {
              header: tx("Access"),
              accessor: (p) => (
                p.access?.view_only ? (
                  <span title={p.access.reason || tx("You can view this record but cannot modify it in this scope.")}>
                    <Badge label={tx("View only")} variant="gray" />
                  </span>
                ) : (
                  <Badge label={tx("Actionable")} variant="green" />
                )
              ),
            },
            {
              header: "",
              accessor: (p) => (
                <div className="flex gap-1.5 justify-end">
                  {p.status === "DRAFT" && p.access?.can_edit !== false && (
                    <Button variant="secondary" loading={act.isPending} onClick={() => act.mutate({ id: p.id, step: "submit" })}>{tx("Submit")}</Button>
                  )}
                  {p.status === "PENDING_APPROVAL" && p.access?.can_approve && (<>
                    <Button loading={act.isPending} onClick={() => act.mutate({ id: p.id, step: "approve" })}>{tx("Approve")}</Button>
                    <Button variant="secondary" onClick={() => { const reason = window.prompt(tx("Reason for rejecting")); if (reason) act.mutate({ id: p.id, step: "reject", reason }); }}>{tx("Reject")}</Button>
                  </>)}
                  {p.status === "APPROVED" && p.access?.can_convert && (
                    <Button variant="secondary" onClick={() => { setConv((c) => ({ ...c, po_no: `PO-${p.pr_no.replace(/^PR-?/, "")}` })); setConvertPr({ id: p.id, pr_no: p.pr_no }); }}>{tx("Create PO")}</Button>
                  )}
                </div>
              ),
            },
            ]}
          />
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={tx("New Purchase Requisition")}>
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("PR No *")} value={form.pr_no} onChange={(e) => setForm((f) => ({ ...f, pr_no: e.target.value }))} placeholder={tx("e.g. PR-2026-001")} required />
            <Input label={tx("Department")} value={form.department} onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))} />
          </div>
          <Input label={tx("Required Date *")} type="date" onChange={(e) => setForm((f) => ({ ...f, required_date: e.target.value }))} required />
          <Input label={tx("Notes")} value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />

          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold text-gray-700">{tx("Requested Items")}</p>
              <button type="button" className="text-xs text-indigo-600 hover:underline" onClick={() => setLines((ls) => [...ls, emptyLine(ls.length + 1)])}>
                {tx("+ Add Line")}
              </button>
            </div>
            <div className="space-y-2">
              {lines.map((l, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-4">
                    <Select options={matOpts} value={l.material_id} onChange={(e) => updateLine(i, "material_id", e.target.value)} />
                  </div>
                  <div className="col-span-2">
                    <Input placeholder={tx("Qty")} value={l.quantity} onChange={(e) => updateLine(i, "quantity", e.target.value)} type="number" step="0.001" />
                  </div>
                  <div className="col-span-2">
                    <Select options={UNIT_OPTS} value={l.unit} onChange={(e) => updateLine(i, "unit", e.target.value)} />
                  </div>
                  <div className="col-span-2">
                    <Input placeholder={tx("Est. cost")} value={l.estimated_unit_cost} onChange={(e) => updateLine(i, "estimated_unit_cost", e.target.value)} type="number" step="0.01" />
                  </div>
                  <div className="col-span-1">
                    <Select options={suppOpts} value={l.preferred_supplier_id} onChange={(e) => updateLine(i, "preferred_supplier_id", e.target.value)} />
                  </div>
                  <div className="col-span-1 flex justify-end">
                    {lines.length > 1 && (
                      <button type="button" className="text-red-400 hover:text-red-600 text-xs" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}>✕</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={create.isPending} disabled={!form.pr_no || !form.required_date}>{tx("Create PR")}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!convertPr} onClose={() => setConvertPr(null)} title={`Create purchase order from ${convertPr?.pr_no ?? ""}`}>
        <form onSubmit={(e) => { e.preventDefault(); convert.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("PO No *")} value={conv.po_no} onChange={(e) => setConv((c) => ({ ...c, po_no: e.target.value }))} required />
            <Select label={tx("Supplier *")} options={suppOpts.map((o) => o.value ? o : { value: "", label: tx("Select supplier…") })} value={conv.supplier_id} onChange={(e) => setConv((c) => ({ ...c, supplier_id: e.target.value }))} />
            <Input label={tx("Order date *")} type="date" value={conv.order_date} onChange={(e) => setConv((c) => ({ ...c, order_date: e.target.value }))} required />
            <Input label={tx("Expected delivery *")} type="date" value={conv.expected_delivery_date} onChange={(e) => setConv((c) => ({ ...c, expected_delivery_date: e.target.value }))} required />
            <Input label={tx("Currency")} value={conv.currency} onChange={(e) => setConv((c) => ({ ...c, currency: e.target.value.toUpperCase() }))} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setConvertPr(null)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={convert.isPending} disabled={!conv.po_no || !conv.supplier_id || !conv.expected_delivery_date}>{tx("Create PO")}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

const ProcurementOrdersPage       = dynamic(() => import("@/app/dashboard/procurement/orders/page"),              { ssr: false });
const ProcurementRFQPage          = dynamic(() => import("@/app/dashboard/procurement/rfq/page"),                 { ssr: false });
const ProcurementDeliveriesPage   = dynamic(() => import("@/app/dashboard/procurement/deliveries/page"),          { ssr: false });
const ProcurementSuppliersPage    = dynamic(() => import("@/app/dashboard/procurement/suppliers/page"),           { ssr: false });
const ProcurementBlanketPage      = dynamic(() => import("@/app/dashboard/procurement/blanket-agreements/page"),  { ssr: false });
const ProcurementReorderPage      = dynamic(() => import("@/app/dashboard/procurement/reorder-policies/page"),    { ssr: false });
const SuggestionsPage             = dynamic(() => import("@/app/dashboard/procurement-suggestion/page"),          { ssr: false });
const SubcontractingPage          = dynamic(() => import("@/app/dashboard/subcontracting/page"),                  { ssr: false });
const LandedCostPage              = dynamic(() => import("@/app/dashboard/landed-cost/page"),                     { ssr: false });
const SupplierPortalPage          = dynamic(() => import("@/app/dashboard/supplier-portal/page"),                 { ssr: false });

export default function ProcurementPage() {
  const tabs = [
    { key: "purchase-requests", label: tx("Purchase Requests"), permission: "procurement.view", content: <ProcurementPRsTab /> },
    { key: "orders",            label: tx("Purchase Orders"),   permission: "procurement.view", content: <ProcurementOrdersPage /> },
    { key: "rfq",               label: "RFQ",               permission: "procurement.view", content: <ProcurementRFQPage /> },
    { key: "deliveries",        label: tx("Deliveries"),        permission: "procurement.view", content: <ProcurementDeliveriesPage /> },
    { key: "suppliers",         label: tx("Suppliers"),         permission: "procurement.view", content: <ProcurementSuppliersPage /> },
    { key: "blanket-agreements",label: tx("Blanket Agreements"),permission: "procurement.view", content: <ProcurementBlanketPage /> },
    { key: "reorder-policies",  label: tx("Reorder Policies"),  permission: "procurement.view", content: <ProcurementReorderPage /> },
    { key: "suggestions",       label: tx("Suggestions"),       permission: "procurement.view", content: <SuggestionsPage /> },
    { key: "subcontracting",    label: tx("Subcontracting"),    permission: "procurement.view", exact: true, content: <SubcontractingPage /> },
    { key: "landed-cost",       label: tx("Landed Cost"),       permission: "procurement.view", content: <LandedCostPage /> },
    { key: "supplier-portal",   label: tx("Supplier Portal"),   permission: "procurement.view", exact: true, content: <SupplierPortalPage /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Procurement")}
      description="Purchase requests, orders, RFQ, suppliers, subcontracting"
      permission="procurement.view"
      tabs={tabs}
      defaultTab="purchase-requests"
    />
  );
}
