"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { salesApi, type MpesaTransaction } from "@/lib/sales";
import { warehousesApi } from "@/lib/warehouses";
import { extractApiError } from "@/lib/inventory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { tx as xlate } from "@/lib/i18n/core";

export default function SODetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [showAllocate, setShowAllocate] = useState(false);
  const [allocWarehouse, setAllocWarehouse] = useState("");

  const [showShipment, setShowShipment] = useState(false);
  const [shipForm, setShipForm] = useState({
    shipment_no: "",
    warehouse_id: "",
    scheduled_date: "",
    carrier: "",
    tracking_number: "",
    delivery_notes: "",
  });

  const [showMpesa, setShowMpesa] = useState(false);
  const [mpesaForm, setMpesaForm] = useState({ phone_number: "", amount: "" });

  const { data: so, isLoading } = useQuery({
    queryKey: ["sales-order", id],
    queryFn: () => salesApi.getOrder(id),
  });
  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(),
  });
  const { data: mpesaTxns = [] } = useQuery({
    queryKey: ["mpesa-transactions", id],
    queryFn: () => salesApi.listMpesaTransactions(id),
    enabled: !!so && so.payment_method === "mpesa",
  });

  const warehouseOpts = warehouses.map((w: any) => ({ value: w.id, label: w.name }));

  const confirmMut = useMutation({
    mutationFn: () => salesApi.confirmOrder(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); toast("success", xlate("Order confirmed")); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const discountMut = useMutation({
    mutationFn: (v: { approve: boolean; reason?: string }) => salesApi.decideOrderDiscount(id, v.approve, v.reason),
    onSuccess: (_d, v) => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); toast("success", v.approve ? xlate("Discount approved") : xlate("Discount rejected")); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const allocateMut = useMutation({
    mutationFn: () => salesApi.allocateOrder(id, allocWarehouse),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); setShowAllocate(false); toast("success", xlate("Stock allocated")); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const cancelMut = useMutation({
    mutationFn: () => salesApi.cancelOrder(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); toast("success", xlate("Order cancelled")); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const mpesaMut = useMutation({
    mutationFn: () =>
      salesApi.initiateMpesaPayment(id, {
        phone_number: mpesaForm.phone_number,
        amount: parseFloat(mpesaForm.amount),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales-order", id] });
      qc.invalidateQueries({ queryKey: ["mpesa-transactions", id] });
      setShowMpesa(false);
      setMpesaForm({ phone_number: "", amount: "" });
      toast("success", xlate("M-Pesa payment request sent"));
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const createShipMut = useMutation({
    mutationFn: () =>
      salesApi.createShipment({
        ...shipForm,
        so_id: id,
        lines: so?.lines?.map((l) => ({
          so_line_id: l.id,
          product_id: l.product_id,
          quantity: Number(l.ordered_quantity) - Number(l.shipped_quantity),
          unit: l.unit,
        })).filter((l) => l.quantity > 0) || [],
      }),
    onSuccess: (ship) => {
      qc.invalidateQueries({ queryKey: ["sales-order", id] });
      setShowShipment(false);
      router.push(`/dashboard/sales/shipments/${ship.id}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  if (isLoading) return <div className="text-center py-12 text-gray-500">{xlate("Loading...")}</div>;
  if (!so) return <div className="text-center py-12 text-red-500">{xlate("Order not found")}</div>;

  const statusColor = (s: string) =>
    s === "INVOICED" || s === "SHIPPED" ? "green"
    : s === "CONFIRMED" || s === "ALLOCATED" ? "blue"
    : s === "PICKING" ? "yellow"
    : s === "CANCELLED" ? "red"
    : "blue";

  const canConfirm = so.status === "DRAFT";
  const canAllocate = so.status === "CONFIRMED";
  const canCreateShipment = ["CONFIRMED", "ALLOCATED", "PICKING"].includes(so.status);
  const canCancel = ["DRAFT", "CONFIRMED", "ALLOCATED"].includes(so.status);
  const canRequestMpesa =
    so.payment_method === "mpesa" &&
    so.payment_status !== "paid" &&
    !["CANCELLED", "INVOICED"].includes(so.status);

  const paymentStatusColor = (ps: string) =>
    ps === "paid" ? "green" : ps === "partially_paid" ? "yellow" : ps === "failed" ? "red" : "blue";

  const mpesaTxStatusColor = (s: string) =>
    s === "completed" ? "green" : s === "failed" || s === "cancelled" ? "red" : "yellow";

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard/sales/orders")} className="text-gray-400 hover:text-gray-600">←</button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{so.order_no}</h1>
            <p className="text-sm text-gray-500">{so.customer_name}</p>
          </div>
          <Badge label={so.status} variant={statusColor(so.status) as "green" | "blue" | "yellow" | "red"} />
          {so.payment_method !== "cash" && (
            <Badge
              label={`${so.payment_method.toUpperCase()} · ${so.payment_status.replace("_", " ").toUpperCase()}`}
              variant={paymentStatusColor(so.payment_status) as "green" | "blue" | "yellow" | "red"}
            />
          )}
        </div>
        <div className="flex gap-2">
          {canRequestMpesa && (
            <Button
              variant="secondary"
              onClick={() => {
                setMpesaForm({ phone_number: "", amount: String(so.total_value ?? "") });
                setShowMpesa(true);
              }}
            >
              {xlate("Request M-Pesa Payment")}
            </Button>
          )}
          {so.approval_status === "PENDING_DISCOUNT" && (
            <span className="self-center text-xs px-2 py-1 rounded bg-amber-50 text-amber-800">{xlate("Discount waiting for approval")}</span>
          )}
          {so.approval_status === "DISCOUNT_REJECTED" && (
            <span className="self-center text-xs px-2 py-1 rounded bg-red-50 text-red-700">{xlate("Discount rejected — cancel and enter a new order")}</span>
          )}
          {so.access?.can_discount_approve && (
            <>
              <Button onClick={() => discountMut.mutate({ approve: true })} disabled={discountMut.isPending}>{xlate("Approve discount")}</Button>
              <Button variant="danger" disabled={discountMut.isPending} onClick={() => {
                const reason = window.prompt(xlate("Why is the discount rejected?"));
                if (reason?.trim()) discountMut.mutate({ approve: false, reason });
              }}>{xlate("Reject discount")}</Button>
            </>
          )}
          {canConfirm && !["PENDING_DISCOUNT", "DISCOUNT_REJECTED"].includes(so.approval_status ?? "") && (
            <Button onClick={() => confirmMut.mutate()} disabled={confirmMut.isPending}>{xlate("Confirm")}</Button>
          )}
          {canAllocate && (
            <Button onClick={() => setShowAllocate(true)}>{xlate("Allocate Stock")}</Button>
          )}
          {canCreateShipment && (
            <Button variant="secondary" onClick={() => {
              setShipForm({
                shipment_no: `SHP-${so.order_no}`,
                warehouse_id: so.warehouse_id || "",
                scheduled_date: so.requested_delivery_date,
                carrier: "",
                tracking_number: "",
                delivery_notes: "",
              });
              setShowShipment(true);
            }}>{xlate("Create Shipment")}</Button>
          )}
          {canCancel && (
            <Button variant="danger" onClick={() => { if (confirm(xlate("Cancel this order?"))) cancelMut.mutate(); }}>{xlate("Cancel")}</Button>
          )}
        </div>
      </div>

      {/* Order Info */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Customer")}</p>
          <p className="font-semibold mt-1">{so.customer_name}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Order Date")}</p>
          <p className="font-semibold mt-1">{so.order_date}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Requested Delivery")}</p>
          <p className={`font-semibold mt-1 ${(so.days_until_delivery ?? 0) < 0 ? "text-red-600" : ""}`}>
            {so.requested_delivery_date}
            {so.days_until_delivery !== undefined && (
              <span className="text-xs ml-2 text-gray-400">
                {so.days_until_delivery >= 0 ? xlate("({days_until_delivery}d)", { days_until_delivery: so.days_until_delivery }) : xlate("({days_until_delivery}d overdue)", { days_until_delivery: Math.abs(so.days_until_delivery) })}
              </span>
            )}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Warehouse")}</p>
          <p className="font-semibold mt-1">{so.warehouse_name || "—"}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Currency")}</p>
          <p className="font-semibold mt-1">{so.currency}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Total Value")}</p>
          <p className="font-semibold mt-1 text-green-700">
            {so.total_value !== undefined
              ? `${so.currency} ${Number(so.total_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
              : "—"}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Payment Method")}</p>
          <p className="font-semibold mt-1 capitalize">{so.payment_method}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{xlate("Payment Status")}</p>
          <p className={`font-semibold mt-1 capitalize ${so.payment_status === "paid" ? "text-green-700" : so.payment_status === "failed" ? "text-red-600" : "text-gray-900"}`}>
            {so.payment_status.replace("_", " ")}
          </p>
          {so.mpesa_reference && (
            <p className="text-xs text-gray-400 mt-1">{xlate("Ref:")} {so.mpesa_reference}</p>
          )}
        </div>
      </div>

      {/* Order Lines */}
      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-900">{xlate("Order Lines")}</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["#", xlate("Product"), xlate("Ordered"), xlate("Allocated"), xlate("Shipped"), xlate("Pending"), xlate("Unit Price"), xlate("Discount"), xlate("Tax"), xlate("Line Total")].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {so.lines?.map((line) => (
                <tr key={line.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-500">{line.line_no}</td>
                  <td className="px-4 py-3 text-sm font-medium">{line.product_name || line.product_id}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.ordered_quantity).toLocaleString()} {line.unit}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.allocated_quantity).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.shipped_quantity).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm font-medium text-blue-700">{Number(line.pending_quantity).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.unit_price).toFixed(2)}</td>
                  <td className="px-4 py-3 text-sm">{(Number(line.discount_pct) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm">{(Number(line.tax_rate) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm font-semibold">{Number(line.line_total).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Shipments */}
      {so.shipments && so.shipments.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-6 py-4 border-b">
            <h2 className="font-semibold text-gray-900">{xlate("Shipments")}</h2>
          </div>
          <div className="divide-y">
            {(so.shipments as any[]).map((ship: any) => (
              <div key={ship.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{ship.shipment_no}</p>
                  <p className="text-sm text-gray-500">{ship.scheduled_date} • {ship.status}</p>
                </div>
                <Button variant="secondary" onClick={() => router.push(`/dashboard/sales/shipments/${ship.id}`)}>
                  {xlate("View")}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invoices */}
      {so.invoices && so.invoices.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-6 py-4 border-b">
            <h2 className="font-semibold text-gray-900">{xlate("Invoices")}</h2>
          </div>
          <div className="divide-y">
            {(so.invoices as any[]).map((inv: any) => (
              <div key={inv.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{inv.invoice_no}</p>
                  <p className="text-sm text-gray-500">{inv.invoice_date} • {inv.status}</p>
                </div>
                <Button variant="secondary" onClick={() => router.push(`/dashboard/sales/invoices/${inv.id}`)}>
                  {xlate("View")}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* M-Pesa Transaction History */}
      {so.payment_method === "mpesa" && (
        <div className="bg-white rounded-lg border">
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">{xlate("M-Pesa Transactions")}</h2>
            {canRequestMpesa && (
              <Button
                variant="secondary"
                onClick={() => {
                  setMpesaForm({ phone_number: "", amount: String(so.total_value ?? "") });
                  setShowMpesa(true);
                }}
              >
                {xlate("+ Request Payment")}
              </Button>
            )}
          </div>
          {mpesaTxns.length === 0 ? (
            <p className="px-6 py-4 text-sm text-gray-400">{xlate("No M-Pesa transactions yet.")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {[xlate("Date"), xlate("Phone"), xlate("Amount"), xlate("Status"), xlate("Reference"), xlate("Description")].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {(mpesaTxns as MpesaTransaction[]).map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-500">{new Date(tx.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm">{tx.phone_number}</td>
                      <td className="px-4 py-3 text-sm font-medium">{Number(tx.amount).toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm">
                        <Badge label={tx.status} variant={mpesaTxStatusColor(tx.status) as "green" | "blue" | "yellow" | "red"} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{tx.mpesa_reference || "—"}</td>
                      <td className="px-4 py-3 text-sm text-gray-400">{tx.result_description || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Allocate Modal */}
      <Modal open={showAllocate} onClose={() => setShowAllocate(false)} title={xlate("Allocate Stock")}>
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{xlate("Select a warehouse to reserve stock for this order.")}</p>
          <Select label={xlate("Warehouse")} options={warehouseOpts} value={allocWarehouse} onChange={(e) => setAllocWarehouse(e.target.value)} />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowAllocate(false)}>{xlate("Cancel")}</Button>
            <Button onClick={() => allocateMut.mutate()} disabled={allocateMut.isPending || !allocWarehouse}>
              {allocateMut.isPending ? xlate("Allocating...") : xlate("Allocate")}
            </Button>
          </div>
        </div>
      </Modal>

      {/* M-Pesa Payment Modal */}
      <Modal open={showMpesa} onClose={() => setShowMpesa(false)} title={xlate("Request M-Pesa Payment")}>
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            {xlate("An STK Push will be sent to the customer's phone to prompt payment.")}
          </p>
          <Input
            label={xlate("Phone Number (e.g. 254712345678)")}
            value={mpesaForm.phone_number}
            onChange={(e) => setMpesaForm({ ...mpesaForm, phone_number: e.target.value })}
            required
          />
          <Input
            label={xlate("Amount ({currency})", { currency: so.currency })}
            type="number"
            value={mpesaForm.amount}
            onChange={(e) => setMpesaForm({ ...mpesaForm, amount: e.target.value })}
            required
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowMpesa(false)}>{xlate("Cancel")}</Button>
            <Button
              onClick={() => mpesaMut.mutate()}
              disabled={mpesaMut.isPending || !mpesaForm.phone_number || !mpesaForm.amount}
            >
              {mpesaMut.isPending ? xlate("Sending...") : xlate("Send STK Push")}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Shipment Modal */}
      <Modal open={showShipment} onClose={() => setShowShipment(false)} title={xlate("Create Shipment")}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={xlate("Shipment No")} value={shipForm.shipment_no} onChange={(e) => setShipForm({ ...shipForm, shipment_no: e.target.value })} required />
            <Select label={xlate("Warehouse")} options={warehouseOpts} value={shipForm.warehouse_id} onChange={(e) => setShipForm({ ...shipForm, warehouse_id: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={xlate("Scheduled Date")} type="date" value={shipForm.scheduled_date} onChange={(e) => setShipForm({ ...shipForm, scheduled_date: e.target.value })} required />
            <Input label={xlate("Carrier")} value={shipForm.carrier} onChange={(e) => setShipForm({ ...shipForm, carrier: e.target.value })} />
          </div>
          <Input label={xlate("Tracking Number")} value={shipForm.tracking_number} onChange={(e) => setShipForm({ ...shipForm, tracking_number: e.target.value })} />
          <Input label={xlate("Delivery Notes")} value={shipForm.delivery_notes} onChange={(e) => setShipForm({ ...shipForm, delivery_notes: e.target.value })} />
          <p className="text-xs text-gray-500">{xlate("Shipment lines will be auto-populated from pending SO lines.")}</p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowShipment(false)}>{xlate("Cancel")}</Button>
            <Button onClick={() => createShipMut.mutate()} disabled={createShipMut.isPending || !shipForm.shipment_no || !shipForm.warehouse_id || !shipForm.scheduled_date}>
              {createShipMut.isPending ? xlate("Creating...") : xlate("Create Shipment")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
