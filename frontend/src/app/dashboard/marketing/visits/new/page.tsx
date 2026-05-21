"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { marketingApi, VisitType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const VISIT_TYPES: VisitType[] = [
  "SALES", "MARKETING", "TRADE_AUDIT", "MERCHANDISING", "FEEDBACK", "STORE_CHECK",
];

export default function NewVisitPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [form, setForm] = useState({
    visit_date:          new Date().toISOString().split("T")[0],
    visit_type:          "STORE_CHECK" as VisitType,
    customer_id:         "",
    crm_profile_id:      "",
    employee_id:         "",
    purpose:             "",
    outcome:             "",
    followup_required:   false,
    display_observation: "",
    stock_observation:   "",
    competitor_notes:    "",
  });
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      marketingApi.visits.create({
        visit_date:          form.visit_date,
        visit_type:          form.visit_type,
        customer_id:         form.customer_id || undefined,
        crm_profile_id:      form.crm_profile_id || undefined,
        employee_id:         form.employee_id || undefined,
        purpose:             form.purpose || undefined,
        outcome:             form.outcome || undefined,
        followup_required:   form.followup_required,
        display_observation: form.display_observation || undefined,
        stock_observation:   form.stock_observation || undefined,
        competitor_notes:    form.competitor_notes || undefined,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["visits"] });
      router.push(`/dashboard/marketing/visits/${res.data.id}`);
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to log visit.");
    },
  });

  function set(key: string, val: string | boolean) {
    setForm((f) => ({ ...f, [key]: val }));
    setError("");
  }

  return (
    <RequirePermission permission="customer_visits.create">
      <div className="min-h-screen bg-[#0b1120] p-4 text-white max-w-lg mx-auto">
        <div className="mb-6">
          <a href="/dashboard/marketing/visits" className="text-sm text-slate-400 hover:text-white mb-2 inline-block">
            ← Field Visits
          </a>
          <h1 className="text-2xl font-bold">Log Visit</h1>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">{error}</div>
        )}

        <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5 space-y-4">
          {/* Type and date — most important, big on mobile */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Visit Type *</label>
              <select value={form.visit_type} onChange={(e) => set("visit_type", e.target.value as VisitType)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white">
                {VISIT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Visit Date *</label>
              <input type="date" value={form.visit_date} onChange={(e) => set("visit_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white" />
            </div>
          </div>

          {/* Purpose */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Purpose</label>
            <input value={form.purpose} onChange={(e) => set("purpose", e.target.value)}
              placeholder="Why are you visiting?"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-600" />
          </div>

          {/* Store/Display observations */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Display Observation</label>
            <textarea value={form.display_observation} onChange={(e) => set("display_observation", e.target.value)}
              rows={2} placeholder="How is the product displayed?"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Stock Observation</label>
            <textarea value={form.stock_observation} onChange={(e) => set("stock_observation", e.target.value)}
              rows={2} placeholder="Stock levels and issues noted"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Competitor Notes</label>
            <textarea value={form.competitor_notes} onChange={(e) => set("competitor_notes", e.target.value)}
              rows={2} placeholder="Competitor products observed"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          {/* Outcome */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Outcome</label>
            <textarea value={form.outcome} onChange={(e) => set("outcome", e.target.value)}
              rows={2} placeholder="What was achieved or agreed?"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex items-center gap-3">
            <input type="checkbox" id="followup_required" checked={form.followup_required}
              onChange={(e) => set("followup_required", e.target.checked)}
              className="w-4 h-4 rounded border-slate-700" />
            <label htmlFor="followup_required" className="text-sm text-slate-300">Follow-up Required</label>
          </div>

          {/* IDs — optional, collapsible feel */}
          <details className="text-sm">
            <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400">Optional: Link to Customer / CRM</summary>
            <div className="mt-3 space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Customer ID (UUID)</label>
                <input value={form.customer_id} onChange={(e) => set("customer_id", e.target.value)}
                  placeholder="Optional"
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 font-mono" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">CRM Profile ID (UUID)</label>
                <input value={form.crm_profile_id} onChange={(e) => set("crm_profile_id", e.target.value)}
                  placeholder="Optional"
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 font-mono" />
              </div>
            </div>
          </details>

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => mut.mutate()}
              disabled={mut.isPending || !form.visit_date}
              className="flex-1 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {mut.isPending ? "Saving..." : "Log Visit"}
            </button>
            <a href="/dashboard/marketing/visits"
              className="px-4 py-2.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
              Cancel
            </a>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
