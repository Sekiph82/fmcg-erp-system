"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
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

const statusVariant = (s: PRStatus) =>
  s === "APPROVED" || s === "CONVERTED" ? "green"
  : s === "PENDING_APPROVAL" ? "blue"
  : s === "REJECTED" || s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = [
  { value: "", label: "All" },
  { value: "DRAFT", label: "Draft" },
  { value: "PENDING_APPROVAL", label: "Pending Approval" },
  { value: "APPROVED", label: "Approved" },
  { value: "CONVERTED", label: "Converted to PO" },
  { value: "REJECTED", label: "Rejected" },
  { value: "CANCELLED", label: "Cancelled" },
];

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

export default function PRsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<PRStatus | "">("");
  const [form, setForm] = useState({
    pr_no: "", department: "", required_date: "", notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine(1)]);

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
    enabled: open,
  });

  const matOpts = [{ value: "", label: "Select material…" }, ...materials.map((m) => ({ value: m.id, label: `${m.code} — ${m.name}` }))];
  const suppOpts = [{ value: "", label: "Any supplier" }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))];

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
      toast("success", "PR created", `${pr.pr_no} created.`);
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const updateLine = (i: number, field: keyof LineForm, val: string) =>
    setLines((ls) => ls.map((l, idx) => idx === i ? { ...l, [field]: val } : l));

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Purchase Requisitions</h1>
          <p className="text-sm text-gray-500 mt-1">{prs.length} total</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ New PR</Button>
      </div>

      <div className="mb-4">
        <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as PRStatus | "")} className="w-52" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="id"
          data={prs}
          emptyMessage="No purchase requisitions yet."
          columns={[
            {
              header: "PR No",
              accessor: (p) => (
                <button className="font-mono text-xs font-medium text-indigo-600 hover:underline" onClick={() => router.push(`/dashboard/procurement/${p.id}`)}>
                  {p.pr_no}
                </button>
              ),
            },
            { header: "Requester", accessor: (p) => p.requester_name ?? "—" },
            { header: "Department", accessor: (p) => p.department ?? "—" },
            { header: "Required By", accessor: (p) => new Date(p.required_date).toLocaleDateString() },
            { header: "Lines", accessor: (p) => p.line_count },
            { header: "Status", accessor: (p) => <Badge label={p.status.replace(/_/g, " ")} variant={statusVariant(p.status)} /> },
            {
              header: "",
              accessor: (p) => (
                <Button variant="secondary" onClick={() => router.push(`/dashboard/procurement/${p.id}`)}>View</Button>
              ),
            },
          ]}
        />
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="New Purchase Requisition">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="PR No *" value={form.pr_no} onChange={(e) => setForm((f) => ({ ...f, pr_no: e.target.value }))} placeholder="e.g. PR-2026-001" required />
            <Input label="Department" value={form.department} onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))} />
          </div>
          <Input label="Required Date *" type="date" onChange={(e) => setForm((f) => ({ ...f, required_date: e.target.value }))} required />
          <Input label="Notes" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />

          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold text-gray-700">Requested Items</p>
              <button type="button" className="text-xs text-indigo-600 hover:underline" onClick={() => setLines((ls) => [...ls, emptyLine(ls.length + 1)])}>
                + Add Line
              </button>
            </div>
            <div className="space-y-2">
              {lines.map((l, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-4">
                    <Select options={matOpts} value={l.material_id} onChange={(e) => updateLine(i, "material_id", e.target.value)} />
                  </div>
                  <div className="col-span-2">
                    <Input placeholder="Qty" value={l.quantity} onChange={(e) => updateLine(i, "quantity", e.target.value)} type="number" step="0.001" />
                  </div>
                  <div className="col-span-2">
                    <Select options={UNIT_OPTS} value={l.unit} onChange={(e) => updateLine(i, "unit", e.target.value)} />
                  </div>
                  <div className="col-span-2">
                    <Input placeholder="Est. cost" value={l.estimated_unit_cost} onChange={(e) => updateLine(i, "estimated_unit_cost", e.target.value)} type="number" step="0.01" />
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
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending} disabled={!form.pr_no || !form.required_date}>Create PR</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
