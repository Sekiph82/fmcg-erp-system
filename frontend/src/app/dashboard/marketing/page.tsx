"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, MarketingDashboard } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx } from "@/lib/i18n/core";

// ── Sub-components ────────────────────────────────────────────────────────────

function KPI({ label, value, sub, color = "text-slate-100" }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="glow-card p-4">
      <p className="text-xs text-slate-400 mb-1 uppercase tracking-wide font-medium">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT:     "bg-slate-600",
  PLANNED:   "bg-blue-500",
  ACTIVE:    "bg-emerald-500",
  PAUSED:    "bg-amber-500",
  COMPLETED: "bg-sky-500",
  CANCELLED: "bg-red-500",
};

const STATUS_BADGE: Record<string, string> = {
  DRAFT:     "bg-slate-700 text-slate-300",
  PLANNED:   "bg-blue-900/60 text-blue-300",
  ACTIVE:    "bg-emerald-900/60 text-emerald-300",
  PAUSED:    "bg-amber-900/60 text-amber-300",
  COMPLETED: "bg-sky-900/60 text-sky-300",
  CANCELLED: "bg-red-900/60 text-red-300",
};

function StatusBar({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return <p className="text-slate-500 text-sm">{tx("No campaigns yet.")}</p>;
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([status, count]) => (
        <div key={status} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-24 shrink-0">{status}</span>
          <div className="flex-1 h-2 bg-slate-800/60 rounded-full overflow-hidden">
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
  if (!rows.length) return <p className="text-slate-500 text-sm">{tx("No budget data.")}</p>;
  const max = Math.max(...rows.flatMap((r) => [r.budget, r.actual_revenue, r.expected_revenue]));
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.name}>
          <p className="text-xs text-slate-400 mb-1 truncate" title={r.name}>{r.name}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-20 shrink-0">{tx("Budget")}</span>
              <div className="flex-1 h-1.5 bg-slate-800/60 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(r.budget / max) * 100}%` }} />
              </div>
              <span className="text-xs text-slate-400 w-20 text-right">
                {r.budget >= 1_000_000 ? `${(r.budget / 1_000_000).toFixed(1)}M` : `${(r.budget / 1_000).toFixed(0)}K`}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 w-20 shrink-0">{tx("Actual Rev")}</span>
              <div className="flex-1 h-1.5 bg-slate-800/60 rounded-full overflow-hidden">
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
  if (!rows.length) return <p className="text-slate-500 text-sm">{tx("No regional data yet.")}</p>;
  const max = Math.max(...rows.map((r) => r.count));
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div key={r.region} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-28 shrink-0 truncate">{r.region}</span>
          <div className="flex-1 h-2 bg-slate-800/60 rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(r.count / max) * 100}%` }} />
          </div>
          <span className="text-xs font-medium text-slate-300 w-6 text-right">{r.count}</span>
        </div>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

function MarketingDashboardTab() {
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
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">{tx("Marketing Dashboard")}</h1>
            <p className="text-sm text-slate-400 mt-1">{tx("Campaign and promotion performance overview")}</p>
          </div>
          <div className="flex gap-2">
            <a href="/dashboard/marketing?tab=campaigns&drawer=create" className="glow-button-secondary text-sm">{tx("+ New Campaign")}</a>
            <a href="/dashboard/marketing?tab=promotions&drawer=create" className="glow-button text-sm">{tx("+ New Promotion")}</a>
          </div>
        </div>

        {isLoading ? (
          <p className="text-slate-400">{tx("Loading...")}</p>
        ) : !data ? (
          <p className="text-red-400">{tx("Failed to load marketing data.")}</p>
        ) : (
          <>
            {/* ── Campaign KPIs ────────────────────────────────────────────── */}
            <section>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("Campaigns")}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI label={tx("Active Campaigns")}  value={data.active_campaigns}           color="text-emerald-400" />
                <KPI label={tx("Planned Campaigns")} value={data.planned_campaigns}           color="text-blue-400" />
                <KPI label={tx("Total Budget")}       value={fmt(data.total_budget)} />
                <KPI label={tx("Actual Revenue")}     value={fmt(data.total_actual_revenue)}  color="text-sky-400" />
              </div>
            </section>

            {/* ── ROI KPIs ─────────────────────────────────────────────────── */}
            <section>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <KPI label={tx("Expected ROI")}     value={`${(data.expected_roi * 100).toFixed(1)}%`}  sub="revenue / budget" />
                <KPI
                  label={tx("Actual ROI")}
                  value={`${(data.actual_roi * 100).toFixed(1)}%`}
                  color={data.actual_roi >= data.expected_roi ? "text-emerald-400" : "text-orange-400"}
                />
                <KPI label={tx("Expected Revenue")} value={fmt(data.total_expected_revenue)} />
              </div>
            </section>

            {/* ── Promotion KPIs ───────────────────────────────────────────── */}
            <section>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("Promotions")}</p>
              <div className="grid grid-cols-2 gap-4">
                <KPI label={tx("Total Promotions")}  value={data.total_promotions} />
                <KPI label={tx("Active Promotions")} value={data.active_promotions} color="text-emerald-400" />
              </div>
            </section>

            {/* ── Charts row ───────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glow-card p-5">
                <h3 className="text-sm font-semibold text-slate-200 mb-4">{tx("Campaign Count by Status")}</h3>
                <StatusBar data={data.campaign_by_status} />
              </div>
              <div className="glow-card p-5">
                <h3 className="text-sm font-semibold text-slate-200 mb-4">{tx("Budget vs Actual Revenue (Top 10)")}</h3>
                <BudgetVsActualChart rows={data.budget_vs_actual} />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glow-card p-5">
                <h3 className="text-sm font-semibold text-slate-200 mb-4">{tx("Promotions by Region")}</h3>
                <PromotionsByRegion rows={data.promotions_by_region} />
              </div>
              <div className="glow-card p-5">
                <h3 className="text-sm font-semibold text-slate-200 mb-4">{tx("Recent Campaign Activity")}</h3>
                {data.recent_campaigns.length === 0 ? (
                  <p className="text-slate-500 text-sm">{tx("No recent campaigns.")}</p>
                ) : (
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {data.recent_campaigns.map((c, i) => (
                      <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-700/50 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-slate-200 truncate max-w-[180px]">{c.name}</p>
                          <p className="text-xs text-slate-500">{c.start_date}</p>
                        </div>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[c.status] ?? "bg-slate-700 text-slate-300"}`}>
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
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("Quick Actions")}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: tx("+ New Campaign"),  href: "/dashboard/marketing?tab=campaigns&drawer=create" },
                  { label: tx("+ New Promotion"), href: "/dashboard/marketing?tab=promotions&drawer=create" },
                  { label: tx("All Campaigns"),   href: "/dashboard/marketing/campaigns" },
                  { label: tx("All Promotions"),  href: "/dashboard/marketing/promotions" },
                ].map((item) => (
                  <a
                    key={item.href}
                    href={item.href}
                    className="glow-card p-4 text-sm font-medium text-slate-300 hover:text-white text-center transition-colors block"
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </RequirePermission>
  );
}

const MarketingCampaignsPage  = dynamic(() => import("@/app/dashboard/marketing/campaigns/page"),   { ssr: false });
const MarketingPromotionsPage = dynamic(() => import("@/app/dashboard/marketing/promotions/page"),  { ssr: false });
const MarketingTradeSpendPage = dynamic(() => import("@/app/dashboard/marketing/trade-spend/page"), { ssr: false });
const MarketingAdsPage        = dynamic(() => import("@/app/dashboard/marketing/ads/page"),          { ssr: false });
const MarketingSocialPage     = dynamic(() => import("@/app/dashboard/marketing/social-media/page"), { ssr: false });
const MarketingSegmentsPage   = dynamic(() => import("@/app/dashboard/marketing/segments/page"),    { ssr: false });
const MarketingInfluencersPage= dynamic(() => import("@/app/dashboard/marketing/influencers/page"), { ssr: false });
const MarketingEcommercePage  = dynamic(() => import("@/app/dashboard/marketing/ecommerce/page"),   { ssr: false });
const MarketingAnalyticsPage  = dynamic(() => import("@/app/dashboard/marketing/analytics/page"),   { ssr: false });
const MarketingVisitsPage     = dynamic(() => import("@/app/dashboard/marketing/visits/page"),       { ssr: false });
const MarketingBrandSpendPage = dynamic(() => import("@/app/dashboard/marketing/brand-spend/page"), { ssr: false });
const TPMPage                 = dynamic(() => import("@/app/dashboard/tpm/page"),                   { ssr: false });
const MarketIntelPage         = dynamic(() => import("@/app/dashboard/market-intelligence/page"),   { ssr: false });
const WebsitePage             = dynamic(() => import("@/app/dashboard/marketing/website/page"),     { ssr: false });   // M46
const ContentStudioPage       = dynamic(() => import("@/app/dashboard/marketing/content-studio/page"), { ssr: false });
const MarketingStudioPage     = dynamic(() => import("@/app/dashboard/marketing/studio/page"), { ssr: false });   // M49.S01.T012
const SeoProPage            = dynamic(() => import("@/app/dashboard/marketing/seo-pro/page"), { ssr: false });   // M51.S01.T003-T005/T009
const MediaStudioPage        = dynamic(() => import("@/app/dashboard/marketing/media-studio/page"), { ssr: false });   // M51.S01.T006/T007/T010
const MembersMediaPage        = dynamic(() => import("@/app/dashboard/marketing/members-media/page"), { ssr: false });

export default function MarketingPage() {
  const tabs = [
    { key: "overview",      label: tx("Overview"),         permission: "marketing.view", content: <MarketingDashboardTab /> },
    { key: "studio",        label: tx("Marketing Studio"), permission: "marketing.view", content: <MarketingStudioPage /> },
    { key: "campaigns",     label: tx("Campaigns"),        permission: "campaigns.view", content: <MarketingCampaignsPage /> },
    { key: "promotions",    label: tx("Promotions"),       permission: "promotions.view", content: <MarketingPromotionsPage /> },
    { key: "promotions-schemes", label: tx("Schemes"),    permission: "promotions.view", content: <MarketingPromotionsPage /> },
    { key: "tpm",           label: "TPM",              permission: "marketing.view", content: <TPMPage /> },
    { key: "trade-spend",   label: tx("Trade Spend"),      permission: "trade_spend.view", content: <MarketingTradeSpendPage /> },
    { key: "ads",           label: tx("Ads"),              permission: "ad_performance.view", content: <MarketingAdsPage /> },
    { key: "social-media",  label: tx("Social Media"),     permission: "social_media.view", content: <MarketingSocialPage /> },
    { key: "segments",      label: tx("Segments"),         permission: "segments.view", content: <MarketingSegmentsPage /> },
    { key: "influencers",   label: tx("Influencers"),      permission: "influencers.view", content: <MarketingInfluencersPage /> },
    { key: "ecommerce",     label: tx("E-Commerce"),       permission: "ecommerce.view", content: <MarketingEcommercePage /> },
    { key: "brand-spend",   label: tx("Brand Spend"),      permission: "brand_spend.view", content: <MarketingBrandSpendPage /> },
    { key: "visits",        label: tx("Visits"),           permission: "customer_visits.view", content: <MarketingVisitsPage /> },
    { key: "market-intel",  label: tx("Market Intel"),     permission: "marketing.view", content: <MarketIntelPage /> },
    { key: "analytics",     label: tx("Analytics"),        permission: "marketing_analytics.view", content: <MarketingAnalyticsPage /> },
    { key: "website",       label: tx("Website & blog"),   permission: "marketing.view", content: <WebsitePage /> },
    { key: "content-studio", label: tx("Content studio"),  permission: "marketing.view", content: <ContentStudioPage /> },
    { key: "media-studio", label: tx("Media studio"),     permission: "marketing.view", content: <MediaStudioPage /> },
    { key: "seo-pro",      label: tx("SEO & AEO"),        permission: "marketing.view", content: <SeoProPage /> },
    { key: "members-media", label: tx("Members & media"),  permission: "marketing.view", content: <MembersMediaPage /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Marketing")}
      description={tx("Campaigns, promotions, TPM, ads, social media, e-commerce")}
      permission="marketing.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
