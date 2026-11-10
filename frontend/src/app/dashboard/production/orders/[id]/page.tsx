"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import {
  productionApi, CompleteOrderRequest, DowntimeReason,
} from "@/lib/production";
import { advProductionApi, WorkOrder, WorkOrderGenealogy } from "@/lib/productionAdvanced";
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
  const [selectedRoutingId, setSelectedRoutingId] = useState("");
  const [splitTarget, setSplitTarget] = useState<WorkOrder | null>(null);
  const [splitQuantities, setSplitQuantities] = useState(["", ""]);
  const [mergeSelection, setMergeSelection] = useState<string[]>([]);
  const [genealogyTarget, setGenealogyTarget] = useState<string | null>(null);
  const [reworkTarget, setReworkTarget] = useState<WorkOrder | null>(null);
  const [reworkForm, setReworkForm] = useState({ quantity: "", reason: "" });
  const [completeForm, setCompleteForm] = useState<CompleteOrderRequest>({
    actual_quantity: 0, consume_materials: true,
  });
  const [pauseForm, setPauseForm] = useState({ machine_id: "", reason: "BREAKDOWN" as DowntimeReason, notes: "" });

  const { data: order, isLoading } = useQuery({
    queryKey: ["production-order", id],
    queryFn: () => productionApi.getOrder(id),
    enabled: !!id,
  });

  useEffect(() => {
    setSelectedRoutingId("");
  }, [id]);

  const { data: transitionHistory = [], isLoading: historyLoading } = useQuery({
    queryKey: ["production-order-transition-history", id],
    queryFn: () => productionApi.getOrderTransitionHistory(id),
    enabled: !!id,
  });

  const { data: routedWorkOrders = [] } = useQuery<WorkOrder[]>({
    queryKey: ["production-work-orders", id],
    queryFn: () => advProductionApi.listWorkOrders({ production_order_id: id }),
    enabled: !!id,
  });

  const { data: availableRoutings = [] } = useQuery({
    queryKey: ["production-order-routings", order?.product_id],
    queryFn: () => advProductionApi.listRoutings({ product_id: order!.product_id }),
    enabled: Boolean(order?.product_id),
  });

  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(0, 100),
  });

  const rmWarehouses = warehouses.filter((w) => w.warehouse_type === "RAW_MATERIAL");

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["production-order", id] });
    qc.invalidateQueries({ queryKey: ["production-order-transition-history", id] });
  };

  const approve = useMutation({
    mutationFn: () => productionApi.approveOrder(id),
    onSuccess: () => { invalidate(); toast("success", "Approved", "Approval recorded; release remains a separate action."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

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

  const generateOperations = useMutation({
    mutationFn: () => advProductionApi.generateWorkOrdersFromRouting({
      production_order_id: id,
      routing_id: selectedRoutingId,
    }),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["production-work-orders", id] });
      setSelectedRoutingId("");
      toast("success", "Operations added", `${created.length} routing operations linked in sequence.`);
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const splitOperation = useMutation({
    mutationFn: () => advProductionApi.splitWorkOrder(
      splitTarget!.id,
      splitQuantities.map((quantity) => Number(quantity)),
    ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-work-orders", id] });
      setSplitTarget(null);
      setSplitQuantities(["", ""]);
      toast("success", "Operation split", "The original operation was preserved and linked to its two replacements.");
    },
    onError: (err) => toast("error", "Split failed", extractApiError(err)),
  });

  const mergeOperations = useMutation({
    mutationFn: () => advProductionApi.mergeWorkOrders(mergeSelection),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-work-orders", id] });
      setMergeSelection([]);
      toast("success", "Operations merged", "The source operations were preserved and linked to the replacement.");
    },
    onError: (err) => toast("error", "Merge failed", extractApiError(err)),
  });

  const reworkOperation = useMutation({
    mutationFn: () => advProductionApi.reworkWorkOrder(
      reworkTarget!.id,
      Number(reworkForm.quantity),
      reworkForm.reason,
    ),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["production-work-orders", id] });
      invalidate();
      setReworkTarget(null);
      setReworkForm({ quantity: "", reason: "" });
      toast("success", "Rework operation created", `${created.work_order_id} is linked to the completed source operation.`);
    },
    onError: (err) => toast("error", "Rework failed", extractApiError(err)),
  });

  const { data: workOrderGenealogy = [] } = useQuery<WorkOrderGenealogy[]>({
    queryKey: ["production-work-order-genealogy", genealogyTarget],
    queryFn: () => advProductionApi.getWorkOrderGenealogy(genealogyTarget!),
    enabled: Boolean(genealogyTarget),
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
  const isApproved = Boolean(order.approved_by && order.approved_at);
  const activeWorkOrders = routedWorkOrders.filter((workOrder) => workOrder.status !== "cancelled");
  const activeRoutedWorkOrders = activeWorkOrders.filter((workOrder) => workOrder.routing_step_id);
  const finalRoutingStepNumber = activeRoutedWorkOrders.reduce(
    (maximum, workOrder) => Math.max(maximum, workOrder.routing_step_number ?? 0),
    0,
  );
  const activeManualGroups = new Set(activeWorkOrders
    .filter((workOrder) => !workOrder.routing_step_id)
    .map((workOrder) => `${workOrder.work_center_id}:${workOrder.operation.trim()}`));
  const hasMixedRoutingModes = activeRoutedWorkOrders.length > 0
    && activeManualGroups.size > 0;
  const isReworkEligible = (workOrder: WorkOrder) => {
    if (hasMixedRoutingModes) return false;
    if (workOrder.routing_step_id) {
      const routingIds = new Set(activeRoutedWorkOrders.map((item) => item.routing_id).filter(Boolean));
      return routingIds.size === 1
        && workOrder.routing_step_number === finalRoutingStepNumber;
    }
    return activeManualGroups.size === 1;
  };

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
              {isPlanned && !isApproved && !order.created_by && (
                <span className="text-xs text-amber-700">Creator attribution is required before approval</span>
              )}
              {isPlanned && !isApproved && order.created_by && (
                <Button variant="secondary" onClick={() => approve.mutate()} loading={approve.isPending}>
                  Approve
                </Button>
              )}
              {isPlanned && isApproved && (
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
              {(isPlanned || isReleased) && !isCompleted && !isCancelled && (
                <Button variant="secondary" onClick={() => cancel.mutate()} loading={cancel.isPending}>
                  Cancel
                </Button>
              )}
            </div>
          </div>
        </div>

        {isApproved && (
          <p className="mt-3 text-xs text-gray-500">
            Approved by <span className="font-mono">{order.approved_by}</span>
            {order.approved_at && <> at {new Date(order.approved_at).toLocaleString()}</>}
          </p>
        )}

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
            <p className="text-xs text-gray-500">Backordered Qty</p>
            <p className="text-lg font-semibold">
              {Number(order.backordered_quantity ?? 0).toLocaleString()} <span className="text-sm font-normal text-gray-400">{order.uom}</span>
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

      {order.backorder_of_id && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          This order is a backorder of{" "}
          <button className="font-mono underline" onClick={() => router.push(`/dashboard/production/orders/${order.backorder_of_id}`)}>
            the source production order
          </button>
          . It remains unapproved until an authorized user approves it.
        </div>
      )}
      {order.backorders.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="font-semibold text-amber-950">Backorder created from this order</h2>
          <p className="mt-1 text-sm text-amber-900">
            The unproduced quantity is recorded separately. The new order stays planned and requires approval before release.
          </p>
          <ul className="mt-3 space-y-2">
            {order.backorders.map((backorder) => (
              <li key={backorder.id}>
                <button
                  className="font-mono text-sm text-indigo-700 underline"
                  onClick={() => router.push(`/dashboard/production/orders/${backorder.id}`)}
                >{backorder.order_no}</button>
                <span className="ml-2 text-sm text-gray-700">
                  {Number(backorder.planned_quantity).toLocaleString()} {order.uom} · {backorder.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Routed Work Orders */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Routing Operations</h2>
            <p className="text-sm text-gray-500">Work orders follow the selected routing step order and work-center assignments.</p>
          </div>
          {isPlanned && !isApproved && (
            <div className="flex items-end gap-2 flex-wrap">
              {routedWorkOrders.length > 0 && mergeSelection.length >= 2 && (
                <Button
                  disabled={mergeOperations.isPending}
                  loading={mergeOperations.isPending}
                  onClick={() => mergeOperations.mutate()}
                >
                  Merge {mergeSelection.length} Operations
                </Button>
              )}
              {routedWorkOrders.length === 0 && <>
              <Select
                label="Active Routing"
                options={[
                  { value: "", label: "Select routing…" },
                  ...availableRoutings.filter((routing) => routing.is_active && routing.steps.length > 0).map((routing) => ({
                    value: routing.id,
                    label: `${routing.routing_id} v${routing.version} · ${routing.steps.length} steps`,
                  })),
                ]}
                value={selectedRoutingId}
                onChange={(e) => setSelectedRoutingId(e.target.value)}
              />
              <Button
                disabled={!selectedRoutingId || generateOperations.isPending}
                loading={generateOperations.isPending}
                onClick={() => generateOperations.mutate()}
              >
                Generate Operations
              </Button>
              </>}
            </div>
          )}
        </div>
        {routedWorkOrders.length === 0 ? (
          <p className="text-sm text-gray-500">No work-order operations are linked to this production order.</p>
        ) : (
          <Table
            keyField="id"
            data={routedWorkOrders}
            emptyMessage="No work-order operations are linked to this production order."
            columns={[
              {
                header: "Merge",
                accessor: (workOrder) => workOrder.status === "planned" && isPlanned && !isApproved ? (
                  <input
                    type="checkbox"
                    aria-label={`Select ${workOrder.work_order_id} for merge`}
                    checked={mergeSelection.includes(workOrder.id)}
                    onChange={(event) => setMergeSelection((current) => event.target.checked
                      ? [...current, workOrder.id]
                      : current.filter((selected) => selected !== workOrder.id))}
                  />
                ) : "—",
              },
              { header: "Step", accessor: (workOrder) => workOrder.routing_step_number ?? "Manual" },
              { header: "Work Order", accessor: (workOrder) => <span className="font-mono text-xs">{workOrder.work_order_id}</span> },
              { header: "Operation", accessor: (workOrder) => workOrder.operation },
              { header: "Rework", accessor: (workOrder) => workOrder.rework_of_id
                ? <span title={workOrder.rework_reason}>Rework · {workOrder.rework_reason}</span>
                : Number(workOrder.rework_quantity ?? 0) > 0
                  ? `${Number(workOrder.rework_quantity).toLocaleString()} ${order.uom} sent to rework`
                  : "—" },
              { header: "Work Center", accessor: (workOrder) => workOrder.work_center_name ?? "—" },
              { header: "Planned Qty", accessor: (workOrder) => workOrder.planned_quantity == null ? "—" : `${Number(workOrder.planned_quantity).toLocaleString()} ${order.uom}` },
              { header: "Actual Qty", accessor: (workOrder) => workOrder.actual_quantity == null ? "—" : `${Number(workOrder.actual_quantity).toLocaleString()} ${order.uom}` },
              { header: "Status", accessor: (workOrder) => <Badge label={workOrder.status} variant={workOrder.status === "completed" ? "green" : workOrder.status === "in_progress" ? "blue" : "blue"} /> },
              {
                header: "Actions",
                accessor: (workOrder) => <div className="flex gap-2 whitespace-nowrap">
                  {isInProgress && isReworkEligible(workOrder) && workOrder.status === "completed" &&
                    Number(workOrder.actual_quantity ?? 0) > Number(workOrder.rework_quantity ?? 0) && (
                    <button
                      className="text-xs font-medium text-amber-700 hover:underline"
                      onClick={() => {
                        setReworkTarget(workOrder);
                        setReworkForm({ quantity: "", reason: "" });
                      }}
                    >Rework</button>
                  )}
                  {workOrder.status === "planned" && isPlanned && !isApproved && Number(workOrder.planned_quantity ?? 0) > 0 && (
                    <button
                      className="text-xs font-medium text-indigo-700 hover:underline"
                      onClick={() => {
                        const first = (Number(workOrder.planned_quantity ?? 0) / 2).toFixed(3);
                        setSplitTarget(workOrder);
                        setSplitQuantities([first, (Number(workOrder.planned_quantity ?? 0) - Number(first)).toFixed(3)]);
                      }}
                    >Split</button>
                  )}
                  <button
                    className="text-xs font-medium text-indigo-700 hover:underline"
                    onClick={() => setGenealogyTarget(workOrder.id)}
                  >History</button>
                </div>,
              },
            ]}
          />
        )}
        {genealogyTarget && (
          <div className="mt-4 rounded-lg border border-gray-200 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-medium text-gray-800">Split / merge / rework history</h3>
              <button className="text-sm text-indigo-700 hover:underline" onClick={() => setGenealogyTarget(null)}>Close</button>
            </div>
            {workOrderGenealogy.length === 0 ? (
              <p className="text-sm text-gray-500">No transformation history for this operation.</p>
            ) : (
              <ul className="space-y-1 text-sm text-gray-600">
                {workOrderGenealogy.map((edge) => (
                  <li key={edge.id}>
                    {edge.action}: {edge.source_work_order_code} → {edge.result_work_order_code} · {Number(edge.transferred_quantity).toLocaleString()} {order.uom} · {new Date(edge.created_at).toLocaleString()}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <Modal open={Boolean(reworkTarget)} onClose={() => setReworkTarget(null)} title="Create Rework Operation">
        {reworkTarget && (
          <form
            onSubmit={(event) => { event.preventDefault(); reworkOperation.mutate(); }}
            className="space-y-4"
          >
            <p className="text-sm text-gray-600">
              A rework operation can be created for completed output while its production order is still in progress. It reuses the source step and work center, preserves batch lineage, and must complete before the parent order can close. Completed parent orders stay immutable.
            </p>
            <p className="text-xs text-gray-500">
              Unreworked source output: {Math.max(0, Number(reworkTarget.actual_quantity ?? 0) - Number(reworkTarget.rework_quantity ?? 0)).toLocaleString()} {order.uom}
            </p>
            <Input
              label="Quantity to rework *"
              type="number"
              min="0.001"
              max={Math.max(0, Number(reworkTarget.actual_quantity ?? 0) - Number(reworkTarget.rework_quantity ?? 0))}
              step="0.001"
              value={reworkForm.quantity}
              onChange={(event) => setReworkForm((current) => ({ ...current, quantity: event.target.value }))}
            />
            <Input
              label="Reason *"
              value={reworkForm.reason}
              onChange={(event) => setReworkForm((current) => ({ ...current, reason: event.target.value }))}
            />
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setReworkTarget(null)}>Cancel</Button>
              <Button
                type="submit"
                loading={reworkOperation.isPending}
                disabled={!Number(reworkForm.quantity) || Number(reworkForm.quantity) > Number(reworkTarget.actual_quantity ?? 0) - Number(reworkTarget.rework_quantity ?? 0) || reworkForm.reason.trim().length < 3}
              >Create Rework</Button>
            </div>
          </form>
        )}
      </Modal>

      {/* OEE card */}
      {order.oee && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">OEE Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "OEE", value: order.oee.oee, color: order.oee.oee == null ? "text-gray-500" : order.oee.oee >= 0.85 ? "text-green-600" : order.oee.oee >= 0.65 ? "text-yellow-600" : "text-red-500" },
              { label: "Availability", value: order.oee.availability, color: order.oee.availability == null ? "text-gray-500" : "text-blue-600" },
              { label: "Performance", value: order.oee.performance, color: order.oee.performance == null ? "text-gray-500" : "text-indigo-600" },
              { label: "Quality", value: order.oee.quality, color: order.oee.quality == null ? "text-gray-500" : "text-purple-600" },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-center p-4 rounded-lg bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className={`text-2xl font-bold ${color}`}>{value == null ? "—" : String((value * 100).toFixed(1)) + "%"}</p>
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

      <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Immutable transition history</h2>
        {historyLoading ? <p className="text-sm text-gray-400">Loading history…</p> : transitionHistory.length === 0 ? (
          <p className="text-sm text-gray-500">No recorded transitions yet. History starts with events created after the audit-history migration; earlier events are not backfilled.</p>
        ) : (
          <ol className="divide-y divide-gray-100">
            {transitionHistory.map((event) => (
              <li key={event.id} className="py-3 grid gap-1 md:grid-cols-[1fr_auto]">
                <div>
                  <p className="text-sm font-medium text-gray-800">{event.action.replace(/_/g, " ")}</p>
                  <p className="text-xs text-gray-500">
                    {event.entity_type.replace(/_/g, " ")} · {event.from_status || "—"} → {event.to_status || "—"}
                  </p>
                  {event.entity_id !== event.parent_entity_id && <p className="text-xs font-mono text-gray-400">Operation: {event.entity_id}</p>}
                </div>
                <div className="text-xs text-gray-500 md:text-right">
                  <p>{new Date(event.created_at).toLocaleString()}</p>
                  <p>Actor: {event.actor_label}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* Complete Modal */}
      <Modal open={completeOpen} onClose={() => setCompleteOpen(false)} title="Complete Production Order">
        <form onSubmit={(e) => { e.preventDefault(); complete.mutate(); }} className="space-y-4">
          <p className="text-sm text-gray-500">
            Materials and finished goods are posted for the actual quantity. If this order has recorded WIP, the quantity must match its available WIP balance. Any unproduced remainder becomes a linked planned backorder, which requires separate approval before release.
          </p>
          <Input
            label="Actual Quantity Produced *"
            type="number"
            min="0.001"
            max={order.planned_quantity}
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
            <Button
              type="submit"
              loading={complete.isPending}
              disabled={!completeForm.actual_quantity || completeForm.actual_quantity > Number(order.planned_quantity)}
            >
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

      <Modal
        open={Boolean(splitTarget)}
        onClose={() => { setSplitTarget(null); setSplitQuantities(["", ""]); }}
        title={`Split ${splitTarget?.work_order_id ?? "work order"}`}
      >
        <form
          onSubmit={(event) => { event.preventDefault(); splitOperation.mutate(); }}
          className="space-y-4"
        >
          <p className="text-sm text-gray-600">
            Enter two planned quantities whose sum exactly matches the source. The source stays in history as cancelled; no actual production data is moved.
          </p>
          <Input
            label={`First quantity (${order.uom})`}
            type="number"
            min="0.001"
            step="0.001"
            value={splitQuantities[0]}
            onChange={(event) => setSplitQuantities(([_, second]) => [event.target.value, second])}
            required
          />
          <Input
            label={`Second quantity (${order.uom})`}
            type="number"
            min="0.001"
            step="0.001"
            value={splitQuantities[1]}
            onChange={(event) => setSplitQuantities(([first]) => [first, event.target.value])}
            required
          />
          <p className="text-xs text-gray-500">
            Source planned quantity: {Number(splitTarget?.planned_quantity ?? 0).toLocaleString()} {order.uom}
          </p>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setSplitTarget(null)}>Cancel</Button>
            <Button
              type="submit"
              loading={splitOperation.isPending}
              disabled={(() => {
                const values = splitQuantities.map(Number);
                const sourceMilli = Math.round(Number(splitTarget?.planned_quantity ?? 0) * 1000);
                return !splitTarget
                  || values.some((value) => !Number.isFinite(value) || value <= 0 || Math.abs(value * 1000 - Math.round(value * 1000)) > 0.000001)
                  || Math.round(values[0] * 1000) + Math.round(values[1] * 1000) !== sourceMilli;
              })()}
            >
              Split Work Order
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
