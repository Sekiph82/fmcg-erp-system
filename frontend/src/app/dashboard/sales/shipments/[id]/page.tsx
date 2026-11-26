"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { salesApi } from "@/lib/sales";
import { extractApiError } from "@/lib/inventory";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { tx } from "@/lib/i18n/core";

export default function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [showInvoice, setShowInvoice] = useState(false);
  const [invoiceForm, setInvoiceForm] = useState({
    invoice_no: "",
    invoice_date: new Date().toISOString().slice(0, 10),
    due_date: "",
    notes: "",
  });
  const [dispatchDate, setDispatchDate] = useState(new Date().toISOString().slice(0, 10));

  const { data: shipment, isLoading } = useQuery({
    queryKey: ["sales-shipment", id],
    queryFn: () => salesApi.getShipment(id),
  });

  const startPickingMut = useMutation({
    mutationFn: () => salesApi.startPicking(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-shipment", id] }); toast("success", tx("Picking started")); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const pickLineMut = useMutation({
    mutationFn: (lineId: string) => salesApi.pickLine(id, lineId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-shipment", id] }); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const dispatchMut = useMutation({
    mutationFn: () => salesApi.dispatchShipment(id, dispatchDate),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-shipment", id] }); toast("success", tx("Shipment dispatched")); },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const invoiceMut = useMutation({
    mutationFn: () =>
      salesApi.createInvoiceFromShipment(id, {
        invoice_no: invoiceForm.invoice_no,
        invoice_date: invoiceForm.invoice_date,
        due_date: invoiceForm.due_date,
        notes: invoiceForm.notes || undefined,
      }),
    onSuccess: (inv) => {
      qc.invalidateQueries({ queryKey: ["sales-shipment", id] });
      setShowInvoice(false);
      router.push(`/dashboard/sales/invoices/${inv.id}`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  if (isLoading) return <div className="text-center py-12 text-gray-500">{tx("Loading...")}</div>;
  if (!shipment) return <div className="text-center py-12 text-red-500">{tx("Shipment not found")}</div>;

  const statusColor = (s: string) =>
    s === "DISPATCHED" || s === "DELIVERED" ? "green"
    : s === "PACKED" ? "blue"
    : s === "PICKING" ? "yellow"
    : s === "CANCELLED" ? "red"
    : "blue";

  const canStartPicking = shipment.status === "PENDING";
  const canPickLines = shipment.status === "PICKING";
  const canDispatch = ["PENDING", "PICKING", "PACKED"].includes(shipment.status);
  const canInvoice = shipment.status === "DISPATCHED";

  const allPicked = shipment.lines?.length ? shipment.lines.every((l) => l.is_picked) : false;

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard/sales/shipments")} className="text-gray-400 hover:text-gray-600">←</button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{shipment.shipment_no}</h1>
            <p className="text-sm text-gray-500">SO: {shipment.so_no} • {shipment.customer_name}</p>
          </div>
          <Badge label={shipment.status} variant={statusColor(shipment.status) as "green" | "blue" | "yellow" | "red"} />
        </div>
        <div className="flex gap-2">
          {canStartPicking && (
            <Button onClick={() => startPickingMut.mutate()} disabled={startPickingMut.isPending}>{tx("Start Picking")}</Button>
          )}
          {canDispatch && (
            <div className="flex items-center gap-2">
              <input type="date" value={dispatchDate} onChange={(e) => setDispatchDate(e.target.value)}
                className="border rounded px-2 py-1 text-sm" />
              <Button onClick={() => { if (confirm(tx("Dispatch this shipment? This will issue stock."))) dispatchMut.mutate(); }}
                disabled={dispatchMut.isPending}>
                {dispatchMut.isPending ? tx("Dispatching...") : tx("Dispatch")}
              </Button>
            </div>
          )}
          {canInvoice && (
            <Button variant="secondary" onClick={() => {
              setInvoiceForm({
                invoice_no: `INV-${shipment.shipment_no}`,
                invoice_date: new Date().toISOString().slice(0, 10),
                due_date: "",
                notes: "",
              });
              setShowInvoice(true);
            }}>{tx("Create Invoice")}</Button>
          )}
        </div>
      </div>

      {/* Shipment Info */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: tx("Warehouse"), value: shipment.warehouse_name || "—" },
          { label: tx("Scheduled Date"), value: shipment.scheduled_date },
          { label: tx("Dispatched Date"), value: shipment.dispatched_date || "—" },
          { label: tx("Carrier"), value: shipment.carrier || "—" },
          { label: tx("Tracking"), value: shipment.tracking_number || "—" },
          { label: tx("Lines"), value: `${shipment.line_count}` },
          { label: tx("Picked"), value: `${shipment.picked_count} / ${shipment.line_count}` },
          { label: tx("Progress"), value: shipment.line_count ? `${Math.round((shipment.picked_count / shipment.line_count) * 100)}%` : "—" },
        ].map((item) => (
          <div key={item.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{item.label}</p>
            <p className="font-semibold mt-1">{item.value}</p>
          </div>
        ))}
      </div>

      {/* Picking progress bar */}
      {shipment.line_count > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">{tx("Picking Progress")}</span>
            <span className="text-sm text-gray-500">{shipment.picked_count}/{shipment.line_count}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{ width: `${Math.round((shipment.picked_count / shipment.line_count) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Shipment Lines */}
      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">{tx("Shipment Lines")}</h2>
          {allPicked && shipment.status === "PICKING" && (
            <span className="text-sm text-green-600 font-medium">{tx("All lines picked — auto-advancing to PACKED")}</span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[tx("Product"), "SKU", tx("Lot"), tx("Quantity"), tx("Unit"), tx("Picked"), tx("Stock Movement"), tx("Action")].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {shipment.lines?.map((line) => (
                <tr key={line.id} className={line.is_picked ? "bg-green-50" : ""}>
                  <td className="px-4 py-3 text-sm font-medium">{line.product_name || "—"}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{line.product_sku || "—"}</td>
                  <td className="px-4 py-3 text-sm">{line.lot_number || "—"}</td>
                  <td className="px-4 py-3 text-sm">{Number(line.quantity).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">{line.unit}</td>
                  <td className="px-4 py-3 text-sm">
                    {line.is_picked
                      ? <span className="text-green-600 font-medium">{tx("✓ Picked")}</span>
                      : <span className="text-gray-400">{tx("Pending")}</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {line.stock_movement_id ? <span className="text-xs font-mono">{line.stock_movement_id.slice(0, 8)}…</span> : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {canPickLines && !line.is_picked && (
                      <Button variant="secondary" onClick={() => pickLineMut.mutate(line.id)}>
                        {tx("Mark Picked")}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invoice Modal */}
      <Modal open={showInvoice} onClose={() => setShowInvoice(false)} title={tx("Create Invoice")}>
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{tx("Create an invoice from dispatched shipment quantities.")}</p>
          <Input label={tx("Invoice No")} value={invoiceForm.invoice_no} onChange={(e) => setInvoiceForm({ ...invoiceForm, invoice_no: e.target.value })} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Invoice Date")} type="date" value={invoiceForm.invoice_date} onChange={(e) => setInvoiceForm({ ...invoiceForm, invoice_date: e.target.value })} required />
            <Input label={tx("Due Date")} type="date" value={invoiceForm.due_date} onChange={(e) => setInvoiceForm({ ...invoiceForm, due_date: e.target.value })} required />
          </div>
          <Input label={tx("Notes")} value={invoiceForm.notes} onChange={(e) => setInvoiceForm({ ...invoiceForm, notes: e.target.value })} />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowInvoice(false)}>{tx("Cancel")}</Button>
            <Button onClick={() => invoiceMut.mutate()} disabled={invoiceMut.isPending || !invoiceForm.invoice_no || !invoiceForm.due_date}>
              {invoiceMut.isPending ? tx("Creating...") : tx("Create Invoice")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
