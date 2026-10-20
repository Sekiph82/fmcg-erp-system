"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { mpsApi, MPSLineConstraintDiagnostic } from "@/lib/mps";

export default function MPSConstraintsPage() {
  const [planId, setPlanId] = useState("");
  const [notice, setNotice] = useState("");
  const queryClient = useQueryClient();
  const plans = useQuery({ queryKey: ["mps-plans"], queryFn: () => mpsApi.listPlans(100, 0) });
  const diagnostics = useQuery({
    queryKey: ["mps-constraints", planId], queryFn: () => mpsApi.getConstraints(planId), enabled: !!planId,
  });
  const run = useMutation({
    mutationFn: async (kind: "project" | "materials") => kind === "project"
      ? mpsApi.projectDemand(planId)
      : mpsApi.evaluateMaterialFeasibility(planId),
    onSuccess: async (result) => {
      setNotice(JSON.stringify(result));
      await queryClient.invalidateQueries({ queryKey: ["mps-constraints", planId] });
    },
    onError: (error: Error) => setNotice(error.message),
  });

  return <main className="p-6 space-y-5">
    <div className="flex items-center justify-between">
      <div><h1 className="text-xl font-semibold">Demand and material constraints</h1>
        <p className="text-sm text-gray-500">Project warehouse scoped demand, check approved BOM supply, and review persisted reasons.</p></div>
      <Link className="text-sm text-blue-700 underline" href="/dashboard/mps">Back to MPS</Link>
    </div>
    <section className="flex flex-wrap items-center gap-3 rounded border bg-white p-4">
      <label className="text-sm font-medium" htmlFor="mps-plan">MPS plan</label>
      <select id="mps-plan" className="min-w-72 rounded border p-2" value={planId} onChange={(e) => setPlanId(e.target.value)}>
        <option value="">Choose a plan</option>
        {(plans.data ?? []).map((plan) => <option key={plan.id} value={plan.id}>{plan.plan_no} · {plan.plan_name} ({plan.status})</option>)}
      </select>
      <button disabled={!planId || run.isPending} onClick={() => run.mutate("project")} className="rounded bg-blue-700 px-3 py-2 text-sm text-white disabled:opacity-50">Project weekly demand</button>
      <button disabled={!planId || run.isPending} onClick={() => run.mutate("materials")} className="rounded bg-emerald-700 px-3 py-2 text-sm text-white disabled:opacity-50">Evaluate material feasibility</button>
    </section>
    {notice && <pre role="status" className="whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">{notice}</pre>}
    {plans.isLoading && <p>Loading plans…</p>}
    {diagnostics.isLoading && <p>Loading persisted diagnostics…</p>}
    {diagnostics.isError && <p className="text-red-700">Could not load diagnostics: {(diagnostics.error as Error).message}</p>}
    <section className="space-y-3">
      {(diagnostics.data ?? []).map((row: MPSLineConstraintDiagnostic) => <article key={`${row.run_id}-${row.line_id}`} className="rounded border bg-white p-4">
        <div className="flex flex-wrap justify-between gap-2"><strong>Line {row.line_id}</strong><span className="text-sm">{row.diagnostics.status} · {row.source_version} · {row.computed_at ? new Date(row.computed_at).toLocaleString() : "time unavailable"}</span></div>
        {row.diagnostics.issues.length ? <ul className="mt-3 list-disc pl-5 text-sm">{row.diagnostics.issues.map((issue, index) => <li key={`${issue.reason_code}-${index}`}><b>{issue.reason_code}</b>{issue.message ? `: ${issue.message}` : ""}{issue.shortage_qty ? ` — shortage ${issue.shortage_qty} ${issue.uom ?? ""}` : ""}</li>)}</ul> : <p className="mt-2 text-sm text-gray-500">No unresolved constraint reasons in this evaluation.</p>}
      </article>)}
      {planId && !diagnostics.isLoading && diagnostics.data?.length === 0 && <p className="text-sm text-gray-500">No persisted evaluations. Run material feasibility to create diagnostic evidence.</p>}
    </section>
  </main>;
}
