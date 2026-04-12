"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { marketingApi, CampaignType, CampaignStatus } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const CAMPAIGN_TYPES: CampaignType[] = [
  "TRADE", "DIGITAL", "RETAIL", "DISTRIBUTOR", "LAUNCH",
  "SEASONAL", "LOYALTY", "AWARENESS", "ACQUISITION", "RETENTION",
];

const CAMPAIGN_STATUSES: CampaignStatus[] = [
  "DRAFT", "PLANNED", "ACTIVE", "PAUSED",
];

export default function NewCampaignPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [form, setForm] = useState({
    campaign_code: "",
    campaign_name: "",
    campaign_type: "TRADE" as CampaignType,
    objective: "",
    region: "",
    country: "",
    start_date: "",
    end_date: "",
    status: "DRAFT" as CampaignStatus,
    budget: "",
    expected_revenue: "",
    notes: "",
  });

  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      marketingApi.campaigns.create({
        campaign_code:    form.campaign_code,
        campaign_name:    form.campaign_name,
        campaign_type:    form.campaign_type,
        objective:        form.objective || undefined,
        region:           form.region || undefined,
        country:          form.country || undefined,
        start_date:       form.start_date,
        end_date:         form.end_date,
        budget:           form.budget ? Number(form.budget) : undefined,
        expected_revenue: form.expected_revenue ? Number(form.expected_revenue) : undefined,
        notes:            form.notes || undefined,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      router.push(`/dashboard/marketing/campaigns/${res.data.id}`);
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create campaign.");
    },
  });

  function set(key: string, val: string) {
    setForm((f) => ({ ...f, [key]: val }));
    setError("");
  }

  return (
    <RequirePermission permission="campaigns.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl">
        <div className="mb-6">
          <a href="/dashboard/marketing/campaigns" className="text-sm text-slate-400 hover:text-white mb-2 inline-block">
            ← Back to Campaigns
          </a>
          <h1 className="text-2xl font-bold">New Campaign</h1>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-6 space-y-5">
          {/* Code & Name */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Campaign Code *</label>
              <input value={form.campaign_code} onChange={(e) => set("campaign_code", e.target.value)}
                placeholder="e.g. CAM-2026-001"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Campaign Name *</label>
              <input value={form.campaign_name} onChange={(e) => set("campaign_name", e.target.value)}
                placeholder="e.g. Ramadan 2026 Push"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          {/* Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Campaign Type *</label>
              <select value={form.campaign_type} onChange={(e) => set("campaign_type", e.target.value as CampaignType)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {CAMPAIGN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Initial Status</label>
              <select value={form.status} onChange={(e) => set("status", e.target.value as CampaignStatus)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {CAMPAIGN_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          {/* Region & Country */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Region</label>
              <input value={form.region} onChange={(e) => set("region", e.target.value)}
                placeholder="e.g. Nairobi, Istanbul"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Country</label>
              <input value={form.country} onChange={(e) => set("country", e.target.value)}
                placeholder="e.g. Kenya"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Start Date *</label>
              <input type="date" value={form.start_date} onChange={(e) => set("start_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">End Date *</label>
              <input type="date" value={form.end_date} onChange={(e) => set("end_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          {/* Budget & Expected Revenue */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Budget (KES)</label>
              <input type="number" value={form.budget} onChange={(e) => set("budget", e.target.value)}
                placeholder="0.00"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Expected Revenue (KES)</label>
              <input type="number" value={form.expected_revenue} onChange={(e) => set("expected_revenue", e.target.value)}
                placeholder="0.00"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          {/* Objective */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Objective</label>
            <textarea value={form.objective} onChange={(e) => set("objective", e.target.value)}
              rows={2} placeholder="Campaign objective and goals..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={2} placeholder="Internal notes..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => mut.mutate()}
              disabled={mut.isPending || !form.campaign_code || !form.campaign_name || !form.start_date || !form.end_date}
              className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {mut.isPending ? "Creating..." : "Create Campaign"}
            </button>
            <a href="/dashboard/marketing/campaigns"
              className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
              Cancel
            </a>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
