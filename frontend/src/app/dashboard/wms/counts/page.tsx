"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { wmsApi, StockCountStatus, StockCountType } from "@/lib/wms";
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

const statusVariant = (s: StockCountStatus) =>
  s === "APPROVED" ? "green"
  : s === "PENDING_APPROVAL" ? "blue"
  : s === "IN_PROGRESS" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = [
  { value: "", label: "All" },
  { value: "DRAFT", label: "Draft" },
  { value: "IN_PROGRESS", label: "In Progress" },
  { value: "PENDING_APPROVAL", label: "Pending Approval" },
  { value: "APPROVED", label: "Approved" },
  { value: "CANCELLED", label: "Cancelled" },
];

const TYPE_OPTS = [
  { value: "CYCLE", label: "Cycle Count" },
  { value: "FULL", label: "Full Count" },
];

export default function StockCountsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StockCountStatus | "">("");
  const [form, setForm] = useState({ count_no: "", warehouse_id: "", count_type: "CYCLE" as StockCountType, scheduled_date: "", notes: "" });

  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: () => warehousesApi.list(0, 100) });
  const { data: counts = [], isLoading } = useQuery({
    queryKey: ["wms-counts", statusFilter],
    queryFn: () => wmsApi.listCounts(statusFilter ? { status: statusFilter } : undefined),
  });

  const create = useMutation({
    mutationFn: () => wmsApi.createCount({ ...form, scheduled_date: new Date(form.scheduled_date).toISOString() }),
    onSuccess: (c) => { qc.invalidateQueries({ queryKey: ["wms-counts"] }); setOpen(false); toast("success", "Count created", `${c.count_no} ready to start.`); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const startCount = useMutation({
    mutationFn: (id: string) => wmsApi.startCount(id),
    onSuccess: (c, id) => { qc.invalidateQueries({ queryKey: ["wms-counts"] }); toast("success", "Started", "Stock count in progress."); router.push(`/dashboard/wms/counts/${id}`); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Stock Counts</h1>
          <p className="text-sm text-gray-500 mt-1">{counts.length} total</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ New Count</Button>
      </div>

      <div className="mb-4">
        <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as StockCountStatus | "")} className="w-48" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="id"
          data={counts}
          emptyMessage="No stock counts yet."
          columns={[
            {
              header: "Count No",
              accessor: (c) => (
                <button className="font-mono text-xs text-indigo-600 hover:underline" onClick={() => router.push(`/dashboard/wms/counts/${c.id}`)}>
                  {c.count_no}
                </button>
              ),
            },
            { header: "Type", accessor: (c) => c.count_type === "CYCLE" ? "Cycle Count" : "Full Count" },
            { header: "Warehouse", accessor: (c) => c.warehouse_name ?? "—" },
            { header: "Zone", accessor: (c) => c.zone_name ?? "All zones" },
            {
              header: "Status",
              accessor: (c) => <Badge label={c.status.replace(/_/g, " ")} variant={statusVariant(c.status)} />,
            },
            {
              header: "Progress",
              accessor: (c) => c.total_lines > 0
                ? `${c.counted_lines} / ${c.total_lines}`
                : "—",
            },
            { header: "Scheduled", accessor: (c) => new Date(c.scheduled_date).toLocaleDateString() },
            {
              header: "",
              accessor: (c) => (
                <div className="flex gap-2">
                  {c.status === "DRAFT" && (
                    <Button variant="secondary" onClick={() => startCount.mutate(c.id)}>Start</Button>
                  )}
                  {c.status !== "DRAFT" && (
                    <Button variant="secondary" onClick={() => router.push(`/dashboard/wms/counts/${c.id}`)}>View</Button>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="New Stock Count">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Count No *" value={form.count_no} onChange={(e) => setForm((f) => ({ ...f, count_no: e.target.value }))} placeholder="e.g. SC-2026-001" required />
            <Select label="Type *" options={TYPE_OPTS} value={form.count_type} onChange={(e) => setForm((f) => ({ ...f, count_type: e.target.value as StockCountType }))} />
          </div>
          <Select
            label="Warehouse *"
            options={[{ value: "", label: "Select…" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))]}
            value={form.warehouse_id}
            onChange={(e) => setForm((f) => ({ ...f, warehouse_id: e.target.value }))}
          />
          <Input label="Scheduled Date *" type="datetime-local" onChange={(e) => setForm((f) => ({ ...f, scheduled_date: e.target.value }))} required />
          <Input label="Notes" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending} disabled={!form.count_no || !form.warehouse_id || !form.scheduled_date}>Create Count</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
