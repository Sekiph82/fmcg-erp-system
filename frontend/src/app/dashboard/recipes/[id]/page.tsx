"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import {
  recipesApi,
  RecipeItemCreate,
  ProcessParameterCreate,
} from "@/lib/recipes";
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
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

const UOMS = [
  { value: "KG", label: "KG" }, { value: "G", label: "G" },
  { value: "L", label: "L" }, { value: "ML", label: "ML" },
  { value: "PCS", label: "PCS" }, { value: "BOX", label: "BOX" },
];

const statusVariant = (s: string) =>
  s === "APPROVED" ? "green" : s === "DRAFT" ? "blue" : "red";

const emptyItem: RecipeItemCreate = {
  material_id: "", line_no: 1, quantity: 0, unit: "KG",
  loss_percentage: 0, is_optional: false,
};

const emptyParam: ProcessParameterCreate = {
  step_no: 1, step_name: "",
};

export default function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [itemOpen, setItemOpen] = useState(false);
  const [paramOpen, setParamOpen] = useState(false);
  const [dupOpen, setDupOpen] = useState(false);
  const [itemForm, setItemForm] = useState<RecipeItemCreate>(emptyItem);
  const [paramForm, setParamForm] = useState<ProcessParameterCreate>(emptyParam);
  const [dupVersion, setDupVersion] = useState("");
  const [dupName, setDupName] = useState("");

  const { data: recipe, isLoading } = useQuery({
    queryKey: ["recipe", id],
    queryFn: () => recipesApi.get(id),
    enabled: !!id,
  });

  const { data: materials = [] } = useQuery({
    queryKey: ["materials"],
    queryFn: () => materialsApi.list(0, 500),
  });

  const materialOptions = materials.map((m) => ({
    value: m.id,
    label: `${m.code} — ${m.name}`,
  }));

  const isDraft = recipe?.status === "DRAFT";

  const invalidate = () => qc.invalidateQueries({ queryKey: ["recipe", id] });

  const approve = useMutation({
    mutationFn: () => recipesApi.approve(id),
    onSuccess: () => { invalidate(); toast("success", "Approved", "Recipe is now APPROVED."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const obsolete = useMutation({
    mutationFn: () => recipesApi.obsolete(id),
    onSuccess: () => { invalidate(); toast("success", "Obsoleted", "Recipe marked as OBSOLETE."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const duplicate = useMutation({
    mutationFn: () => recipesApi.duplicate(id, dupVersion, dupName || undefined),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["recipes"] });
      setDupOpen(false);
      toast("success", "Duplicated", `New recipe v${r.version} created as DRAFT.`);
      router.push(`/dashboard/recipes/${r.id}`);
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const addItem = useMutation({
    mutationFn: () => recipesApi.addItem(id, itemForm),
    onSuccess: () => {
      invalidate();
      setItemOpen(false);
      setItemForm(emptyItem);
      toast("success", "Item added", "Recipe item saved.");
    },
    onError: (err) => toast("error", "Failed to add item", extractApiError(err)),
  });

  const deleteItem = useMutation({
    mutationFn: (itemId: string) => recipesApi.deleteItem(id, itemId),
    onSuccess: () => { invalidate(); toast("success", "Removed", "Item removed."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const addParam = useMutation({
    mutationFn: () => recipesApi.addProcessParam(id, paramForm),
    onSuccess: () => {
      invalidate();
      setParamOpen(false);
      setParamForm(emptyParam);
      toast("success", "Step added", "Process step saved.");
    },
    onError: (err) => toast("error", "Failed to add step", extractApiError(err)),
  });

  const deleteParam = useMutation({
    mutationFn: (paramId: string) => recipesApi.deleteProcessParam(id, paramId),
    onSuccess: () => { invalidate(); toast("success", "Removed", "Process step removed."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const setI = (key: keyof RecipeItemCreate, value: unknown) =>
    setItemForm((f) => ({ ...f, [key]: value }));
  const setP = (key: keyof ProcessParameterCreate, value: unknown) =>
    setParamForm((f) => ({ ...f, [key]: value }));

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  if (!recipe) {
    return <div className="text-gray-500 py-16 text-center">Recipe not found.</div>;
  }

  return (
    <RequirePermission permission="recipe.view">
    <div className="space-y-8">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button
              className="text-sm text-indigo-600 hover:underline mb-2 block"
              onClick={() => router.push("/dashboard/recipes")}
            >
              ← Back to Recipes
            </button>
            <h1 className="text-2xl font-bold text-gray-900">{recipe.name}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Version <span className="font-mono font-medium">{recipe.version}</span>
              {" · "}
              {recipe.product_sku && (
                <span className="font-mono text-xs">{recipe.product_sku}</span>
              )}{" "}
              {recipe.product_name}
            </p>
            {recipe.description && (
              <p className="text-sm text-gray-600 mt-2">{recipe.description}</p>
            )}
            <div className="flex gap-3 mt-3 flex-wrap text-sm text-gray-500">
              {recipe.valid_from && <span>Valid from: {recipe.valid_from}</span>}
              {recipe.valid_to && <span>Valid to: {recipe.valid_to}</span>}
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <Badge label={recipe.status} variant={statusVariant(recipe.status)} />
            <div className="flex gap-2 flex-wrap justify-end">
              {isDraft && (
                <PermissionGuard permission="recipe.approve">
                <Button
                  variant="secondary"
                  onClick={() => approve.mutate()}
                  loading={approve.isPending}
                >
                  Approve
                </Button>
                </PermissionGuard>
              )}
              {recipe.status !== "OBSOLETE" && (
                <PermissionGuard permission="recipe.obsolete">
                <Button
                  variant="secondary"
                  onClick={() => obsolete.mutate()}
                  loading={obsolete.isPending}
                >
                  Mark Obsolete
                </Button>
                </PermissionGuard>
              )}
              <PermissionGuard permission="recipe.create">
                <Button variant="secondary" onClick={() => setDupOpen(true)}>
                  Duplicate as New Version
                </Button>
              </PermissionGuard>
            </div>
          </div>
        </div>
      </div>

      {/* BOM / Recipe Items */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            BOM / Formulation Items
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({recipe.items.length} lines)
            </span>
          </h2>
          {isDraft && (
            <PermissionGuard permission="recipe.edit">
            <Button onClick={() => setItemOpen(true)}>+ Add Item</Button>
            </PermissionGuard>
          )}
        </div>
        <Table
          keyField="id"
          data={recipe.items}
          emptyMessage="No items yet. Add materials to build the BOM."
          columns={[
            { header: "Line", accessor: "line_no", className: "w-16 text-center" },
            {
              header: "Material",
              accessor: (r) => (
                <span>
                  <span className="font-mono text-xs text-gray-500">{r.material_code}</span>
                  {" "}
                  {r.material_name}
                </span>
              ),
            },
            { header: "Qty", accessor: (r) => Number(r.quantity).toLocaleString() },
            { header: "Unit", accessor: "unit" },
            {
              header: "Loss %",
              accessor: (r) =>
                Number(r.loss_percentage) > 0
                  ? `${Number(r.loss_percentage).toFixed(2)}%`
                  : "—",
            },
            {
              header: "Optional",
              accessor: (r) =>
                r.is_optional ? (
                  <Badge label="Optional" variant="blue" />
                ) : null,
            },
            { header: "Alt. Group", accessor: (r) => r.alternative_group ?? "—" },
            { header: "Notes", accessor: (r) => r.notes ?? "—" },
            {
              header: "",
              accessor: (r) =>
                isDraft ? (
                  <PermissionGuard permission="recipe.delete">
                  <Button
                    variant="secondary"
                    onClick={() => deleteItem.mutate(r.id)}
                  >
                    Remove
                  </Button>
                  </PermissionGuard>
                ) : null,
            },
          ]}
        />
      </div>

      {/* Process Parameters */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            Process Parameters
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({recipe.process_parameters.length} steps)
            </span>
          </h2>
          {isDraft && (
            <PermissionGuard permission="recipe.edit">
            <Button onClick={() => setParamOpen(true)}>+ Add Step</Button>
            </PermissionGuard>
          )}
        </div>
        <Table
          keyField="id"
          data={recipe.process_parameters}
          emptyMessage="No process steps defined yet."
          columns={[
            { header: "Step", accessor: "step_no", className: "w-16 text-center" },
            { header: "Step Name", accessor: "step_name" },
            {
              header: "Temp (°C)",
              accessor: (r) =>
                r.target_temperature != null ? `${r.target_temperature}°C` : "—",
            },
            {
              header: "pH",
              accessor: (r) =>
                r.target_ph != null ? String(r.target_ph) : "—",
            },
            {
              header: "Viscosity (cP)",
              accessor: (r) =>
                r.target_viscosity != null ? String(r.target_viscosity) : "—",
            },
            {
              header: "Mix Time (min)",
              accessor: (r) =>
                r.mixing_time_minutes != null ? String(r.mixing_time_minutes) : "—",
            },
            {
              header: "RPM",
              accessor: (r) => (r.rpm != null ? String(r.rpm) : "—"),
            },
            { header: "Notes", accessor: (r) => r.notes ?? "—" },
            {
              header: "",
              accessor: (r) =>
                isDraft ? (
                  <PermissionGuard permission="recipe.delete">
                  <Button
                    variant="secondary"
                    onClick={() => deleteParam.mutate(r.id)}
                  >
                    Remove
                  </Button>
                  </PermissionGuard>
                ) : null,
            },
          ]}
        />
      </div>

      {/* Add Item Modal */}
      <Modal
        open={itemOpen}
        onClose={() => { setItemOpen(false); setItemForm(emptyItem); }}
        title="Add BOM Item"
      >
        <form
          onSubmit={(e) => { e.preventDefault(); addItem.mutate(); }}
          className="space-y-4"
        >
          <Select
            label="Material *"
            options={[{ value: "", label: "Select material…" }, ...materialOptions]}
            value={itemForm.material_id}
            onChange={(e) => setI("material_id", e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Line No *"
              type="number"
              value={itemForm.line_no}
              onChange={(e) => setI("line_no", parseInt(e.target.value) || 1)}
              required
            />
            <Select
              label="Unit *"
              options={UOMS}
              value={itemForm.unit}
              onChange={(e) => setI("unit", e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Quantity *"
              type="number"
              step="0.0001"
              value={itemForm.quantity}
              onChange={(e) => setI("quantity", parseFloat(e.target.value) || 0)}
              required
            />
            <Input
              label="Loss % (e.g. 2.5)"
              type="number"
              step="0.01"
              value={itemForm.loss_percentage}
              onChange={(e) => setI("loss_percentage", parseFloat(e.target.value) || 0)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Alternative Group"
              value={itemForm.alternative_group ?? ""}
              onChange={(e) => setI("alternative_group", e.target.value || undefined)}
              placeholder="e.g. EMULSIFIER-A"
            />
            <label className="flex items-center gap-2 mt-6">
              <input
                type="checkbox"
                checked={itemForm.is_optional}
                onChange={(e) => setI("is_optional", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Optional component</span>
            </label>
          </div>
          <Input
            label="Notes"
            value={itemForm.notes ?? ""}
            onChange={(e) => setI("notes", e.target.value || undefined)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={() => { setItemOpen(false); setItemForm(emptyItem); }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={addItem.isPending}
              disabled={!itemForm.material_id || itemForm.quantity <= 0}
            >
              Add Item
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Process Parameter Modal */}
      <Modal
        open={paramOpen}
        onClose={() => { setParamOpen(false); setParamForm(emptyParam); }}
        title="Add Process Step"
      >
        <form
          onSubmit={(e) => { e.preventDefault(); addParam.mutate(); }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Step No *"
              type="number"
              value={paramForm.step_no}
              onChange={(e) => setP("step_no", parseInt(e.target.value) || 1)}
              required
            />
            <Input
              label="Step Name *"
              value={paramForm.step_name}
              onChange={(e) => setP("step_name", e.target.value)}
              required
              placeholder="e.g. Mixing, Heating, Cooling"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Temperature (°C)"
              type="number"
              step="0.1"
              placeholder="e.g. 80"
              onChange={(e) => setP("target_temperature", parseFloat(e.target.value) || undefined)}
            />
            <Input
              label="Target pH"
              type="number"
              step="0.01"
              placeholder="e.g. 6.5"
              onChange={(e) => setP("target_ph", parseFloat(e.target.value) || undefined)}
            />
            <Input
              label="Viscosity (cP)"
              type="number"
              step="0.1"
              placeholder="e.g. 500"
              onChange={(e) => setP("target_viscosity", parseFloat(e.target.value) || undefined)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Mix Time (minutes)"
              type="number"
              placeholder="e.g. 30"
              onChange={(e) => setP("mixing_time_minutes", parseInt(e.target.value) || undefined)}
            />
            <Input
              label="RPM"
              type="number"
              placeholder="e.g. 200"
              onChange={(e) => setP("rpm", parseInt(e.target.value) || undefined)}
            />
          </div>
          <Input
            label="Notes"
            value={paramForm.notes ?? ""}
            onChange={(e) => setP("notes", e.target.value || undefined)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={() => { setParamOpen(false); setParamForm(emptyParam); }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={addParam.isPending}
              disabled={!paramForm.step_name}
            >
              Add Step
            </Button>
          </div>
        </form>
      </Modal>

      {/* Duplicate Modal */}
      <Modal
        open={dupOpen}
        onClose={() => setDupOpen(false)}
        title="Duplicate as New Version"
      >
        <form
          onSubmit={(e) => { e.preventDefault(); duplicate.mutate(); }}
          className="space-y-4"
        >
          <p className="text-sm text-gray-500">
            Creates a new DRAFT recipe with all items and process steps copied from
            <strong> {recipe.name} v{recipe.version}</strong>.
          </p>
          <Input
            label="New Version *"
            value={dupVersion}
            onChange={(e) => setDupVersion(e.target.value)}
            required
            placeholder="e.g. 2.0"
          />
          <Input
            label="New Name (optional)"
            value={dupName}
            onChange={(e) => setDupName(e.target.value)}
            placeholder={`${recipe.name} v${dupVersion || "..."}`}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setDupOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={duplicate.isPending}
              disabled={!dupVersion}
            >
              Duplicate
            </Button>
          </div>
        </form>
      </Modal>
    </div>
    </RequirePermission>
  );
}
