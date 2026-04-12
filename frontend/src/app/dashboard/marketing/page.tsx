"use client";

import { useQuery } from "@tanstack/react-query";
import { marketingApi, MarketingDashboard, CampaignStatus } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

// ── Sub-components ────────────────────────────────────────────────────────────

function KPI({ label, value, sub, color = "text-white" }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT:     "bg-slate-600",
  PLANNED:   "bg-blue-600",
  ACTIVE:    "bg-emerald-600",
  PAUSED:    "bg-yellow-600",
  COMPLETED: "bg-sky-600",
  CANCELLED: "bg-red-600",
};

function StatusBar({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return <p className="text-slate-500 text-sm">No campaigns yet.</p>;
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([status, count]) => (
        <div key={status} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-24 shrink-0">{status}</span>
          <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${STATUS_COLORS[status] ?? "bg-slate-500"}`}
              style={{ width: `${(count / total) * 100}%` }}
            />
          </div>
          <span className="text-xs font-medium text-slate-300 w-8 text-right">{count}</span>
        </div>
      ))}
    </div>
  );
}

function BudgetVsActualChart({ rows }: { rows: MarketingDashboard["budget_vs_actual"] }) {
  if (!rows.length) return <p className="text-slate-500 text-sm">No budget data.</p>;
  const max = Math.max(...rows.flatMap((r) => [r.budget, r.actual_revenue, r.expected_revenue]));
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.name}>
          <p className="text-xs text-slate-400 mb-1 truncate" title={r.name}>{r.name}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-20 shrink-0">Budget</span>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(r.budget / max) * 100}%` }} />
              </div>
              <span className="text-xs text-slate-400 w-20 text-right">
                {r.budget >= 1_000_000 ? `${(r.budget / 1_000_000).toFixed(1)}M` : `${(r.budget / 1_000).toFixed(0)}K`}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-20 shrink-0">Actual Rev</span>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${r.actual_revenue >= r.budget ? "bg-emerald-500" : "bg-orange-500"}`}
                  style={{ width: `${(r.actual_revenue / max) * 100}%` }} />
              </div>
              <span className="text-xs text-slate-400 w-20 text-right">
                {r.actual_revenue >= 1_000_000 ? `${(r.actual_revenue / 1_000_000).toFixed(1)}M` : `${(r.actual_revenue / 1_000).toFixed(0)}K`}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function PromotionsByRegion({ rows }: { rows: Array<{ region: string; count: number }> }) {
  if (!rows.length) return <p className="text-slate-500 text-sm">No regional data yet.</p>;
  const max = Math.max(...rows.map((r) => r.count));
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div key={r.region} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-28 shrink-0 truncate">{r.region}</span>
          <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(r.count / max) * 100}%` }} />
          </div>
          <span className="text-xs font-medium text-slate-300 w-6 text-right">{r.count}</span>
        </div>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MarketingDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["marketing-dashboard"],
    queryFn: () => marketingApi.analytics.dashboard().then((r) => r.data),
  });

  const fmt = (n: number) =>
    n >= 1_000_000
      ? `KES ${(n / 1_000_000).toFixed(2)}M`
      : n >= 1_000
      ? `KES ${(n / 1_000).toFixed(1)}K`
      : `KES ${n.toFixed(0)}`;

  return (
    <RequirePermission permission="marketing.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Marketing Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Campaign and promotion performance overview</p>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : data ? (
          <>
            {/* ── Campaign KPIs ──────────────────────────────────────────── */}
            <section className="mb-8">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Campaigns
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI label="Active Campaigns"    value={data.active_campaigns}    color="text-emerald-400" />
                <KPI label="Planned Campaigns"   value={data.planned_campaigns}   color="text-blue-400" />
                <KPI label="Total Budget"         value={fmt(data.total_budget)} />
                <KPI label="Actual Revenue"       value={fmt(data.total_actual_revenue)} color="text-sky-400" />
              </div>
            </section>

            {/* ── ROI KPIs ──────────────────────────────────────────────── */}
            <section className="mb-8">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <KPI
                  label="Expected ROI"
                  value={`${(data.expected_roi * 100).toFixed(1)}%`}
                  sub="revenue / budget"
                />
                <KPI
                  label="Actual ROI"
                  value={`${(data.actual_roi * 100).toFixed(1)}%`}
                  color={data.actual_roi >= data.expected_roi ? "text-emerald-400" : "text-orange-400"}
                />
                <KPI label="Expected Revenue"    value={fmt(data.total_expected_revenue)} />
              </div>
            </section>

            {/* ── Promotion KPIs ────────────────────────────────────────── */}
            <section className="mb-8">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Promotions
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
                <KPI label="Total Promotions"    value={data.total_promotions} />
                <KPI label="Active Promotions"   value={data.active_promotions} color="text-emerald-400" />
              </div>
            </section>

            {/* ── Charts row ────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {/* Campaign by status */}
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
                <h3 className="text-sm font-semibold mb-4">Campaign Count by Status</h3>
                <StatusBar data={data.campaign_by_status} />
              </div>

              {/* Budget vs Actual Revenue */}
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
                <h3 className="text-sm font-semibold mb-4">Budget vs Actual Revenue (Top 10)</h3>
                <BudgetVsActualChart rows={data.budget_vs_actual} />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {/* Promotions by region */}
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
                <h3 className="text-sm font-semibold mb-4">Promotions by Region</h3>
                <PromotionsByRegion rows={data.promotions_by_region} />
              </div>

              {/* Campaign activity summary */}
              <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5">
                <h3 className="text-sm font-semibold mb-4">Recent Campaign Activity</h3>
                {data.recent_campaigns.length === 0 ? (
                  <p className="text-slate-500 text-sm">No recent campaigns.</p>
                ) : (
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {data.recent_campaigns.map((c, i) => (
                      <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-800 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-slate-200 truncate max-w-[180px]">{c.name}</p>
                          <p className="text-xs text-slate-500">{c.start_date}</p>
                        </div>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded ${STATUS_COLORS[c.status] ?? "bg-slate-600"} text-white`}
                        >
                          {c.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Quick links */}
            <section>
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Quick Actions</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "+ New Campaign",  href: "/dashboard/marketing/campaigns/new" },
                  { label: "+ New Promotion", href: "/dashboard/marketing/promotions/new" },
                  { label: "All Campaigns",   href: "/dashboard/marketing/campaigns" },
                  { label: "All Promotions",  href: "/dashboard/marketing/promotions" },
                ].map((item) => (
                  <a
                    key={item.href}
                    href={item.href}
                    className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4 text-sm font-medium hover:border-blue-500/50 transition-colors text-center"
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </section>
          </>
        ) : (
          <p className="text-slate-400">No data available.</p>
        )}
      </div>
    </RequirePermission>
  );
}
