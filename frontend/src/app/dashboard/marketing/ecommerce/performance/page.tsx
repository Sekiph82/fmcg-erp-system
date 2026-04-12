"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, StorePerformance } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function StorePerformancePage() {
  const router = useRouter();
  const [storeId, setStoreId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["store-performance", storeId, dateFrom, dateTo],
    queryFn: () =>
      marketingApi.storePerformance
        .list({ limit: 100, store_id: storeId || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined })
        .then((r) => r.data),
  });

  const totalRevenue = records.reduce((s, p) => s + Number(p.total_revenue ?? 0), 0);
  const totalOrders = records.reduce((s, p) => s + p.total_orders, 0);

  return (
    <RequirePermission permission="ecommerce.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">Store Performance</h1>
            <p className="text-slate-400 text-sm mt-1">{records.length} records</p>
          </div>
          <RequirePermission permission="store_performance.create">
            <button onClick={() => router.push("/dashboard/marketing/ecommerce/performance/new")}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-sm font-medium">
              + Log Entry
            </button>
          </RequirePermission>
        </div>

        {/* KPI summary */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Total Revenue (KES)</p>
            <p className="text-xl font-bold text-sky-400">KES {totalRevenue.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Total Orders</p>
            <p className="text-xl font-bold">{totalOrders.toLocaleString()}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <select value={storeId} onChange={(e) => setStoreId(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All stores</option>
            {stores.map((s) => <option key={s.id} value={s.id}>{s.store_name}</option>)}
          </select>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Date", "Revenue (KES)", "Orders", "Units", "Returns", "Margin", "Ad Spend", "Net Revenue", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((p: StorePerformance) => (
                  <tr key={p.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-300">{p.perf_date}</td>
                    <td className="px-4 py-3 font-medium text-sky-400">
                      {p.total_revenue ? Number(p.total_revenue).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{p.total_orders}</td>
                    <td className="px-4 py-3 text-slate-300">{p.total_units_sold}</td>
                    <td className="px-4 py-3 text-slate-300">{p.returns_count}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {p.gross_margin ? `KES ${Number(p.gross_margin).toLocaleString()}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-red-400">
                      {p.ad_spend ? Number(p.ad_spend).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-emerald-400">
                      {p.net_revenue ? Number(p.net_revenue).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => router.push(`/dashboard/marketing/ecommerce/performance/${p.id}`)}
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
