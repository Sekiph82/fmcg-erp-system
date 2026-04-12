"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  marketingApi, Influencer, InfluencerCampaignLink, InfluencerAttribution,
  InfluencerPlatform, InfluencerStatus, ContentType, INFLUENCER_STATUS_COLORS,
} from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: InfluencerPlatform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "FACEBOOK", "X", "OTHER"];
const STATUSES: InfluencerStatus[] = ["PROSPECT", "ACTIVE", "INACTIVE", "BLOCKED"];
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

export default function InfluencerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"profile" | "campaigns" | "attribution">("profile");
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<Influencer>>({});
  const [error, setError] = useState("");

  // New campaign link form
  const [showLinkForm, setShowLinkForm] = useState(false);
  const [linkForm, setLinkForm] = useState({
    campaign_id: "",
    content_type: "POST" as ContentType,
    tracking_link: "",
    agreed_fee: "",
    expected_posts: "",
    notes: "",
  });

  const { data: inf, isLoading } = useQuery({
    queryKey: ["influencer", id],
    queryFn: () => marketingApi.influencers.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: links = [] } = useQuery({
    queryKey: ["influencer-links", id],
    queryFn: () => marketingApi.influencerLinks.list(id).then((r) => r.data),
    enabled: !!id && tab === "campaigns",
  });

  const { data: attributions = [] } = useQuery({
    queryKey: ["influencer-attribution", id],
    queryFn: () => marketingApi.attribution.list({ influencer_id: id }).then((r) => r.data),
    enabled: !!id && tab === "attribution",
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.influencers.update(id, editForm as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["influencer", id] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.influencers.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/influencers"),
  });

  const createLinkMut = useMutation({
    mutationFn: () =>
      marketingApi.influencerLinks.create({
        influencer_id: id,
        campaign_id: linkForm.campaign_id,
        content_type: linkForm.content_type,
        tracking_link: linkForm.tracking_link || null,
        agreed_fee: linkForm.agreed_fee ? parseFloat(linkForm.agreed_fee) : null,
        expected_posts: linkForm.expected_posts ? parseInt(linkForm.expected_posts) : null,
        notes: linkForm.notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["influencer-links", id] });
      setShowLinkForm(false);
      setLinkForm({ campaign_id: "", content_type: "POST", tracking_link: "", agreed_fee: "", expected_posts: "", notes: "" });
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const startEdit = () => {
    if (!inf) return;
    setEditForm({
      influencer_name: inf.influencer_name,
      platform: inf.platform,
      handle: inf.handle ?? undefined,
      category: inf.category ?? undefined,
      region: inf.region ?? undefined,
      followers_count: inf.followers_count ?? undefined,
      engagement_rate: inf.engagement_rate ?? undefined,
      status: inf.status,
      notes: inf.notes ?? undefined,
    });
    setEditing(true);
  };

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!inf) return <div className="p-8 text-red-400">Influencer not found.</div>;

  const totalAttributedRevenue = attributions.reduce((s, a) => s + Number(a.attributed_revenue ?? 0), 0);
  const totalConversions = attributions.reduce((s, a) => s + a.conversions, 0);

  return (
    <RequirePermission permission="influencers.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Influencers
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{inf.influencer_name}</h1>
              <p className="text-slate-400 text-sm mt-1">
                {inf.platform}{inf.handle && ` · @${inf.handle}`}{inf.region && ` · ${inf.region}`}
              </p>
            </div>
            <span className={`text-sm font-semibold ${INFLUENCER_STATUS_COLORS[inf.status as InfluencerStatus]}`}>
              {inf.status}
            </span>
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Followers</p>
            <p className="text-lg font-bold">{fmt(inf.followers_count)}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Engagement</p>
            <p className="text-lg font-bold">{inf.engagement_rate ? `${Number(inf.engagement_rate).toFixed(2)}%` : "—"}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Campaign Links</p>
            <p className="text-lg font-bold">{links.length}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Attributed Revenue</p>
            <p className="text-lg font-bold text-emerald-400">
              {totalAttributedRevenue > 0 ? `KES ${totalAttributedRevenue.toLocaleString()}` : "—"}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 bg-[#131c2e] rounded-lg p-1 w-fit">
          {(["profile", "campaigns", "attribution"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}>
              {t}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        {/* Profile tab */}
        {tab === "profile" && (
          <>
            {!editing ? (
              <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
                <div className="grid grid-cols-2 gap-x-8 gap-y-5 mb-6">
                  <Field label="Name" value={inf.influencer_name} />
                  <Field label="Platform" value={inf.platform} />
                  <Field label="Handle" value={inf.handle ? `@${inf.handle}` : null} />
                  <Field label="Category" value={inf.category} />
                  <Field label="Region" value={inf.region} />
                  <Field label="Status" value={inf.status} />
                  <Field label="Contact" value={inf.contact_info} />
                  <Field label="Created" value={inf.created_at ? new Date(inf.created_at).toLocaleDateString() : null} />
                </div>
                {inf.notes && (
                  <div className="border-t border-slate-700/50 pt-4">
                    <p className="text-xs text-slate-400 mb-1">Notes</p>
                    <p className="text-sm text-slate-300">{inf.notes}</p>
                  </div>
                )}
                <div className="border-t border-slate-700/50 pt-4 mt-4 flex justify-end gap-2">
                  <RequirePermission permission="influencers.edit">
                    <button onClick={startEdit}
                      className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">
                      Edit
                    </button>
                    <button
                      onClick={() => { if (confirm("Delete this influencer?")) deleteMut.mutate(); }}
                      className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">
                      Delete
                    </button>
                  </RequirePermission>
                </div>
              </div>
            ) : (
              <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Name</label>
                    <input type="text" value={editForm.influencer_name ?? ""}
                      onChange={(e) => setEditForm((f) => ({ ...f, influencer_name: e.target.value }))}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Platform</label>
                    <select value={editForm.platform}
                      onChange={(e) => setEditForm((f) => ({ ...f, platform: e.target.value as InfluencerPlatform }))}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                      {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Handle</label>
                    <input type="text" value={editForm.handle ?? ""}
                      onChange={(e) => setEditForm((f) => ({ ...f, handle: e.target.value }))}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Status</label>
                    <select value={editForm.status}
                      onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value as InfluencerStatus }))}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                      {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Followers</label>
                    <input type="number" value={editForm.followers_count ?? ""}
                      onChange={(e) => setEditForm((f) => ({ ...f, followers_count: parseInt(e.target.value) || undefined }))}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Engagement %</label>
                    <input type="number" step="0.01" value={editForm.engagement_rate ?? ""}
                      onChange={(e) => setEditForm((f) => ({ ...f, engagement_rate: e.target.value as unknown as string | null }))}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Notes</label>
                  <textarea value={editForm.notes ?? ""}
                    onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                    rows={3}
                    className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
                </div>
                <div className="flex justify-end gap-3">
                  <button onClick={() => setEditing(false)}
                    className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
                  <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                    className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-sm font-medium">
                    {updateMut.isPending ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Campaigns tab */}
        {tab === "campaigns" && (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Campaign Links</h2>
              <RequirePermission permission="influencers.create">
                <button onClick={() => setShowLinkForm((v) => !v)}
                  className="px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 text-sm">
                  {showLinkForm ? "Cancel" : "+ Link Campaign"}
                </button>
              </RequirePermission>
            </div>

            {showLinkForm && (
              <div className="mb-5 p-4 bg-[#0b1120] rounded-lg border border-slate-700/50 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Campaign ID *</label>
                    <input type="text" value={linkForm.campaign_id}
                      onChange={(e) => setLinkForm((f) => ({ ...f, campaign_id: e.target.value }))}
                      placeholder="UUID"
                      className="w-full bg-[#0d1527] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Content Type</label>
                    <select value={linkForm.content_type}
                      onChange={(e) => setLinkForm((f) => ({ ...f, content_type: e.target.value as ContentType }))}
                      className="w-full bg-[#0d1527] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                      {CONTENT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Agreed Fee (KES)</label>
                    <input type="number" step="0.01" value={linkForm.agreed_fee}
                      onChange={(e) => setLinkForm((f) => ({ ...f, agreed_fee: e.target.value }))}
                      className="w-full bg-[#0d1527] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Expected Posts</label>
                    <input type="number" min="0" value={linkForm.expected_posts}
                      onChange={(e) => setLinkForm((f) => ({ ...f, expected_posts: e.target.value }))}
                      className="w-full bg-[#0d1527] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Tracking Link</label>
                  <input type="text" value={linkForm.tracking_link}
                    onChange={(e) => setLinkForm((f) => ({ ...f, tracking_link: e.target.value }))}
                    placeholder="https://…"
                    className="w-full bg-[#0d1527] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                </div>
                <div className="flex justify-end">
                  <button onClick={() => createLinkMut.mutate()}
                    disabled={!linkForm.campaign_id || createLinkMut.isPending}
                    className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-sm font-medium">
                    {createLinkMut.isPending ? "Saving…" : "Add Link"}
                  </button>
                </div>
              </div>
            )}

            {links.length === 0 ? (
              <p className="text-slate-500 text-sm">No campaign links yet.</p>
            ) : (
              <div className="space-y-3">
                {links.map((l: InfluencerCampaignLink) => (
                  <div key={l.id} className="p-4 bg-[#0b1120] rounded-lg border border-slate-700/50">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="text-xs text-slate-500 font-mono">{l.campaign_id.slice(0, 8)}…</p>
                        <p className="text-sm font-medium mt-0.5">{l.content_type ?? "—"}</p>
                      </div>
                      {l.performance_score && (
                        <span className="px-2 py-0.5 rounded bg-emerald-600/20 text-emerald-400 text-xs font-medium">
                          Score: {Number(l.performance_score).toFixed(1)}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-4 gap-3 text-xs">
                      <div><p className="text-slate-500">Agreed Fee</p><p>{l.agreed_fee ? `KES ${Number(l.agreed_fee).toLocaleString()}` : "—"}</p></div>
                      <div><p className="text-slate-500">Posts</p><p>{l.actual_posts ?? "—"}/{l.expected_posts ?? "—"}</p></div>
                      <div><p className="text-slate-500">Impressions</p><p>{fmt(l.impressions)}</p></div>
                      <div><p className="text-slate-500">Conversions</p><p>{l.conversions ?? "—"}</p></div>
                    </div>
                    {l.attributed_revenue && (
                      <p className="text-xs text-emerald-400 mt-2">Revenue: KES {Number(l.attributed_revenue).toLocaleString()}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Attribution tab */}
        {tab === "attribution" && (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Attribution Records</h2>
              <div className="text-right">
                <p className="text-xs text-slate-400">Total Attributed Revenue</p>
                <p className="text-lg font-bold text-emerald-400">
                  KES {totalAttributedRevenue.toLocaleString()}
                </p>
              </div>
            </div>

            {attributions.length === 0 ? (
              <p className="text-slate-500 text-sm">No attribution records.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/50">
                      {["Date", "Clicks", "Conversions", "Orders", "Revenue", "Tracking Link"].map((h) => (
                        <th key={h} className="text-left px-3 py-2 text-xs text-slate-400">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {attributions.map((a: InfluencerAttribution) => (
                      <tr key={a.id} className="border-b border-slate-800">
                        <td className="px-3 py-2 text-slate-400">{a.attribution_date}</td>
                        <td className="px-3 py-2">{a.clicks.toLocaleString()}</td>
                        <td className="px-3 py-2 text-blue-400">{a.conversions}</td>
                        <td className="px-3 py-2">{a.attributed_orders}</td>
                        <td className="px-3 py-2 text-emerald-400">
                          {a.attributed_revenue ? `KES ${Number(a.attributed_revenue).toLocaleString()}` : "—"}
                        </td>
                        <td className="px-3 py-2 text-slate-500 text-xs truncate max-w-xs">
                          {a.tracking_link ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="mt-3 text-xs text-slate-500">
                  Total conversions: {totalConversions} ·
                  CPC avg: {totalConversions > 0 ? `KES ${(totalAttributedRevenue / totalConversions).toFixed(2)}` : "—"}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
