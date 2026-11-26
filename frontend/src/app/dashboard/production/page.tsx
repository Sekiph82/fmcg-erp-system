"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
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
import { tx, lx } from "@/lib/i18n/core";

const planStatusVariant = (s: PlanStatus) =>
  s === "CONFIRMED" || s === "IN_PROGRESS"
    ? "green"
    : s === "DRAFT"
    ? "blue"
    : s === "COMPLETED"
    ? "green"
    : "red";

const STATUS_OPTIONS = lx(() => [
  { value: "", label: tx("All Statuses") },
  { value: "DRAFT", label: tx("Draft") },
  { value: "CONFIRMED", label: tx("Confirmed") },
  { value: "IN_PROGRESS", label: tx("In Progress") },
  { value: "COMPLETED", label: tx("Completed") },
  { value: "CANCELLED", label: tx("Cancelled") },
]);

const emptyPlan: PlanCreate = { plan_no: "", name: "", planned_date: "" };

function ProductionPlansTab() {
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
      toast("success", tx("Plan created"), tx("{plan_no} created as DRAFT.", { plan_no: p.plan_no }));
    },
    onError: (err) => toast("error", tx("Failed"), extractApiError(err)),
  });

  const confirmPlan = useMutation({
    mutationFn: (id: string) => productionApi.confirmPlan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-plans"] });
      toast("success", tx("Confirmed"), tx("Plan confirmed."));
    },
    onError: (err) => toast("error", tx("Failed"), extractApiError(err)),
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
          <h1 className="text-2xl font-bold text-gray-900">{tx("Production Plans")}</h1>
          <p className="text-sm text-gray-500 mt-1">{plans.length} {tx("total")}</p>
        </div>
        <Button onClick={() => setPlanOpen(true)} data-testid="production-create-plan-button">{tx("+ New Plan")}</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          placeholder={tx("Search by name or plan no…")}
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
              header: tx("Plan No"),
              accessor: (p) => (
                <button
                  className="font-mono text-xs text-indigo-600 hover:underline"
                  onClick={() => router.push(`/dashboard/production/plans/${p.id}`)}
                >
                  {p.plan_no}
                </button>
              ),
            },
            { header: tx("Name"), accessor: "name" },
            {
              header: tx("Status"),
              accessor: (p) => <Badge label={p.status} variant={planStatusVariant(p.status)} />,
            },
            {
              header: tx("Planned Date"),
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
                      {tx("Confirm")}
                    </Button>
                  )}
                  <Button
                    variant="secondary"
                    onClick={() => router.push(`/dashboard/production/plans/${p.id}`)}
                  >
                    {tx("View")}
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
        title={tx("New Production Plan")}
      >
        <form
          onSubmit={(e) => { e.preventDefault(); createPlan.mutate(planForm); }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label={tx("Plan No *")}
              value={planForm.plan_no}
              onChange={(e) => setPlanForm((f) => ({ ...f, plan_no: e.target.value }))}
              required
              placeholder={tx("e.g. PP-2026-001")}
            />
            <Input
              label={tx("Name *")}
              value={planForm.name}
              onChange={(e) => setPlanForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <Input
            label={tx("Planned Date *")}
            type="datetime-local"
            onChange={(e) => setPlanForm((f) => ({ ...f, planned_date: e.target.value }))}
            required
          />
          <Input
            label={tx("Description")}
            value={planForm.description ?? ""}
            onChange={(e) => setPlanForm((f) => ({ ...f, description: e.target.value || undefined }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setPlanOpen(false); setPlanForm(emptyPlan); }}>
              {tx("Cancel")}
            </Button>
            <Button type="submit" loading={createPlan.isPending} disabled={!planForm.plan_no || !planForm.name}>
              {tx("Create Plan")}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

const ProductionOrdersPage     = dynamic(() => import("@/app/dashboard/production/orders/page"),         { ssr: false });
const ProductionWarehouseLinksPage = dynamic(() => import("@/app/dashboard/production/warehouse-links/page"), { ssr: false });
const ProductionSchedulingPage = dynamic(() => import("@/app/dashboard/production/scheduling/page"),     { ssr: false });
const ProductionWorkCentersPage= dynamic(() => import("@/app/dashboard/production/work-centers/page"),   { ssr: false });
const ProductionBatchLotsPage  = dynamic(() => import("@/app/dashboard/production/batch-lots/page"),     { ssr: false });
const ProductionQCPage         = dynamic(() => import("@/app/dashboard/production/quality-control/page"),{ ssr: false });
const ProductionLaborPage      = dynamic(() => import("@/app/dashboard/production/labor/page"),          { ssr: false });
const ProductionOEEPage        = dynamic(() => import("@/app/dashboard/production/oee/page"),            { ssr: false });
const ProductionDowntimePage   = dynamic(() => import("@/app/dashboard/production/downtime/page"),       { ssr: false });
const ProductionWasteYieldPage = dynamic(() => import("@/app/dashboard/production/waste-yield/page"),    { ssr: false });
const ProductionWIPPage        = dynamic(() => import("@/app/dashboard/production/wip/page"),            { ssr: false });
const ProductionCostingPage    = dynamic(() => import("@/app/dashboard/production/costing/page"),        { ssr: false });
const ProductionVariancePage   = dynamic(() => import("@/app/dashboard/production/variance/page"),       { ssr: false });
const ProductionReportsPage    = dynamic(() => import("@/app/dashboard/production/reports/page"),        { ssr: false });
const ProductionRoutingPage    = dynamic(() => import("@/app/dashboard/production/routing/page"),        { ssr: false });
const ProductionTimeTrackPage  = dynamic(() => import("@/app/dashboard/production/time-tracking/page"),  { ssr: false });
const ExecutionPage            = dynamic(() => import("@/app/dashboard/production-execution/page"),      { ssr: false });
const MachineOpsPage           = dynamic(() => import("@/app/dashboard/machine-ops/page"),               { ssr: false });
const MaterialFlowPage         = dynamic(() => import("@/app/dashboard/material-flow/page"),             { ssr: false });
const ProjectsPage             = dynamic(() => import("@/app/dashboard/projects/page"),                  { ssr: false });

export default function ProductionPage() {
  const tabs = [
    { key: "plans",         label: tx("Plans"),           permission: "production.view", content: <ProductionPlansTab /> },
    { key: "orders",        label: tx("Work Orders"),     permission: "production.view", content: <ProductionOrdersPage /> },
    { key: "scheduling",    label: tx("Scheduling"),      permission: "production.view", content: <ProductionSchedulingPage /> },
    { key: "work-centers",  label: tx("Work Centers"),    permission: "production.view", content: <ProductionWorkCentersPage /> },
    { key: "routing",       label: tx("Routing"),         permission: "production.view", content: <ProductionRoutingPage /> },
    { key: "batch-lots",    label: tx("Batch / Lots"),    permission: "production.view", content: <ProductionBatchLotsPage /> },
    { key: "quality-control",label:"QC",              permission: "production.view", content: <ProductionQCPage /> },
    { key: "labor",         label: tx("Labor"),           permission: "production.view", content: <ProductionLaborPage /> },
    { key: "time-tracking", label: tx("Time Tracking"),   permission: "production.view", content: <ProductionTimeTrackPage /> },
    { key: "oee",           label: "OEE",             permission: "production.view", content: <ProductionOEEPage /> },
    { key: "downtime",      label: tx("Downtime"),        permission: "production.view", content: <ProductionDowntimePage /> },
    { key: "waste-yield",   label: tx("Waste & Yield"),   permission: "production.view", content: <ProductionWasteYieldPage /> },
    { key: "wip",           label: "WIP",             permission: "finance.view", exact: true, content: <ProductionWIPPage /> },
    { key: "costing",       label: tx("Costing"),         permission: "finance.view", exact: true, content: <ProductionCostingPage /> },
    { key: "variance",      label: tx("Variance"),        permission: "finance.view", exact: true, content: <ProductionVariancePage /> },
    { key: "reports",       label: tx("Reports"),         permission: "production.view", content: <ProductionReportsPage /> },
    { key: "execution",     label: tx("Execution"),       permission: "production.view", exact: true, content: <ExecutionPage /> },
    { key: "machine-ops",   label: tx("Machine Ops"),     permission: "production.view", exact: true, content: <MachineOpsPage /> },
    { key: "material-flow", label: tx("Material Flow"),   permission: "production.view", content: <MaterialFlowPage /> },
    { key: "projects",      label: tx("Projects"),        permission: "production.view", content: <ProjectsPage /> },
    { key: "warehouse-links", label: tx("Warehouse Links"), permission: "production.view", content: <ProductionWarehouseLinksPage /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Production")}
      description="Plans, work orders, scheduling, OEE, quality, costing"
      permission="production.view"
      tabs={tabs}
      defaultTab="plans"
    />
  );
}
