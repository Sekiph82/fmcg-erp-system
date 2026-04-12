"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { marketingApi } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function NewProductChannelPerfPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefilledStoreId = searchParams.get("store_id") ?? "";

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const [form, setForm] = useState({
    product_id: "",
    store_id: prefilledStoreId,
    perf_date: new Date().toISOString().slice(0, 10),
    units_sold: "",
    revenue: "",
    impressions: "",
    clicks: "",
    conversion_rate: "",
    return_rate: "",
    ranking: "",
    stock_level: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.channelPerformance.create({
        product_id: form.product_id,
        store_id: form.store_id,
        perf_date: form.perf_date,
        units_sold: parseInt(form.units_sold) || 0,
        revenue: form.revenue || null,
        impressions: form.impressions ? parseInt(form.impressions) : null,
        clicks: form.clicks ? parseInt(form.clicks) : null,
        conversion_rate: form.conversion_rate || null,
        return_rate: form.return_rate || null,
        ranking: form.ranking ? parseInt(form.ranking) : null,
        stock_level: form.stock_level ? parseInt(form.stock_level) : null,
      }),
    onSuccess: (r) => router.push(`/dashboard/marketing/ecommerce/products/${r.data.id}`),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const canSubmit = form.product_id && form.store_id && form.perf_date;

  return (
    <RequirePermission permission="channel_products.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">← Back</button>
          <h1 className="text-2xl font-bold">Log Product Channel Performance</h1>
          <p className="text-slate-400 text-sm mt-1">Record SKU-level daily metrics for a channel</p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          {/* Product ID + Store + Date */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Product ID *</label>
            <input type="text" value={form.product_id} onChange={(e) => set("product_id", e.target.value)}
              placeholder="UUID of the product"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Store *</label>
              <select value={form.store_id} onChange={(e) => set("store_id", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                <option value="">Select store</option>
                {stores.map((s) => <option key={s.id} value={s.id}>{s.store_name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Date *</label>
              <input type="date" value={form.perf_date} onChange={(e) => set("perf_date", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          {/* Sales metrics */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Units Sold</label>
              <input type="number" min="0" value={form.units_sold} onChange={(e) => set("units_sold", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Revenue (KES)</label>
              <input type="number" step="0.01" value={form.revenue} onChange={(e) => set("revenue", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          {/* Digital metrics */}
          <p className="text-xs text-slate-500 uppercase tracking-wider pt-1">Digital Metrics</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Impressions</label>
              <input type="number" min="0" value={form.impressions} onChange={(e) => set("impressions", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Clicks</label>
              <input type="number" min="0" value={form.clicks} onChange={(e) => set("clicks", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Conversion Rate (%)</label>
              <input type="number" step="0.01" min="0" max="100" value={form.conversion_rate}
                onChange={(e) => set("conversion_rate", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Return Rate (%)</label>
              <input type="number" step="0.01" min="0" max="100" value={form.return_rate}
                onChange={(e) => set("return_rate", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Search Ranking</label>
              <input type="number" min="1" value={form.ranking} onChange={(e) => set("ranking", e.target.value)}
                placeholder="1 = top"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Stock Level</label>
              <input type="number" min="0" value={form.stock_level} onChange={(e) => set("stock_level", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
            <button onClick={() => createMut.mutate()}
              disabled={!canSubmit || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Log Performance"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
