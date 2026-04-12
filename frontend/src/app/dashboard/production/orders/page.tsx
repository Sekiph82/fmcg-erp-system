"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { productionApi, OrderCreate, OrderStatus } from "@/lib/production";
import { productsApi } from "@/lib/products";
import { recipesApi } from "@/lib/recipes";
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

const statusVariant = (s: OrderStatus) =>
  s === "COMPLETED" ? "green"
  : s === "IN_PROGRESS" || s === "RELEASED" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "PLANNED", label: "Planned" },
  { value: "RELEASED", label: "Released" },
  { value: "IN_PROGRESS", label: "In Progress" },
  { value: "COMPLETED", label: "Completed" },
  { value: "CANCELLED", label: "Cancelled" },
];

const UOMS = [
  { value: "KG", label: "KG" }, { value: "L", label: "L" },
  { value: "PCS", label: "PCS" }, { value: "G", label: "G" },
];

const emptyOrder: OrderCreate = {
  order_no: "", product_id: "", recipe_id: "", planned_quantity: 0,
  uom: "KG", target_warehouse_id: "", scheduled_start: "", scheduled_end: "",
};

export default function ProductionOrdersPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<OrderCreate>(emptyOrder);
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "">("");
  const [search, setSearch] = useState("");

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["production-orders", statusFilter],
    queryFn: () => productionApi.listOrders({ status: statusFilter || undefined, limit: 200 }),
  });

  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: () => productsApi.list(0, 200) });
  const { data: recipes = [] } = useQuery({ queryKey: ["recipes"], queryFn: () => recipesApi.list({ status: "APPROVED", limit: 200 }) });
  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: () => warehousesApi.list(0, 100) });

  const filteredRecipes = recipes.filter((r) => !form.product_id || r.product_id === form.product_id);
  const fgWarehouses = warehouses.filter((w) => w.warehouse_type === "FINISHED_GOODS");
  const rmWarehouses = warehouses.filter((w) => w.warehouse_type === "RAW_MATERIAL");

  const create = useMutation({
    mutationFn: productionApi.createOrder,
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ["production-orders"] });
      setOpen(false);
      setForm(emptyOrder);
      toast("success", "Order created", `${o.order_no} created.`);
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const setF = (key: keyof OrderCreate, value: unknown) =>
    setForm((f) => ({ ...f, [key]: value }));

  const filtered = orders.filter(
    (o) =>
      o.order_no.toLowerCase().includes(search.toLowerCase()) ||
      (o.product_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (o.batch_no ?? "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Orders</h1>
          <p className="text-sm text-gray-500 mt-1">{orders.length} total</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ New Order</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          placeholder="Search by order no, product, batch…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as OrderStatus | "")}
          className="w-44"
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <Table
          keyField="id"
          data={filtered}
          emptyMessage="No production orders yet."
          columns={[
            {
              header: "Order No",
              accessor: (o) => (
                <button
                  className="font-mono text-xs text-indigo-600 hover:underline"
                  onClick={() => router.push(`/dashboard/production/orders/${o.id}`)}
                >
                  {o.order_no}
                </button>
              ),
            },
            {
              header: "Product",
              accessor: (o) => (
                <span>
                  <span className="font-mono text-xs text-gray-500">{o.product_sku}</span>{" "}
                  {o.product_name}
                </span>
              ),
            },
            { header: "Batch", accessor: (o) => o.batch_no ?? "—" },
            {
              header: "Planned Qty",
              accessor: (o) => `${Number(o.planned_quantity).toLocaleString()} ${o.uom}`,
            },
            {
              header: "Actual Qty",
              accessor: (o) =>
                o.actual_quantity != null
                  ? `${Number(o.actual_quantity).toLocaleString()} ${o.uom}`
                  : "—",
            },
            {
              header: "Status",
              accessor: (o) => <Badge label={o.status} variant={statusVariant(o.status)} />,
            },
            {
              header: "Scheduled",
              accessor: (o) =>
                o.scheduled_start
                  ? new Date(o.scheduled_start).toLocaleDateString()
                  : "—",
            },
            {
              header: "",
              accessor: (o) => (
                <Button variant="secondary" onClick={() => router.push(`/dashboard/production/orders/${o.id}`)}>
                  View
                </Button>
              ),
            },
          ]}
        />
      )}

      <Modal open={open} onClose={() => { setOpen(false); setForm(emptyOrder); }} title="New Production Order">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Order No *"
              value={form.order_no}
              onChange={(e) => setF("order_no", e.target.value)}
              required
              placeholder="e.g. PO-2026-0001"
            />
            <Input
              label="Batch No"
              value={form.batch_no ?? ""}
              onChange={(e) => setF("batch_no", e.target.value || undefined)}
              placeholder="e.g. BT-20260401-001"
            />
          </div>
          <Select
            label="Product *"
            options={[{ value: "", label: "Select product…" }, ...products.map((p) => ({ value: p.id, label: `${p.sku} — ${p.name}` }))]}
            value={form.product_id}
            onChange={(e) => { setF("product_id", e.target.value); setF("recipe_id", ""); }}
          />
          <Select
            label="Recipe (Approved) *"
            options={[{ value: "", label: "Select recipe…" }, ...filteredRecipes.map((r) => ({ value: r.id, label: `${r.name} v${r.version}` }))]}
            value={form.recipe_id}
            onChange={(e) => setF("recipe_id", e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Planned Quantity *"
              type="number"
              step="0.001"
              value={form.planned_quantity}
              onChange={(e) => setF("planned_quantity", parseFloat(e.target.value) || 0)}
              required
            />
            <Select label="Unit" options={UOMS} value={form.uom} onChange={(e) => setF("uom", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="FG Target Warehouse *"
              options={[{ value: "", label: "Select…" }, ...fgWarehouses.map((w) => ({ value: w.id, label: w.name }))]}
              value={form.target_warehouse_id}
              onChange={(e) => setF("target_warehouse_id", e.target.value)}
            />
            <Select
              label="Material Source Warehouse"
              options={[{ value: "", label: "None (manual)" }, ...rmWarehouses.map((w) => ({ value: w.id, label: w.name }))]}
              value={form.source_warehouse_id ?? ""}
              onChange={(e) => setF("source_warehouse_id", e.target.value || undefined)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Scheduled Start *"
              type="datetime-local"
              onChange={(e) => setF("scheduled_start", e.target.value)}
              required
            />
            <Input
              label="Scheduled End *"
              type="datetime-local"
              onChange={(e) => setF("scheduled_end", e.target.value)}
              required
            />
          </div>
          <Input
            label="Notes"
            value={form.notes ?? ""}
            onChange={(e) => setF("notes", e.target.value || undefined)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setOpen(false); setForm(emptyOrder); }}>Cancel</Button>
            <Button
              type="submit"
              loading={create.isPending}
              disabled={!form.order_no || !form.product_id || !form.recipe_id || !form.target_warehouse_id}
            >
              Create Order
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
