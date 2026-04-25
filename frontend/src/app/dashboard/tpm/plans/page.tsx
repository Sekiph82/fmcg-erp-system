"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tpmApi, TPMPlanStatus, TPMPlan, fmtCurrency, PLAN_STATUS_BADGE, PERIOD_TYPE_LABEL } from "@/lib/tpm";
import Link from "next/link";

export default function TPMPlansPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TPMPlanStatus | "">("");

  const { data: plans = [], isLoading } = useQuery({
    queryKey: ["tpm-plans", statusFilter],
    queryFn: () => tpmApi.getPlans(statusFilter as TPMPlanStatus || undefined),
  });

  const approve = useMutation({
    mutationFn: (id: string) => tpmApi.approvePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-plans"] }),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TPMPlanStatus }) =>
      tpmApi.updatePlanStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tpm-plans"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trade Promotion Plans</h1>
          <p className="text-sm text-gray-500">Annual and periodic trade promotion planning.</p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TPMPlanStatus | "")}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
            <option value="">All Statuses</option>
            {(["DRAFT","UNDER_REVIEW","APPROVED","ACTIVE","CLOSED","ARCHIVED"] as TPMPlanStatus[]).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <Link href="/dashboard/tpm/plans/new" className="glow-button text-sm">+ New Plan</Link>
        </div>
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Plan</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Year</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Period</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Planned Budget</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actual Spend</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Promos</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : plans.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-10 text-gray-400">No plans found.</td></tr>
            ) : plans.map((plan: TPMPlan) => (
              <tr key={plan.id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-200">{plan.plan_name}</p>
                  <p className="text-xs text-gray-500 font-mono">{plan.plan_code}</p>
                </td>
                <td className="px-4 py-3 text-gray-300">{plan.fiscal_year}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{PERIOD_TYPE_LABEL[plan.period_type]}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PLAN_STATUS_BADGE[plan.status]}`}>
                    {plan.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-indigo-400">{fmtCurrency(plan.total_planned_budget)}</td>
                <td className="px-4 py-3 text-right text-orange-400">{fmtCurrency(plan.total_actual_spend)}</td>
                <td className="px-4 py-3 text-right text-blue-400">{plan.promotion_count}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    {plan.status === "DRAFT" || plan.status === "UNDER_REVIEW" ? (
                      <button onClick={() => approve.mutate(plan.id)}
                        disabled={approve.isPending} className="glow-button text-xs !py-1">Approve</button>
                    ) : null}
                    {plan.status === "APPROVED" && (
                      <button onClick={() => updateStatus.mutate({ id: plan.id, status: "ACTIVE" })}
                        disabled={updateStatus.isPending} className="glow-button-secondary text-xs !py-1">Activate</button>
                    )}
                    {plan.status === "ACTIVE" && (
                      <button onClick={() => updateStatus.mutate({ id: plan.id, status: "CLOSED" })}
                        disabled={updateStatus.isPending} className="text-xs text-red-400 border border-red-200 rounded px-2 py-1">Close</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
