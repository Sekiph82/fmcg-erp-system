"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { qualityApi, QCType, QCStatus } from "@/lib/quality";
import { suppliersApi } from "@/lib/suppliers";
import { materialsApi } from "@/lib/materials";
import { warehousesApi } from "@/lib/warehouses";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const statusVariant = (s: QCStatus) =>
  s === "PASSED" ? "green"
  : s === "FAILED" ? "red"
  : s === "CONDITIONAL_RELEASE" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const decisionVariant = (d?: string) =>
  d === "ACCEPT" ? "green"
  : d === "REJECT" || d === "REWORK" ? "red"
  : d === "CONDITIONAL_RELEASE" ? "blue"
  : "blue";

const TYPE_OPTS = [
  { value: "", label: "All Types" },
  { value: "INCOMING", label: "Incoming QC" },
  { value: "IN_PROCESS", label: "In-Process QC" },
  { value: "FINISHED_GOODS", label: "Finished Goods QC" },
];

const STATUS_OPTS = [
  { value: "", label: "All Statuses" },
  { value: "PENDING", label: "Pending" },
  { value: "IN_PROGRESS", label: "In Progress" },
  { value: "PASSED", label: "Passed" },
  { value: "FAILED", label: "Failed" },
  { value: "CONDITIONAL_RELEASE", label: "Conditional Release" },
  { value: "CANCELLED", label: "Cancelled" },
];

export default function QCInspectionsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [typeFilter, setTypeFilter] = useState<QCType | "">("");
  const [statusFilter, setStatusFilter] = useState<QCStatus | "">("");
  const [form, setForm] = useState({
    inspection_no: "", qc_type: "INCOMING" as QCType,
    inspection_date: "", lot_number: "", batch_no: "",
    supplier_id: "", material_id: "", product_id: "", warehouse_id: "",
    sample_size: "", sample_unit: "KG", notes: "",
  });

  const { data: inspections = [], isLoading } = useQuery({
    queryKey: ["qc-inspections", typeFilter, statusFilter],
    queryFn: () => qualityApi.listInspections({
      ...(typeFilter ? { qc_type: typeFilter } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
  });

  const { data: suppliers = [] } = useQuery({ queryKey: ["suppliers"], queryFn: () => suppliersApi.list(0, 200), enabled: open });
  const { data: materials = [] } = useQuery({ queryKey: ["materials"], queryFn: () => materialsApi.list(0, 200), enabled: open });
  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: () => warehousesApi.list(0, 100), enabled: open });

  const create = useMutation({
    mutationFn: () => qualityApi.createInspection({
      ...form,
      sample_size: form.sample_size ? parseFloat(form.sample_size) : undefined,
      supplier_id: form.supplier_id || undefined,
      material_id: form.material_id || undefined,
      product_id: form.product_id || undefined,
      warehouse_id: form.warehouse_id || undefined,
      lot_number: form.lot_number || undefined,
      batch_no: form.batch_no || undefined,
    }),
    onSuccess: (insp) => {
      qc.invalidateQueries({ queryKey: ["qc-inspections"] });
      setOpen(false);
      router.push(`/dashboard/quality/${insp.id}`);
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  // Dashboard counts
  const pending = inspections.filter((i) => i.status === "PENDING" || i.status === "IN_PROGRESS").length;
  const failed = inspections.filter((i) => i.status === "FAILED").length;
  const criticalFails = inspections.filter((i) => i.critical_fail).length;

  return (
    <div data-testid="quality-page">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">QC Inspections</h1>
          <p className="text-sm text-gray-500 mt-1">{inspections.length} total · {pending} open · {failed} failed</p>
        </div>
        <Button onClick={() => setOpen(true)} data-testid="quality-create-inspection-button">+ New Inspection</Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Pending / Active", value: pending, color: "text-blue-600" },
          { label: "Passed", value: inspections.filter((i) => i.status === "PASSED").length, color: "text-green-600" },
          { label: "Failed", value: failed, color: failed > 0 ? "text-red-600" : "text-gray-400" },
          { label: "Critical Failures", value: criticalFails, color: criticalFails > 0 ? "text-red-700 font-extrabold" : "text-gray-400" },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-gray-500">{c.label}</p>
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="mb-4 flex gap-3">
        <Select options={TYPE_OPTS} value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as QCType | "")} className="w-48" />
        <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as QCStatus | "")} className="w-48" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <div data-testid="quality-inspection-list">
          <Table
            keyField="id"
            data={inspections}
            emptyMessage="No QC inspections yet."
            columns={[
            {
              header: "Inspection No",
              accessor: (i) => (
                <button className="font-mono text-xs font-medium text-indigo-600 hover:underline" onClick={() => router.push(`/dashboard/quality/${i.id}`)}>
                  {i.inspection_no}
                </button>
              ),
            },
            {
              header: "Type",
              accessor: (i) => (
                <Badge
                  label={i.qc_type.replace(/_/g, " ")}
                  variant={i.qc_type === "INCOMING" ? "blue" : i.qc_type === "IN_PROCESS" ? "blue" : "green"}
                />
              ),
            },
            {
              header: "Item",
              accessor: (i) => (
                <span>
                  {i.material_code && <span className="font-mono text-xs text-gray-400 mr-1">{i.material_code}</span>}
                  {i.material_name || i.product_name || "—"}
                </span>
              ),
            },
            { header: "Supplier", accessor: (i) => i.supplier_name ?? "—" },
            { header: "Lot / Batch", accessor: (i) => i.lot_number || i.batch_no || "—" },
            { header: "Date", accessor: (i) => new Date(i.inspection_date).toLocaleDateString() },
            {
              header: "Tests",
              accessor: (i) => i.test_count > 0 ? (
                <span className="text-sm">
                  <span className="text-green-600">{i.pass_count}✓</span>
                  {i.fail_count > 0 && <span className="text-red-500 ml-1">{i.fail_count}✗</span>}
                  {i.critical_fail && <span className="ml-1 text-red-700 font-bold text-xs">CRIT</span>}
                </span>
              ) : <span className="text-gray-400 text-xs">—</span>,
            },
            {
              header: "Status",
              accessor: (i) => (
                <div className="flex items-center gap-1">
                  <Badge label={i.status.replace(/_/g, " ")} variant={statusVariant(i.status)} />
                  {i.quarantine_applied && <Badge label="QUARANTINED" variant="red" />}
                </div>
              ),
            },
            {
              header: "",
              accessor: (i) => <Button variant="secondary" onClick={() => router.push(`/dashboard/quality/${i.id}`)}>View</Button>,
            },
            ]}
          />
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="New QC Inspection">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Inspection No *" value={form.inspection_no} onChange={(e) => setForm((f) => ({ ...f, inspection_no: e.target.value }))} placeholder="e.g. QC-2026-001" required />
            <Select label="QC Type *" options={[
              { value: "INCOMING", label: "Incoming QC" },
              { value: "IN_PROCESS", label: "In-Process QC" },
              { value: "FINISHED_GOODS", label: "Finished Goods QC" },
            ]} value={form.qc_type} onChange={(e) => setForm((f) => ({ ...f, qc_type: e.target.value as QCType }))} />
          </div>
          <Input label="Inspection Date *" type="date" onChange={(e) => setForm((f) => ({ ...f, inspection_date: e.target.value }))} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Lot Number" value={form.lot_number} onChange={(e) => setForm((f) => ({ ...f, lot_number: e.target.value }))} />
            <Input label="Batch No" value={form.batch_no} onChange={(e) => setForm((f) => ({ ...f, batch_no: e.target.value }))} />
          </div>
          {form.qc_type === "INCOMING" && (
            <>
              <Select label="Supplier" options={[{ value: "", label: "Select…" }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))]}
                value={form.supplier_id} onChange={(e) => setForm((f) => ({ ...f, supplier_id: e.target.value }))} />
              <Select label="Material" options={[{ value: "", label: "Select material…" }, ...materials.map((m) => ({ value: m.id, label: `${m.code} — ${m.name}` }))]}
                value={form.material_id} onChange={(e) => setForm((f) => ({ ...f, material_id: e.target.value }))} />
            </>
          )}
          <Select label="Warehouse" options={[{ value: "", label: "Select warehouse…" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))]}
            value={form.warehouse_id} onChange={(e) => setForm((f) => ({ ...f, warehouse_id: e.target.value }))} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Sample Size" type="number" step="0.001" value={form.sample_size} onChange={(e) => setForm((f) => ({ ...f, sample_size: e.target.value }))} />
            <Input label="Sample Unit" value={form.sample_unit} onChange={(e) => setForm((f) => ({ ...f, sample_unit: e.target.value }))} />
          </div>
          <Input label="Notes" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending} disabled={!form.inspection_no || !form.inspection_date}>Create Inspection</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
