"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { procurementApi, POStatus } from "@/lib/procurement";
import { suppliersApi } from "@/lib/suppliers";
import { materialsApi } from "@/lib/materials";
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

const statusVariant = (s: POStatus) =>
  s === "RECEIVED" ? "green"
  : s === "PARTIALLY_RECEIVED" || s === "ORDERED" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = lx(() => [
  { value: "", label: tx("All") },
  { value: "DRAFT", label: tx("Draft") },
  { value: "APPROVED", label: tx("Approved") },
  { value: "ORDERED", label: tx("Ordered") },
  { value: "PARTIALLY_RECEIVED", label: tx("Partially Received") },
  { value: "RECEIVED", label: tx("Received") },
  { value: "CANCELLED", label: tx("Cancelled") },
]);

const UNIT_OPTS = ["KG", "G", "L", "ML", "PCS", "BOX", "CARTON", "PALLET"].map((u) => ({ value: u, label: u }));

type LineForm = { line_no: number; material_id: string; quantity: string; unit: string; unit_price: string; tax_rate: string };
const emptyLine = (n: number): LineForm => ({ line_no: n, material_id: "", quantity: "", unit: "KG", unit_price: "0", tax_rate: "0" });

export default function PurchaseOrdersPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<POStatus | "">("");
  const [supplierFilter, setSupplierFilter] = useState("");
  const [form, setForm] = useState({
    po_no: "", supplier_id: "", order_date: "", expected_delivery_date: "",
    payment_terms: "", currency: "USD", notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine(1)]);

  const { data: pos = [], isLoading } = useQuery({
    queryKey: ["pos", statusFilter, supplierFilter],
    queryFn: () => procurementApi.listPOs({
      ...(statusFilter ? { status: statusFilter } : {}),
      ...(supplierFilter ? { supplier_id: supplierFilter } : {}),
    }),
  });

  const { hasPermission } = useAuth();
  const { data: suppliers = [] } = useQuery({ queryKey: ["suppliers"], queryFn: () => suppliersApi.list(0, 200), enabled: hasPermission("suppliers.view") });
  const { data: materials = [] } = useQuery({ queryKey: ["materials"], queryFn: () => materialsApi.list(0, 200), enabled: open });

  const suppOpts = [{ value: "", label: tx("All Suppliers") }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))];
  const matOpts = [{ value: "", label: tx("Select material…") }, ...materials.map((m) => ({ value: m.id, label: `${m.code} — ${m.name}` }))];

  const create = useMutation({
    mutationFn: () =>
      procurementApi.createPO({
        ...form,
        exchange_rate: 1.0,
        lines: lines.filter((l) => l.material_id && l.quantity).map((l) => ({
          line_no: l.line_no,
          material_id: l.material_id || undefined,
          ordered_quantity: parseFloat(l.quantity),
          unit: l.unit,
          unit_price: parseFloat(l.unit_price) || 0,
          tax_rate: parseFloat(l.tax_rate) || 0,
        })),
      }),
    onSuccess: (po) => {
      qc.invalidateQueries({ queryKey: ["pos"] });
      setOpen(false);
      toast("success", tx("PO created"), tx("{po_no} created.", { po_no: po.po_no }));
    },
    onError: (e) => toast("error", tx("Failed"), extractApiError(e)),
  });

  const updateLine = (i: number, field: keyof LineForm, val: string) =>
    setLines((ls) => ls.map((l, idx) => idx === i ? { ...l, [field]: val } : l));

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Purchase Orders")}</h1>
          <p className="text-sm text-gray-500 mt-1">{pos.length} {tx("total")}</p>
        </div>
        <Button onClick={() => setOpen(true)}>{tx("+ New PO")}</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as POStatus | "")} className="w-48" />
        <Select options={suppOpts} value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} className="w-52" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="id"
          data={pos}
          emptyMessage="No purchase orders yet."
          columns={[
            {
              header: tx("PO No"),
              accessor: (p) => (
                <button className="font-mono text-xs font-medium text-indigo-600 hover:underline" onClick={() => router.push(`/dashboard/procurement/orders/${p.id}`)}>
                  {p.po_no}
                </button>
              ),
            },
            { header: tx("Supplier"), accessor: (p) => p.supplier_name ?? "—" },
            { header: "PR", accessor: (p) => p.pr_no ? <span className="font-mono text-xs text-gray-500">{p.pr_no}</span> : "—" },
            { header: tx("Order Date"), accessor: (p) => new Date(p.order_date).toLocaleDateString() },
            {
              header: tx("Delivery"),
              accessor: (p) => (
                <span className={(p.days_until_delivery ?? 0) < 0 ? "text-red-600 font-semibold" : (p.days_until_delivery ?? 0) <= 7 ? "text-amber-600" : ""}>
                  {new Date(p.expected_delivery_date).toLocaleDateString()}
                  {p.days_until_delivery != null && (
                    <span className="ml-1 text-xs text-gray-400">
                      {p.days_until_delivery < 0 ? tx("({days_until_delivery}d overdue)", { days_until_delivery: Math.abs(p.days_until_delivery) }) : tx("({days_until_delivery}d)", { days_until_delivery: p.days_until_delivery })}
                    </span>
                  )}
                </span>
              ),
            },
            { header: tx("Currency"), accessor: "currency", className: "text-xs" },
            {
              header: tx("Value"),
              accessor: (p) => p.total_value != null
                ? Number(p.total_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : "—",
            },
            { header: tx("Status"), accessor: (p) => <Badge label={p.status.replace(/_/g, " ")} variant={statusVariant(p.status)} /> },
            {
              header: "",
              accessor: (p) => <Button variant="secondary" onClick={() => router.push(`/dashboard/procurement/orders/${p.id}`)}>{tx("View")}</Button>,
            },
          ]}
        />
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={tx("New Purchase Order")}>
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("PO No *")} value={form.po_no} onChange={(e) => setForm((f) => ({ ...f, po_no: e.target.value }))} placeholder={tx("e.g. PO-2026-001")} required />
            <Input label={tx("Currency")} value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))} />
          </div>
          <Select label={tx("Supplier *")} options={[{ value: "", label: tx("Select…") }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))]}
            value={form.supplier_id} onChange={(e) => setForm((f) => ({ ...f, supplier_id: e.target.value }))} />
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Order Date *")} type="date" onChange={(e) => setForm((f) => ({ ...f, order_date: e.target.value }))} required />
            <Input label={tx("Expected Delivery *")} type="date" onChange={(e) => setForm((f) => ({ ...f, expected_delivery_date: e.target.value }))} required />
          </div>
          <Input label={tx("Payment Terms")} value={form.payment_terms} onChange={(e) => setForm((f) => ({ ...f, payment_terms: e.target.value }))} placeholder={tx("e.g. Net 30")} />

          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold text-gray-700">{tx("Order Lines")}</p>
              <button type="button" className="text-xs text-indigo-600 hover:underline" onClick={() => setLines((ls) => [...ls, emptyLine(ls.length + 1)])}>{tx("+ Add Line")}</button>
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
                    <Input placeholder={tx("Unit price")} value={l.unit_price} onChange={(e) => updateLine(i, "unit_price", e.target.value)} type="number" step="0.0001" />
                  </div>
                  <div className="col-span-1">
                    <Input placeholder={tx("Tax%")} value={l.tax_rate} onChange={(e) => updateLine(i, "tax_rate", e.target.value)} type="number" step="0.01" />
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
            <Button type="submit" loading={create.isPending} disabled={!form.po_no || !form.supplier_id || !form.order_date || !form.expected_delivery_date}>{tx("Create PO")}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
