"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { marketingApi, Campaign, CampaignStatus, CAMPAIGN_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const STATUS_OPTIONS: CampaignStatus[] = [
  "DRAFT", "PLANNED", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED",
];

const APPROVAL_BADGES: Record<string, string> = {
  PENDING:  "bg-yellow-500/10 text-yellow-400",
  APPROVED: "bg-emerald-500/10 text-emerald-400",
  REJECTED: "bg-red-500/10 text-red-400",
};

export default function CampaignsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");

  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ["campaigns", statusFilter, regionFilter],
    queryFn: () =>
      marketingApi.campaigns
        .list({
          status: statusFilter || undefined,
          region: regionFilter || undefined,
          limit: 100,
        })
        .then((r) => r.data),
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => marketingApi.campaigns.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => marketingApi.campaigns.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  const regions = Array.from(new Set(campaigns.map((c: Campaign) => c.region).filter(Boolean))) as string[];

  return (
    <RequirePermission permission="campaigns.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Campaigns</h1>
            <p className="text-slate-400 text-sm mt-1">{campaigns.length} campaigns</p>
          </div>
          <Link
            href="/dashboard/marketing/campaigns/new"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium transition-colors"
          >
            + New Campaign
          </Link>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {regions.length > 0 && (
            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="">All regions</option>
              {regions.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          )}
        </div>

        {/* Table */}
        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-slate-400 mb-4">No campaigns found.</p>
            <Link href="/dashboard/marketing/campaigns/new"
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium">
              Create your first campaign
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Code", "Name", "Type", "Status", "Region", "Budget", "Actual Rev", "ROI", "Dates", "Approval", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c: Campaign) => (
                  <tr key={c.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">{c.campaign_code}</td>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/marketing/campaigns/${c.id}`}
                        className="font-medium text-blue-400 hover:text-blue-300 hover:underline">
                        {c.campaign_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{c.campaign_type}</td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${CAMPAIGN_STATUS_COLORS[c.status as CampaignStatus]}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{c.region ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {c.budget ? `KES ${Number(c.budget).toLocaleString()}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-emerald-400">
                      {c.actual_revenue ? `KES ${Number(c.actual_revenue).toLocaleString()}` : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {c.actual_roi ? (
                        <span className={Number(c.actual_roi) >= 1 ? "text-emerald-400" : "text-orange-400"}>
                          {Number(c.actual_roi).toFixed(2)}x
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap text-xs">
                      {c.start_date} → {c.end_date}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${APPROVAL_BADGES[c.approval_status] ?? ""}`}>
                        {c.approval_status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5">
                        <Link href={`/dashboard/marketing/campaigns/${c.id}`}
                          className="px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 text-xs">
                          View
                        </Link>
                        {c.approval_status === "PENDING" && (
                          <button
                            onClick={() => approveMut.mutate(c.id)}
                            className="px-2 py-1 rounded bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 text-xs"
                          >
                            Approve
                          </button>
                        )}
                        <button
                          onClick={() => { if (confirm(`Delete "${c.campaign_name}"?`)) deleteMut.mutate(c.id); }}
                          className="px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/40 text-xs"
                        >
                          Del
                        </button>
                      </div>
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
