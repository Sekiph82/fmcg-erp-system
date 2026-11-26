"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { mpsApi, MPSLineConstraintDiagnostic } from "@/lib/mps";
import { tx } from "@/lib/i18n/core";

export default function MPSConstraintsPage() {
  const [planId, setPlanId] = useState("");
  const [notice, setNotice] = useState("");
  const queryClient = useQueryClient();
  const plans = useQuery({ queryKey: ["mps-plans"], queryFn: () => mpsApi.listPlans(100, 0) });
  const diagnostics = useQuery({
    queryKey: ["mps-constraints", planId], queryFn: () => mpsApi.getConstraints(planId), enabled: !!planId,
  });
  const run = useMutation({
    mutationFn: async (kind: "project" | "materials" | "capacity") => kind === "project"
      ? mpsApi.projectDemand(planId)
      : kind === "materials"
        ? mpsApi.evaluateMaterialFeasibility(planId)
        : mpsApi.runCapacity(planId),
    onSuccess: async (result) => {
      setNotice(JSON.stringify(result));
      await queryClient.invalidateQueries({ queryKey: ["mps-constraints", planId] });
    },
    onError: (error: Error) => setNotice(error.message),
  });

  return <main className="p-6 space-y-5">
    <div className="flex items-center justify-between">
      <div><h1 className="text-xl font-semibold">{tx("MPS demand, material, and capacity diagnostics")}</h1>
        <p className="text-sm text-gray-500">{tx("Run an evaluation and review its persisted reason, capacity slot, scenario, and recalculation provenance.")}</p></div>
      <Link className="text-sm text-blue-700 underline" href="/dashboard/mps">{tx("Back to MPS")}</Link>
    </div>
    <section className="flex flex-wrap items-center gap-3 rounded border bg-white p-4">
      <label className="text-sm font-medium" htmlFor="mps-plan">{tx("MPS plan")}</label>
      <select id="mps-plan" className="min-w-72 rounded border p-2" value={planId} onChange={(e) => setPlanId(e.target.value)}>
        <option value="">{tx("Choose a plan")}</option>
        {(plans.data ?? []).map((plan) => <option key={plan.id} value={plan.id}>{plan.plan_no} · {plan.plan_name} ({plan.status})</option>)}
      </select>
      <button disabled={!planId || run.isPending} onClick={() => run.mutate("project")} className="rounded bg-blue-700 px-3 py-2 text-sm text-white disabled:opacity-50">{tx("Project weekly demand")}</button>
      <button disabled={!planId || run.isPending} onClick={() => run.mutate("materials")} className="rounded bg-emerald-700 px-3 py-2 text-sm text-white disabled:opacity-50">{tx("Evaluate material feasibility")}</button>
      <button disabled={!planId || run.isPending} onClick={() => run.mutate("capacity")} className="rounded bg-amber-700 px-3 py-2 text-sm text-white disabled:opacity-50">{tx("Run capacity diagnostics")}</button>
    </section>
    {notice && <pre role="status" className="whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">{notice}</pre>}
    {plans.isLoading && <p>{tx("Loading plans…")}</p>}
    {diagnostics.isLoading && <p>{tx("Loading persisted diagnostics…")}</p>}
    {diagnostics.isError && <p className="text-red-700">{tx("Could not load diagnostics:")} {(diagnostics.error as Error).message}</p>}
    <section className="space-y-3">
      {(diagnostics.data ?? []).map((row: MPSLineConstraintDiagnostic) => <article key={`${row.run_id}-${row.line_id}`} className="rounded border bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div><strong>{tx("Line")} {row.diagnostics.line_no ?? row.line_id}</strong><p className="text-xs text-gray-500">{tx("Line ID")} {row.line_id}</p></div>
          <span className="text-sm">{row.diagnostics.status} · {row.source_version}{row.diagnostics.recalculation_state ? ` · ${row.diagnostics.recalculation_state}` : ""} · {row.computed_at ? new Date(row.computed_at).toLocaleString() : tx("time unavailable")}</span>
        </div>
        {row.diagnostics.evaluation_kind === "CAPACITY" && <p className="mt-2 text-xs text-gray-600">{tx("Run")} {row.run_id} · {row.diagnostics.scenario_provenance === "BASE_PLAN" ? tx("Base plan") : `Scenario ${row.diagnostics.scenario_id ?? "not recorded"}`} · {row.diagnostics.capacity_mode ?? tx("mode unavailable")}{row.diagnostics.superseded_by_run_id ? tx(" · replaced by run {superseded_by_run_id}", { superseded_by_run_id: row.diagnostics.superseded_by_run_id }) : ""}</p>}
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div><dt className="text-gray-500">{tx("Required date")}</dt><dd>{row.diagnostics.required_date ?? tx("Not recorded")}</dd></div>
          <div><dt className="text-gray-500">{tx("Planned quantity")}</dt><dd>{row.diagnostics.planned_quantity ?? tx("Not recorded")}</dd></div>
        </dl>
        {row.diagnostics.issues.length ? <ul className="mt-4 space-y-3">
          {row.diagnostics.issues.map((issue, index) => <li key={`${issue.reason_code}-${index}`} className="rounded border border-amber-200 bg-amber-50/50 p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <b>{issue.reason_code}</b>
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${issue.priority === "CRITICAL" ? "bg-red-100 text-red-800" : issue.priority === "HIGH" ? "bg-orange-100 text-orange-800" : "bg-slate-100 text-slate-700"}`}>{issue.priority}</span>
            </div>
            {issue.message && <p className="mt-2">{issue.message}</p>}
            {(issue.material_id || issue.material_code || issue.required_qty !== undefined || issue.shortage_qty !== undefined) && <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div><dt className="text-gray-500">{tx("Material")}</dt><dd>{issue.material_code ?? issue.material_id ?? tx("Not identified")}</dd></div>
              <div><dt className="text-gray-500">{tx("Required by")}</dt><dd>{issue.required_date ?? row.diagnostics.required_date ?? tx("Not recorded")}</dd></div>
              <div><dt className="text-gray-500">{tx("Required quantity")}</dt><dd>{issue.required_qty !== undefined ? `${issue.required_qty} ${issue.uom ?? ""}` : tx("Not available")}</dd></div>
              <div><dt className="text-gray-500">{tx("Available quantity")}</dt><dd>{issue.available_qty !== undefined ? `${issue.available_qty} ${issue.uom ?? ""}` : tx("Not available")}</dd></div>
              <div><dt className="text-gray-500">{tx("Shortage quantity")}</dt><dd>{issue.shortage_qty !== undefined ? `${issue.shortage_qty} ${issue.uom ?? ""}` : tx("Not available")}</dd></div>
              <div><dt className="text-gray-500">{tx("Latest order date")}</dt><dd>{issue.latest_order_date ?? tx("Not calculated")}</dd></div>
            </dl>}
            {(issue.work_center_id || issue.required_hours !== undefined || issue.overload_hours !== undefined) && <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div><dt className="text-gray-500">{tx("Work center")}</dt><dd>{issue.work_center_id ?? tx("Not identified")}</dd></div>
              <div><dt className="text-gray-500">{tx("Affected date")}</dt><dd>{issue.date ?? (issue.from_date && issue.to_date ? `${issue.from_date} – ${issue.to_date}` : issue.dates?.join(", ") ?? row.diagnostics.required_date ?? tx("Not recorded"))}</dd></div>
              <div><dt className="text-gray-500">{tx("Required hours")}</dt><dd>{issue.required_hours ?? tx("Not available")}</dd></div>
              <div><dt className="text-gray-500">{tx("Available hours")}</dt><dd>{issue.available_hours ?? tx("Not available")}</dd></div>
              <div><dt className="text-gray-500">{tx("Downtime hours")}</dt><dd>{issue.downtime_hours ?? tx("Not available")}</dd></div>
              <div><dt className="text-gray-500">{tx("Overload hours")}</dt><dd>{issue.overload_hours ?? tx("Not available")}</dd></div>
              {(issue.capacity_slot_key || issue.capacity_slot_id) && <div><dt className="text-gray-500">{tx("Capacity slot")}</dt><dd>{issue.capacity_slot_key ?? issue.capacity_slot_id}</dd></div>}
              {issue.slot_required_hours !== undefined && <div><dt className="text-gray-500">{tx("Total slot load")}</dt><dd>{issue.slot_required_hours}</dd></div>}
              {issue.net_available_hours !== undefined && <div><dt className="text-gray-500">{tx("Net available hours")}</dt><dd>{issue.net_available_hours}</dd></div>}
              {issue.affected_line_ids?.length ? <div className="sm:col-span-2 lg:col-span-3"><dt className="text-gray-500">{tx("Affected lines")}</dt><dd>{issue.affected_line_ids.join(", ")}</dd></div> : null}
              {issue.capacity_uom && <div><dt className="text-gray-500">{tx("Configured capacity rate unit")}</dt><dd>{issue.capacity_uom}</dd></div>}
              {issue.product_uom && <div><dt className="text-gray-500">{tx("Product unit")}</dt><dd>{issue.product_uom}</dd></div>}
            </dl>}
            {issue.substitution_policy && <p className="mt-2">{tx("Substitution policy:")} <b>{issue.substitution_policy}</b>{issue.substitute_group_id ? tx(" · group {substitute_group_id}", { substitute_group_id: issue.substitute_group_id }) : ""}</p>}
            {issue.excluded_receipts?.length ? <p className="mt-2">{tx("Excluded receipts:")} {issue.excluded_receipts.map((receipt) => `${receipt.po_no} (${receipt.due_date}: ${receipt.reason})`).join(", ")}</p> : null}
            <p className="mt-2 text-xs text-gray-600">{tx("Source:")} {issue.provenance}</p>
          </li>)}
        </ul> : <p className="mt-3 text-sm text-gray-500">{tx("No unresolved constraint reasons in this evaluation.")}</p>}
      </article>)}
      {planId && !diagnostics.isLoading && diagnostics.data?.length === 0 && <p className="text-sm text-gray-500">{tx("No persisted evaluations. Run material feasibility to create diagnostic evidence.")}</p>}
    </section>
  </main>;
}
