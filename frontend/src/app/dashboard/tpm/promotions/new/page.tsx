"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { tpmApi, TPMPromotionType, TPMObjectiveType } from "@/lib/tpm";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function NewTPMPromotionPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    promotion_code: "",
    promotion_name: "",
    promotion_type: "DISCOUNT" as TPMPromotionType,
    objective_type: "VOLUME" as TPMObjectiveType,
    valid_from: "",
    valid_to: "",
    brand_id: "",
    category_id: "",
    channel_id: "",
    region_id: "",
    distributor_group_id: "",
    notes: "",
  });

  const create = useMutation({
    mutationFn: () => tpmApi.createPromotion({
      ...form,
      brand_id: form.brand_id || undefined,
      category_id: form.category_id || undefined,
      channel_id: form.channel_id || undefined,
      region_id: form.region_id || undefined,
      distributor_group_id: form.distributor_group_id || undefined,
    }),
    onSuccess: (p) => router.push(`/dashboard/tpm/promotions/${p.id}`),
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      <div>
        <Link href="/dashboard/tpm/promotions" className="text-xs text-gray-500 hover:text-indigo-400">← Back to Promotions</Link>
        <h1 className="text-2xl font-bold text-gray-900 mt-1">New Trade Promotion</h1>
        <p className="text-sm text-gray-500">Define the promotion event, objective, and targeting scope.</p>
      </div>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Promotion Identity</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Promotion Code *</label>
            <input type="text" value={form.promotion_code} onChange={(e) => set("promotion_code", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="PROMO-001" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Promotion Type *</label>
            <select value={form.promotion_type} onChange={(e) => set("promotion_type", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {(["DISCOUNT","FREE_GOODS","VISIBILITY","DISPLAY","REBATE","OFF_INVOICE","BILL_BACK","LISTING_FEE","BUNDLE","EVENT","CUSTOM"] as TPMPromotionType[]).map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-gray-500">Promotion Name *</label>
            <input type="text" value={form.promotion_name} onChange={(e) => set("promotion_name", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. Ramadan Visibility Drive 2026" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Objective *</label>
            <select value={form.objective_type} onChange={(e) => set("objective_type", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {(["VOLUME","MARKET_SHARE","DISTRIBUTION_GAIN","STOCK_CLEARANCE","LAUNCH_SUPPORT","RETENTION","SEASONAL_PUSH","CHANNEL_ACTIVATION"] as TPMObjectiveType[]).map((o) => (
                <option key={o} value={o}>{o.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Valid From *</label>
            <input type="date" value={form.valid_from} onChange={(e) => set("valid_from", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Valid To *</label>
            <input type="date" value={form.valid_to} onChange={(e) => set("valid_to", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
        </div>
      </div>

      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Targeting Scope</h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: "Brand",              key: "brand_id",             placeholder: "e.g. CleanPower" },
            { label: "Category",           key: "category_id",          placeholder: "e.g. Detergents" },
            { label: "Channel",            key: "channel_id",           placeholder: "e.g. modern-trade" },
            { label: "Region",             key: "region_id",            placeholder: "e.g. Nairobi" },
            { label: "Distributor Group",  key: "distributor_group_id", placeholder: "e.g. Tier1-Central" },
          ].map(({ label, key, placeholder }) => (
            <div key={key} className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">{label}</label>
              <input type="text" value={(form as any)[key]} onChange={(e) => set(key, e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder={placeholder} />
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Notes</label>
          <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
            rows={3} className="rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none" />
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <Link href="/dashboard/tpm/promotions" className="glow-button-secondary text-sm">Cancel</Link>
        <button onClick={() => create.mutate()} disabled={create.isPending || !form.promotion_code || !form.promotion_name}
          className="glow-button">
          {create.isPending ? "Creating…" : "Create Promotion"}
        </button>
      </div>
      {create.isError && <p className="text-sm text-red-400">Failed to create. Check required fields.</p>}
    </div>
  );
}
