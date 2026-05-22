"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, AdPerformance, AdPlatform } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const AD_PLATFORMS: AdPlatform[] = ["META", "GOOGLE", "TIKTOK", "TWITTER", "LINKEDIN", "YOUTUBE", "OTHER"];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

export default function AdDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<AdPerformance>>({});
  const [error, setError] = useState("");

  const { data: ad, isLoading } = useQuery({
    queryKey: ["ad", id],
    queryFn: () => marketingApi.ads.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.ads.update(id, form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ad", id] });
      qc.invalidateQueries({ queryKey: ["ads"] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.ads.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/ads"),
  });

  const startEdit = () => {
    if (!ad) return;
    setForm({ ...ad });
    setEditing(true);
  };

  const set = (k: keyof AdPerformance, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!ad) return <div className="p-8 text-red-400">Ad record not found.</div>;

  const roas = ad.spend && ad.revenue_generated && Number(ad.spend) > 0
    ? (Number(ad.revenue_generated) / Number(ad.spend)).toFixed(2)
    : null;

  return (
    <RequirePermission permission="ad_performance.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Ads Performance
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{ad.ad_name ?? ad.platform}</h1>
              <p className="text-slate-400 text-sm mt-1">{ad.platform} · {ad.ad_date}</p>
            </div>
            {roas && (
              <div className="text-right">
                <p className="text-xs text-slate-400">ROAS</p>
                <p className={`text-xl font-bold ${Number(roas) >= 3 ? "text-emerald-400" : Number(roas) >= 1 ? "text-yellow-400" : "text-red-400"}`}>
                  {roas}x
                </p>
              </div>
            )}
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Spend</p>
            <p className="text-base font-bold text-red-400">{ad.spend ? `KES ${Number(ad.spend).toLocaleString()}` : "—"}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Revenue</p>
            <p className="text-base font-bold text-emerald-400">{ad.revenue_generated ? `KES ${Number(ad.revenue_generated).toLocaleString()}` : "—"}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Impressions</p>
            <p className="text-base font-bold">{ad.impressions?.toLocaleString() ?? "—"}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Clicks</p>
            <p className="text-base font-bold">{ad.clicks?.toLocaleString() ?? "—"}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-3">
            <p className="text-xs text-slate-400 mb-0.5">Conversions</p>
            <p className="text-base font-bold">{ad.conversions?.toLocaleString() ?? "—"}</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        {!editing ? (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="grid grid-cols-2 gap-x-8 gap-y-5 mb-6">
              <Field label="Platform" value={ad.platform} />
              <Field label="Ad Date" value={ad.ad_date} />
              <Field label="Ad Name" value={ad.ad_name} />
              <Field label="Campaign ID" value={ad.campaign_id} />
              <Field label="CTR" value={ad.ctr ? `${Number(ad.ctr).toFixed(2)}%` : null} />
              <Field label="CPC (KES)" value={ad.cpc ? Number(ad.cpc).toLocaleString() : null} />
              <Field label="Cost / Conversion" value={ad.cost_per_conversion ? `KES ${Number(ad.cost_per_conversion).toLocaleString()}` : null} />
              <Field label="Created" value={ad.created_at ? new Date(ad.created_at).toLocaleDateString() : null} />
            </div>
            {ad.notes && (
              <div className="border-t border-slate-700/50 pt-4">
                <p className="text-xs text-slate-400 mb-1">Notes</p>
                <p className="text-sm text-slate-300">{ad.notes}</p>
              </div>
            )}
            <div className="border-t border-slate-700/50 pt-4 mt-4 flex justify-end gap-2">
              <RequirePermission permission="ad_performance.edit">
                <button onClick={startEdit}
                  className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">Edit</button>
                <button onClick={() => { if (confirm("Delete this ad record?")) deleteMut.mutate(); }}
                  className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">Delete</button>
              </RequirePermission>
            </div>
          </div>
        ) : (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Platform</label>
                <select value={String(form.platform ?? ad.platform)}
                  onChange={(e) => set("platform", e.target.value as AdPlatform)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {AD_PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Ad Date</label>
                <input type="date" value={String(form.ad_date ?? ad.ad_date)}
                  onChange={(e) => set("ad_date", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Ad Name</label>
              <input type="text" value={String(form.ad_name ?? "")}
                onChange={(e) => set("ad_name", e.target.value || null)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Impressions</label>
                <input type="number" value={String(form.impressions ?? "")}
                  onChange={(e) => set("impressions", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Clicks</label>
                <input type="number" value={String(form.clicks ?? "")}
                  onChange={(e) => set("clicks", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Spend (KES)</label>
                <input type="number" step="0.01" value={String(form.spend ?? "")}
                  onChange={(e) => set("spend", e.target.value || null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Conversions</label>
                <input type="number" value={String(form.conversions ?? "")}
                  onChange={(e) => set("conversions", e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Revenue Generated (KES)</label>
                <input type="number" step="0.01" value={String(form.revenue_generated ?? "")}
                  onChange={(e) => set("revenue_generated", e.target.value || null)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">CTR %</label>
                <input type="number" step="0.01" value={String(form.ctr ?? "")}
                  onChange={(e) => set("ctr", e.target.value || null)}
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
                className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium">
                {updateMut.isPending ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
