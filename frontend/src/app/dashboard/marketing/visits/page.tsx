"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { marketingApi, CustomerVisit, VisitType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const VISIT_TYPE_OPTIONS: VisitType[] = [
  "SALES", "MARKETING", "TRADE_AUDIT", "MERCHANDISING", "FEEDBACK", "STORE_CHECK",
];

const TYPE_COLORS: Record<VisitType, string> = {
  SALES:         "bg-blue-600/20 text-blue-300",
  MARKETING:     "bg-purple-600/20 text-purple-300",
  TRADE_AUDIT:   "bg-orange-600/20 text-orange-300",
  MERCHANDISING: "bg-teal-600/20 text-teal-300",
  FEEDBACK:      "bg-yellow-600/20 text-yellow-300",
  STORE_CHECK:   "bg-slate-600/20 text-slate-300",
};

export default function VisitsPage() {
  const [typeFilter, setTypeFilter] = useState("");

  const { data: visits = [], isLoading } = useQuery({
    queryKey: ["visits", typeFilter],
    queryFn: () =>
      marketingApi.visits
        .list({ visit_type: typeFilter || undefined, limit: 100 })
        .then((r) => r.data),
  });

  return (
    <RequirePermission permission="customer_visits.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Field Visits</h1>
            <p className="text-slate-400 text-sm mt-1">{visits.length} visits recorded</p>
          </div>
          <Link href="/dashboard/marketing/visits/new"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium transition-colors">
            + Log Visit
          </Link>
        </div>

        <div className="flex gap-3 mb-6 flex-wrap">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="">All types</option>
            {VISIT_TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : visits.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-slate-400 mb-4">No visits found.</p>
            <Link href="/dashboard/marketing/visits/new"
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium">
              Log your first visit
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Type", "Date", "Purpose", "Outcome", "Follow-up", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visits.map((v: CustomerVisit) => (
                  <tr key={v.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${TYPE_COLORS[v.visit_type]}`}>
                        {v.visit_type.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{v.visit_date}</td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate">{v.purpose ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-300 max-w-xs truncate">{v.outcome ?? "—"}</td>
                    <td className="px-4 py-3">
                      {v.followup_required ? (
                        <span className="text-xs text-orange-400 font-medium">Required</span>
                      ) : (
                        <span className="text-xs text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/marketing/visits/${v.id}`}
                        className="px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 text-xs">
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
