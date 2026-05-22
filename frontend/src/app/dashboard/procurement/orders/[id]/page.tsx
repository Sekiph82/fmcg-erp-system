"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { procurementApi, type SupplierPayment } from "@/lib/procurement";
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

const statusVariant = (s: string) =>
  s === "RECEIVED" ? "green"
  : s === "PARTIALLY_RECEIVED" || s === "ORDERED" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

type GRNLineForm = {
  po_line_id: string;
  material_id: string;
  material_name: string;
  ordered_quantity: number;
  unit: string;
  received_quantity: string;
  accepted_quantity: string;
  rejected_quantity: string;
  lot_number: string;
  expiry_date: string;
};

export default function PODetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [grnOpen, setGrnOpen] = useState(false);
  const [shipOpen, setShipOpen] = useState(false);
  const [evalOpen, setEvalOpen] = useState(false);
  const [payOpen, setPayOpen] = useState(false);
  const [payForm, setPayForm] = useState({ payment_date: "", amount: "", method: "bank", reference: "", notes: "" });
  const [grnForm, setGrnForm] = useState({ grn_no: "", received_date: "", warehouse_id: "", notes: "" });
  const [grnLines, setGrnLines] = useState<GRNLineForm[]>([]);
  const [shipForm, setShipForm] = useState({
    shipment_no: "", bl_number: "", vessel_name: "", port_of_loading: "",
    port_of_discharge: "", eta: "", customs_ref: "",
    landed_cost_freight: "", landed_cost_insurance: "", landed_cost_duties: "", landed_cost_other: "",
  });
  const [evalForm, setEvalForm] = useState({
    evaluation_date: "", on_time_delivery_score: "", quality_score: "",
    price_competitiveness_score: "", responsiveness_score: "", notes: "",
  });

  const { data: po, isLoading } = useQuery({
    queryKey: ["po", id],
    queryFn: () => procurementApi.getPO(id),
    enabled: !!id,
  });

  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(0, 100),
    enabled: grnOpen,
  });

  const { data: grns = [] } = useQuery({
    queryKey: ["grns", id],
    queryFn: () => procurementApi.listGRNs({ po_id: id }),
    enabled: !!id,
  });

  const { data: shipment } = useQuery({
    queryKey: ["shipment", id],
    queryFn: () => procurementApi.listShipments({ po_id: id }).then((r) => r[0] ?? null),
    enabled: !!id,
  });

  const { data: payments = [] } = useQuery({
    queryKey: ["po-payments", id],
    queryFn: () => procurementApi.listPayments(id),
    enabled: !!id,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["po", id] });
    qc.invalidateQueries({ queryKey: ["grns", id] });
    qc.invalidateQueries({ queryKey: ["shipment", id] });
    qc.invalidateQueries({ queryKey: ["pos"] });
    qc.invalidateQueries({ queryKey: ["po-payments", id] });
  };

  const approvePO = useMutation({
    mutationFn: () => procurementApi.approvePO(id),
    onSuccess: () => { invalidate(); toast("success", "Approved", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const markOrdered = useMutation({
    mutationFn: () => procurementApi.markOrdered(id),
    onSuccess: () => { invalidate(); toast("success", "Marked as Ordered", "Awaiting delivery."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const cancelPO = useMutation({
    mutationFn: () => procurementApi.cancelPO(id),
    onSuccess: () => { invalidate(); toast("success", "Cancelled", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const createGRN = useMutation({
    mutationFn: () => procurementApi.createGRN({
      ...grnForm,
      po_id: id,
      lines: grnLines.map((l) => ({
        po_line_id: l.po_line_id || undefined,
        material_id: l.material_id || undefined,
        received_quantity: parseFloat(l.received_quantity) || 0,
        accepted_quantity: parseFloat(l.accepted_quantity) || 0,
        rejected_quantity: parseFloat(l.rejected_quantity) || 0,
        unit: l.unit,
        lot_number: l.lot_number || undefined,
        expiry_date: l.expiry_date || undefined,
      })),
    }),
    onSuccess: (grn) => {
      invalidate();
      setGrnOpen(false);
      toast("success", "GRN created", `${grn.grn_no} — post it to update stock.`);
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const postGRN = useMutation({
    mutationFn: (grnId: string) => procurementApi.postGRN(grnId),
    onSuccess: () => { invalidate(); toast("success", "Posted", "Stock updated from GRN."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const createShipment = useMutation({
    mutationFn: () => procurementApi.createShipment({
      ...shipForm,
      po_id: id,
      landed_cost_freight: shipForm.landed_cost_freight ? parseFloat(shipForm.landed_cost_freight) : undefined,
      landed_cost_insurance: shipForm.landed_cost_insurance ? parseFloat(shipForm.landed_cost_insurance) : undefined,
      landed_cost_duties: shipForm.landed_cost_duties ? parseFloat(shipForm.landed_cost_duties) : undefined,
      landed_cost_other: shipForm.landed_cost_other ? parseFloat(shipForm.landed_cost_other) : undefined,
      eta: shipForm.eta || undefined,
    }),
    onSuccess: () => { invalidate(); setShipOpen(false); toast("success", "Shipment linked", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const recordPayment = useMutation({
    mutationFn: () => procurementApi.recordPayment(id, {
      payment_date: payForm.payment_date,
      amount: parseFloat(payForm.amount),
      method: payForm.method,
      reference: payForm.reference || undefined,
      notes: payForm.notes || undefined,
    }),
    onSuccess: () => {
      invalidate();
      setPayOpen(false);
      setPayForm({ payment_date: "", amount: "", method: "bank", reference: "", notes: "" });
      toast("success", "Payment recorded", "");
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const createEval = useMutation({
    mutationFn: () => procurementApi.createEvaluation({
      supplier_id: po!.supplier_id,
      po_id: id,
      ...evalForm,
      on_time_delivery_score: parseFloat(evalForm.on_time_delivery_score),
      quality_score: parseFloat(evalForm.quality_score),
      price_competitiveness_score: parseFloat(evalForm.price_competitiveness_score),
      responsiveness_score: parseFloat(evalForm.responsiveness_score),
    }),
    onSuccess: () => { setEvalOpen(false); toast("success", "Evaluation saved", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  if (isLoading) return <div className="flex justify-center py-24"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>;
  if (!po) return <div className="text-center py-16 text-gray-500">PO not found.</div>;

  const isDraft = po.status === "DRAFT";
  const isApproved = po.status === "APPROVED";
  const isOrdered = po.status === "ORDERED";
  const isPartial = po.status === "PARTIALLY_RECEIVED";
  const isReceived = po.status === "RECEIVED";
  const canReceive = isOrdered || isPartial;
  const canPay = po.status !== "CANCELLED" && po.payment_status !== "paid";

  const payStatusVariant = (s: string) =>
    s === "paid" ? "green" : s === "partially_paid" ? "blue" : "blue";
  const payMethodColor = (m: string) =>
    m === "mpesa" ? "text-green-700 font-semibold" : "text-gray-700";

  const openGRN = () => {
    setGrnLines(po.lines.map((l) => ({
      po_line_id: l.id,
      material_id: l.material_id ?? "",
      material_name: l.material_name ?? l.description ?? "—",
      ordered_quantity: l.ordered_quantity,
      unit: l.unit,
      received_quantity: String(l.pending_quantity),
      accepted_quantity: String(l.pending_quantity),
      rejected_quantity: "0",
      lot_number: "",
      expiry_date: "",
    })));
    setGrnOpen(true);
  };

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button className="text-sm text-indigo-600 hover:underline mb-2 block" onClick={() => router.push("/dashboard/procurement/orders")}>
              ← Back to Purchase Orders
            </button>
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{po.po_no}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {po.supplier_name}
              {po.pr_no && ` · PR: ${po.pr_no}`}
              {` · ${po.currency}`}
              {po.payment_terms && ` · ${po.payment_terms}`}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Order date: {new Date(po.order_date).toLocaleDateString()} ·
              Expected delivery: <span className={(po.days_until_delivery ?? 0) < 0 ? "text-red-600 font-semibold" : ""}>{new Date(po.expected_delivery_date).toLocaleDateString()}</span>
              {po.days_until_delivery != null && (
                <span className="ml-1">
                  {po.days_until_delivery < 0 ? `(${Math.abs(po.days_until_delivery)}d overdue)` : `(in ${po.days_until_delivery}d)`}
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-2">
              <Badge label={po.status.replace(/_/g, " ")} variant={statusVariant(po.status)} />
              <Badge
                label={`Payment: ${po.payment_status.replace(/_/g, " ")}`}
                variant={payStatusVariant(po.payment_status)}
              />
            </div>
            <div className="flex gap-2 flex-wrap justify-end">
              {isDraft && <Button onClick={() => approvePO.mutate()} loading={approvePO.isPending}>Approve</Button>}
              {isApproved && <Button onClick={() => markOrdered.mutate()} loading={markOrdered.isPending}>Mark as Ordered</Button>}
              {canReceive && <Button onClick={openGRN}>Record Receipt</Button>}
              {canPay && (
                <Button variant="secondary" onClick={() => {
                  setPayForm((f) => ({ ...f, amount: String(po.total_value ?? ""), payment_date: new Date().toISOString().split("T")[0] }));
                  setPayOpen(true);
                }}>Record Payment</Button>
              )}
              {isReceived && <Button variant="secondary" onClick={() => setEvalOpen(true)}>Evaluate Supplier</Button>}
              {!shipment && (isOrdered || isPartial) && (
                <Button variant="secondary" onClick={() => setShipOpen(true)}>Link Shipment</Button>
              )}
              {(isDraft || isApproved || isOrdered) && (
                <Button variant="secondary" onClick={() => cancelPO.mutate()} loading={cancelPO.isPending}>Cancel</Button>
              )}
            </div>
          </div>
        </div>

        {/* Value summary */}
        <div className="mt-4 grid grid-cols-4 gap-4 pt-4 border-t border-gray-100">
          <div>
            <p className="text-xs text-gray-500">Total Value</p>
            <p className="text-xl font-bold">
              {po.total_value != null ? Number(po.total_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"} {po.currency}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Paid</p>
            <p className={`text-xl font-bold ${po.payment_status === "paid" ? "text-green-600" : "text-gray-900"}`}>
              {po.paid_amount != null ? Number(po.paid_amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0.00"} {po.currency}
            </p>
            {po.mpesa_reference && (
              <p className="text-xs text-gray-400 mt-0.5">M-Pesa: {po.mpesa_reference}</p>
            )}
          </div>
          <div>
            <p className="text-xs text-gray-500">Lines</p>
            <p className="text-xl font-bold">{po.lines.length}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Receipts</p>
            <p className="text-xl font-bold">{grns.length}</p>
          </div>
        </div>
      </div>

      {/* Shipment card */}
      {shipment && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-start justify-between flex-wrap gap-2">
            <div>
              <p className="text-sm font-semibold text-blue-800 mb-1">Import Shipment: {shipment.shipment_no}</p>
              <div className="text-xs text-blue-700 space-y-0.5">
                {shipment.vessel_name && <p>Vessel: {shipment.vessel_name}</p>}
                {shipment.bl_number && <p>B/L: {shipment.bl_number}</p>}
                {shipment.port_of_loading && <p>{shipment.port_of_loading} → {shipment.port_of_discharge}</p>}
                {shipment.eta && <p>ETA: {new Date(shipment.eta).toLocaleDateString()}</p>}
                {shipment.ata && <p>ATA: {new Date(shipment.ata).toLocaleDateString()}</p>}
                {shipment.customs_ref && <p>Customs ref: {shipment.customs_ref}</p>}
              </div>
            </div>
            <div className="text-right">
              <Badge label={shipment.status.replace(/_/g, " ")} variant="blue" />
              {shipment.total_landed_cost > 0 && (
                <p className="text-xs text-blue-700 mt-1">
                  Landed cost: {Number(shipment.total_landed_cost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* PO Lines */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Order Lines</h2>
        <Table
          keyField="id"
          data={po.lines}
          emptyMessage="No lines."
          columns={[
            { header: "#", accessor: "line_no", className: "w-10 text-gray-400 text-xs" },
            {
              header: "Material / Item",
              accessor: (l) => (
                <span>
                  {l.material_code && <span className="font-mono text-xs text-gray-400 mr-1">{l.material_code}</span>}
                  {l.material_name || l.product_name || l.description || "—"}
                </span>
              ),
            },
            { header: "Ordered", accessor: (l) => `${Number(l.ordered_quantity).toFixed(3)} ${l.unit}` },
            { header: "Received", accessor: (l) => <span className={l.received_quantity >= l.ordered_quantity ? "text-green-600 font-medium" : ""}>{Number(l.received_quantity).toFixed(3)}</span> },
            { header: "Pending", accessor: (l) => <span className={l.pending_quantity > 0 ? "text-amber-600" : "text-gray-400"}>{Number(l.pending_quantity).toFixed(3)}</span> },
            { header: "Unit Price", accessor: (l) => Number(l.unit_price).toFixed(4) },
            { header: "Tax %", accessor: (l) => `${(Number(l.tax_rate) * 100).toFixed(1)}%` },
            { header: "Line Total", accessor: (l) => Number(l.line_total).toLocaleString(undefined, { minimumFractionDigits: 2 }) },
          ]}
        />
      </div>

      {/* GRNs */}
      {grns.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Goods Receipts</h2>
          <Table
            keyField="id"
            data={grns}
            emptyMessage=""
            columns={[
              { header: "GRN No", accessor: (g) => <span className="font-mono text-xs font-medium">{g.grn_no}</span> },
              { header: "Received Date", accessor: (g) => new Date(g.received_date).toLocaleDateString() },
              { header: "Warehouse", accessor: (g) => g.warehouse_name ?? "—" },
              { header: "Status", accessor: (g) => <Badge label={g.status} variant={g.status === "POSTED" ? "green" : "blue"} /> },
              {
                header: "",
                accessor: (g) => g.status === "DRAFT"
                  ? <Button onClick={() => postGRN.mutate(g.id)} loading={postGRN.isPending}>Post to Stock</Button>
                  : <span className="text-xs text-gray-400">Posted</span>,
              },
            ]}
          />
        </div>
      )}

      {/* Payment History */}
      {payments.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Payment History</h2>
          <Table
            keyField="id"
            data={payments as SupplierPayment[]}
            emptyMessage=""
            columns={[
              { header: "Date", accessor: (p) => new Date(p.payment_date).toLocaleDateString() },
              {
                header: "Method",
                accessor: (p) => (
                  <span className={payMethodColor(p.method)}>
                    {p.method.toUpperCase()}
                  </span>
                ),
              },
              { header: "Amount", accessor: (p) => `${Number(p.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
              { header: "Reference", accessor: (p) => p.reference || "—" },
              { header: "Notes", accessor: (p) => p.notes || "—" },
            ]}
          />
        </div>
      )}

      {/* Record Payment Modal */}
      <Modal open={payOpen} onClose={() => setPayOpen(false)} title="Record Supplier Payment">
        <form onSubmit={(e) => { e.preventDefault(); recordPayment.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Payment Date *" type="date" value={payForm.payment_date} onChange={(e) => setPayForm((f) => ({ ...f, payment_date: e.target.value }))} required />
            <Input label={`Amount (${po.currency}) *`} type="number" step="0.01" value={payForm.amount} onChange={(e) => setPayForm((f) => ({ ...f, amount: e.target.value }))} required />
          </div>
          <Select
            label="Payment Method *"
            options={[
              { value: "bank", label: "Bank Transfer" },
              { value: "cash", label: "Cash" },
              { value: "mpesa", label: "M-Pesa" },
            ]}
            value={payForm.method}
            onChange={(e) => setPayForm((f) => ({ ...f, method: e.target.value }))}
          />
          <Input
            label={payForm.method === "mpesa" ? "M-Pesa Receipt Number" : "Reference / Transaction ID"}
            value={payForm.reference}
            onChange={(e) => setPayForm((f) => ({ ...f, reference: e.target.value }))}
            placeholder={payForm.method === "mpesa" ? "e.g. RCK0X1234XYZ" : ""}
          />
          <Input label="Notes" value={payForm.notes} onChange={(e) => setPayForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setPayOpen(false)}>Cancel</Button>
            <Button type="submit" loading={recordPayment.isPending} disabled={!payForm.payment_date || !payForm.amount}>
              Save Payment
            </Button>
          </div>
        </form>
      </Modal>

      {/* GRN Modal */}
      <Modal open={grnOpen} onClose={() => setGrnOpen(false)} title="Record Goods Receipt">
        <form onSubmit={(e) => { e.preventDefault(); createGRN.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="GRN No *" value={grnForm.grn_no} onChange={(e) => setGrnForm((f) => ({ ...f, grn_no: e.target.value }))} placeholder="e.g. GRN-2026-001" required />
            <Input label="Received Date *" type="date" onChange={(e) => setGrnForm((f) => ({ ...f, received_date: e.target.value }))} required />
          </div>
          <Select
            label="Warehouse *"
            options={[{ value: "", label: "Select…" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))]}
            value={grnForm.warehouse_id}
            onChange={(e) => setGrnForm((f) => ({ ...f, warehouse_id: e.target.value }))}
          />

          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">Receipt Lines</p>
            <div className="space-y-3">
              {grnLines.map((l, i) => (
                <div key={i} className="rounded-lg border border-gray-200 p-3 space-y-2">
                  <p className="text-xs font-medium text-gray-600">{l.material_name} — Ordered: {l.ordered_quantity} {l.unit}</p>
                  <div className="grid grid-cols-3 gap-2">
                    <Input label="Received Qty" type="number" step="0.001" value={l.received_quantity}
                      onChange={(e) => setGrnLines((ls) => ls.map((r, idx) => idx === i ? { ...r, received_quantity: e.target.value, accepted_quantity: e.target.value } : r))} />
                    <Input label="Accepted Qty" type="number" step="0.001" value={l.accepted_quantity}
                      onChange={(e) => setGrnLines((ls) => ls.map((r, idx) => idx === i ? { ...r, accepted_quantity: e.target.value } : r))} />
                    <Input label="Rejected Qty" type="number" step="0.001" value={l.rejected_quantity}
                      onChange={(e) => setGrnLines((ls) => ls.map((r, idx) => idx === i ? { ...r, rejected_quantity: e.target.value } : r))} />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Input label="Lot Number" value={l.lot_number}
                      onChange={(e) => setGrnLines((ls) => ls.map((r, idx) => idx === i ? { ...r, lot_number: e.target.value } : r))} />
                    <Input label="Expiry Date" type="date" value={l.expiry_date}
                      onChange={(e) => setGrnLines((ls) => ls.map((r, idx) => idx === i ? { ...r, expiry_date: e.target.value } : r))} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setGrnOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createGRN.isPending} disabled={!grnForm.grn_no || !grnForm.received_date || !grnForm.warehouse_id}>Save Receipt</Button>
          </div>
        </form>
      </Modal>

      {/* Shipment Modal */}
      <Modal open={shipOpen} onClose={() => setShipOpen(false)} title="Link Import Shipment">
        <form onSubmit={(e) => { e.preventDefault(); createShipment.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Shipment No *" value={shipForm.shipment_no} onChange={(e) => setShipForm((f) => ({ ...f, shipment_no: e.target.value }))} required />
            <Input label="B/L Number" value={shipForm.bl_number} onChange={(e) => setShipForm((f) => ({ ...f, bl_number: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Vessel Name" value={shipForm.vessel_name} onChange={(e) => setShipForm((f) => ({ ...f, vessel_name: e.target.value }))} />
            <Input label="ETA" type="date" value={shipForm.eta} onChange={(e) => setShipForm((f) => ({ ...f, eta: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Port of Loading" value={shipForm.port_of_loading} onChange={(e) => setShipForm((f) => ({ ...f, port_of_loading: e.target.value }))} />
            <Input label="Port of Discharge" value={shipForm.port_of_discharge} onChange={(e) => setShipForm((f) => ({ ...f, port_of_discharge: e.target.value }))} />
          </div>
          <Input label="Customs Reference" value={shipForm.customs_ref} onChange={(e) => setShipForm((f) => ({ ...f, customs_ref: e.target.value }))} />
          <p className="text-xs font-semibold text-gray-600">Landed Costs</p>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Freight" type="number" step="0.01" value={shipForm.landed_cost_freight} onChange={(e) => setShipForm((f) => ({ ...f, landed_cost_freight: e.target.value }))} />
            <Input label="Insurance" type="number" step="0.01" value={shipForm.landed_cost_insurance} onChange={(e) => setShipForm((f) => ({ ...f, landed_cost_insurance: e.target.value }))} />
            <Input label="Duties" type="number" step="0.01" value={shipForm.landed_cost_duties} onChange={(e) => setShipForm((f) => ({ ...f, landed_cost_duties: e.target.value }))} />
            <Input label="Other" type="number" step="0.01" value={shipForm.landed_cost_other} onChange={(e) => setShipForm((f) => ({ ...f, landed_cost_other: e.target.value }))} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setShipOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createShipment.isPending} disabled={!shipForm.shipment_no}>Save Shipment</Button>
          </div>
        </form>
      </Modal>

      {/* Supplier Evaluation Modal */}
      <Modal open={evalOpen} onClose={() => setEvalOpen(false)} title="Evaluate Supplier">
        <form onSubmit={(e) => { e.preventDefault(); createEval.mutate(); }} className="space-y-4">
          <p className="text-xs text-gray-500">Score each dimension 0–100</p>
          <Input label="Evaluation Date *" type="date" onChange={(e) => setEvalForm((f) => ({ ...f, evaluation_date: e.target.value }))} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="On-Time Delivery" type="number" min="0" max="100" value={evalForm.on_time_delivery_score} onChange={(e) => setEvalForm((f) => ({ ...f, on_time_delivery_score: e.target.value }))} />
            <Input label="Quality" type="number" min="0" max="100" value={evalForm.quality_score} onChange={(e) => setEvalForm((f) => ({ ...f, quality_score: e.target.value }))} />
            <Input label="Price Competitiveness" type="number" min="0" max="100" value={evalForm.price_competitiveness_score} onChange={(e) => setEvalForm((f) => ({ ...f, price_competitiveness_score: e.target.value }))} />
            <Input label="Responsiveness" type="number" min="0" max="100" value={evalForm.responsiveness_score} onChange={(e) => setEvalForm((f) => ({ ...f, responsiveness_score: e.target.value }))} />
          </div>
          <Input label="Notes" value={evalForm.notes} onChange={(e) => setEvalForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setEvalOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createEval.isPending}
              disabled={!evalForm.evaluation_date || !evalForm.on_time_delivery_score || !evalForm.quality_score || !evalForm.price_competitiveness_score || !evalForm.responsiveness_score}>
              Save Evaluation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
