"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { marketingApi, CRMProfile, RelationshipStatus, CRM_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const STATUS_OPTIONS: RelationshipStatus[] = ["PROSPECT", "ACTIVE", "AT_RISK", "DORMANT", "CHURNED", "VIP"];

export default function CRMPage() {
  const [statusFilter, setStatusFilter] = useState("");

  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ["crm-profiles", statusFilter],
    queryFn: () =>
      marketingApi.crm
        .list({ status: statusFilter || undefined, limit: 100 })
        .then((r) => r.data),
  });

  return (
    <RequirePermission permission="crm.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">CRM</h1>
            <p className="text-slate-400 text-sm mt-1">{profiles.length} profiles</p>
          </div>
          <Link href="/dashboard/marketing/crm/followup"
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
            Follow-ups Due
          </Link>
        </div>

        {/* Status filters */}
        <div className="flex gap-2 mb-6 flex-wrap">
          <button
            onClick={() => setStatusFilter("")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors
              ${!statusFilter ? "bg-blue-600 border-blue-600 text-white" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}
          >
            All
          </button>
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors
                ${statusFilter === s ? "bg-blue-600 border-blue-600 text-white" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}
            >
              {s}
            </button>
          ))}
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : profiles.length === 0 ? (
          <p className="text-slate-400 text-center py-16">No CRM profiles found.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Customer ID", "Status", "Loyalty", "LTV (KES)", "Engagement", "Source", "Next Follow-up", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {profiles.map((p: CRMProfile) => (
                  <tr key={p.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{p.customer_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${CRM_STATUS_COLORS[p.relationship_status as RelationshipStatus]}`}>
                        {p.relationship_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{p.loyalty_status}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {p.estimated_ltv ? Number(p.estimated_ltv).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {p.engagement_score ? Number(p.engagement_score).toFixed(1) : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{p.acquisition_source ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {p.next_followup_date ? (
                        <span className={new Date(p.next_followup_date) < new Date() ? "text-red-400" : "text-slate-300"}>
                          {p.next_followup_date}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/marketing/crm/${p.id}`}
                        className="px-2 py-1 rounded bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 text-xs">
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
