"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { recipesApi, RecipeCreate, RecipeStatus } from "@/lib/recipes";
import { productsApi } from "@/lib/products";
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

const STATUS_FILTER_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "APPROVED", label: "Approved" },
  { value: "OBSOLETE", label: "Obsolete" },
];

const statusVariant = (s: RecipeStatus) =>
  s === "APPROVED" ? "green" : s === "DRAFT" ? "blue" : "red";

const empty: RecipeCreate = {
  product_id: "",
  version: "1.0",
  name: "",
  description: "",
  is_active: true,
};

export default function RecipesPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<RecipeCreate>(empty);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<RecipeStatus | "">("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: recipes = [], isLoading } = useQuery({
    queryKey: ["recipes", statusFilter],
    queryFn: () =>
      recipesApi.list({ status: statusFilter || undefined, limit: 200 }),
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => productsApi.list(0, 200),
  });

  const productOptions = products.map((p) => ({
    value: p.id,
    label: `${p.sku} — ${p.name}`,
  }));

  const create = useMutation({
    mutationFn: recipesApi.create,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["recipes"] });
      setOpen(false);
      setForm(empty);
      toast("success", "Recipe created", `${r.name} v${r.version} created as DRAFT.`);
    },
    onError: (err) => toast("error", "Failed to create recipe", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => recipesApi.deleteRecipe(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recipes"] });
      toast("success", "Recipe deleted", "Draft recipe removed.");
      setDeletingId(null);
    },
    onError: (err) => toast("error", "Failed to delete recipe", extractApiError(err)),
  });

  const deletingRecipe = recipes.find((r) => r.id === deletingId);

  const set = (key: keyof RecipeCreate, value: unknown) =>
    setForm((f) => ({ ...f, [key]: value }));

  const filtered = recipes.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      (r.product_sku ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (r.product_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      r.version.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recipes / Formulations</h1>
          <p className="text-sm text-gray-500 mt-1">{recipes.length} total</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal
            module="recipes"
            onSuccess={() => qc.invalidateQueries({ queryKey: ["recipes"] })}
          />
          <Button onClick={() => setOpen(true)}>+ New Recipe</Button>
        </div>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          placeholder="Search by name, product, version…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select
          options={STATUS_FILTER_OPTIONS}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as RecipeStatus | "")}
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
          emptyMessage={search ? "No recipes match your search." : "No recipes yet."}
          columns={[
            {
              header: "Name",
              accessor: (r) => (
                <button
                  className="text-indigo-600 hover:underline font-medium text-left"
                  onClick={() => router.push(`/dashboard/recipes/${r.id}`)}
                >
                  {r.name}
                </button>
              ),
            },
            { header: "Version", accessor: "version", className: "font-mono text-xs" },
            {
              header: "Product",
              accessor: (r) =>
                r.product_sku ? (
                  <span>
                    <span className="font-mono text-xs text-gray-500">{r.product_sku}</span>
                    {" "}
                    {r.product_name}
                  </span>
                ) : (
                  "—"
                ),
            },
            {
              header: "Status",
              accessor: (r) => (
                <Badge label={r.status} variant={statusVariant(r.status)} />
              ),
            },
            {
              header: "Active",
              accessor: (r) => (
                <Badge
                  label={r.is_active ? "Yes" : "No"}
                  variant={r.is_active ? "green" : "red"}
                />
              ),
            },
            { header: "Valid From", accessor: (r) => r.valid_from ?? "—" },
            { header: "Valid To", accessor: (r) => r.valid_to ?? "—" },
            {
              header: "",
              accessor: (r) => (
                <div className="flex items-center justify-end gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => router.push(`/dashboard/recipes/${r.id}`)}
                  >
                    View
                  </Button>
                  {r.status === "DRAFT" && (
                    <button
                      onClick={() => setDeletingId(r.id)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline"
                    >
                      Delete
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete Recipe">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete the DRAFT recipe{" "}
          <span className="font-semibold text-gray-900">{deletingRecipe?.name}</span>{" "}
          <span className="font-mono text-xs text-gray-500">(v{deletingRecipe?.version})</span>?
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

      <Modal
        open={open}
        onClose={() => {
          setOpen(false);
          setForm(empty);
        }}
        title="New Recipe / Formulation"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate(form);
          }}
          className="space-y-4"
        >
          <Select
            label="Product *"
            options={[{ value: "", label: "Select a product…" }, ...productOptions]}
            value={form.product_id}
            onChange={(e) => set("product_id", e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Recipe Name *"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
            />
            <Input
              label="Version *"
              value={form.version}
              onChange={(e) => set("version", e.target.value)}
              required
              placeholder="e.g. 1.0"
            />
          </div>
          <Input
            label="Description"
            value={form.description ?? ""}
            onChange={(e) => set("description", e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Valid From"
              type="date"
              onChange={(e) => set("valid_from", e.target.value || undefined)}
            />
            <Input
              label="Valid To"
              type="date"
              onChange={(e) => set("valid_to", e.target.value || undefined)}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={() => {
                setOpen(false);
                setForm(empty);
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={create.isPending}
              disabled={!form.product_id || !form.name || !form.version}
            >
              Create Recipe
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
