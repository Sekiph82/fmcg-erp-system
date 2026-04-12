"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { marketingApi, InfluencerPlatform, ContentType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: InfluencerPlatform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "FACEBOOK", "X", "OTHER"];
const CONTENT_TYPES: ContentType[] = ["POST", "STORY", "REEL", "VIDEO", "LIVE", "BLOG", "OTHER"];

export default function NewSocialActivityPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    platform: "INSTAGRAM" as InfluencerPlatform,
    content_type: "POST" as ContentType,
    published_date: new Date().toISOString().split("T")[0],
    campaign_id: "",
    post_url: "",
    impressions: "",
    reach: "",
    clicks: "",
    engagements: "",
    comments_count: "",
    shares_count: "",
    saves_count: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.social.create({
        platform: form.platform,
        content_type: form.content_type,
        published_date: form.published_date,
        campaign_id: form.campaign_id || null,
        post_url: form.post_url || null,
        impressions: form.impressions ? parseInt(form.impressions) : null,
        reach: form.reach ? parseInt(form.reach) : null,
        clicks: form.clicks ? parseInt(form.clicks) : null,
        engagements: form.engagements ? parseInt(form.engagements) : null,
        comments_count: form.comments_count ? parseInt(form.comments_count) : null,
        shares_count: form.shares_count ? parseInt(form.shares_count) : null,
        saves_count: form.saves_count ? parseInt(form.saves_count) : null,
        notes: form.notes || null,
      }),
    onSuccess: (r) => router.push(`/dashboard/marketing/social-media/${r.data.id}`),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <RequirePermission permission="social_media.edit">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Back
          </button>
          <h1 className="text-2xl font-bold">Log Social Activity</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Platform *</label>
              <select value={form.platform} onChange={(e) => set("platform", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Content Type</label>
              <select value={form.content_type} onChange={(e) => set("content_type", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {CONTENT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Published Date *</label>
              <input type="date" value={form.published_date}
                onChange={(e) => set("published_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Post URL</label>
            <input type="text" value={form.post_url} onChange={(e) => set("post_url", e.target.value)}
              placeholder="https://instagram.com/p/..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Campaign ID <span className="text-slate-600">(optional)</span></label>
            <input type="text" value={form.campaign_id} onChange={(e) => set("campaign_id", e.target.value)}
              placeholder="UUID"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <hr className="border-slate-700/50" />
          <p className="text-xs text-slate-500 -mb-2">Performance metrics</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Impressions</label>
              <input type="number" min="0" value={form.impressions} onChange={(e) => set("impressions", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Reach</label>
              <input type="number" min="0" value={form.reach} onChange={(e) => set("reach", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Engagements</label>
              <input type="number" min="0" value={form.engagements} onChange={(e) => set("engagements", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Clicks</label>
              <input type="number" min="0" value={form.clicks} onChange={(e) => set("clicks", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Comments</label>
              <input type="number" min="0" value={form.comments_count} onChange={(e) => set("comments_count", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Shares</label>
              <input type="number" min="0" value={form.shares_count} onChange={(e) => set("shares_count", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Saves</label>
              <input type="number" min="0" value={form.saves_count} onChange={(e) => set("saves_count", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={2} placeholder="Context, observations…"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
            <button
              onClick={() => createMut.mutate()}
              disabled={!form.published_date || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Log Activity"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
