"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { tpmApi, TPMPeriodType } from "@/lib/tpm";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function NewTPMPlanPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    plan_code: "",
    plan_name: "",
    fiscal_year: new Date().getFullYear(),
    period_type: "ANNUAL" as TPMPeriodType,
    plan_start_date: "",
    plan_end_date: "",
    total_planned_budget: "",
    notes: "",
  });

  const create = useMutation({
    mutationFn: () => tpmApi.createPlan({
      ...form,
      fiscal_year: Number(form.fiscal_year),
      total_planned_budget: Number(form.total_planned_budget) || 0,
    }),
    onSuccess: () => router.push("/dashboard/tpm/plans"),
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      <div>
        <Link href="/dashboard/tpm/plans" className="text-xs text-gray-500 hover:text-indigo-400">← Back to Plans</Link>
        <h1 className="text-2xl font-bold text-gray-900 mt-1">New Trade Promotion Plan</h1>
        <p className="text-sm text-gray-500">Define the plan scope, fiscal year, and budget envelope.</p>
      </div>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Plan Identity</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Plan Code *</label>
            <input type="text" value={form.plan_code} onChange={(e) => set("plan_code", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="TPM-2026-Q1" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Fiscal Year *</label>
            <input type="number" value={form.fiscal_year} onChange={(e) => set("fiscal_year", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-gray-500">Plan Name *</label>
            <input type="text" value={form.plan_name} onChange={(e) => set("plan_name", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. FY2026 Annual Trade Plan" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Period Type</label>
            <select value={form.period_type} onChange={(e) => set("period_type", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {(["ANNUAL","QUARTERLY","MONTHLY","EVENT_BASED"] as TPMPeriodType[]).map((t) => (
                <option key={t} value={t}>{t.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Total Planned Budget (KES)</label>
            <input type="number" value={form.total_planned_budget} onChange={(e) => set("total_planned_budget", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Plan Start Date *</label>
            <input type="date" value={form.plan_start_date} onChange={(e) => set("plan_start_date", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Plan End Date *</label>
            <input type="date" value={form.plan_end_date} onChange={(e) => set("plan_end_date", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={3} className="rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none" />
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <Link href="/dashboard/tpm/plans" className="glow-button-secondary text-sm">Cancel</Link>
        <button onClick={() => create.mutate()} disabled={create.isPending || !form.plan_code || !form.plan_name}
          className="glow-button">
          {create.isPending ? "Creating…" : "Create Plan"}
        </button>
      </div>
      {create.isError && (
        <p className="text-sm text-red-400">Failed to create plan. Check required fields.</p>
      )}
    </div>
  );
}
