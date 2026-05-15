"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { productionApi, PlanCreate, PlanLineCreate, PlanStatus } from "@/lib/production";
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

const planStatusVariant = (s: PlanStatus) =>
  s === "CONFIRMED" || s === "IN_PROGRESS"
    ? "green"
    : s === "DRAFT"
    ? "blue"
    : s === "COMPLETED"
    ? "green"
    : "red";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "CONFIRMED", label: "Confirmed" },
  { value: "IN_PROGRESS", label: "In Progress" },
  { value: "COMPLETED", label: "Completed" },
  { value: "CANCELLED", label: "Cancelled" },
];

const emptyPlan: PlanCreate = { plan_no: "", name: "", planned_date: "" };

export default function ProductionPlansPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { toasts, toast, dismiss } = useToast();
  const [planOpen, setPlanOpen] = useState(false);
  const [planForm, setPlanForm] = useState<PlanCreate>(emptyPlan);
  const [statusFilter, setStatusFilter] = useState<PlanStatus | "">("");
  const [search, setSearch] = useState("");

  const { data: plans = [], isLoading } = useQuery({
    queryKey: ["production-plans", statusFilter],
    queryFn: () => productionApi.listPlans({ status: statusFilter || undefined, limit: 100 }),
  });

  const createPlan = useMutation({
    mutationFn: productionApi.createPlan,
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["production-plans"] });
      setPlanOpen(false);
      setPlanForm(emptyPlan);
      toast("success", "Plan created", `${p.plan_no} created as DRAFT.`);
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const confirmPlan = useMutation({
    mutationFn: (id: string) => productionApi.confirmPlan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-plans"] });
      toast("success", "Confirmed", "Plan confirmed.");
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const filtered = plans.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.plan_no.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div data-testid="production-page">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Plans</h1>
          <p className="text-sm text-gray-500 mt-1">{plans.length} total</p>
        </div>
        <Button onClick={() => setPlanOpen(true)} data-testid="production-create-plan-button">+ New Plan</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          placeholder="Search by name or plan no…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as PlanStatus | "")}
          className="w-44"
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <div data-testid="production-plan-list">
          <Table
            keyField="id"
            data={filtered}
            emptyMessage="No production plans yet."
            columns={[
            {
              header: "Plan No",
              accessor: (p) => (
                <button
                  className="font-mono text-xs text-indigo-600 hover:underline"
                  onClick={() => router.push(`/dashboard/production/plans/${p.id}`)}
                >
                  {p.plan_no}
                </button>
              ),
            },
            { header: "Name", accessor: "name" },
            {
              header: "Status",
              accessor: (p) => <Badge label={p.status} variant={planStatusVariant(p.status)} />,
            },
            {
              header: "Planned Date",
              accessor: (p) => new Date(p.planned_date).toLocaleDateString(),
            },
            {
              header: "",
              accessor: (p) => (
                <div className="flex gap-2">
                  {p.status === "DRAFT" && (
                    <Button
                      variant="secondary"
                      onClick={() => confirmPlan.mutate(p.id)}
                      data-testid="production-confirm-plan-button"
                    >
                      Confirm
                    </Button>
                  )}
                  <Button
                    variant="secondary"
                    onClick={() => router.push(`/dashboard/production/plans/${p.id}`)}
                  >
                    View
                  </Button>
                </div>
              ),
            },
            ]}
          />
        </div>
      )}

      <Modal
        open={planOpen}
        onClose={() => { setPlanOpen(false); setPlanForm(emptyPlan); }}
        title="New Production Plan"
      >
        <form
          onSubmit={(e) => { e.preventDefault(); createPlan.mutate(planForm); }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Plan No *"
              value={planForm.plan_no}
              onChange={(e) => setPlanForm((f) => ({ ...f, plan_no: e.target.value }))}
              required
              placeholder="e.g. PP-2026-001"
            />
            <Input
              label="Name *"
              value={planForm.name}
              onChange={(e) => setPlanForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <Input
            label="Planned Date *"
            type="datetime-local"
            onChange={(e) => setPlanForm((f) => ({ ...f, planned_date: e.target.value }))}
            required
          />
          <Input
            label="Description"
            value={planForm.description ?? ""}
            onChange={(e) => setPlanForm((f) => ({ ...f, description: e.target.value || undefined }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setPlanOpen(false); setPlanForm(emptyPlan); }}>
              Cancel
            </Button>
            <Button type="submit" loading={createPlan.isPending} disabled={!planForm.plan_no || !planForm.name}>
              Create Plan
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
