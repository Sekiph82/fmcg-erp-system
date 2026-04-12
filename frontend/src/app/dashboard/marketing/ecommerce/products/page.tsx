"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, ProductChannelPerformance } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function ProductChannelPage() {
  const router = useRouter();
  const [storeId, setStoreId] = useState("");

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["product-channel-perf", storeId],
    queryFn: () =>
      marketingApi.channelPerformance
        .list({ limit: 100, store_id: storeId || undefined })
        .then((r) => r.data),
  });

  const totalRevenue = records.reduce((s, p) => s + Number(p.revenue ?? 0), 0);
  const totalUnits = records.reduce((s, p) => s + p.units_sold, 0);

  return (
    <RequirePermission permission="ecommerce.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">Product Channel Performance</h1>
            <p className="text-slate-400 text-sm mt-1">{records.length} records</p>
          </div>
          <RequirePermission permission="channel_products.create">
            <button onClick={() => router.push("/dashboard/marketing/ecommerce/products/new")}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-medium">
              + Log Entry
            </button>
          </RequirePermission>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Revenue (KES)</p>
            <p className="text-xl font-bold text-emerald-400">KES {totalRevenue.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Units Sold</p>
            <p className="text-xl font-bold">{totalUnits.toLocaleString()}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6">
          <select value={storeId} onChange={(e) => setStoreId(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All stores</option>
            {stores.map((s) => <option key={s.id} value={s.id}>{s.store_name}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Date", "Units Sold", "Revenue (KES)", "Impressions", "Clicks", "Conv. Rate", "Return Rate", "Stock", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((p: ProductChannelPerformance) => (
                  <tr key={p.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-300">{p.perf_date}</td>
                    <td className="px-4 py-3 text-slate-300">{p.units_sold}</td>
                    <td className="px-4 py-3 font-medium text-emerald-400">
                      {p.revenue ? Number(p.revenue).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{p.impressions?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{p.clicks?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {p.conversion_rate ? `${Number(p.conversion_rate).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {p.return_rate ? `${Number(p.return_rate).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{p.stock_level ?? "—"}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => router.push(`/dashboard/marketing/ecommerce/products/${p.id}`)}
                        className="text-sky-400 hover:text-sky-300 text-xs">View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
