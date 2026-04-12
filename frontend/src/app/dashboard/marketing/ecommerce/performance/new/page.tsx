"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { marketingApi } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function NewStorePerformancePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefilledStoreId = searchParams.get("store_id") ?? "";

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const [form, setForm] = useState({
    store_id: prefilledStoreId,
    perf_date: new Date().toISOString().slice(0, 10),
    total_orders: "",
    total_units_sold: "",
    total_revenue: "",
    gross_margin: "",
    ad_spend: "",
    impressions: "",
    clicks: "",
    conversions: "",
    returns_count: "0",
    net_revenue: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.storePerformance.create({
        store_id: form.store_id,
        perf_date: form.perf_date,
        total_orders: parseInt(form.total_orders) || 0,
        total_units_sold: parseInt(form.total_units_sold) || 0,
        total_revenue: form.total_revenue || null,
        gross_margin: form.gross_margin || null,
        ad_spend: form.ad_spend || null,
        impressions: form.impressions ? parseInt(form.impressions) : null,
        clicks: form.clicks ? parseInt(form.clicks) : null,
        conversions: form.conversions ? parseInt(form.conversions) : null,
        returns_count: parseInt(form.returns_count) || 0,
        net_revenue: form.net_revenue || null,
        notes: form.notes || null,
      }),
    onSuccess: (r) => {
      if (prefilledStoreId) {
        router.push(`/dashboard/marketing/ecommerce/stores/${prefilledStoreId}`);
      } else {
        router.push(`/dashboard/marketing/ecommerce/performance/${r.data.id}`);
      }
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const canSubmit = form.store_id && form.perf_date;

  return (
    <RequirePermission permission="store_performance.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">← Back</button>
          <h1 className="text-2xl font-bold">Log Store Performance</h1>
          <p className="text-slate-400 text-sm mt-1">Record daily metrics for a store / channel</p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          {/* Store + Date */}
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

          {/* Orders + Units */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Total Orders</label>
              <input type="number" min="0" value={form.total_orders} onChange={(e) => set("total_orders", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Units Sold</label>
              <input type="number" min="0" value={form.total_units_sold} onChange={(e) => set("total_units_sold", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          {/* Revenue */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Total Revenue (KES)</label>
              <input type="number" step="0.01" value={form.total_revenue} onChange={(e) => set("total_revenue", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Gross Margin (KES)</label>
              <input type="number" step="0.01" value={form.gross_margin} onChange={(e) => set("gross_margin", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Net Revenue (KES)</label>
              <input type="number" step="0.01" value={form.net_revenue} onChange={(e) => set("net_revenue", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Ad Spend (KES)</label>
              <input type="number" step="0.01" value={form.ad_spend} onChange={(e) => set("ad_spend", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          {/* Digital metrics */}
          <p className="text-xs text-slate-500 uppercase tracking-wider pt-1">Digital Metrics</p>
          <div className="grid grid-cols-3 gap-3">
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
            <div>
              <label className="block text-xs text-slate-400 mb-1">Conversions</label>
              <input type="number" min="0" value={form.conversions} onChange={(e) => set("conversions", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Returns Count</label>
            <input type="number" min="0" value={form.returns_count} onChange={(e) => set("returns_count", e.target.value)}
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={2} placeholder="Promotions active, anomalies, context…"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
            <button onClick={() => createMut.mutate()}
              disabled={!canSubmit || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Log Performance"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
