"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketingApi } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

function RoasBadge({ roas }: { roas: number }) {
  const cls = roas >= 3 ? "text-emerald-400" : roas >= 1 ? "text-yellow-400" : "text-red-400";
  return <span className={`font-bold ${cls}`}>{roas.toFixed(2)}x</span>;
}

export default function EcommerceAnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data: analytics, isLoading, error } = useQuery({
    queryKey: ["ecommerce-analytics", days],
    queryFn: () => marketingApi.ecommerceAnalytics(days).then((r) => r.data),
  });

  return (
    <RequirePermission permission="ecommerce.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold">E-commerce Analytics</h1>
            <p className="text-slate-400 text-sm mt-1">Aggregated performance across all channels</p>
          </div>
          <div className="flex gap-2">
            {[7, 14, 30, 90].map((d) => (
              <button key={d} onClick={() => setDays(d)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  days === d
                    ? "bg-sky-600 text-white"
                    : "bg-[#131c2e] border border-slate-700 text-slate-400 hover:text-white"
                }`}>
                {d}d
              </button>
            ))}
          </div>
        </div>

        {isLoading && <p className="text-slate-400">Loading analytics…</p>}
        {error && <p className="text-red-400">Failed to load analytics.</p>}

        {analytics && (
          <>
            {/* Summary KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Total Revenue</p>
                <p className="text-xl font-bold text-sky-400">KES {analytics.total_revenue.toLocaleString()}</p>
              </div>
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Total Orders</p>
                <p className="text-xl font-bold">{analytics.total_orders.toLocaleString()}</p>
              </div>
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Avg. Order Value</p>
                <p className="text-xl font-bold text-emerald-400">KES {analytics.avg_order_value.toLocaleString()}</p>
              </div>
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Overall ROAS</p>
                <p className="text-xl font-bold">
                  <RoasBadge roas={analytics.overall_roas} />
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Units Sold</p>
                <p className="text-xl font-bold">{analytics.total_units_sold.toLocaleString()}</p>
              </div>
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Total Ad Spend</p>
                <p className="text-xl font-bold text-red-400">KES {analytics.total_ad_spend.toLocaleString()}</p>
              </div>
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Return Rate</p>
                <p className={`text-xl font-bold ${analytics.overall_return_rate > 10 ? "text-red-400" : "text-slate-300"}`}>
                  {analytics.overall_return_rate.toFixed(1)}%
                </p>
              </div>
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 mb-1">Period</p>
                <p className="text-xl font-bold">{analytics.period_days} days</p>
              </div>
            </div>

            {/* Channel Breakdown */}
            {analytics.channel_breakdown.length > 0 && (
              <div className="mb-8">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Channel Breakdown</h2>
                <div className="overflow-x-auto rounded-xl border border-slate-700/50">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                        {["Store", "Platform", "Revenue (KES)", "Orders", "Units", "Ad Spend", "ROAS", "Return %", "Conv %"].map((h) => (
                          <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.channel_breakdown.map((ch, i) => (
                        <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/30">
                          <td className="px-4 py-3 font-medium text-white">{ch.store_name}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded bg-sky-600/20 text-sky-300 text-xs">{ch.platform}</span>
                          </td>
                          <td className="px-4 py-3 text-sky-400 font-medium">{ch.revenue.toLocaleString()}</td>
                          <td className="px-4 py-3 text-slate-300">{ch.orders.toLocaleString()}</td>
                          <td className="px-4 py-3 text-slate-300">{ch.units.toLocaleString()}</td>
                          <td className="px-4 py-3 text-red-400">{ch.ad_spend.toLocaleString()}</td>
                          <td className="px-4 py-3"><RoasBadge roas={ch.roas} /></td>
                          <td className={`px-4 py-3 ${ch.return_rate > 10 ? "text-red-400" : "text-slate-300"}`}>
                            {ch.return_rate.toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-slate-300">{ch.conv_rate.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Products */}
              {analytics.top_products.length > 0 && (
                <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
                  <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Top Products</h2>
                  <div className="space-y-2">
                    {analytics.top_products.map((p, i) => (
                      <div key={i} className="flex justify-between items-center py-2 border-b border-slate-800 last:border-0">
                        <div>
                          <p className="text-xs font-mono text-slate-400">{p.product_id.slice(0, 12)}…</p>
                          <p className="text-xs text-slate-500">{p.units} units · {p.return_rate.toFixed(1)}% return rate</p>
                        </div>
                        <p className="text-sm font-semibold text-emerald-400">KES {p.revenue.toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Return Reasons */}
              {analytics.return_reasons.length > 0 && (
                <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
                  <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Return Reasons</h2>
                  <div className="space-y-3">
                    {analytics.return_reasons.map((r, i) => {
                      const total = analytics.return_reasons.reduce((s, x) => s + x.count, 0);
                      const pct = total > 0 ? (r.count / total) * 100 : 0;
                      return (
                        <div key={i}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-300">{r.reason || "Unspecified"}</span>
                            <span className="text-slate-400">{r.count} ({pct.toFixed(0)}%)</span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-1.5">
                            <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {analytics.channel_breakdown.length === 0 && analytics.top_products.length === 0 && (
              <div className="text-center py-16 text-slate-500">
                <p className="text-lg">No data for the selected period.</p>
                <p className="text-sm mt-1">Log store performance entries to see analytics here.</p>
              </div>
            )}
          </>
        )}
      </div>
    </RequirePermission>
  );
}
