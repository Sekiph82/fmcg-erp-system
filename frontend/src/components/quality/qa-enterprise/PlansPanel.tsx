"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type PlanCoverage, type PlanStep, type QCType, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { LoadError, type Notify, ReadOnlyNotice, Section, statusVariant, useAction, useQualityPermissions } from "./shared";

const QC_TYPES: QCType[] = ["INCOMING", "IN_PROCESS", "FINISHED_GOODS", "RETEST"];

export function PlansPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const plans = useQuery({ queryKey: ["qa-plans"], queryFn: qaEnterpriseApi.listPlans, enabled: perms.canView });
  const [form, setForm] = useState({ plan_code: "", name: "", item_type: "product_id", item_id: "" });
  const [steps, setSteps] = useState<PlanStep[]>([{ sequence: 1, qc_type: "INCOMING", qc_sub_type: "", is_mandatory: true }]);
  const [coverageFor, setCoverageFor] = useState({ plan_id: "", ref_type: "production_order_id", ref_id: "" });
  const [coverage, setCoverage] = useState<PlanCoverage | null>(null);

  const createPlan = useAction(qaEnterpriseApi.createPlan, notify, (p) => `QC plan ${p.plan_code} v${p.version} saved as draft`, ["qa-plans"]);
  const activate = useAction(qaEnterpriseApi.activatePlan, notify, (p) => `QC plan ${p.plan_code} v${p.version} is active`, ["qa-plans"]);
  const checkCoverage = useAction(
    () => qaEnterpriseApi.planCoverage(coverageFor.plan_id, { [coverageFor.ref_type]: coverageFor.ref_id.trim() }),
    notify, (c) => (c.complete ? "All mandatory steps are satisfied" : "Plan coverage is incomplete"), [],
  );

  if (!perms.canView) return <ReadOnlyNotice>QC plans require quality.view.</ReadOnlyNotice>;

  const updateStep = (index: number, patch: Partial<PlanStep>) =>
    setSteps((current) => current.map((s, i) => (i === index ? { ...s, ...patch } : s)));

  return (
    <div className="space-y-4">
      <Section title="Quality control plans" description="Ordered inspection steps per item. A second person activates a plan; the previous active version retires.">
        {plans.error ? <LoadError error={plans.error} /> : (
          <Table
            keyField="id"
            data={plans.data ?? []}
            emptyMessage="No QC plans yet."
            columns={[
              { header: "Plan", accessor: (p) => `${p.plan_code} v${p.version}` },
              { header: "Name", accessor: "name" },
              { header: "Steps", accessor: (p) => p.steps.map((s) => `${s.sequence}. ${s.qc_type}${s.qc_sub_type ? `/${s.qc_sub_type}` : ""}${s.is_mandatory ? "" : " (optional)"}`).join(" · ") },
              { header: "Status", accessor: (p) => <Badge label={p.status} variant={statusVariant(p.status)} /> },
              {
                header: "Actions",
                accessor: (p) => p.status === "DRAFT" && perms.canApprove ? (
                  <Button variant="secondary" aria-label={`Activate ${p.plan_code} v${p.version}`}
                    loading={activate.isPending} onClick={() => activate.mutate(p.id)}>Activate</Button>
                ) : null,
              },
            ]}
          />
        )}

        {perms.canCreate && (
          <form className="space-y-3" onSubmit={(e) => {
            e.preventDefault();
            createPlan.mutate({
              plan_code: form.plan_code.trim(), name: form.name.trim(), [form.item_type]: form.item_id.trim(),
              steps: steps.map((s) => ({ ...s, qc_sub_type: s.qc_sub_type || null })),
            });
          }}>
            <div className="grid gap-3 md:grid-cols-4">
              <Input id="plan-code" label="Plan code" required value={form.plan_code} onChange={(e) => setForm((f) => ({ ...f, plan_code: e.target.value }))} />
              <Input id="plan-name" label="Plan name" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              <Select id="plan-item-type" label="Item type" value={form.item_type}
                onChange={(e) => setForm((f) => ({ ...f, item_type: e.target.value }))}
                options={[{ value: "product_id", label: "Product" }, { value: "material_id", label: "Material" }]} />
              <Input id="plan-item-id" label="Item ID" required value={form.item_id} onChange={(e) => setForm((f) => ({ ...f, item_id: e.target.value }))} />
            </div>
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-gray-700">Steps</legend>
              {steps.map((s, i) => (
                <div key={i} className="grid items-end gap-2 md:grid-cols-[4rem_1fr_1fr_auto_auto]">
                  <span className="text-sm text-gray-500">#{s.sequence}</span>
                  <Select aria-label={`Step ${s.sequence} QC type`} value={s.qc_type}
                    onChange={(e) => updateStep(i, { qc_type: e.target.value as QCType })}
                    options={QC_TYPES.map((t) => ({ value: t, label: t.replace("_", " ") }))} />
                  <Input aria-label={`Step ${s.sequence} sub-type`} placeholder="Sub-type (optional)" value={s.qc_sub_type ?? ""}
                    onChange={(e) => updateStep(i, { qc_sub_type: e.target.value })} />
                  <label className="flex items-center gap-1 text-sm text-gray-700">
                    <input type="checkbox" checked={s.is_mandatory} onChange={(e) => updateStep(i, { is_mandatory: e.target.checked })} />
                    Mandatory
                  </label>
                  <Button type="button" variant="secondary" aria-label={`Remove step ${s.sequence}`} disabled={steps.length === 1}
                    onClick={() => setSteps((cur) => cur.filter((_, j) => j !== i).map((x, j) => ({ ...x, sequence: j + 1 })))}>Remove</Button>
                </div>
              ))}
              <Button type="button" variant="secondary"
                onClick={() => setSteps((cur) => [...cur, { sequence: cur.length + 1, qc_type: "FINISHED_GOODS", qc_sub_type: "", is_mandatory: true }])}>
                Add step
              </Button>
            </fieldset>
            <div className="flex justify-end">
              <Button type="submit" loading={createPlan.isPending} disabled={!form.plan_code || !form.name || !form.item_id}>Save draft plan</Button>
            </div>
          </form>
        )}
      </Section>

      <Section title="Plan coverage" description="Which mandatory steps are satisfied, missing or failed for one production order or lot.">
        <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => {
          e.preventDefault();
          checkCoverage.mutate(undefined, { onSuccess: setCoverage });
        }}>
          <Select id="coverage-plan" label="Plan" value={coverageFor.plan_id}
            onChange={(e) => setCoverageFor((c) => ({ ...c, plan_id: e.target.value }))}
            options={[{ value: "", label: "Select plan" }, ...(plans.data ?? []).map((p) => ({ value: p.id, label: `${p.plan_code} v${p.version} (${p.status})` }))]} />
          <Select id="coverage-ref-type" label="Check against" value={coverageFor.ref_type}
            onChange={(e) => setCoverageFor((c) => ({ ...c, ref_type: e.target.value }))}
            options={[{ value: "production_order_id", label: "Production order" }, { value: "lot_id", label: "Lot" }]} />
          <Input id="coverage-ref" label="Reference ID" value={coverageFor.ref_id}
            onChange={(e) => setCoverageFor((c) => ({ ...c, ref_id: e.target.value }))} />
          <div className="flex items-end">
            <Button type="submit" loading={checkCoverage.isPending} disabled={!coverageFor.plan_id || !coverageFor.ref_id}>Check coverage</Button>
          </div>
        </form>
        {coverage && (
          <div data-testid="plan-coverage" className="space-y-2">
            <Badge label={coverage.complete ? "Complete" : "Incomplete"} variant={coverage.complete ? "green" : "red"} />
            <ul className="space-y-1 text-sm">
              {coverage.steps.map((s) => (
                <li key={s.sequence} className="flex items-center gap-2">
                  <span className="w-48 text-gray-700">{s.sequence}. {s.qc_type}{s.qc_sub_type ? `/${s.qc_sub_type}` : ""}{s.is_mandatory ? "" : " (optional)"}</span>
                  <Badge label={s.state.replace("_", " ")} variant={statusVariant(s.state)} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>
    </div>
  );
}
