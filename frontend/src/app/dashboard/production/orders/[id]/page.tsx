"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import {
  productionApi, CompleteOrderRequest, DowntimeReason,
} from "@/lib/production";
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

const DOWNTIME_REASONS: { value: DowntimeReason; label: string }[] = [
  { value: "BREAKDOWN", label: "Equipment Breakdown" },
  { value: "MAINTENANCE", label: "Planned Maintenance" },
  { value: "CHANGEOVER", label: "Product Changeover" },
  { value: "MATERIAL_SHORTAGE", label: "Material Shortage" },
  { value: "QUALITY_HOLD", label: "Quality Hold" },
  { value: "OTHER", label: "Other" },
];

const statusVariant = (s: string) =>
  s === "COMPLETED" ? "green"
  : s === "IN_PROGRESS" || s === "RELEASED" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [completeOpen, setCompleteOpen] = useState(false);
  const [pauseOpen, setPauseOpen] = useState(false);
  const [completeForm, setCompleteForm] = useState<CompleteOrderRequest>({
    actual_quantity: 0, consume_materials: true,
  });
  const [pauseForm, setPauseForm] = useState({ machine_id: "", reason: "BREAKDOWN" as DowntimeReason, notes: "" });

  const { data: order, isLoading } = useQuery({
    queryKey: ["production-order", id],
    queryFn: () => productionApi.getOrder(id),
    enabled: !!id,
  });

  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(0, 100),
  });

  const rmWarehouses = warehouses.filter((w) => w.warehouse_type === "RAW_MATERIAL");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["production-order", id] });

  const release = useMutation({
    mutationFn: () => productionApi.releaseOrder(id),
    onSuccess: () => { invalidate(); toast("success", "Released", "Order released to production floor."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const start = useMutation({
    mutationFn: () => productionApi.startOrder(id),
    onSuccess: () => { invalidate(); toast("success", "Started", "Production started."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const pause = useMutation({
    mutationFn: () => productionApi.pauseOrder(id, { machine_id: pauseForm.machine_id || undefined, reason: pauseForm.reason, notes: pauseForm.notes || undefined }),
    onSuccess: () => { invalidate(); setPauseOpen(false); toast("success", "Paused", "Downtime logged."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const resume = useMutation({
    mutationFn: () => productionApi.resumeOrder(id),
    onSuccess: () => { invalidate(); toast("success", "Resumed", "Downtime closed."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const complete = useMutation({
    mutationFn: () => productionApi.completeOrder(id, completeForm),
    onSuccess: () => { invalidate(); setCompleteOpen(false); toast("success", "Completed", "Production order completed. Stock updated."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const cancel = useMutation({
    mutationFn: () => productionApi.cancelOrder(id),
    onSuccess: () => { invalidate(); toast("success", "Cancelled", "Order cancelled."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const hasActiveDowntime = order?.downtime_logs.some((d) => !d.end_time);

  if (isLoading) return (
    <div className="flex justify-center py-24">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  );

  if (!order) return <div className="text-gray-500 py-16 text-center">Order not found.</div>;

  const isInProgress = order.status === "IN_PROGRESS";
  const isReleased = order.status === "RELEASED";
  const isPlanned = order.status === "PLANNED";
  const isCompleted = order.status === "COMPLETED";
  const isCancelled = order.status === "CANCELLED";

  const variancePct = order.actual_quantity != null && order.planned_quantity
    ? (((order.actual_quantity - order.planned_quantity) / order.planned_quantity) * 100).toFixed(1)
    : null;

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button className="text-sm text-indigo-600 hover:underline mb-2 block" onClick={() => router.push("/dashboard/production/orders")}>
              ← Back to Orders
            </button>
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{order.order_no}</h1>
            <p className="text-sm text-gray-600 mt-1">
              <span className="font-mono text-xs text-gray-400">{order.product_sku}</span>{" "}
              {order.product_name} — {order.recipe_name}
            </p>
            {order.batch_no && (
              <p className="text-xs text-gray-500 mt-1">Batch: <span className="font-mono">{order.batch_no}</span></p>
            )}
          </div>

          <div className="flex flex-col items-end gap-3">
            <Badge label={order.status} variant={statusVariant(order.status)} />
            <div className="flex gap-2 flex-wrap justify-end">
              {isPlanned && (
                <Button variant="secondary" onClick={() => release.mutate()} loading={release.isPending}>
                  Release
                </Button>
              )}
              {isReleased && (
                <Button onClick={() => start.mutate()} loading={start.isPending}>
                  Start Production
                </Button>
              )}
              {isInProgress && !hasActiveDowntime && (
                <Button variant="secondary" onClick={() => setPauseOpen(true)}>
                  Record Downtime
                </Button>
              )}
              {isInProgress && hasActiveDowntime && (
                <Button variant="secondary" onClick={() => resume.mutate()} loading={resume.isPending}>
                  Resume
                </Button>
              )}
              {isInProgress && (
                <Button onClick={() => setCompleteOpen(true)}>
                  Complete
                </Button>
              )}
              {!isCompleted && !isCancelled && (
                <Button variant="secondary" onClick={() => cancel.mutate()} loading={cancel.isPending}>
                  Cancel
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Key metrics row */}
        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4 pt-5 border-t border-gray-100">
          <div>
            <p className="text-xs text-gray-500">Planned Qty</p>
            <p className="text-lg font-semibold">{Number(order.planned_quantity).toLocaleString()} <span className="text-sm font-normal text-gray-400">{order.uom}</span></p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Actual Qty</p>
            <p className="text-lg font-semibold">
              {order.actual_quantity != null ? (
                <>
                  {Number(order.actual_quantity).toLocaleString()}{" "}
                  <span className="text-sm font-normal text-gray-400">{order.uom}</span>
                  {variancePct && (
                    <span className={`ml-2 text-sm ${parseFloat(variancePct) < 0 ? "text-red-500" : "text-green-600"}`}>
                      ({parseFloat(variancePct) > 0 ? "+" : ""}{variancePct}%)
                    </span>
                  )}
                </>
              ) : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Scheduled</p>
            <p className="text-sm font-medium">{new Date(order.scheduled_start).toLocaleString()}</p>
            <p className="text-xs text-gray-400">→ {new Date(order.scheduled_end).toLocaleString()}</p>
          </div>
          {order.actual_start && (
            <div>
              <p className="text-xs text-gray-500">Actual</p>
              <p className="text-sm font-medium">{new Date(order.actual_start).toLocaleString()}</p>
              {order.actual_end && <p className="text-xs text-gray-400">→ {new Date(order.actual_end).toLocaleString()}</p>}
            </div>
          )}
        </div>
      </div>

      {/* OEE card */}
      {order.oee && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">OEE Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "OEE", value: order.oee.oee, color: order.oee.oee >= 85 ? "text-green-600" : order.oee.oee >= 60 ? "text-yellow-600" : "text-red-500" },
              { label: "Availability", value: order.oee.availability, color: "text-blue-600" },
              { label: "Performance", value: order.oee.performance, color: "text-indigo-600" },
              { label: "Quality", value: order.oee.quality, color: "text-purple-600" },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-center p-4 rounded-lg bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className={`text-2xl font-bold ${color}`}>{value.toFixed(1)}%</p>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-gray-400 flex gap-4">
            <span>Scheduled: {order.oee.scheduled_minutes.toFixed(0)} min</span>
            {order.oee.actual_minutes != null && <span>Actual: {order.oee.actual_minutes.toFixed(0)} min</span>}
            <span>Downtime: {order.oee.downtime_minutes.toFixed(0)} min</span>
          </div>
        </div>
      )}

      {/* Material Consumption */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Material Consumption
          <span className="ml-2 text-sm font-normal text-gray-400">({order.consumptions.length})</span>
        </h2>
        <Table
          keyField="id"
          data={order.consumptions}
          emptyMessage="No material consumption recorded."
          columns={[
            {
              header: "Material",
              accessor: (c) => (
                <span>
                  <span className="font-mono text-xs text-gray-500">{c.material_code}</span>{" "}
                  {c.material_name}
                </span>
              ),
            },
            { header: "Lot", accessor: (c) => c.lot_number ?? "—" },
            {
              header: "Standard",
              accessor: (c) => `${Number(c.standard_quantity).toFixed(3)} ${c.unit}`,
            },
            {
              header: "Actual",
              accessor: (c) => `${Number(c.actual_quantity).toFixed(3)} ${c.unit}`,
            },
            {
              header: "Variance",
              accessor: (c) => {
                const v = Number(c.variance_quantity);
                return (
                  <span className={v > 0.001 ? "text-red-500 font-medium" : v < -0.001 ? "text-green-600 font-medium" : "text-gray-500"}>
                    {v > 0 ? "+" : ""}{v.toFixed(3)} {c.unit}
                  </span>
                );
              },
            },
            { header: "Warehouse", accessor: (c) => c.source_warehouse_name ?? "—" },
          ]}
        />
      </div>

      {/* FG Receipts */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Finished Goods Receipts
          <span className="ml-2 text-sm font-normal text-gray-400">({order.fg_receipts.length})</span>
        </h2>
        <Table
          keyField="id"
          data={order.fg_receipts}
          emptyMessage="No finished goods received yet."
          columns={[
            { header: "Quantity", accessor: (r) => `${Number(r.quantity).toLocaleString()} ${r.uom}` },
            { header: "Lot No", accessor: (r) => r.lot_number ?? "—" },
            { header: "Batch No", accessor: (r) => r.batch_no ?? "—" },
            { header: "Warehouse", accessor: (r) => r.warehouse_name ?? "—" },
          ]}
        />
      </div>

      {/* Downtime */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Downtime Log
          <span className="ml-2 text-sm font-normal text-gray-400">({order.downtime_logs.length})</span>
          {hasActiveDowntime && (
            <Badge label="Active" variant="red" />
          )}
        </h2>
        <Table
          keyField="id"
          data={order.downtime_logs}
          emptyMessage="No downtime recorded."
          columns={[
            { header: "Machine", accessor: (d) => d.machine_id ?? "—" },
            { header: "Reason", accessor: (d) => d.reason.replace(/_/g, " ") },
            { header: "Start", accessor: (d) => new Date(d.start_time).toLocaleString() },
            { header: "End", accessor: (d) => d.end_time ? new Date(d.end_time).toLocaleString() : <Badge label="Open" variant="red" /> },
            { header: "Duration", accessor: (d) => d.duration_minutes != null ? `${d.duration_minutes} min` : "—" },
            { header: "Notes", accessor: (d) => d.notes ?? "—" },
          ]}
        />
      </div>

      {/* Complete Modal */}
      <Modal open={completeOpen} onClose={() => setCompleteOpen(false)} title="Complete Production Order">
        <form onSubmit={(e) => { e.preventDefault(); complete.mutate(); }} className="space-y-4">
          <p className="text-sm text-gray-500">
            This will issue materials from inventory, receive finished goods into the target warehouse, and close the order.
          </p>
          <Input
            label="Actual Quantity Produced *"
            type="number"
            step="0.001"
            value={completeForm.actual_quantity || ""}
            onChange={(e) => setCompleteForm((f) => ({ ...f, actual_quantity: parseFloat(e.target.value) || 0 }))}
            required
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="FG Lot Number"
              value={completeForm.fg_lot_number ?? ""}
              onChange={(e) => setCompleteForm((f) => ({ ...f, fg_lot_number: e.target.value || undefined }))}
              placeholder="e.g. LOT-20260401"
            />
            <Input
              label="FG Expiry Date"
              type="date"
              onChange={(e) => setCompleteForm((f) => ({ ...f, fg_expiry_date: e.target.value || undefined }))}
            />
          </div>
          {rmWarehouses.length > 0 && (
            <Select
              label="Material Source Warehouse"
              options={[
                { value: "", label: order.source_warehouse_id ? "Use order default" : "Skip material consumption" },
                ...rmWarehouses.map((w) => ({ value: w.id, label: w.name })),
              ]}
              value={completeForm.source_warehouse_id ?? ""}
              onChange={(e) => setCompleteForm((f) => ({ ...f, source_warehouse_id: e.target.value || undefined }))}
            />
          )}
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={completeForm.consume_materials}
              onChange={(e) => setCompleteForm((f) => ({ ...f, consume_materials: e.target.checked }))}
              className="h-4 w-4 rounded border-gray-300"
            />
            <span className="text-sm text-gray-700">Auto-consume materials from BOM</span>
          </label>
          <Input
            label="Notes"
            value={completeForm.notes ?? ""}
            onChange={(e) => setCompleteForm((f) => ({ ...f, notes: e.target.value || undefined }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setCompleteOpen(false)}>Cancel</Button>
            <Button type="submit" loading={complete.isPending} disabled={!completeForm.actual_quantity}>
              Complete Order
            </Button>
          </div>
        </form>
      </Modal>

      {/* Pause / Downtime Modal */}
      <Modal open={pauseOpen} onClose={() => setPauseOpen(false)} title="Record Downtime">
        <form onSubmit={(e) => { e.preventDefault(); pause.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Machine / Line ID"
              value={pauseForm.machine_id}
              onChange={(e) => setPauseForm((f) => ({ ...f, machine_id: e.target.value }))}
              placeholder="e.g. LINE-01"
            />
            <Select
              label="Reason *"
              options={DOWNTIME_REASONS}
              value={pauseForm.reason}
              onChange={(e) => setPauseForm((f) => ({ ...f, reason: e.target.value as DowntimeReason }))}
            />
          </div>
          <Input
            label="Notes"
            value={pauseForm.notes}
            onChange={(e) => setPauseForm((f) => ({ ...f, notes: e.target.value }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setPauseOpen(false)}>Cancel</Button>
            <Button type="submit" loading={pause.isPending}>Log Downtime</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
