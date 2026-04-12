"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { marketingApi, Campaign, CampaignStatus, CampaignType, CAMPAIGN_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const CAMPAIGN_TYPES: CampaignType[] = [
  "TRADE", "DIGITAL", "RETAIL", "DISTRIBUTOR", "LAUNCH",
  "SEASONAL", "LOYALTY", "AWARENESS", "ACQUISITION", "RETENTION",
];
const CAMPAIGN_STATUSES: CampaignStatus[] = [
  "DRAFT", "PLANNED", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED",
];

const APPROVAL_BADGES: Record<string, string> = {
  PENDING:  "bg-yellow-500/10 text-yellow-400",
  APPROVED: "bg-emerald-500/10 text-emerald-400",
  REJECTED: "bg-red-500/10 text-red-400",
};

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<Campaign>>({});
  const [saveError, setSaveError] = useState("");

  const { data: campaign, isLoading } = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => marketingApi.campaigns.get(id).then((r) => r.data),
    enabled: !!id,
  });

  // Load promotions linked to this campaign
  const { data: promotions = [] } = useQuery({
    queryKey: ["promotions", id],
    queryFn: () => marketingApi.promotions.list({ campaign_id: id, limit: 50 }).then((r) => r.data),
    enabled: !!id,
  });

  const approveMut = useMutation({
    mutationFn: () => marketingApi.campaigns.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaign", id] }),
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.campaigns.update(id, editForm as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaign", id] });
      setEditing(false);
    },
    onError: (err: unknown) => {
      setSaveError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Save failed.");
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.campaigns.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/campaigns"),
  });

  function startEdit() {
    if (!campaign) return;
    setEditForm({
      campaign_name:    campaign.campaign_name,
      campaign_type:    campaign.campaign_type,
      objective:        campaign.objective ?? "",
      region:           campaign.region ?? "",
      country:          campaign.country ?? "",
      start_date:       campaign.start_date,
      end_date:         campaign.end_date,
      status:           campaign.status,
      budget:           campaign.budget,
      expected_revenue: campaign.expected_revenue,
      actual_revenue:   campaign.actual_revenue,
      actual_roi:       campaign.actual_roi,
      notes:            campaign.notes ?? "",
    });
    setEditing(true);
  }

  if (isLoading) return <div className="min-h-screen bg-[#0b1120] p-6 text-slate-400">Loading...</div>;
  if (!campaign) return <div className="min-h-screen bg-[#0b1120] p-6 text-red-400">Campaign not found.</div>;

  return (
    <RequirePermission permission="campaigns.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <a href="/dashboard/marketing/campaigns" className="text-sm text-slate-400 hover:text-white mb-1 inline-block">
              ← Campaigns
            </a>
            <h1 className="text-2xl font-bold">{campaign.campaign_name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-slate-400 font-mono text-xs">{campaign.campaign_code}</span>
              <span className={`font-medium text-sm ${CAMPAIGN_STATUS_COLORS[campaign.status as CampaignStatus]}`}>
                {campaign.status}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${APPROVAL_BADGES[campaign.approval_status] ?? ""}`}>
                {campaign.approval_status}
              </span>
            </div>
          </div>
          <div className="flex gap-2 mt-5">
            {!editing && (
              <>
                <button onClick={startEdit}
                  className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
                  Edit
                </button>
                {campaign.approval_status === "PENDING" && (
                  <button onClick={() => approveMut.mutate()}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-sm font-medium transition-colors">
                    Approve
                  </button>
                )}
                <button
                  onClick={() => { if (confirm("Delete this campaign?")) deleteMut.mutate(); }}
                  className="px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40 text-sm font-medium transition-colors">
                  Delete
                </button>
              </>
            )}
          </div>
        </div>

        {/* View mode */}
        {!editing && (
          <div className="space-y-6">
            {/* Core Info */}
            <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Campaign Details</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><p className="text-xs text-slate-500 mb-0.5">Type</p><p>{campaign.campaign_type}</p></div>
                <div><p className="text-xs text-slate-500 mb-0.5">Region</p><p>{campaign.region ?? "—"}</p></div>
                <div><p className="text-xs text-slate-500 mb-0.5">Country</p><p>{campaign.country ?? "—"}</p></div>
                <div><p className="text-xs text-slate-500 mb-0.5">Dates</p><p>{campaign.start_date} → {campaign.end_date}</p></div>
              </div>
              {campaign.objective && (
                <div className="mt-4">
                  <p className="text-xs text-slate-500 mb-0.5">Objective</p>
                  <p className="text-sm text-slate-300">{campaign.objective}</p>
                </div>
              )}
              {campaign.notes && (
                <div className="mt-4">
                  <p className="text-xs text-slate-500 mb-0.5">Notes</p>
                  <p className="text-sm text-slate-400">{campaign.notes}</p>
                </div>
              )}
            </div>

            {/* Financials */}
            <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Financials</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-sm">
                  <p className="text-xs text-slate-500 mb-0.5">Budget</p>
                  <p className="font-semibold">{campaign.budget ? `KES ${Number(campaign.budget).toLocaleString()}` : "—"}</p>
                </div>
                <div className="text-sm">
                  <p className="text-xs text-slate-500 mb-0.5">Expected Revenue</p>
                  <p className="font-semibold">{campaign.expected_revenue ? `KES ${Number(campaign.expected_revenue).toLocaleString()}` : "—"}</p>
                </div>
                <div className="text-sm">
                  <p className="text-xs text-slate-500 mb-0.5">Actual Revenue</p>
                  <p className={`font-semibold ${campaign.actual_revenue ? "text-emerald-400" : ""}`}>
                    {campaign.actual_revenue ? `KES ${Number(campaign.actual_revenue).toLocaleString()}` : "—"}
                  </p>
                </div>
                <div className="text-sm">
                  <p className="text-xs text-slate-500 mb-0.5">Actual ROI</p>
                  <p className={`font-semibold ${campaign.actual_roi && Number(campaign.actual_roi) >= 1 ? "text-emerald-400" : "text-orange-400"}`}>
                    {campaign.actual_roi ? `${Number(campaign.actual_roi).toFixed(2)}x` : "—"}
                  </p>
                </div>
              </div>
            </div>

            {/* Linked Promotions */}
            {promotions.length > 0 && (
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                  Linked Promotions ({promotions.length})
                </h2>
                <div className="space-y-2">
                  {promotions.map((p) => (
                    <div key={p.id} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                      <div>
                        <p className="text-sm font-medium">{p.promotion_name}</p>
                        <p className="text-xs text-slate-400">{p.promotion_type} · {p.region ?? "No region"}</p>
                      </div>
                      <span className={`text-xs font-medium ${p.status === "ACTIVE" ? "text-emerald-400" : "text-slate-400"}`}>
                        {p.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Edit mode */}
        {editing && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-6 space-y-4">
            {saveError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">{saveError}</div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Campaign Name</label>
                <input value={editForm.campaign_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, campaign_name: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Type</label>
                <select value={editForm.campaign_type ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, campaign_type: e.target.value as CampaignType }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {CAMPAIGN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Status</label>
                <select value={editForm.status ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value as CampaignStatus }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {CAMPAIGN_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Region</label>
                <input value={editForm.region ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, region: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Start Date</label>
                <input type="date" value={editForm.start_date ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, start_date: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">End Date</label>
                <input type="date" value={editForm.end_date ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, end_date: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Actual Revenue (KES)</label>
                <input type="number" value={editForm.actual_revenue ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, actual_revenue: e.target.value as unknown as string }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Actual ROI (multiplier)</label>
                <input type="number" step="0.01" value={editForm.actual_roi ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, actual_roi: e.target.value as unknown as string }))}
                  placeholder="e.g. 2.5"
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Objective</label>
              <textarea value={editForm.objective ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, objective: e.target.value }))}
                rows={2} className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea value={editForm.notes ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                rows={2} className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>

            <div className="flex gap-3 pt-2">
              <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors">
                {updateMut.isPending ? "Saving..." : "Save Changes"}
              </button>
              <button onClick={() => setEditing(false)}
                className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
