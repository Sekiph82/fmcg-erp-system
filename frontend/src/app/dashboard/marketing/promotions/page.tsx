"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { marketingApi, MktPromotion } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const STATUS_COLORS: Record<string, string> = {
  DRAFT:   "text-slate-400",
  ACTIVE:  "text-emerald-400",
  EXPIRED: "text-red-400",
  PAUSED:  "text-yellow-400",
};

export default function PromotionsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [campaignFilter, setCampaignFilter] = useState("");

  const { data: campaigns = [] } = useQuery({
    queryKey: ["campaigns-all"],
    queryFn: () => marketingApi.campaigns.list({ limit: 200 }).then((r) => r.data),
  });

  const { data: promotions = [], isLoading } = useQuery({
    queryKey: ["promotions", statusFilter, campaignFilter],
    queryFn: () =>
      marketingApi.promotions
        .list({
          status: statusFilter || undefined,
          campaign_id: campaignFilter || undefined,
          limit: 100,
        })
        .then((r) => r.data),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => marketingApi.promotions.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promotions"] }),
  });

  return (
    <RequirePermission permission="promotions.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Promotions</h1>
            <p className="text-slate-400 text-sm mt-1">{promotions.length} promotions</p>
          </div>
          <Link href="/dashboard/marketing/promotions/new"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium transition-colors">
            + New Promotion
          </Link>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All statuses</option>
            {["DRAFT", "ACTIVE", "EXPIRED", "PAUSED"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {campaigns.length > 0 && (
            <select value={campaignFilter} onChange={(e) => setCampaignFilter(e.target.value)}
              className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
              <option value="">All campaigns</option>
              {campaigns.map((c) => <option key={c.id} value={c.id}>{c.campaign_name}</option>)}
            </select>
          )}
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : promotions.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-slate-400 mb-4">No promotions found.</p>
            <Link href="/dashboard/marketing/promotions/new"
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium">
              Create your first promotion
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Code", "Name", "Type", "Status", "Region", "Discount", "Dates", "Campaign", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {promotions.map((p: MktPromotion) => {
                  const linkedCampaign = p.campaign_id
                    ? campaigns.find((c) => c.id === p.campaign_id)
                    : null;
                  return (
                    <tr key={p.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{p.promotion_code ?? "—"}</td>
                      <td className="px-4 py-3">
                        <Link href={`/dashboard/marketing/promotions/${p.id}`}
                          className="font-medium text-blue-400 hover:text-blue-300 hover:underline">
                          {p.promotion_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-slate-300">{p.promotion_type}</td>
                      <td className="px-4 py-3">
                        <span className={`font-medium ${STATUS_COLORS[p.status] ?? "text-white"}`}>{p.status}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{p.region ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-300">
                        {p.discount_type && p.discount_value
                          ? `${Number(p.discount_value).toFixed(2)}${p.discount_type === "PERCENTAGE" ? "%" : " KES"}`
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-400 whitespace-nowrap text-xs">
                        {p.start_date} → {p.end_date}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {linkedCampaign ? linkedCampaign.campaign_name : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1.5">
                          <Link href={`/dashboard/marketing/promotions/${p.id}`}
                            className="px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 text-xs">
                            View
                          </Link>
                          <button
                            onClick={() => { if (confirm(`Delete "${p.promotion_name}"?`)) deleteMut.mutate(p.id); }}
                            className="px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/40 text-xs">
                            Del
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
