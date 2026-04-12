"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { marketingApi, PromotionType, DiscountType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PROMOTION_TYPES: PromotionType[] = [
  "DISCOUNT", "BUNDLE", "FREE_ITEM", "REBATE", "BUY_X_GET_Y",
  "RETAILER_SUPPORT", "DISTRIBUTOR_SUPPORT", "CASHBACK",
];

export default function NewPromotionPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: campaigns = [] } = useQuery({
    queryKey: ["campaigns-all"],
    queryFn: () => marketingApi.campaigns.list({ limit: 200 }).then((r) => r.data),
  });

  const [form, setForm] = useState({
    promotion_name:   "",
    promotion_code:   "",
    promotion_type:   "DISCOUNT" as PromotionType,
    campaign_id:      "",
    region:           "",
    start_date:       "",
    end_date:         "",
    discount_type:    "" as DiscountType | "",
    discount_value:   "",
    minimum_quantity: "",
    notes:            "",
  });

  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      marketingApi.promotions.create({
        promotion_name:   form.promotion_name,
        promotion_code:   form.promotion_code || undefined,
        promotion_type:   form.promotion_type,
        campaign_id:      form.campaign_id || undefined,
        region:           form.region || undefined,
        start_date:       form.start_date,
        end_date:         form.end_date,
        discount_type:    (form.discount_type as DiscountType) || undefined,
        discount_value:   form.discount_value ? Number(form.discount_value) : undefined,
        minimum_quantity: form.minimum_quantity ? Number(form.minimum_quantity) : undefined,
        notes:            form.notes || undefined,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["promotions"] });
      router.push(`/dashboard/marketing/promotions/${res.data.id}`);
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create promotion.");
    },
  });

  function set(key: string, val: string) {
    setForm((f) => ({ ...f, [key]: val }));
    setError("");
  }

  return (
    <RequirePermission permission="promotions.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl">
        <div className="mb-6">
          <a href="/dashboard/marketing/promotions" className="text-sm text-slate-400 hover:text-white mb-2 inline-block">
            ← Back to Promotions
          </a>
          <h1 className="text-2xl font-bold">New Promotion</h1>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">{error}</div>
        )}

        <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-6 space-y-5">
          {/* Name & Code */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Promotion Name *</label>
              <input value={form.promotion_name} onChange={(e) => set("promotion_name", e.target.value)}
                placeholder="e.g. Buy 2 Get 1 Free"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Promotion Code</label>
              <input value={form.promotion_code} onChange={(e) => set("promotion_code", e.target.value)}
                placeholder="e.g. PROMO-2026-01"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          {/* Type & Campaign */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Promotion Type *</label>
              <select value={form.promotion_type} onChange={(e) => set("promotion_type", e.target.value as PromotionType)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {PROMOTION_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Link to Campaign</label>
              <select value={form.campaign_id} onChange={(e) => set("campaign_id", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                <option value="">No campaign</option>
                {campaigns.map((c) => <option key={c.id} value={c.id}>{c.campaign_name}</option>)}
              </select>
            </div>
          </div>

          {/* Region */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Region</label>
            <input value={form.region} onChange={(e) => set("region", e.target.value)}
              placeholder="e.g. Nairobi, Western Kenya"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
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

          {/* Discount */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Discount Type</label>
              <select value={form.discount_type} onChange={(e) => set("discount_type", e.target.value as DiscountType)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                <option value="">None</option>
                <option value="PERCENTAGE">Percentage (%)</option>
                <option value="FIXED">Fixed Amount</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Discount Value</label>
              <input type="number" value={form.discount_value} onChange={(e) => set("discount_value", e.target.value)}
                placeholder="e.g. 10 or 500"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Min. Quantity</label>
              <input type="number" value={form.minimum_quantity} onChange={(e) => set("minimum_quantity", e.target.value)}
                placeholder="e.g. 2"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={2} placeholder="Internal notes..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => mut.mutate()}
              disabled={mut.isPending || !form.promotion_name || !form.start_date || !form.end_date}
              className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {mut.isPending ? "Creating..." : "Create Promotion"}
            </button>
            <a href="/dashboard/marketing/promotions"
              className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
              Cancel
            </a>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
