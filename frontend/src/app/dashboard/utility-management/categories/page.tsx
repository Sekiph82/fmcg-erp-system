"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  utilityManagementApi,
  UtilityAssetCategory,
  UtilityAssetCategoryCreate,
  UtilityAssetCategoryUpdate,
  UtilityType,
  UTILITY_TYPE_OPTIONS,
  UTILITY_TYPE_LABELS,
  downloadAuthenticatedCsv,
} from "@/lib/utilityManagement";
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
import { RequirePermission } from "@/components/PermissionGuard";

const EMPTY_CREATE: UtilityAssetCategoryCreate = {
  code: "",
  name: "",
  utility_type: "ELECTRICITY",
  default_unit: "",
  description: "",
  is_active: true,
};

function utilityTypeVariant(t: UtilityType) {
  const map: Record<UtilityType, "blue" | "green" | "yellow" | "red" | "gray"> = {
    ELECTRICITY: "yellow",
    WATER: "blue",
    SOFT_WATER: "blue",
    PROCESS_WATER: "blue",
    STEAM: "red",
    COMPRESSED_AIR: "gray",
    SOLAR: "yellow",
    NATURAL_GAS: "red",
    WASTEWATER: "gray",
    DIESEL: "red",
    CHILLED_WATER: "blue",
    OTHER: "gray",
  };
  return map[t] ?? "gray";
}

export default function UtilityAssetCategoriesPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<UtilityType | "">("");
  const [filterActive, setFilterActive] = useState<"" | "true" | "false">("");

  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UtilityAssetCategoryCreate>(EMPTY_CREATE);

  const [editTarget, setEditTarget] = useState<UtilityAssetCategory | null>(null);
  const [editForm, setEditForm] = useState<UtilityAssetCategoryUpdate>({});

  const [deleteTarget, setDeleteTarget] = useState<UtilityAssetCategory | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["utility-management", "categories", filterType, filterActive],
    queryFn: () =>
      utilityManagementApi.categories.list({
        utility_type: filterType || undefined,
        is_active: filterActive === "" ? undefined : filterActive === "true",
        limit: 500,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: UtilityAssetCategoryCreate) =>
      utilityManagementApi.categories.create(data),
    onSuccess: (cat) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "categories"] });
      setCreateOpen(false);
      setForm(EMPTY_CREATE);
      toast("success", "Category created", `${cat.name} (${cat.code}) added.`);
    },
    onError: (err) => toast("error", "Failed to create", extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityAssetCategoryUpdate }) =>
      utilityManagementApi.categories.update(id, data),
    onSuccess: (cat) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "categories"] });
      setEditTarget(null);
      toast("success", "Category updated", `${cat.name} saved.`);
    },
    onError: (err) => toast("error", "Failed to update", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilityManagementApi.categories.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utility-management", "categories"] });
      setDeleteTarget(null);
      toast("success", "Category deleted");
    },
    onError: (err) => toast("error", "Cannot delete", extractApiError(err)),
  });

  const openEdit = (cat: UtilityAssetCategory) => {
    setEditTarget(cat);
    setEditForm({
      name: cat.name,
      description: cat.description ?? "",
      utility_type: cat.utility_type,
      default_unit: cat.default_unit ?? "",
      is_active: cat.is_active,
    });
  };

  const filtered = categories.filter((c) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return c.code.toLowerCase().includes(s) || c.name.toLowerCase().includes(s);
  });

  const handleExport = async () => {
    try {
      await downloadAuthenticatedCsv(
        "/api/v1/utility-management/asset-categories/export/csv",
        "utility_asset_categories.csv",
      );
    } catch {
      toast("error", "Export failed");
    }
  };

  return (
    <RequirePermission permission="utility_management.view">
      <div>
        <ToastContainer toasts={toasts} onDismiss={dismiss} />

        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Asset Categories</h1>
            <p className="text-sm text-gray-500 mt-1">
              {categories.length} categories &nbsp;·&nbsp; Classify utility assets by type
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={handleExport}>Export CSV</Button>
            <ImportModal
              module="utility_asset_categories"
              onSuccess={() => qc.invalidateQueries({ queryKey: ["utility-management", "categories"] })}
            />
            <Button onClick={() => setCreateOpen(true)}>+ Add Category</Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Input
            placeholder="Search code or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select
            label=""
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as UtilityType | "")}
            options={[{ value: "", label: "All utility types" }, ...UTILITY_TYPE_OPTIONS]}
          />
          <Select
            label=""
            value={filterActive}
            onChange={(e) => setFilterActive(e.target.value as "" | "true" | "false")}
            options={[
              { value: "", label: "All statuses" },
              { value: "true", label: "Active only" },
              { value: "false", label: "Inactive only" },
            ]}
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
            emptyMessage={
              search ? "No categories match your search." : "No categories yet."
            }
            columns={[
              {
                header: "Code",
                accessor: (r) => (
                  <span className="font-mono text-xs font-semibold text-gray-800">{r.code}</span>
                ),
              },
              { header: "Name", accessor: "name" },
              {
                header: "Utility Type",
                accessor: (r) => (
                  <Badge label={UTILITY_TYPE_LABELS[r.utility_type]} variant={utilityTypeVariant(r.utility_type)} />
                ),
              },
              {
                header: "Default Unit",
                accessor: (r) => r.default_unit ? (
                  <span className="font-mono text-sm text-gray-600">{r.default_unit}</span>
                ) : <span className="text-gray-400">—</span>,
              },
              {
                header: "Assets",
                accessor: (r) => (
                  <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                    {r.asset_count}
                  </span>
                ),
              },
              {
                header: "Status",
                accessor: (r) => (
                  <Badge
                    label={r.is_active ? "Active" : "Inactive"}
                    variant={r.is_active ? "green" : "gray"}
                  />
                ),
              },
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
                      onClick={() => setDeleteTarget(r)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline"
                      disabled={r.asset_count > 0}
                      title={r.asset_count > 0 ? "Cannot delete — has assets" : "Delete"}
                    >
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
          />
        )}

        {/* Create Modal */}
        <Modal
          open={createOpen}
          onClose={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}
          title="Add Asset Category"
        >
          <form
            onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Category Code *"
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value.toUpperCase() }))}
                placeholder="e.g. BOILER"
                required
              />
              <Input
                label="Category Name *"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Utility Type *"
                value={form.utility_type}
                onChange={(e) => setForm((f) => ({ ...f, utility_type: e.target.value as UtilityType }))}
                options={UTILITY_TYPE_OPTIONS}
              />
              <Input
                label="Default Unit"
                value={form.default_unit ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, default_unit: e.target.value || null }))}
                placeholder="e.g. kW, m³/h, kg/h"
              />
            </div>
            <Input
              label="Description"
              value={form.description ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value || null }))}
              placeholder="Optional description"
            />
            <div className="flex items-center gap-2">
              <input
                id="create-is-active"
                type="checkbox"
                checked={form.is_active ?? true}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="create-is-active" className="text-sm text-gray-700">Active</label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>Create</Button>
            </div>
          </form>
        </Modal>

        {/* Edit Modal */}
        <Modal
          open={!!editTarget}
          onClose={() => setEditTarget(null)}
          title={`Edit Category — ${editTarget?.code}`}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (editTarget) updateMutation.mutate({ id: editTarget.id, data: editForm });
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Category Name *"
                value={editForm.name ?? ""}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
              <Select
                label="Utility Type *"
                value={editForm.utility_type ?? "ELECTRICITY"}
                onChange={(e) => setEditForm((f) => ({ ...f, utility_type: e.target.value as UtilityType }))}
                options={UTILITY_TYPE_OPTIONS}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Default Unit"
                value={editForm.default_unit ?? ""}
                onChange={(e) => setEditForm((f) => ({ ...f, default_unit: e.target.value || null }))}
                placeholder="e.g. kW, m³/h"
              />
              <div />
            </div>
            <Input
              label="Description"
              value={editForm.description ?? ""}
              onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value || null }))}
            />
            <div className="flex items-center gap-2">
              <input
                id="edit-is-active"
                type="checkbox"
                checked={editForm.is_active ?? true}
                onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="edit-is-active" className="text-sm text-gray-700">Active</label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setEditTarget(null)}>Cancel</Button>
              <Button type="submit" loading={updateMutation.isPending}>Save Changes</Button>
            </div>
          </form>
        </Modal>

        {/* Delete Confirm Modal */}
        <Modal
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          title="Delete Category"
        >
          {deleteTarget && deleteTarget.asset_count > 0 ? (
            <div className="space-y-4">
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                <p className="text-sm font-semibold text-red-800">
                  Cannot delete &quot;{deleteTarget.name}&quot;
                </p>
                <p className="text-xs text-red-600 mt-1">
                  {deleteTarget.asset_count} asset(s) are assigned to this category.
                  Reassign or delete those assets first.
                </p>
              </div>
              <div className="flex justify-end">
                <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Close</Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Delete category{" "}
                <span className="font-semibold">{deleteTarget?.name}</span>{" "}
                <span className="font-mono text-xs text-gray-500">({deleteTarget?.code})</span>?
                This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
                <Button
                  variant="danger"
                  loading={deleteMutation.isPending}
                  onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
                >
                  Delete
                </Button>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </RequirePermission>
  );
}
