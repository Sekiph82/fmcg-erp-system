"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { productsApi, Product, ProductCreate, ProductCategory, UnitOfMeasure } from "@/lib/products";
import { extractApiError, extractStructuredError, ProductInUseError } from "@/lib/inventory";
import Link from "next/link";
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

const DELETE_BLOCKERS = [
  { module: "Inventory", detail: "Stock entries, stock lots, and stock movement records for this product." },
  { module: "Sales", detail: "Sales order lines, invoice lines, and delivery lines referencing this product." },
  { module: "Production", detail: "Production plan lines, production orders, and output records for this product." },
  { module: "Recipe", detail: "All recipe versions that have this product as their output." },
  { module: "Procurement", detail: "Purchase order lines, goods receipt lines, and supplier quotes for this product." },
  { module: "Returns", detail: "All customer/supplier return records referencing this product." },
  { module: "Warehouse (WMS)", detail: "Warehouse movement records tied to this product." },
  { module: "Finance – Product Cost", detail: "Cost entries (standard cost per period) for this product." },
];

function ProductsListTab() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<ProductCreate>(empty);
  const [search, setSearch] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteBlockedProduct, setDeleteBlockedProduct] = useState<Product | null>(null);
  const [deleteBlockedRefs, setDeleteBlockedRefs] = useState<ProductInUseError["details"]["references"]>([]);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editForm, setEditForm] = useState<Partial<ProductCreate>>({});

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

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProductCreate> }) =>
      productsApi.update(id, data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      setEditingProduct(null);
      toast("success", "Product updated", `${p.name} saved successfully.`);
    },
    onError: (err) => toast("error", "Failed to update product", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => productsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      toast("success", "Product deleted", "Product removed successfully.");
      setDeletingId(null);
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const blocked = products.find((p) => p.id === deletingId) ?? null;
      if (status === 409) {
        const structured = extractStructuredError(err) as ProductInUseError | null;
        setDeleteBlockedProduct(blocked);
        setDeleteBlockedRefs(structured?.details?.references ?? []);
        setDeletingId(null);
      } else if (status === 403) {
        toast("error", "Permission denied", "You do not have permission to delete products.");
        setDeletingId(null);
      } else if (status === 500 || status === 422) {
        // Fallback for unexpected server errors
        setDeleteBlockedProduct(blocked);
        setDeleteBlockedRefs([]);
        setDeletingId(null);
      } else {
        toast("error", "Failed to delete product", extractApiError(err));
      }
    },
  });

  const set = (key: keyof ProductCreate, value: unknown) => setForm((f) => ({ ...f, [key]: value }));
  const setEdit = (key: keyof ProductCreate, value: unknown) => setEditForm((f) => ({ ...f, [key]: value }));

  const openEdit = (p: Product) => {
    setEditingProduct(p);
    setEditForm({
      sku: p.sku, name: p.name, category: p.category, uom: p.uom,
      units_per_carton: p.units_per_carton, reorder_point: p.reorder_point,
      selling_price: p.selling_price, standard_cost: p.standard_cost,
      shelf_life_days: p.shelf_life_days, is_active: p.is_active,
    });
  };

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
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => openEdit(r)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => setDeletingId(r.id)}
                    className="text-xs text-red-500 hover:text-red-700 hover:underline"
                  >
                    Delete
                  </button>
                </div>
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

      {/* Delete Blocked — explain what must be cleared first */}
      <Modal
        open={!!deleteBlockedProduct}
        onClose={() => { setDeleteBlockedProduct(null); setDeleteBlockedRefs([]); }}
        title="Cannot Delete Product"
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
            <p className="text-sm font-semibold text-red-800">
              &quot;{deleteBlockedProduct?.name}&quot; ({deleteBlockedProduct?.sku}) cannot be deleted.
            </p>
            <p className="text-xs text-red-600 mt-1">
              This product is referenced by existing records. Remove or clear all linked records before deleting.
            </p>
          </div>

          {deleteBlockedRefs.length > 0 ? (
            <div>
              <p className="text-sm font-semibold text-gray-800 mb-2">Blocking dependencies:</p>
              <ol className="space-y-2">
                {deleteBlockedRefs.map((ref, i) => (
                  <li key={ref.module} className="flex gap-3 text-sm">
                    <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-700 font-bold text-xs mt-0.5">
                      {i + 1}
                    </span>
                    <span>
                      <span className="font-semibold text-gray-900">{ref.module}</span>
                      <span className="ml-1 inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{ref.count}</span>
                      <span className="block text-xs text-gray-500 mt-0.5">{ref.hint}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <div>
              <p className="text-sm font-semibold text-gray-800 mb-2">Common places to check:</p>
              <ol className="space-y-2">
                {DELETE_BLOCKERS.map((b, i) => (
                  <li key={b.module} className="flex gap-3 text-sm">
                    <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs mt-0.5">
                      {i + 1}
                    </span>
                    <span>
                      <span className="font-semibold text-gray-900">{b.module}:&nbsp;</span>
                      <span className="text-gray-600">{b.detail}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-xs text-gray-600">
            <p className="font-semibold mb-1">Quick navigation:</p>
            <div className="flex flex-wrap gap-2 mt-1">
              <Link href="/dashboard/inventory" className="text-indigo-600 hover:underline" onClick={() => setDeleteBlockedProduct(null)}>→ Inventory</Link>
              <Link href="/dashboard/movements" className="text-indigo-600 hover:underline" onClick={() => setDeleteBlockedProduct(null)}>→ Stock Movements</Link>
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <Button variant="secondary" onClick={() => { setDeleteBlockedProduct(null); setDeleteBlockedRefs([]); }}>Close</Button>
          </div>
        </div>
      </Modal>

      {/* Edit Product Modal */}
      <Modal open={!!editingProduct} onClose={() => setEditingProduct(null)} title={`Edit Product — ${editingProduct?.sku}`}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (editingProduct) update.mutate({ id: editingProduct.id, data: editForm });
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input label="SKU *" value={editForm.sku ?? ""} onChange={(e) => setEdit("sku", e.target.value)} required />
            <Input label="Name *" value={editForm.name ?? ""} onChange={(e) => setEdit("name", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Category" options={CATEGORIES} value={editForm.category ?? "FOOD"}
              onChange={(e) => setEdit("category", e.target.value as ProductCategory)} />
            <Select label="Unit of Measure" options={UOMS} value={editForm.uom ?? "PCS"}
              onChange={(e) => setEdit("uom", e.target.value as UnitOfMeasure)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Selling Price (Rp)" type="number" step="0.01"
              value={editForm.selling_price ?? ""}
              onChange={(e) => setEdit("selling_price", parseFloat(e.target.value) || undefined)} />
            <Input label="Standard Cost (Rp)" type="number" step="0.01"
              value={editForm.standard_cost ?? ""}
              onChange={(e) => setEdit("standard_cost", parseFloat(e.target.value) || undefined)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Reorder Point" type="number"
              value={editForm.reorder_point ?? 0}
              onChange={(e) => setEdit("reorder_point", parseFloat(e.target.value) || 0)} />
            <Input label="Shelf Life (days)" type="number"
              value={editForm.shelf_life_days ?? ""}
              onChange={(e) => setEdit("shelf_life_days", parseInt(e.target.value) || undefined)} />
          </div>
          <div className="flex items-center gap-2">
            <input
              id="edit-is-active"
              type="checkbox"
              checked={editForm.is_active ?? true}
              onChange={(e) => setEdit("is_active", e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="edit-is-active" className="text-sm text-gray-700">Active product</label>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setEditingProduct(null)}>Cancel</Button>
            <Button type="submit" loading={update.isPending}>Save Changes</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

export default function ProductsPage() {
  const tabs = [
    { key: "products", label: "Products", permission: "products.view", content: <ProductsListTab /> },
  ];
  return (
    <ModuleWorkspace
      title="Products"
      description="Finished goods, SKUs, categories, pricing, units of measure"
      permission="products.view"
      tabs={tabs}
      defaultTab="products"
    />
  );
}
