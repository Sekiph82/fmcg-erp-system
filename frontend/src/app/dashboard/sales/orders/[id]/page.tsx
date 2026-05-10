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
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); toast("success", "Order confirmed"); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const allocateMut = useMutation({
    mutationFn: () => salesApi.allocateOrder(id, allocWarehouse),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); setShowAllocate(false); toast("success", "Stock allocated"); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const cancelMut = useMutation({
    mutationFn: () => salesApi.cancelOrder(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-order", id] }); toast("success", "Order cancelled"); },
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
      toast("success", "M-Pesa payment request sent");
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

  if (isLoading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!so) return <div className="text-center py-12 text-red-500">Order not found</div>;

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
              Request M-Pesa Payment
            </Button>
          )}
          {canConfirm && (
            <Button onClick={() => confirmMut.mutate()} disabled={confirmMut.isPending}>Confirm</Button>
          )}
          {canAllocate && (
            <Button onClick={() => setShowAllocate(true)}>Allocate Stock</Button>
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
            }}>Create Shipment</Button>
          )}
          {canCancel && (
            <Button variant="danger" onClick={() => { if (confirm("Cancel this order?")) cancelMut.mutate(); }}>Cancel</Button>
          )}
        </div>
      </div>

      {/* Order Info */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Customer</p>
          <p className="font-semibold mt-1">{so.customer_name}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Order Date</p>
          <p className="font-semibold mt-1">{so.order_date}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Requested Delivery</p>
          <p className={`font-semibold mt-1 ${(so.days_until_delivery ?? 0) < 0 ? "text-red-600" : ""}`}>
            {so.requested_delivery_date}
            {so.days_until_delivery !== undefined && (
              <span className="text-xs ml-2 text-gray-400">
                {so.days_until_delivery >= 0 ? `(${so.days_until_delivery}d)` : `(${Math.abs(so.days_until_delivery)}d overdue)`}
              </span>
            )}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Warehouse</p>
          <p className="font-semibold mt-1">{so.warehouse_name || "—"}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Currency</p>
          <p className="font-semibold mt-1">{so.currency}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Value</p>
          <p className="font-semibold mt-1 text-green-700">
            {so.total_value !== undefined
              ? `${so.currency} ${Number(so.total_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
              : "—"}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Payment Method</p>
          <p className="font-semibold mt-1 capitalize">{so.payment_method}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Payment Status</p>
          <p className={`font-semibold mt-1 capitalize ${so.payment_status === "paid" ? "text-green-700" : so.payment_status === "failed" ? "text-red-600" : "text-gray-900"}`}>
            {so.payment_status.replace("_", " ")}
          </p>
          {so.mpesa_reference && (
            <p className="text-xs text-gray-400 mt-1">Ref: {so.mpesa_reference}</p>
          )}
        </div>
      </div>

      {/* Order Lines */}
      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-900">Order Lines</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["#", "Product", "Ordered", "Allocated", "Shipped", "Pending", "Unit Price", "Discount", "Tax", "Line Total"].map((h) => (
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
            <h2 className="font-semibold text-gray-900">Shipments</h2>
          </div>
          <div className="divide-y">
            {(so.shipments as any[]).map((ship: any) => (
              <div key={ship.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{ship.shipment_no}</p>
                  <p className="text-sm text-gray-500">{ship.scheduled_date} • {ship.status}</p>
                </div>
                <Button variant="secondary" onClick={() => router.push(`/dashboard/sales/shipments/${ship.id}`)}>
                  View
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
            <h2 className="font-semibold text-gray-900">Invoices</h2>
          </div>
          <div className="divide-y">
            {(so.invoices as any[]).map((inv: any) => (
              <div key={inv.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{inv.invoice_no}</p>
                  <p className="text-sm text-gray-500">{inv.invoice_date} • {inv.status}</p>
                </div>
                <Button variant="secondary" onClick={() => router.push(`/dashboard/sales/invoices/${inv.id}`)}>
                  View
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
            <h2 className="font-semibold text-gray-900">M-Pesa Transactions</h2>
            {canRequestMpesa && (
              <Button
                variant="secondary"
                onClick={() => {
                  setMpesaForm({ phone_number: "", amount: String(so.total_value ?? "") });
                  setShowMpesa(true);
                }}
              >
                + Request Payment
              </Button>
            )}
          </div>
          {mpesaTxns.length === 0 ? (
            <p className="px-6 py-4 text-sm text-gray-400">No M-Pesa transactions yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {["Date", "Phone", "Amount", "Status", "Reference", "Description"].map((h) => (
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
      <Modal open={showAllocate} onClose={() => setShowAllocate(false)} title="Allocate Stock">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">Select a warehouse to reserve stock for this order.</p>
          <Select label="Warehouse" options={warehouseOpts} value={allocWarehouse} onChange={(e) => setAllocWarehouse(e.target.value)} />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowAllocate(false)}>Cancel</Button>
            <Button onClick={() => allocateMut.mutate()} disabled={allocateMut.isPending || !allocWarehouse}>
              {allocateMut.isPending ? "Allocating..." : "Allocate"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* M-Pesa Payment Modal */}
      <Modal open={showMpesa} onClose={() => setShowMpesa(false)} title="Request M-Pesa Payment">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            An STK Push will be sent to the customer&apos;s phone to prompt payment.
          </p>
          <Input
            label="Phone Number (e.g. 254712345678)"
            value={mpesaForm.phone_number}
            onChange={(e) => setMpesaForm({ ...mpesaForm, phone_number: e.target.value })}
            required
          />
          <Input
            label={`Amount (${so.currency})`}
            type="number"
            value={mpesaForm.amount}
            onChange={(e) => setMpesaForm({ ...mpesaForm, amount: e.target.value })}
            required
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowMpesa(false)}>Cancel</Button>
            <Button
              onClick={() => mpesaMut.mutate()}
              disabled={mpesaMut.isPending || !mpesaForm.phone_number || !mpesaForm.amount}
            >
              {mpesaMut.isPending ? "Sending..." : "Send STK Push"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Shipment Modal */}
      <Modal open={showShipment} onClose={() => setShowShipment(false)} title="Create Shipment">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Shipment No" value={shipForm.shipment_no} onChange={(e) => setShipForm({ ...shipForm, shipment_no: e.target.value })} required />
            <Select label="Warehouse" options={warehouseOpts} value={shipForm.warehouse_id} onChange={(e) => setShipForm({ ...shipForm, warehouse_id: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Scheduled Date" type="date" value={shipForm.scheduled_date} onChange={(e) => setShipForm({ ...shipForm, scheduled_date: e.target.value })} required />
            <Input label="Carrier" value={shipForm.carrier} onChange={(e) => setShipForm({ ...shipForm, carrier: e.target.value })} />
          </div>
          <Input label="Tracking Number" value={shipForm.tracking_number} onChange={(e) => setShipForm({ ...shipForm, tracking_number: e.target.value })} />
          <Input label="Delivery Notes" value={shipForm.delivery_notes} onChange={(e) => setShipForm({ ...shipForm, delivery_notes: e.target.value })} />
          <p className="text-xs text-gray-500">Shipment lines will be auto-populated from pending SO lines.</p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowShipment(false)}>Cancel</Button>
            <Button onClick={() => createShipMut.mutate()} disabled={createShipMut.isPending || !shipForm.shipment_no || !shipForm.warehouse_id || !shipForm.scheduled_date}>
              {createShipMut.isPending ? "Creating..." : "Create Shipment"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
