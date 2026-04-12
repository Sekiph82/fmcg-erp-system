"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, SocialMediaActivity, InfluencerPlatform, ContentType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: InfluencerPlatform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "FACEBOOK", "X", "OTHER"];
const CONTENT_TYPES: ContentType[] = ["POST", "STORY", "REEL", "VIDEO", "LIVE", "BLOG", "OTHER"];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);
}

export default function SocialActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<SocialMediaActivity>>({});
  const [error, setError] = useState("");

  const { data: activity, isLoading } = useQuery({
    queryKey: ["social-media", id],
    queryFn: () => marketingApi.social.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.social.update(id, form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["social-media", id] });
      qc.invalidateQueries({ queryKey: ["social-media"] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.social.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/social-media"),
  });

  const startEdit = () => {
    if (!activity) return;
    setForm({ ...activity });
    setEditing(true);
  };

  const set = (k: keyof SocialMediaActivity, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!activity) return <div className="p-8 text-red-400">Activity not found.</div>;

  const engagementRate =
    activity.reach && activity.engagements
      ? ((activity.engagements / activity.reach) * 100).toFixed(2)
      : null;

  return (
    <RequirePermission permission="social_media.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Social Media
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{activity.platform} · {activity.content_type ?? "Post"}</h1>
              <p className="text-slate-400 text-sm mt-1">{activity.published_date}</p>
            </div>
            {activity.post_url && (
              <a href={activity.post_url} target="_blank" rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm text-slate-300">
                View Post ↗
              </a>
            )}
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: "Impressions", value: fmt(activity.impressions) },
            { label: "Reach",       value: fmt(activity.reach) },
            { label: "Engagements", value: fmt(activity.engagements) },
            { label: "Eng. Rate",   value: engagementRate ? `${engagementRate}%` : "—" },
          ].map((k) => (
            <div key={k.label} className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
              <p className="text-xs text-slate-400 mb-0.5">{k.label}</p>
              <p className="text-lg font-bold">{k.value}</p>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        {!editing ? (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="grid grid-cols-2 gap-x-8 gap-y-5 mb-6">
              <Field label="Platform" value={activity.platform} />
              <Field label="Content Type" value={activity.content_type} />
              <Field label="Published" value={activity.published_date} />
              <Field label="Campaign ID" value={activity.campaign_id} />
              <Field label="Clicks" value={activity.clicks?.toLocaleString()} />
              <Field label="Shares" value={activity.shares_count?.toLocaleString()} />
              <Field label="Comments" value={activity.comments_count?.toLocaleString()} />
              <Field label="Saves" value={activity.saves_count?.toLocaleString()} />
            </div>
            {activity.notes && (
              <div className="border-t border-slate-700/50 pt-4">
                <p className="text-xs text-slate-400 mb-1">Notes</p>
                <p className="text-sm text-slate-300">{activity.notes}</p>
              </div>
            )}
            <div className="border-t border-slate-700/50 pt-4 mt-4 flex justify-end gap-2">
              <RequirePermission permission="social_media.edit">
                <button onClick={startEdit}
                  className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">Edit</button>
                <button onClick={() => { if (confirm("Delete this activity?")) deleteMut.mutate(); }}
                  className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">Delete</button>
              </RequirePermission>
            </div>
          </div>
        ) : (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Platform</label>
                <select value={String(form.platform ?? activity.platform)}
                  onChange={(e) => set("platform", e.target.value as InfluencerPlatform)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Content Type</label>
                <select value={String(form.content_type ?? activity.content_type ?? "POST")}
                  onChange={(e) => set("content_type", e.target.value as ContentType)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {CONTENT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Date</label>
                <input type="date" value={String(form.published_date ?? activity.published_date)}
                  onChange={(e) => set("published_date", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Impressions</label>
                <input type="number" value={String(form.impressions ?? "")}
                  onChange={(e) => set("impressions", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Reach</label>
                <input type="number" value={String(form.reach ?? "")}
                  onChange={(e) => set("reach", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Engagements</label>
                <input type="number" value={String(form.engagements ?? "")}
                  onChange={(e) => set("engagements", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Clicks</label>
                <input type="number" value={String(form.clicks ?? "")}
                  onChange={(e) => set("clicks", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Comments</label>
                <input type="number" value={String(form.comments_count ?? "")}
                  onChange={(e) => set("comments_count", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Shares</label>
                <input type="number" value={String(form.shares_count ?? "")}
                  onChange={(e) => set("shares_count", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Saves</label>
                <input type="number" value={String(form.saves_count ?? "")}
                  onChange={(e) => set("saves_count", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea value={String(form.notes ?? "")}
                onChange={(e) => set("notes", e.target.value || null)}
                rows={2}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>

            <div className="flex justify-end gap-3">
              <button onClick={() => { setEditing(false); setError(""); }}
                className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
              <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium">
                {updateMut.isPending ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
