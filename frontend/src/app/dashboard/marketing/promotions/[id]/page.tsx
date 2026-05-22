"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { marketingApi, MktPromotion, PromotionType, DiscountType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PROMOTION_TYPES: PromotionType[] = [
  "DISCOUNT", "BUNDLE", "FREE_ITEM", "REBATE", "BUY_X_GET_Y",
  "RETAILER_SUPPORT", "DISTRIBUTOR_SUPPORT", "CASHBACK",
];

const STATUS_COLORS: Record<string, string> = {
  DRAFT:   "text-slate-400",
  ACTIVE:  "text-emerald-400",
  EXPIRED: "text-red-400",
  PAUSED:  "text-yellow-400",
};

export default function PromotionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<MktPromotion>>({});
  const [saveError, setSaveError] = useState("");

  const { data: promotion, isLoading } = useQuery({
    queryKey: ["promotion", id],
    queryFn: () => marketingApi.promotions.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: campaigns = [] } = useQuery({
    queryKey: ["campaigns-all"],
    queryFn: () => marketingApi.campaigns.list({ limit: 200 }).then((r) => r.data),
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.promotions.update(id, editForm as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["promotion", id] });
      setEditing(false);
    },
    onError: (err: unknown) => {
      setSaveError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Save failed.");
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.promotions.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/promotions"),
  });

  function startEdit() {
    if (!promotion) return;
    setEditForm({
      promotion_name:   promotion.promotion_name,
      promotion_code:   promotion.promotion_code ?? "",
      promotion_type:   promotion.promotion_type,
      campaign_id:      promotion.campaign_id ?? "",
      region:           promotion.region ?? "",
      start_date:       promotion.start_date,
      end_date:         promotion.end_date,
      status:           promotion.status,
      discount_type:    promotion.discount_type,
      discount_value:   promotion.discount_value,
      minimum_quantity: promotion.minimum_quantity,
      notes:            promotion.notes ?? "",
    });
    setEditing(true);
  }

  const linkedCampaign = promotion?.campaign_id
    ? campaigns.find((c) => c.id === promotion.campaign_id)
    : null;

  if (isLoading) return <div className="min-h-screen bg-[#0b1120] p-6 text-slate-400">Loading...</div>;
  if (!promotion) return <div className="min-h-screen bg-[#0b1120] p-6 text-red-400">Promotion not found.</div>;

  return (
    <RequirePermission permission="promotions.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <a href="/dashboard/marketing/promotions" className="text-sm text-slate-400 hover:text-white mb-1 inline-block">
              ← Promotions
            </a>
            <h1 className="text-2xl font-bold">{promotion.promotion_name}</h1>
            <div className="flex items-center gap-3 mt-1">
              {promotion.promotion_code && (
                <span className="text-slate-400 font-mono text-xs">{promotion.promotion_code}</span>
              )}
              <span className={`font-medium text-sm ${STATUS_COLORS[promotion.status] ?? "text-white"}`}>
                {promotion.status}
              </span>
              <span className="text-xs text-slate-400">{promotion.promotion_type.replace(/_/g, " ")}</span>
            </div>
          </div>
          {!editing && (
            <div className="flex gap-2 mt-5">
              <button onClick={startEdit}
                className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
                Edit
              </button>
              <button onClick={() => { if (confirm("Delete this promotion?")) deleteMut.mutate(); }}
                className="px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40 text-sm font-medium transition-colors">
                Delete
              </button>
            </div>
          )}
        </div>

        {/* View mode */}
        {!editing && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5 space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><p className="text-xs text-slate-500 mb-0.5">Region</p><p>{promotion.region ?? "—"}</p></div>
              <div><p className="text-xs text-slate-500 mb-0.5">Dates</p><p>{promotion.start_date} → {promotion.end_date}</p></div>
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Discount</p>
                <p>{promotion.discount_type && promotion.discount_value
                  ? `${Number(promotion.discount_value).toFixed(2)}${promotion.discount_type === "PERCENTAGE" ? "%" : " KES"}`
                  : "—"}</p>
              </div>
              <div><p className="text-xs text-slate-500 mb-0.5">Min. Quantity</p><p>{promotion.minimum_quantity ?? "—"}</p></div>
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Linked Campaign</p>
                {linkedCampaign ? (
                  <a href={`/dashboard/marketing/campaigns/${linkedCampaign.id}`}
                    className="text-blue-400 hover:underline text-sm">{linkedCampaign.campaign_name}</a>
                ) : <p>—</p>}
              </div>
            </div>
            {promotion.notes && (
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Notes</p>
                <p className="text-sm text-slate-400">{promotion.notes}</p>
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
                <label className="block text-xs text-slate-400 mb-1">Promotion Name</label>
                <input value={editForm.promotion_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, promotion_name: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Type</label>
                <select value={editForm.promotion_type ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, promotion_type: e.target.value as PromotionType }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {PROMOTION_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Status</label>
                <select value={editForm.status ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  {["DRAFT", "ACTIVE", "PAUSED", "EXPIRED"].map((s) => <option key={s} value={s}>{s}</option>)}
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
                <label className="block text-xs text-slate-400 mb-1">Discount Type</label>
                <select value={editForm.discount_type ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, discount_type: e.target.value as DiscountType }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  <option value="">None</option>
                  <option value="PERCENTAGE">Percentage (%)</option>
                  <option value="FIXED">Fixed Amount</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Discount Value</label>
                <input type="number" value={editForm.discount_value ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, discount_value: e.target.value as unknown as string }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Campaign</label>
              <select value={editForm.campaign_id ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, campaign_id: e.target.value }))}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                <option value="">No campaign</option>
                {campaigns.map((c) => <option key={c.id} value={c.id}>{c.campaign_name}</option>)}
              </select>
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
