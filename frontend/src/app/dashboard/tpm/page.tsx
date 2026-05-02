"use client";
import { useQuery } from "@tanstack/react-query";
import { tpmApi, fmtCurrency, PROMOTION_STATUS_BADGE } from "@/lib/tpm";
import Link from "next/link";

export default function TPMDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["tpm-dashboard"],
    queryFn: () => tpmApi.getDashboard(),
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading…</div>;
  if (!data) return <div className="p-6 text-red-500">Failed to load TPM dashboard.</div>;

  const d = data;
  const spendPct = d.total_planned_budget > 0
    ? Math.min((d.total_actual_spend / d.total_planned_budget) * 100, 100)
    : 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trade Promotion Management</h1>
          <p className="text-sm text-gray-500">Plan, budget, execute, and analyse trade promotions across all channels.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/tpm/plans/new" className="glow-button-secondary text-sm">+ New Plan</Link>
          <Link href="/dashboard/tpm/promotions/new" className="glow-button text-sm">+ New Promotion</Link>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Active Plans",       value: d.active_plans,                       color: "text-blue-400" },
          { label: "Active Promotions",  value: d.active_promotions,                  color: "text-green-400" },
          { label: "Open Claims",        value: d.open_claims,                        color: "text-yellow-400" },
          { label: "Pending Approvals",  value: d.pending_approvals,                  color: "text-orange-400" },
          { label: "Planned Budget",     value: fmtCurrency(d.total_planned_budget),  color: "text-indigo-400" },
          { label: "Actual Spend",       value: fmtCurrency(d.total_actual_spend),    color: "text-red-400" },
          { label: "Open Claims Value",  value: fmtCurrency(d.open_claims_amount),    color: "text-purple-400" },
          { label: "Budget Utilization", value: `${spendPct.toFixed(1)}%`,            color: spendPct > 90 ? "text-red-400" : "text-teal-400" },
        ].map((k) => (
          <div key={k.label} className="glow-card p-4 text-center">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-lg font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Budget bar */}
      <div className="liquid-glass p-5 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Budget Spend Progress</span>
          <span className="text-gray-300 font-medium">
            {fmtCurrency(d.total_actual_spend)} / {fmtCurrency(d.total_planned_budget)}
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${spendPct > 90 ? "bg-red-500" : spendPct > 70 ? "bg-orange-500" : "bg-green-500"}`}
            style={{ width: `${spendPct}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Status breakdown */}
        <div className="liquid-glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Promotions by Status</h2>
          {Object.entries(d.promotions_by_status).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between text-sm">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PROMOTION_STATUS_BADGE[status as import("@/lib/tpm").TPMPromotionStatus] ?? "bg-gray-100 text-gray-600"}`}>
                {status}
              </span>
              <span className="text-gray-300 font-bold">{count}</span>
            </div>
          ))}
        </div>

        {/* Top promotions */}
        <div className="liquid-glass p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Recent Promotions</h2>
            <Link href="/dashboard/tpm/promotions" className="text-xs text-indigo-400 hover:text-indigo-300">View all →</Link>
          </div>
          {d.top_promotions.length === 0 ? (
            <p className="text-xs text-gray-500">No promotions yet.</p>
          ) : d.top_promotions.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-3">
              <div>
                <Link href={`/dashboard/tpm/promotions/${p.id}`} className="text-sm font-medium text-gray-200 hover:text-indigo-300">
                  {p.promotion_name}
                </Link>
                <p className="text-xs text-gray-500 font-mono">{p.promotion_code}</p>
              </div>
              <div className="text-right text-xs text-gray-500">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PROMOTION_STATUS_BADGE[p.status as import("@/lib/tpm").TPMPromotionStatus] ?? ""}`}>{p.status}</span>
                <p className="mt-1">{p.valid_from} → {p.valid_to}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Promotion Calendar",  href: "/dashboard/tpm/calendar" },
          { label: "Budget Monitor",      href: "/dashboard/tpm/budget" },
          { label: "Claims Queue",        href: "/dashboard/tpm/claims" },
          { label: "ROI Analysis",        href: "/dashboard/tpm/roi" },
          { label: "Settlement Tracker",  href: "/dashboard/tpm/settlement" },
          { label: "Plans Master",        href: "/dashboard/tpm/plans" },
          { label: "All Promotions",      href: "/dashboard/tpm/promotions" },
          { label: "AI Agents",           href: "/dashboard/tpm/ai" },
        ].map((q) => (
          <Link key={q.label} href={q.href} className="glow-card p-3 text-center text-sm text-gray-300 hover:text-indigo-300 transition-colors">
            {q.label} →
          </Link>
        ))}
      </div>
    </div>
  );
}
