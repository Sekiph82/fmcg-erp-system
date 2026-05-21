"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { marketingApi, InfluencerPlatform, InfluencerStatus } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: InfluencerPlatform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "FACEBOOK", "X", "OTHER"];
const STATUSES: InfluencerStatus[] = ["PROSPECT", "ACTIVE", "INACTIVE", "BLOCKED"];

export default function NewInfluencerPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    influencer_name: "",
    platform: "INSTAGRAM" as InfluencerPlatform,
    handle: "",
    category: "",
    region: "",
    followers_count: "",
    engagement_rate: "",
    contact_info: "",
    status: "PROSPECT" as InfluencerStatus,
    notes: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.influencers.create({
        influencer_name: form.influencer_name,
        platform: form.platform,
        handle: form.handle || null,
        category: form.category || null,
        region: form.region || null,
        followers_count: form.followers_count ? parseInt(form.followers_count) : null,
        engagement_rate: form.engagement_rate ? parseFloat(form.engagement_rate) : null,
        contact_info: form.contact_info || null,
        status: form.status,
        notes: form.notes || null,
      }),
    onSuccess: (r) => router.push(`/dashboard/marketing/influencers/${r.data.id}`),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <RequirePermission permission="influencers.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Back
          </button>
          <h1 className="text-2xl font-bold">Add Influencer</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Name *</label>
            <input type="text" value={form.influencer_name}
              onChange={(e) => set("influencer_name", e.target.value)}
              placeholder="Full name or brand name"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Platform *</label>
              <select value={form.platform} onChange={(e) => set("platform", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Status</label>
              <select value={form.status} onChange={(e) => set("status", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Handle</label>
              <input type="text" value={form.handle}
                onChange={(e) => set("handle", e.target.value)}
                placeholder="@username (without @)"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Category</label>
              <input type="text" value={form.category}
                onChange={(e) => set("category", e.target.value)}
                placeholder="e.g. Lifestyle, Food, Tech"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Region</label>
              <input type="text" value={form.region}
                onChange={(e) => set("region", e.target.value)}
                placeholder="Nairobi, Lagos…"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Followers</label>
              <input type="number" min="0" value={form.followers_count}
                onChange={(e) => set("followers_count", e.target.value)}
                placeholder="50000"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Engagement %</label>
              <input type="number" step="0.01" min="0" max="100" value={form.engagement_rate}
                onChange={(e) => set("engagement_rate", e.target.value)}
                placeholder="3.5"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Contact Info</label>
            <input type="text" value={form.contact_info}
              onChange={(e) => set("contact_info", e.target.value)}
              placeholder="Email / WhatsApp / DM"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={3} placeholder="Additional context, past collaborations…"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">
              Cancel
            </button>
            <button
              onClick={() => createMut.mutate()}
              disabled={!form.influencer_name || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Add Influencer"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
