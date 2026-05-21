"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { marketingApi, AdPlatform } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const AD_PLATFORMS: AdPlatform[] = ["META", "GOOGLE", "TIKTOK", "TWITTER", "LINKEDIN", "YOUTUBE", "OTHER"];

export default function NewAdPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    platform: "META" as AdPlatform,
    ad_name: "",
    ad_date: new Date().toISOString().split("T")[0],
    campaign_id: "",
    impressions: "",
    clicks: "",
    ctr: "",
    cpc: "",
    spend: "",
    conversions: "",
    cost_per_conversion: "",
    revenue_generated: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.ads.create({
        platform: form.platform,
        ad_name: form.ad_name || null,
        ad_date: form.ad_date,
        campaign_id: form.campaign_id || null,
        impressions: form.impressions ? parseInt(form.impressions) : null,
        clicks: form.clicks ? parseInt(form.clicks) : null,
        ctr: form.ctr ? parseFloat(form.ctr) : null,
        cpc: form.cpc ? parseFloat(form.cpc) : null,
        spend: form.spend ? parseFloat(form.spend) : null,
        conversions: form.conversions ? parseInt(form.conversions) : null,
        cost_per_conversion: form.cost_per_conversion ? parseFloat(form.cost_per_conversion) : null,
        revenue_generated: form.revenue_generated ? parseFloat(form.revenue_generated) : null,
        notes: form.notes || null,
      }),
    onSuccess: (r) => router.push(`/dashboard/marketing/ads/${r.data.id}`),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <RequirePermission permission="ad_performance.edit">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Back
          </button>
          <h1 className="text-2xl font-bold">Log Ad Performance</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Platform *</label>
              <select value={form.platform} onChange={(e) => set("platform", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {AD_PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Ad Date *</label>
              <input type="date" value={form.ad_date} onChange={(e) => set("ad_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Ad Name</label>
            <input type="text" value={form.ad_name} onChange={(e) => set("ad_name", e.target.value)}
              placeholder="e.g. Ramadan Launch — Carousel"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Campaign ID <span className="text-slate-600">(optional)</span></label>
            <input type="text" value={form.campaign_id} onChange={(e) => set("campaign_id", e.target.value)}
              placeholder="UUID"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <hr className="border-slate-700/50" />
          <p className="text-xs text-slate-500 -mb-2">Reach & engagement</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Impressions</label>
              <input type="number" min="0" value={form.impressions} onChange={(e) => set("impressions", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Clicks</label>
              <input type="number" min="0" value={form.clicks} onChange={(e) => set("clicks", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">CTR %</label>
              <input type="number" step="0.01" min="0" value={form.ctr} onChange={(e) => set("ctr", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">CPC (KES)</label>
              <input type="number" step="0.01" min="0" value={form.cpc} onChange={(e) => set("cpc", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <hr className="border-slate-700/50" />
          <p className="text-xs text-slate-500 -mb-2">Spend & conversions</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Spend (KES)</label>
              <input type="number" step="0.01" min="0" value={form.spend} onChange={(e) => set("spend", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Conversions</label>
              <input type="number" min="0" value={form.conversions} onChange={(e) => set("conversions", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Cost / Conversion (KES)</label>
              <input type="number" step="0.01" min="0" value={form.cost_per_conversion}
                onChange={(e) => set("cost_per_conversion", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Revenue Generated (KES)</label>
              <input type="number" step="0.01" min="0" value={form.revenue_generated}
                onChange={(e) => set("revenue_generated", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={2} placeholder="Observations, creative notes…"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
            <button
              onClick={() => createMut.mutate()}
              disabled={!form.ad_date || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Log Ad"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
