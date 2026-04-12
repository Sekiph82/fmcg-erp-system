"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import {
  marketingApi,
  CRMProfile,
  CustomerInteraction,
  CustomerVisit,
  RelationshipStatus,
  LoyaltyStatus,
  CRM_STATUS_COLORS,
} from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const STATUS_OPTIONS: RelationshipStatus[] = ["PROSPECT", "ACTIVE", "AT_RISK", "DORMANT", "CHURNED", "VIP"];
const LOYALTY_OPTIONS: LoyaltyStatus[] = ["NONE", "BRONZE", "SILVER", "GOLD", "PLATINUM"];

export default function CRMDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, unknown>>({});
  const [saveError, setSaveError] = useState("");
  const [addingInteraction, setAddingInteraction] = useState(false);
  const [interactionForm, setInteractionForm] = useState({
    interaction_date: new Date().toISOString().split("T")[0],
    channel: "",
    summary: "",
    outcome: "",
    follow_up_date: "",
  });

  const { data: profile, isLoading } = useQuery({
    queryKey: ["crm-profile", id],
    queryFn: () => marketingApi.crm.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: interactions = [] } = useQuery({
    queryKey: ["crm-interactions", id],
    queryFn: () => marketingApi.crm.interactions(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: visits = [] } = useQuery({
    queryKey: ["crm-visits", id],
    queryFn: () => marketingApi.visits.list({ limit: 50 }).then((r) => r.data.filter((v) => v.crm_profile_id === id)),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.crm.update(id, editForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-profile", id] });
      setEditing(false);
    },
    onError: (err: unknown) => {
      setSaveError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Save failed.");
    },
  });

  const addInteractionMut = useMutation({
    mutationFn: () =>
      marketingApi.crm.addInteraction(id, {
        crm_profile_id:   id,
        interaction_date: interactionForm.interaction_date,
        channel:          interactionForm.channel || undefined,
        summary:          interactionForm.summary || undefined,
        outcome:          interactionForm.outcome || undefined,
        follow_up_date:   interactionForm.follow_up_date || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-interactions", id] });
      setAddingInteraction(false);
      setInteractionForm({
        interaction_date: new Date().toISOString().split("T")[0],
        channel: "", summary: "", outcome: "", follow_up_date: "",
      });
    },
  });

  function startEdit() {
    if (!profile) return;
    setEditForm({
      relationship_status: profile.relationship_status,
      loyalty_status:      profile.loyalty_status,
      acquisition_source:  profile.acquisition_source ?? "",
      acquisition_channel: profile.acquisition_channel ?? "",
      next_followup_date:  profile.next_followup_date ?? "",
      engagement_score:    profile.engagement_score ?? "",
      estimated_ltv:       profile.estimated_ltv ?? "",
      churn_risk_score:    profile.churn_risk_score ?? "",
      notes:               profile.notes ?? "",
    });
    setEditing(true);
  }

  if (isLoading) return <div className="min-h-screen bg-[#0b1120] p-6 text-slate-400">Loading...</div>;
  if (!profile) return <div className="min-h-screen bg-[#0b1120] p-6 text-red-400">CRM Profile not found.</div>;

  return (
    <RequirePermission permission="crm.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <a href="/dashboard/marketing/crm" className="text-sm text-slate-400 hover:text-white mb-1 inline-block">
              ← CRM
            </a>
            <h1 className="text-2xl font-bold">CRM Profile</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className={`font-medium text-sm ${CRM_STATUS_COLORS[profile.relationship_status]}`}>
                {profile.relationship_status}
              </span>
              <span className="text-xs text-slate-400">{profile.loyalty_status}</span>
              <span className="text-xs font-mono text-slate-500">{profile.customer_id.slice(0, 8)}…</span>
            </div>
          </div>
          {!editing && (
            <button onClick={startEdit}
              className="mt-5 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
              Edit
            </button>
          )}
        </div>

        {/* Profile details */}
        {!editing && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5 mb-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><p className="text-xs text-slate-500 mb-0.5">Acquisition Source</p><p>{profile.acquisition_source ?? "—"}</p></div>
              <div><p className="text-xs text-slate-500 mb-0.5">Acquisition Channel</p><p>{profile.acquisition_channel ?? "—"}</p></div>
              <div><p className="text-xs text-slate-500 mb-0.5">Estimated LTV (KES)</p>
                <p className="font-medium">{profile.estimated_ltv ? Number(profile.estimated_ltv).toLocaleString() : "—"}</p>
              </div>
              <div><p className="text-xs text-slate-500 mb-0.5">Engagement Score</p>
                <p>{profile.engagement_score ? Number(profile.engagement_score).toFixed(1) : "—"}</p>
              </div>
              <div><p className="text-xs text-slate-500 mb-0.5">Churn Risk</p>
                <p className={Number(profile.churn_risk_score) > 0.6 ? "text-red-400" : "text-slate-300"}>
                  {profile.churn_risk_score ? `${(Number(profile.churn_risk_score) * 100).toFixed(0)}%` : "—"}
                </p>
              </div>
              <div><p className="text-xs text-slate-500 mb-0.5">Last Contact</p><p>{profile.last_contact_date ?? "—"}</p></div>
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Next Follow-up</p>
                <p className={profile.next_followup_date && new Date(profile.next_followup_date) < new Date() ? "text-red-400" : ""}>
                  {profile.next_followup_date ?? "—"}
                </p>
              </div>
            </div>
            {profile.notes && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <p className="text-xs text-slate-500 mb-0.5">Notes</p>
                <p className="text-sm text-slate-400">{profile.notes}</p>
              </div>
            )}
          </div>
        )}

        {/* Edit mode */}
        {editing && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-6 space-y-4 mb-6">
            {saveError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">{saveError}</div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Relationship Status</label>
                <select value={editForm.relationship_status as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, relationship_status: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Loyalty Status</label>
                <select value={editForm.loyalty_status as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, loyalty_status: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {LOYALTY_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Estimated LTV (KES)</label>
                <input type="number" value={editForm.estimated_ltv as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, estimated_ltv: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Engagement Score (0–10)</label>
                <input type="number" step="0.1" min="0" max="10" value={editForm.engagement_score as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, engagement_score: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Churn Risk (0–1)</label>
                <input type="number" step="0.01" min="0" max="1" value={editForm.churn_risk_score as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, churn_risk_score: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Next Follow-up Date</label>
                <input type="date" value={editForm.next_followup_date as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, next_followup_date: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea value={editForm.notes as string ?? ""}
                onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
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

        {/* Interaction History */}
        <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Interaction History</h2>
            <button onClick={() => setAddingInteraction(!addingInteraction)}
              className="px-3 py-1.5 rounded-lg bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 text-xs font-medium transition-colors">
              + Add Interaction
            </button>
          </div>

          {addingInteraction && (
            <div className="mb-4 p-4 rounded-lg bg-[#0b1120] border border-slate-700 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Date</label>
                  <input type="date" value={interactionForm.interaction_date}
                    onChange={(e) => setInteractionForm((f) => ({ ...f, interaction_date: e.target.value }))}
                    className="w-full bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Channel</label>
                  <input value={interactionForm.channel}
                    onChange={(e) => setInteractionForm((f) => ({ ...f, channel: e.target.value }))}
                    placeholder="e.g. Phone, Visit, Email"
                    className="w-full bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Summary</label>
                <textarea value={interactionForm.summary}
                  onChange={(e) => setInteractionForm((f) => ({ ...f, summary: e.target.value }))}
                  rows={2} placeholder="What was discussed?"
                  className="w-full bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Outcome</label>
                  <input value={interactionForm.outcome}
                    onChange={(e) => setInteractionForm((f) => ({ ...f, outcome: e.target.value }))}
                    placeholder="Result of interaction"
                    className="w-full bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Follow-up Date</label>
                  <input type="date" value={interactionForm.follow_up_date}
                    onChange={(e) => setInteractionForm((f) => ({ ...f, follow_up_date: e.target.value }))}
                    className="w-full bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => addInteractionMut.mutate()} disabled={addInteractionMut.isPending}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs font-medium disabled:opacity-50 transition-colors">
                  {addInteractionMut.isPending ? "Saving..." : "Save"}
                </button>
                <button onClick={() => setAddingInteraction(false)}
                  className="px-4 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs font-medium transition-colors">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {interactions.length === 0 ? (
            <p className="text-slate-400 text-sm">No interactions recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {(interactions as CustomerInteraction[]).map((i) => (
                <div key={i.id} className="border-b border-slate-700/50 pb-3 last:border-0">
                  <div className="flex items-center gap-2 mb-1">
                    {i.channel && (
                      <span className="text-xs px-2 py-0.5 rounded bg-blue-600/20 text-blue-400">{i.channel}</span>
                    )}
                    <span className="text-xs text-slate-500">{i.interaction_date}</span>
                    {i.follow_up_date && (
                      <span className="text-xs text-orange-400">Follow-up: {i.follow_up_date}</span>
                    )}
                  </div>
                  {i.summary && <p className="text-sm text-slate-300">{i.summary}</p>}
                  {i.outcome && <p className="text-xs text-slate-400 mt-0.5">Outcome: {i.outcome}</p>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Linked Visits */}
        {(visits as CustomerVisit[]).length > 0 && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
            <h2 className="font-semibold mb-4">Field Visits</h2>
            <div className="space-y-2">
              {(visits as CustomerVisit[]).map((v) => (
                <div key={v.id} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                  <div>
                    <span className="text-xs px-2 py-0.5 rounded bg-purple-600/20 text-purple-300 mr-2">
                      {v.visit_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm text-slate-300">{v.visit_date}</span>
                    {v.outcome && <p className="text-xs text-slate-400 mt-0.5">{v.outcome}</p>}
                  </div>
                  <a href={`/dashboard/marketing/visits/${v.id}`}
                    className="text-xs text-blue-400 hover:underline">
                    View
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
