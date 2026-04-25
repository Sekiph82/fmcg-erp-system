"use client";
import { useQuery } from "@tanstack/react-query";
import { promoApi, SCHEME_TYPE_LABEL, SchemeType, fmtCurrency } from "@/lib/promotions";
import Link from "next/link";

export default function PromoAnalyticsPage() {
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["promo-usage"],
    queryFn: () => promoApi.getUsageReport(),
  });

  const { data: schemes = [] } = useQuery({
    queryKey: ["promo-schemes"],
    queryFn: () => promoApi.getSchemes(),
  });

  const activeCount   = schemes.filter((s) => s.status === "ACTIVE").length;
  const expiredCount  = schemes.filter((s) => s.status === "EXPIRED").length;
  const totalDiscount = rows.reduce((s: number, r: any) => s + (r.total_discount || 0), 0);
  const totalFree     = rows.reduce((s: number, r: any) => s + (r.total_free_value || 0), 0);
  const totalOrders   = rows.reduce((s: number, r: any) => s + (r.order_count || 0), 0);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Promo Cost Analytics</h1>
          <p className="text-sm text-gray-500">Usage, cost, and effectiveness of all promotional schemes.</p>
        </div>
        <Link href="/dashboard/promotions/schemes" className="glow-button-secondary text-sm">View Schemes →</Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Active Schemes",    value: activeCount,              color: "text-green-400" },
          { label: "Expired Schemes",   value: expiredCount,             color: "text-gray-400" },
          { label: "Total Orders",      value: totalOrders,              color: "text-blue-400" },
          { label: "Total Discount",    value: fmtCurrency(totalDiscount), color: "text-orange-400" },
          { label: "Free Goods Value",  value: fmtCurrency(totalFree),   color: "text-purple-400" },
        ].map((k) => (
          <div key={k.label} className="glow-card p-4 text-center">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-lg font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="glass-table overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-blue-900/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Scheme</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Type</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Orders</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Total Discount</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Free Value</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Total Cost</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase">Cost Share</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">No usage data yet.</td></tr>
            ) : rows.map((r: any) => {
              const pct = totalDiscount > 0 ? (r.total_discount / totalDiscount) * 100 : 0;
              return (
                <tr key={r.scheme_id} className="border-b border-blue-900/20 hover:bg-blue-950/20 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/dashboard/promotions/schemes/${r.scheme_id}`} className="font-medium text-gray-200 hover:text-indigo-300">
                      {r.scheme_name}
                    </Link>
                    <p className="text-xs text-gray-500 font-mono">{r.scheme_code}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {SCHEME_TYPE_LABEL[r.scheme_type as SchemeType] ?? r.scheme_type}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">{r.order_count}</td>
                  <td className="px-4 py-3 text-right text-orange-400">{fmtCurrency(r.total_discount)}</td>
                  <td className="px-4 py-3 text-right text-purple-400">{fmtCurrency(r.total_free_value)}</td>
                  <td className="px-4 py-3 text-right font-medium text-red-400">{fmtCurrency(r.total_cost)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                        <div className="bg-orange-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-400 w-10 text-right">{pct.toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
