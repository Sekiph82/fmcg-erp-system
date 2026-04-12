"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { salesApi, SOStatus, SOLineCreate } from "@/lib/sales";
import { productsApi } from "@/lib/products";
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

const statusVariant = (s: SOStatus) =>
  s === "INVOICED" || s === "SHIPPED" ? "green"
  : s === "CONFIRMED" || s === "ALLOCATED" ? "blue"
  : s === "PICKING" ? "yellow"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = [
  { value: "", label: "All" },
  { value: "DRAFT", label: "Draft" },
  { value: "CONFIRMED", label: "Confirmed" },
  { value: "ALLOCATED", label: "Allocated" },
  { value: "PICKING", label: "Picking" },
  { value: "SHIPPED", label: "Shipped" },
  { value: "INVOICED", label: "Invoiced" },
  { value: "CANCELLED", label: "Cancelled" },
];

const UNIT_OPTS = ["PCS", "BOX", "CARTON", "PALLET", "KG", "L"].map((u) => ({ value: u, label: u }));
const CURRENCY_OPTS = ["USD", "EUR", "GBP", "JPY", "CNY", "SGD"].map((c) => ({ value: c, label: c }));

type LineForm = {
  line_no: number;
  product_id: string;
  ordered_quantity: string;
  unit: string;
  unit_price: string;
  discount_pct: string;
  tax_rate: string;
  notes: string;
};

const emptyLine = (n: number): LineForm => ({
  line_no: n,
  product_id: "",
  ordered_quantity: "",
  unit: "PCS",
  unit_price: "0",
  discount_pct: "0",
  tax_rate: "0",
  notes: "",
});

export default function SalesOrdersPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const [form, setForm] = useState({
    order_no: "",
    customer_id: "",
    order_date: new Date().toISOString().slice(0, 10),
    requested_delivery_date: "",
    warehouse_id: "",
    currency: "USD",
    notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine(1)]);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["sales-orders", statusFilter],
    queryFn: () => salesApi.listOrders(statusFilter ? { status: statusFilter as SOStatus } : {}),
  });
  const { data: customers = [] } = useQuery({
    queryKey: ["sales-customers"],
    queryFn: () => salesApi.listCustomers(false),
  });
  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => productsApi.list(),
  });
  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(),
  });

  const createMut = useMutation({
    mutationFn: () =>
      salesApi.createOrder({
        ...form,
        warehouse_id: form.warehouse_id || undefined,
        lines: lines
          .filter((l) => l.product_id && l.ordered_quantity)
          .map((l) => ({
            line_no: l.line_no,
            product_id: l.product_id,
            ordered_quantity: parseFloat(l.ordered_quantity),
            unit: l.unit,
            unit_price: parseFloat(l.unit_price) || 0,
            discount_pct: parseFloat(l.discount_pct) || 0,
            tax_rate: parseFloat(l.tax_rate) || 0,
            notes: l.notes || undefined,
          })),
      }),
    onSuccess: (so) => {
      qc.invalidateQueries({ queryKey: ["sales-orders"] });
      setShowCreate(false);
      resetForm();
      toast("success", `Sales order ${so.order_no} created`);
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const resetForm = () => {
    setForm({
      order_no: "",
      customer_id: "",
      order_date: new Date().toISOString().slice(0, 10),
      requested_delivery_date: "",
      warehouse_id: "",
      currency: "USD",
      notes: "",
    });
    setLines([emptyLine(1)]);
  };

  const updateLine = (idx: number, field: keyof LineForm, val: string) => {
    setLines((prev) => prev.map((l, i) => i === idx ? { ...l, [field]: val } : l));
  };

  const addLine = () => setLines((prev) => [...prev, emptyLine(prev.length + 1)]);
  const removeLine = (idx: number) =>
    setLines((prev) => prev.filter((_, i) => i !== idx).map((l, i) => ({ ...l, line_no: i + 1 })));

  const columns = [
    { header: "Order No", accessor: (r: typeof orders[0]) => (
      <button onClick={() => router.push(`/dashboard/sales/orders/${r.id}`)} className="text-blue-600 hover:underline font-medium">
        {r.order_no}
      </button>
    )},
    { header: "Customer", accessor: (r: typeof orders[0]) => r.customer_name || "—" },
    { header: "Order Date", accessor: (r: typeof orders[0]) => r.order_date },
    { header: "Delivery Date", accessor: (r: typeof orders[0]) => {
      const due = r.days_until_delivery;
      const cls = due !== undefined && due < 0 ? "text-red-600 font-medium" : due !== undefined && due <= 3 ? "text-yellow-600" : "";
      return <span className={cls}>{r.requested_delivery_date}</span>;
    }},
    { header: "Lines", accessor: (r: typeof orders[0]) => r.line_count },
    { header: "Total Value", accessor: (r: typeof orders[0]) =>
      r.total_value !== undefined ? `${r.currency} ${Number(r.total_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "—"
    },
    { header: "Status", accessor: (r: typeof orders[0]) => (
      <Badge label={r.status} variant={statusVariant(r.status)} />
    )},
  ];

  const customerOpts = [{ value: "", label: "Select customer..." }, ...customers.map((c) => ({ value: c.id, label: c.name }))];
  const productOpts = [{ value: "", label: "Select product..." }, ...products.map((p: any) => ({ value: p.id, label: `${p.sku} – ${p.name}` }))];
  const warehouseOpts = [{ value: "", label: "No warehouse" }, ...warehouses.map((w: any) => ({ value: w.id, label: w.name }))];

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sales Orders</h1>
          <p className="text-sm text-gray-500 mt-1">{orders.length} orders</p>
        </div>
        <div className="flex gap-3">
          <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} />
          <Button onClick={() => setShowCreate(true)}>+ New Order</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : (
        <Table columns={columns} data={orders} keyField="id" emptyMessage="No sales orders found." />
      )}

      <Modal open={showCreate} onClose={() => { setShowCreate(false); resetForm(); }} title="Create Sales Order">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Order No" value={form.order_no} onChange={(e) => setForm({ ...form, order_no: e.target.value })} required />
            <Select label="Customer" options={customerOpts} value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Order Date" type="date" value={form.order_date} onChange={(e) => setForm({ ...form, order_date: e.target.value })} />
            <Input label="Requested Delivery" type="date" value={form.requested_delivery_date} onChange={(e) => setForm({ ...form, requested_delivery_date: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Warehouse (optional)" options={warehouseOpts} value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })} />
            <Select label="Currency" options={CURRENCY_OPTS} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
          </div>
          <Input label="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-gray-700">Order Lines</h3>
              <Button variant="secondary" onClick={addLine}>+ Add Line</Button>
            </div>
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {lines.map((line, idx) => (
                <div key={idx} className="border rounded p-3 space-y-2 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-500">Line {line.line_no}</span>
                    {lines.length > 1 && (
                      <button onClick={() => removeLine(idx)} className="text-red-500 text-xs hover:underline">Remove</button>
                    )}
                  </div>
                  <Select options={productOpts} value={line.product_id} onChange={(e) => updateLine(idx, "product_id", e.target.value)} />
                  <div className="grid grid-cols-3 gap-2">
                    <Input placeholder="Qty" type="number" value={line.ordered_quantity} onChange={(e) => updateLine(idx, "ordered_quantity", e.target.value)} />
                    <Select options={UNIT_OPTS} value={line.unit} onChange={(e) => updateLine(idx, "unit", e.target.value)} />
                    <Input placeholder="Unit Price" type="number" value={line.unit_price} onChange={(e) => updateLine(idx, "unit_price", e.target.value)} />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Input placeholder="Discount %" type="number" value={line.discount_pct} onChange={(e) => updateLine(idx, "discount_pct", e.target.value)} />
                    <Input placeholder="Tax Rate" type="number" value={line.tax_rate} onChange={(e) => updateLine(idx, "tax_rate", e.target.value)} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreate(false); resetForm(); }}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} disabled={createMut.isPending || !form.order_no || !form.customer_id || !form.requested_delivery_date}>
              {createMut.isPending ? "Creating..." : "Create"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
