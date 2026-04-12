"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { productionApi, PlanLineCreate } from "@/lib/production";
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

const emptyLine: PlanLineCreate = {
  line_no: 1, product_id: "", recipe_id: "", target_quantity: 0,
  uom: "KG", target_warehouse_id: "",
};

const UOMS = [
  { value: "KG", label: "KG" }, { value: "L", label: "L" },
  { value: "PCS", label: "PCS" }, { value: "G", label: "G" },
];

export default function PlanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [lineOpen, setLineOpen] = useState(false);
  const [lineForm, setLineForm] = useState<PlanLineCreate>(emptyLine);

  const { data: plan, isLoading } = useQuery({
    queryKey: ["production-plan", id],
    queryFn: () => productionApi.getPlan(id),
    enabled: !!id,
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => productsApi.list(0, 200),
  });
  const { data: recipes = [] } = useQuery({
    queryKey: ["recipes"],
    queryFn: () => recipesApi.list({ status: "APPROVED", limit: 200 }),
  });
  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(0, 100),
  });

  const fgWarehouses = warehouses.filter((w) => w.warehouse_type === "FINISHED_GOODS");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["production-plan", id] });

  const confirm = useMutation({
    mutationFn: () => productionApi.confirmPlan(id),
    onSuccess: () => { invalidate(); qc.invalidateQueries({ queryKey: ["production-plans"] }); toast("success", "Confirmed", "Plan confirmed."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const addLine = useMutation({
    mutationFn: () => productionApi.addPlanLine(id, lineForm),
    onSuccess: () => { invalidate(); setLineOpen(false); setLineForm(emptyLine); toast("success", "Line added", "Plan line saved."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const deleteLine = useMutation({
    mutationFn: (lineId: string) => productionApi.deletePlanLine(id, lineId),
    onSuccess: () => { invalidate(); toast("success", "Removed", "Line removed."); },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const setF = (key: keyof PlanLineCreate, value: unknown) =>
    setLineForm((f) => ({ ...f, [key]: value }));

  const filteredRecipes = recipes.filter(
    (r) => !lineForm.product_id || r.product_id === lineForm.product_id
  );

  if (isLoading) return <div className="flex justify-center py-24"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>;
  if (!plan) return <div className="text-gray-500 py-16 text-center">Plan not found.</div>;

  const isDraft = plan.status === "DRAFT";

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button className="text-sm text-indigo-600 hover:underline mb-2 block" onClick={() => router.push("/dashboard/production")}>
              ← Back to Plans
            </button>
            <h1 className="text-2xl font-bold text-gray-900">{plan.name}</h1>
            <p className="text-sm text-gray-500 mt-1">
              <span className="font-mono">{plan.plan_no}</span>
              {" · "}
              {new Date(plan.planned_date).toLocaleDateString()}
            </p>
            {plan.description && <p className="text-sm text-gray-600 mt-2">{plan.description}</p>}
          </div>
          <div className="flex flex-col items-end gap-3">
            <Badge
              label={plan.status}
              variant={plan.status === "CONFIRMED" ? "green" : plan.status === "DRAFT" ? "blue" : "red"}
            />
            <div className="flex gap-2">
              {isDraft && (
                <Button variant="secondary" onClick={() => confirm.mutate()} loading={confirm.isPending}>
                  Confirm Plan
                </Button>
              )}
              {isDraft && (
                <Button onClick={() => setLineOpen(true)}>+ Add Line</Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Plan Lines
          <span className="ml-2 text-sm font-normal text-gray-400">({plan.lines.length})</span>
        </h2>
        <Table
          keyField="id"
          data={plan.lines}
          emptyMessage="No lines yet. Add products to plan."
          columns={[
            { header: "#", accessor: "line_no", className: "w-12 text-center" },
            {
              header: "Product",
              accessor: (l) => (
                <span>
                  <span className="font-mono text-xs text-gray-500">{l.product_sku}</span>{" "}
                  {l.product_name}
                </span>
              ),
            },
            {
              header: "Recipe",
              accessor: (l) => l.recipe_name ? `${l.recipe_name} v${l.recipe_version}` : "—",
            },
            { header: "Target Qty", accessor: (l) => `${Number(l.target_quantity).toLocaleString()} ${l.uom}` },
            { header: "Warehouse", accessor: (l) => l.target_warehouse_name ?? "—" },
            { header: "Planned Date", accessor: (l) => l.planned_date ? new Date(l.planned_date).toLocaleDateString() : "—" },
            {
              header: "",
              accessor: (l) =>
                isDraft ? (
                  <Button variant="secondary" onClick={() => deleteLine.mutate(l.id)}>Remove</Button>
                ) : null,
            },
          ]}
        />
      </div>

      <Modal open={lineOpen} onClose={() => { setLineOpen(false); setLineForm(emptyLine); }} title="Add Plan Line">
        <form onSubmit={(e) => { e.preventDefault(); addLine.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Line No *"
              type="number"
              value={lineForm.line_no}
              onChange={(e) => setF("line_no", parseInt(e.target.value) || 1)}
              required
            />
            <Select
              label="Unit *"
              options={UOMS}
              value={lineForm.uom}
              onChange={(e) => setF("uom", e.target.value)}
            />
          </div>
          <Select
            label="Product *"
            options={[{ value: "", label: "Select product…" }, ...products.map((p) => ({ value: p.id, label: `${p.sku} — ${p.name}` }))]}
            value={lineForm.product_id}
            onChange={(e) => { setF("product_id", e.target.value); setF("recipe_id", ""); }}
          />
          <Select
            label="Recipe (Approved) *"
            options={[{ value: "", label: "Select recipe…" }, ...filteredRecipes.map((r) => ({ value: r.id, label: `${r.name} v${r.version}` }))]}
            value={lineForm.recipe_id}
            onChange={(e) => setF("recipe_id", e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Target Quantity *"
              type="number"
              step="0.001"
              value={lineForm.target_quantity}
              onChange={(e) => setF("target_quantity", parseFloat(e.target.value) || 0)}
              required
            />
            <Select
              label="Target Warehouse *"
              options={[
                { value: "", label: "Select warehouse…" },
                ...fgWarehouses.map((w) => ({ value: w.id, label: w.name })),
              ]}
              value={lineForm.target_warehouse_id}
              onChange={(e) => setF("target_warehouse_id", e.target.value)}
            />
          </div>
          <Input
            label="Planned Date"
            type="datetime-local"
            onChange={(e) => setF("planned_date", e.target.value || undefined)}
          />
          <Input
            label="Notes"
            value={lineForm.notes ?? ""}
            onChange={(e) => setF("notes", e.target.value || undefined)}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setLineOpen(false); setLineForm(emptyLine); }}>Cancel</Button>
            <Button
              type="submit"
              loading={addLine.isPending}
              disabled={!lineForm.product_id || !lineForm.recipe_id || !lineForm.target_warehouse_id || lineForm.target_quantity <= 0}
            >
              Add Line
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
