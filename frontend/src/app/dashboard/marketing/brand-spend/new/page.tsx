"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { marketingApi, BrandSpendCategory } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const CATEGORIES: BrandSpendCategory[] = [
  "TV", "RADIO", "DIGITAL_ADS", "INFLUENCER", "EVENT", "SAMPLING",
  "BRANDING_MATERIAL", "AGENCY_COST", "CREATIVE_PRODUCTION", "MEDIA_BUYING",
];

export default function NewBrandSpendPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    spend_category: "DIGITAL_ADS" as BrandSpendCategory,
    vendor: "",
    amount: "",
    currency: "KES",
    spend_date: new Date().toISOString().split("T")[0],
    campaign_id: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.brandSpend.create({
        spend_category: form.spend_category,
        vendor: form.vendor || null,
        amount: parseFloat(form.amount),
        currency: form.currency,
        spend_date: form.spend_date,
        campaign_id: form.campaign_id || null,
        notes: form.notes || null,
      }),
    onSuccess: () => router.push("/dashboard/marketing/brand-spend"),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <RequirePermission permission="brand_spend.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Back
          </button>
          <h1 className="text-2xl font-bold">New Brand Spend</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Category *</label>
              <select value={form.spend_category} onChange={(e) => set("spend_category", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Currency</label>
              <select value={form.currency} onChange={(e) => set("currency", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {["KES", "USD", "EUR", "GBP", "TRY"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Amount *</label>
              <input type="number" min="0" step="0.01" value={form.amount}
                onChange={(e) => set("amount", e.target.value)}
                placeholder="0.00"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Spend Date *</label>
              <input type="date" value={form.spend_date}
                onChange={(e) => set("spend_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Vendor / Supplier</label>
            <input type="text" value={form.vendor}
              onChange={(e) => set("vendor", e.target.value)}
              placeholder="Vendor or agency name"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Campaign ID <span className="text-slate-600">(optional)</span></label>
            <input type="text" value={form.campaign_id}
              onChange={(e) => set("campaign_id", e.target.value)}
              placeholder="UUID of linked campaign"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={3} placeholder="Additional details..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">
              Cancel
            </button>
            <button
              onClick={() => createMut.mutate()}
              disabled={!form.amount || !form.spend_date || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Create Brand Spend"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
