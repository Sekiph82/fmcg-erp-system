"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, AdPerformance, AdPlatform } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const AD_PLATFORMS: AdPlatform[] = ["META", "GOOGLE", "TIKTOK", "TWITTER", "LINKEDIN", "YOUTUBE", "OTHER"];

export default function AdsPage() {
  const [platform, setPlatform] = useState("");

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["ads", platform],
    queryFn: () =>
      marketingApi.ads
        .list({ limit: 100, platform: platform || undefined })
        .then((r) => r.data),
  });

  const totals = records.reduce(
    (acc, a: AdPerformance) => ({
      spend:       acc.spend + Number(a.spend ?? 0),
      revenue:     acc.revenue + Number(a.revenue_generated ?? 0),
      impressions: acc.impressions + (a.impressions ?? 0),
      clicks:      acc.clicks + (a.clicks ?? 0),
      conversions: acc.conversions + (a.conversions ?? 0),
    }),
    { spend: 0, revenue: 0, impressions: 0, clicks: 0, conversions: 0 }
  );

  const roas = totals.spend > 0 ? (totals.revenue / totals.spend).toFixed(2) : "—";

  return (
    <RequirePermission permission="ad_performance.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Ads Performance</h1>
            <p className="text-slate-400 text-sm mt-1">{records.length} records</p>
          </div>
          <RequirePermission permission="ad_performance.edit">
            <Link href="/dashboard/marketing/ads/new"
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-medium text-white">
              + Log Ad
            </Link>
          </RequirePermission>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Spend (KES)</p>
            <p className="text-xl font-bold text-red-400">{totals.spend.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Revenue (KES)</p>
            <p className="text-xl font-bold text-emerald-400">{totals.revenue.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">ROAS</p>
            <p className={`text-xl font-bold ${Number(roas) >= 3 ? "text-emerald-400" : "text-yellow-400"}`}>{roas}x</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Clicks</p>
            <p className="text-xl font-bold">{totals.clicks.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-1">Conversions</p>
            <p className="text-xl font-bold">{totals.conversions.toLocaleString()}</p>
          </div>
        </div>

        {/* Platform filter */}
        <div className="flex gap-2 mb-6 flex-wrap">
          <button onClick={() => setPlatform("")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${!platform ? "bg-blue-600 border-blue-600 text-white" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}>
            All
          </button>
          {AD_PLATFORMS.map((p) => (
            <button key={p} onClick={() => setPlatform(p)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${platform === p ? "bg-blue-600 border-blue-600 text-white" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}>
              {p}
            </button>
          ))}
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Platform", "Ad Name", "Date", "Spend (KES)", "Revenue", "Impressions", "Clicks", "CTR %", "Conversions", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((a: AdPerformance) => (
                  <tr key={a.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded bg-indigo-600/20 text-indigo-300 text-xs font-medium">{a.platform}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{a.ad_name ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{a.ad_date}</td>
                    <td className="px-4 py-3 text-red-400 font-medium">
                      {a.spend ? Number(a.spend).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-emerald-400">
                      {a.revenue_generated ? Number(a.revenue_generated).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">{a.impressions?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{a.clicks?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{a.ctr ? `${Number(a.ctr).toFixed(2)}%` : "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{a.conversions?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/marketing/ads/${a.id}`}
                        className="px-2 py-1 rounded bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs">
                        View
                      </Link>
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
