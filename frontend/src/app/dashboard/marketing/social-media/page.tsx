"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, SocialMediaActivity, InfluencerPlatform } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: InfluencerPlatform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "FACEBOOK", "X", "OTHER"];

const SENTIMENT_COLORS: Record<string, string> = {
  POSITIVE: "text-emerald-400",
  NEUTRAL:  "text-slate-400",
  NEGATIVE: "text-red-400",
};

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);
}

export default function SocialMediaPage() {
  const [platform, setPlatform] = useState("");

  const { data: activities = [], isLoading } = useQuery({
    queryKey: ["social-media", platform],
    queryFn: () =>
      marketingApi.social
        .list({ limit: 100, platform: platform || undefined })
        .then((r) => r.data),
  });

  const totals = activities.reduce(
    (acc, a: SocialMediaActivity) => ({
      reach:       acc.reach + (a.reach ?? 0),
      impressions: acc.impressions + (a.impressions ?? 0),
      engagements: acc.engagements + (a.engagements ?? 0),
      clicks:      acc.clicks + (a.clicks ?? 0),
    }),
    { reach: 0, impressions: 0, engagements: 0, clicks: 0 }
  );

  return (
    <RequirePermission permission="social_media.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Social Media Activity</h1>
            <p className="text-slate-400 text-sm mt-1">{activities.length} posts tracked</p>
          </div>
          <RequirePermission permission="social_media.edit">
            <Link href="/dashboard/marketing/social-media/new"
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white">
              + Log Activity
            </Link>
          </RequirePermission>
        </div>

        {/* Summary KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Reach",        value: fmt(totals.reach) },
            { label: "Impressions",  value: fmt(totals.impressions) },
            { label: "Engagements",  value: fmt(totals.engagements) },
            { label: "Clicks",       value: fmt(totals.clicks) },
          ].map((k) => (
            <div key={k.label} className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
              <p className="text-xs text-slate-400 mb-1">{k.label}</p>
              <p className="text-xl font-bold">{k.value}</p>
            </div>
          ))}
        </div>

        {/* Platform filter */}
        <div className="flex gap-2 mb-6 flex-wrap">
          <button onClick={() => setPlatform("")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${!platform ? "bg-blue-600 border-blue-600 text-white" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}>
            All
          </button>
          {PLATFORMS.map((p) => (
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
                  {["Platform", "Type", "Date", "Reach", "Impressions", "Engagements", "Clicks", "Saves", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {activities.map((a: SocialMediaActivity) => (
                  <tr key={a.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded bg-purple-600/20 text-purple-300 text-xs font-medium">{a.platform}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{a.content_type ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{a.published_date}</td>
                    <td className="px-4 py-3 text-slate-300">{fmt(a.reach)}</td>
                    <td className="px-4 py-3 text-slate-300">{fmt(a.impressions)}</td>
                    <td className="px-4 py-3 text-slate-300">{fmt(a.engagements)}</td>
                    <td className="px-4 py-3 text-slate-300">{fmt(a.clicks)}</td>
                    <td className="px-4 py-3 text-slate-300">{fmt(a.saves_count)}</td>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/marketing/social-media/${a.id}`}
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
