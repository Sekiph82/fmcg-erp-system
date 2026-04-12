"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { productsApi, ProductCreate, ProductCategory, UnitOfMeasure } from "@/lib/products";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { ImportModal } from "@/components/import/ImportModal";

const CATEGORIES: { value: string; label: string }[] = [
  { value: "FOOD", label: "Food" },
  { value: "BEVERAGE", label: "Beverage" },
  { value: "PERSONAL_CARE", label: "Personal Care" },
  { value: "HOUSEHOLD", label: "Household" },
  { value: "OTHER", label: "Other" },
];

const UOMS: { value: string; label: string }[] = [
  { value: "PCS", label: "PCS" }, { value: "KG", label: "KG" },
  { value: "G", label: "G" }, { value: "L", label: "L" },
  { value: "ML", label: "ML" }, { value: "BOX", label: "BOX" },
  { value: "CARTON", label: "CARTON" }, { value: "PALLET", label: "PALLET" },
];

const empty: ProductCreate = { sku: "", name: "", category: "FOOD", uom: "PCS", units_per_carton: 1, reorder_point: 0, is_active: true };

export default function ProductsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<ProductCreate>(empty);
  const [search, setSearch] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products"],
    queryFn: () => productsApi.list(0, 200),
  });

  const create = useMutation({
    mutationFn: productsApi.create,
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      setOpen(false);
      setForm(empty);
      toast("success", "Product created", `${p.name} (${p.sku}) added successfully.`);
    },
    onError: (err) => toast("error", "Failed to create product", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => productsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      toast("success", "Product deleted", "Product removed successfully.");
      setDeletingId(null);
    },
    onError: (err) => toast("error", "Failed to delete product", extractApiError(err)),
  });

  const set = (key: keyof ProductCreate, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const filtered = products.filter(
    (p) => p.name.toLowerCase().includes(search.toLowerCase()) || p.sku.toLowerCase().includes(search.toLowerCase())
  );

  const deletingProduct = products.find((p) => p.id === deletingId);

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Products</h1>
          <p className="text-sm text-gray-500 mt-1">{products.length} total</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal module="products" onSuccess={() => qc.invalidateQueries({ queryKey: ["products"] })} />
          <Button onClick={() => setOpen(true)}>+ Add Product</Button>
        </div>
      </div>

      <div className="mb-4">
        <Input placeholder="Search by name or SKU…" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-xs" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="id"
          data={filtered}
          emptyMessage={search ? "No products match your search." : "No products yet. Add your first product."}
          columns={[
            { header: "SKU", accessor: "sku", className: "font-mono text-xs font-medium" },
            { header: "Name", accessor: "name" },
            { header: "Category", accessor: (r) => <Badge label={r.category} variant="blue" /> },
            { header: "UOM", accessor: "uom" },
            { header: "Reorder Point", accessor: (r) => Number(r.reorder_point).toLocaleString() },
            { header: "Selling Price", accessor: (r) => r.selling_price ? `Rp ${Number(r.selling_price).toLocaleString()}` : "—" },
            { header: "Status", accessor: (r) => <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "red"} /> },
            {
              header: "",
              accessor: (r) => (
                <button
                  onClick={() => setDeletingId(r.id)}
                  className="text-xs text-red-500 hover:text-red-700 hover:underline"
                >
                  Delete
                </button>
              ),
            },
          ]}
        />
      )}

      {/* Add Product Modal */}
      <Modal open={open} onClose={() => { setOpen(false); setForm(empty); }} title="Add Product">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="SKU *" value={form.sku} onChange={(e) => set("sku", e.target.value)} required />
            <Input label="Name *" value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Category" options={CATEGORIES} value={form.category}
              onChange={(e) => set("category", e.target.value as ProductCategory)} />
            <Select label="Unit of Measure" options={UOMS} value={form.uom}
              onChange={(e) => set("uom", e.target.value as UnitOfMeasure)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Selling Price (Rp)" type="number" step="0.01"
              onChange={(e) => set("selling_price", parseFloat(e.target.value) || undefined)} />
            <Input label="Standard Cost (Rp)" type="number" step="0.01"
              onChange={(e) => set("standard_cost", parseFloat(e.target.value) || undefined)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Reorder Point" type="number" defaultValue={0}
              onChange={(e) => set("reorder_point", parseFloat(e.target.value) || 0)} />
            <Input label="Shelf Life (days)" type="number"
              onChange={(e) => set("shelf_life_days", parseInt(e.target.value) || undefined)} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setOpen(false); setForm(empty); }}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create Product</Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete Product">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete{" "}
          <span className="font-semibold text-gray-900">{deletingProduct?.name}</span>{" "}
          <span className="font-mono text-xs text-gray-500">({deletingProduct?.sku})</span>?
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeletingId(null)}>Cancel</Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deletingId && deleteMutation.mutate(deletingId)}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
