"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, Influencer, InfluencerPlatform, InfluencerStatus, INFLUENCER_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: InfluencerPlatform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "FACEBOOK", "X", "OTHER"];
const STATUSES: InfluencerStatus[] = ["PROSPECT", "ACTIVE", "INACTIVE", "BLOCKED"];

export default function InfluencersPage() {
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("");

  const { data: influencers = [], isLoading } = useQuery({
    queryKey: ["influencers", platform, status],
    queryFn: () =>
      marketingApi.influencers
        .list({ limit: 100, platform: platform || undefined, status: status || undefined })
        .then((r) => r.data),
  });

  return (
    <RequirePermission permission="influencers.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Influencers</h1>
            <p className="text-slate-400 text-sm mt-1">{influencers.length} influencers</p>
          </div>
          <RequirePermission permission="influencers.create">
            <Link href="/dashboard/marketing/influencers/new"
              className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-sm font-medium text-white">
              + Add Influencer
            </Link>
          </RequirePermission>
        </div>

        <div className="flex gap-3 mb-6 flex-wrap">
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All platforms</option>
            {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : influencers.length === 0 ? (
          <p className="text-slate-400 text-center py-16">No influencers found.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Name", "Platform", "Handle", "Status", "Followers", "Engagement %", "Region", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {influencers.map((i: Influencer) => (
                  <tr key={i.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-medium">{i.influencer_name}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded bg-purple-600/20 text-purple-300 text-xs font-medium">{i.platform}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{i.handle ? `@${i.handle}` : "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${INFLUENCER_STATUS_COLORS[i.status as InfluencerStatus]}`}>{i.status}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {i.followers_count ? i.followers_count.toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {i.engagement_rate ? `${Number(i.engagement_rate).toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{i.region ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/marketing/influencers/${i.id}`}
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
