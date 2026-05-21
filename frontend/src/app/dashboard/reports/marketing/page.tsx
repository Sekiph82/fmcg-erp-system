"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  analyticsApi,
  MarketingBIKPIs,
  MarketingCampaignsDetail,
  MarketingInfluencersDetail,
  MarketingAdsDetail,
  MarketingSocialDetail,
  MarketingStoresDetail,
  MarketingReturnsDetail,
  fmtKES,
  fmt,
} from "@/lib/analytics";
import { TrendLineChart, HBarChart, Sparkline } from "@/components/bi/Charts";

// ── Shared UI primitives ──────────────────────────────────────────────────────

function KpiTile({
  label, value, sub, accent = "text-white",
}: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-[#131c2e] p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function Section({ title, href, children }: { title: string; href?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest">{title}</h2>
        {href && (
          <Link href={href} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
            View source →
          </Link>
        )}
      </div>
      {children}
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-700/50 bg-[#131c2e] p-4 ${className}`}>
      {children}
    </div>
  );
}

function LoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-800/50" />
      ))}
    </div>
  );
}

function BarRow({ label, value, max, formatted }: { label: string; value: number; max: number; formatted: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 text-xs text-slate-300 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-slate-700/50">
        <div className="h-2 rounded-full bg-blue-500/70 transition-all" style={{ width: `${(value / Math.max(max, 1)) * 100}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-24 text-right shrink-0">{formatted}</span>
    </div>
  );
}

const SEV_CLS: Record<string, string> = {
  critical: "bg-red-500/10 border-red-500/30 text-red-400",
  high:     "bg-orange-500/10 border-orange-500/30 text-orange-400",
  medium:   "bg-yellow-500/10 border-yellow-500/30 text-yellow-400",
  low:      "bg-slate-700/40 border-slate-600/30 text-slate-400",
};

// ── Tab definitions ───────────────────────────────────────────────────────────

const TABS = [
  { id: "overview",    label: "Overview" },
  { id: "campaigns",  label: "Campaigns" },
  { id: "spend",      label: "Spend" },
  { id: "influencers",label: "Influencers" },
  { id: "social",     label: "Social" },
  { id: "ads",        label: "Ads" },
  { id: "ecommerce",  label: "E-commerce" },
  { id: "crm",        label: "CRM" },
  { id: "returns",    label: "Returns" },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ── Tab: Overview ─────────────────────────────────────────────────────────────

function OverviewTab({ kpi, days }: { kpi: MarketingBIKPIs; days: number }) {
  return (
    <div className="space-y-6">
      {kpi.exceptions.length > 0 && (
        <div className="space-y-2">
          {kpi.exceptions.map((ex) => (
            <Link key={ex.id} href={ex.href}
              className={`rounded-xl border p-3 flex items-start gap-3 transition-opacity hover:opacity-90 ${SEV_CLS[ex.severity] ?? SEV_CLS.low}`}>
              <div>
                <p className="text-sm font-semibold">{ex.label}</p>
                <p className="text-xs mt-0.5 opacity-80">{ex.detail}</p>
              </div>
            </Link>
          ))}
        </div>
      )}

      <Section title="Campaign Performance" href="/dashboard/marketing/campaigns">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <KpiTile label="Active" value={fmt(kpi.active_campaigns)} accent="text-blue-400" />
          <KpiTile label="Completed" value={fmt(kpi.completed_campaigns)} />
          <KpiTile label="Avg ROI" value={`${kpi.avg_campaign_roi.toFixed(2)}x`} accent="text-emerald-400" />
          <KpiTile label="Budget" value={fmtKES(kpi.total_campaign_budget)} accent="text-amber-400" />
          <KpiTile label="Revenue" value={fmtKES(kpi.total_campaign_revenue)} accent="text-emerald-400" />
          <KpiTile label="Efficiency" value={`${kpi.overall_campaign_efficiency.toFixed(2)}x`}
            accent={kpi.overall_campaign_efficiency >= 1 ? "text-emerald-400" : "text-red-400"} />
        </div>
        <Card>
          <p className="text-xs text-slate-500 mb-2">Campaign Revenue Trend</p>
          <TrendLineChart data={kpi.campaign_revenue_trend} color="#10b981" formatY={fmtKES} />
        </Card>
      </Section>

      <div className="grid md:grid-cols-2 gap-6">
        <Section title="Marketing Spend" href="/dashboard/reports/marketing?tab=spend">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <KpiTile label="Trade Spend" value={fmtKES(kpi.total_trade_spend)} accent="text-orange-400" />
            <KpiTile label="Brand Spend" value={fmtKES(kpi.total_brand_spend)} accent="text-blue-400" />
            <KpiTile label="Trade/Sales %" value={`${kpi.trade_spend_vs_sales_pct.toFixed(1)}%`}
              accent={kpi.trade_spend_vs_sales_pct > 15 ? "text-orange-400" : "text-slate-200"} />
            <KpiTile label="Brand/Revenue %" value={`${kpi.brand_spend_vs_revenue_pct.toFixed(1)}%`} />
          </div>
        </Section>

        <Section title="Ad Performance" href="/dashboard/reports/marketing?tab=ads">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <KpiTile label="Total Ad Spend" value={fmtKES(kpi.total_ad_spend)} accent="text-blue-400" />
            <KpiTile label="Ad Revenue" value={fmtKES(kpi.total_ad_revenue)} accent="text-emerald-400" />
            <KpiTile label="ROAS" value={`${kpi.overall_roas.toFixed(2)}x`}
              accent={kpi.overall_roas >= 2 ? "text-emerald-400" : kpi.overall_roas >= 1.2 ? "text-yellow-400" : "text-red-400"} />
            <KpiTile label="Best Platform" value={kpi.best_ad_platform ?? "—"} accent="text-sky-400" />
          </div>
        </Section>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <Section title="Influencers" href="/dashboard/reports/marketing?tab=influencers">
          <div className="space-y-3">
            <KpiTile label="Active Influencers" value={fmt(kpi.active_influencers)} accent="text-pink-400" />
            <KpiTile label="Influencer Revenue" value={fmtKES(kpi.total_influencer_revenue)} accent="text-emerald-400" />
            <KpiTile label="Influencer ROI" value={`${kpi.influencer_roi.toFixed(2)}x`}
              accent={kpi.influencer_roi >= 2 ? "text-emerald-400" : "text-yellow-400"} />
          </div>
        </Section>

        <Section title="Social Media" href="/dashboard/reports/marketing?tab=social">
          <div className="space-y-3">
            <KpiTile label="Total Impressions" value={fmt(kpi.total_impressions)} accent="text-sky-400" />
            <KpiTile label="Total Engagements" value={fmt(kpi.total_engagements)} accent="text-indigo-400" />
            <KpiTile label="Engagement Rate" value={`${(kpi.avg_engagement_rate * 100).toFixed(2)}%`}
              accent={kpi.avg_engagement_rate > 0.03 ? "text-emerald-400" : "text-slate-200"} />
          </div>
        </Section>

        <Section title="CRM & Sentiment" href="/dashboard/reports/marketing?tab=crm">
          <div className="space-y-3">
            <KpiTile label="At-Risk Customers" value={fmt(kpi.at_risk_customers)} accent="text-orange-400" />
            <KpiTile label="VIP Customers" value={fmt(kpi.vip_customers)} accent="text-yellow-300" />
            <KpiTile label="Survey Sentiment" value={`${kpi.avg_survey_sentiment.toFixed(1)}/10`}
              accent={kpi.avg_survey_sentiment >= 7 ? "text-emerald-400" : kpi.avg_survey_sentiment >= 5 ? "text-yellow-400" : "text-red-400"} />
          </div>
        </Section>
      </div>

      {kpi.by_campaign_type.length > 0 && (
        <Section title="Campaign ROI by Type">
          <Card>
            <HBarChart
              data={kpi.by_campaign_type.map(d => ({ label: d.label, value: d.value }))}
              color="#6366f1"
              height={180}
              formatY={(v) => `${v.toFixed(1)}x`}
            />
          </Card>
        </Section>
      )}
    </div>
  );
}

// ── Tab: Campaigns ────────────────────────────────────────────────────────────

function CampaignsTab({ days }: { days: number }) {
  const { data, isLoading } = useQuery<MarketingCampaignsDetail>({
    queryKey: ["mkt-campaigns", days],
    queryFn: () => analyticsApi.mktCampaigns(days),
  });

  const STATUS_CLS: Record<string, string> = {
    COMPLETED: "text-emerald-400", ACTIVE: "text-blue-400",
    DRAFT: "text-slate-400", CANCELLED: "text-red-400", PAUSED: "text-yellow-400",
  };

  return (
    <div className="space-y-6">
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiTile label="Total Budget" value={fmtKES(data.total_budget)} accent="text-amber-400" />
          <KpiTile label="Total Revenue" value={fmtKES(data.total_revenue)} accent="text-emerald-400" />
          <KpiTile label="Avg ROI" value={`${data.avg_roi.toFixed(2)}x`} accent={data.avg_roi >= 1 ? "text-emerald-400" : "text-red-400"} />
          <KpiTile label="Campaigns" value={fmt(data.campaigns.length)} />
        </div>
      )}

      {data && (
        <Section title="Revenue by Type" href="/dashboard/marketing/campaigns">
          <Card>
            <HBarChart
              data={data.by_type}
              color="#10b981"
              height={160}
              formatY={fmtKES}
            />
          </Card>
        </Section>
      )}

      {data && (
        <Section title="Campaign Revenue Trend">
          <Card>
            <TrendLineChart data={data.revenue_trend} color="#10b981" formatY={fmtKES} />
          </Card>
        </Section>
      )}

      <Section title="Campaign List" href="/dashboard/marketing/campaigns">
        {isLoading ? <LoadingSkeleton rows={6} /> : data && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/50 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">Campaign</th>
                  <th className="px-3 py-2 text-left font-medium">Type</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                  <th className="px-3 py-2 text-left font-medium">Region</th>
                  <th className="px-3 py-2 text-right font-medium">Budget</th>
                  <th className="px-3 py-2 text-right font-medium">Revenue</th>
                  <th className="px-3 py-2 text-right font-medium">ROI</th>
                </tr>
              </thead>
              <tbody>
                {data.campaigns.slice(0, 20).map((c) => (
                  <tr key={c.id} className="border-t border-slate-700/30 hover:bg-slate-800/20 transition-colors">
                    <td className="px-3 py-2 text-slate-200 max-w-[180px] truncate">{c.campaign_name}</td>
                    <td className="px-3 py-2 text-slate-400">{c.campaign_type}</td>
                    <td className={`px-3 py-2 font-medium ${STATUS_CLS[c.status] ?? "text-slate-400"}`}>{c.status}</td>
                    <td className="px-3 py-2 text-slate-400">{c.region ?? "—"}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmtKES(c.budget)}</td>
                    <td className="px-3 py-2 text-right text-emerald-400">{fmtKES(c.actual_revenue)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${c.actual_roi >= 1 ? "text-emerald-400" : "text-red-400"}`}>
                      {c.actual_roi.toFixed(2)}x
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Tab: Spend ────────────────────────────────────────────────────────────────

function SpendTab({ kpi }: { kpi: MarketingBIKPIs }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiTile label="Trade Spend" value={fmtKES(kpi.total_trade_spend)} accent="text-orange-400" />
        <KpiTile label="Brand Spend" value={fmtKES(kpi.total_brand_spend)} accent="text-blue-400" />
        <KpiTile label="Trade vs Sales" value={`${kpi.trade_spend_vs_sales_pct.toFixed(1)}%`}
          sub="% of invoiced revenue"
          accent={kpi.trade_spend_vs_sales_pct > 15 ? "text-orange-400" : "text-slate-200"} />
        <KpiTile label="Brand vs Revenue" value={`${kpi.brand_spend_vs_revenue_pct.toFixed(1)}%`}
          sub="% of campaign revenue" />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Section title="Trade Spend Trend" href="/dashboard/marketing/trade-spend">
          <Card>
            <TrendLineChart data={kpi.trade_spend_trend} color="#f97316" formatY={fmtKES} />
          </Card>
        </Section>
        <Section title="Brand Spend Trend" href="/dashboard/marketing/brand-spend">
          <Card>
            <TrendLineChart data={kpi.brand_spend_trend} color="#3b82f6" formatY={fmtKES} />
          </Card>
        </Section>
      </div>

      <Section title="Attribution" href="/dashboard/marketing/sales">
        <div className="grid grid-cols-2 gap-3">
          <KpiTile label="Campaign-Linked Orders" value={fmt(kpi.campaign_linked_orders)}
            sub="Sales orders with campaign_id" accent="text-indigo-400" />
          <KpiTile label="Promotion-Linked Orders" value={fmt(kpi.promotion_linked_orders)}
            sub="Sales orders with promotion_id" accent="text-violet-400" />
        </div>
      </Section>

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-400">
        For full spend breakdown by trade type / brand category, view the{" "}
        <Link href="/dashboard/marketing/trade-spend" className="underline">Trade Spend</Link> and{" "}
        <Link href="/dashboard/marketing/brand-spend" className="underline">Brand Spend</Link> source pages.
      </div>
    </div>
  );
}

// ── Tab: Influencers ──────────────────────────────────────────────────────────

function InfluencersTab({ days }: { days: number }) {
  const { data, isLoading } = useQuery<MarketingInfluencersDetail>({
    queryKey: ["mkt-influencers", days],
    queryFn: () => analyticsApi.mktInfluencers(days),
  });

  return (
    <div className="space-y-6">
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiTile label="Total Revenue" value={fmtKES(data.total_revenue)} accent="text-emerald-400" />
          <KpiTile label="Total Fees" value={fmtKES(data.total_fees)} accent="text-orange-400" />
          <KpiTile label="Overall ROI" value={`${data.overall_roi.toFixed(2)}x`}
            accent={data.overall_roi >= 2 ? "text-emerald-400" : "text-yellow-400"} />
          <KpiTile label="Avg Score" value={data.avg_score.toFixed(1)} sub="/ 10" />
        </div>
      )}

      {data && data.by_platform.length > 0 && (
        <Section title="Revenue by Platform">
          <Card>
            <div className="space-y-2">
              {data.by_platform.map(p => (
                <BarRow key={p.label} label={p.label} value={p.value}
                  max={data.by_platform[0]?.value || 1} formatted={fmtKES(p.value)} />
              ))}
            </div>
          </Card>
        </Section>
      )}

      <Section title="Top Influencers" href="/dashboard/marketing/influencers">
        {isLoading ? <LoadingSkeleton rows={6} /> : data && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/50 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">Influencer</th>
                  <th className="px-3 py-2 text-left font-medium">Platform</th>
                  <th className="px-3 py-2 text-left font-medium">Category</th>
                  <th className="px-3 py-2 text-right font-medium">Followers</th>
                  <th className="px-3 py-2 text-right font-medium">Revenue</th>
                  <th className="px-3 py-2 text-right font-medium">Fee</th>
                  <th className="px-3 py-2 text-right font-medium">ROI</th>
                  <th className="px-3 py-2 text-right font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.influencers.map((inf) => (
                  <tr key={inf.id} className="border-t border-slate-700/30 hover:bg-slate-800/20 transition-colors">
                    <td className="px-3 py-2 text-slate-200">
                      <div>{inf.influencer_name}</div>
                      {inf.handle && <div className="text-slate-500">@{inf.handle}</div>}
                    </td>
                    <td className="px-3 py-2 text-pink-400">{inf.platform}</td>
                    <td className="px-3 py-2 text-slate-400">{inf.category ?? "—"}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmt(inf.followers_count)}</td>
                    <td className="px-3 py-2 text-right text-emerald-400">{fmtKES(inf.attributed_revenue)}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmtKES(inf.agreed_fee)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${inf.roi >= 2 ? "text-emerald-400" : inf.roi >= 1 ? "text-yellow-400" : "text-red-400"}`}>
                      {inf.roi.toFixed(2)}x
                    </td>
                    <td className="px-3 py-2 text-right text-slate-300">{inf.performance_score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Tab: Social ───────────────────────────────────────────────────────────────

function SocialTab({ days }: { days: number }) {
  const { data, isLoading } = useQuery<MarketingSocialDetail>({
    queryKey: ["mkt-social", days],
    queryFn: () => analyticsApi.mktSocial(days),
  });

  return (
    <div className="space-y-6">
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KpiTile label="Total Impressions" value={fmt(data.total_impressions)} accent="text-sky-400" />
          <KpiTile label="Total Engagements" value={fmt(data.total_engagements)} accent="text-indigo-400" />
          <KpiTile label="Avg Engagement Rate" value={`${(data.avg_engagement_rate * 100).toFixed(2)}%`}
            accent={data.avg_engagement_rate > 0.03 ? "text-emerald-400" : "text-slate-200"} />
        </div>
      )}

      {data && (
        <div className="grid md:grid-cols-2 gap-6">
          <Section title="Engagement Trend">
            <Card>
              <TrendLineChart data={data.engagement_trend} color="#6366f1" height={180} />
            </Card>
          </Section>
          <Section title="Impression Trend">
            <Card>
              <TrendLineChart data={data.impression_trend} color="#0ea5e9" height={180} />
            </Card>
          </Section>
        </div>
      )}

      <Section title="By Platform" href="/dashboard/marketing/social">
        {isLoading ? <LoadingSkeleton rows={4} /> : data && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/50 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">Platform</th>
                  <th className="px-3 py-2 text-right font-medium">Impressions</th>
                  <th className="px-3 py-2 text-right font-medium">Engagements</th>
                  <th className="px-3 py-2 text-right font-medium">Clicks</th>
                  <th className="px-3 py-2 text-right font-medium">Posts</th>
                  <th className="px-3 py-2 text-right font-medium">Eng. Rate</th>
                </tr>
              </thead>
              <tbody>
                {data.by_platform.map((p) => (
                  <tr key={p.platform} className="border-t border-slate-700/30 hover:bg-slate-800/20">
                    <td className="px-3 py-2 text-violet-400 font-medium">{p.platform}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmt(p.impressions)}</td>
                    <td className="px-3 py-2 text-right text-indigo-400">{fmt(p.engagements)}</td>
                    <td className="px-3 py-2 text-right text-slate-400">{fmt(p.clicks)}</td>
                    <td className="px-3 py-2 text-right text-slate-400">{fmt(p.post_count)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${p.engagement_rate > 0.03 ? "text-emerald-400" : "text-slate-300"}`}>
                      {(p.engagement_rate * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Tab: Ads ──────────────────────────────────────────────────────────────────

function AdsTab({ days }: { days: number }) {
  const { data, isLoading } = useQuery<MarketingAdsDetail>({
    queryKey: ["mkt-ads", days],
    queryFn: () => analyticsApi.mktAds(days),
  });

  return (
    <div className="space-y-6">
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KpiTile label="Total Ad Spend" value={fmtKES(data.total_spend)} accent="text-blue-400" />
          <KpiTile label="Total Ad Revenue" value={fmtKES(data.total_revenue)} accent="text-emerald-400" />
          <KpiTile label="Overall ROAS" value={`${data.overall_roas.toFixed(2)}x`}
            accent={data.overall_roas >= 2 ? "text-emerald-400" : data.overall_roas >= 1.2 ? "text-yellow-400" : "text-red-400"} />
        </div>
      )}

      {data && (
        <div className="grid md:grid-cols-2 gap-6">
          <Section title="Ad Spend Trend">
            <Card>
              <TrendLineChart data={data.spend_trend} color="#3b82f6" formatY={fmtKES} height={180} />
            </Card>
          </Section>
          <Section title="Ad Revenue Trend">
            <Card>
              <TrendLineChart data={data.revenue_trend} color="#10b981" formatY={fmtKES} height={180} />
            </Card>
          </Section>
        </div>
      )}

      <Section title="By Ad Platform" href="/dashboard/marketing/ads">
        {isLoading ? <LoadingSkeleton rows={4} /> : data && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/50 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">Platform</th>
                  <th className="px-3 py-2 text-right font-medium">Spend</th>
                  <th className="px-3 py-2 text-right font-medium">Revenue</th>
                  <th className="px-3 py-2 text-right font-medium">ROAS</th>
                  <th className="px-3 py-2 text-right font-medium">Impressions</th>
                  <th className="px-3 py-2 text-right font-medium">Clicks</th>
                  <th className="px-3 py-2 text-right font-medium">Conversions</th>
                </tr>
              </thead>
              <tbody>
                {data.by_platform.map((p) => (
                  <tr key={p.platform} className="border-t border-slate-700/30 hover:bg-slate-800/20">
                    <td className="px-3 py-2 text-blue-400 font-medium">{p.platform}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmtKES(p.spend)}</td>
                    <td className="px-3 py-2 text-right text-emerald-400">{fmtKES(p.revenue)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${p.roas >= 2 ? "text-emerald-400" : p.roas >= 1.2 ? "text-yellow-400" : "text-red-400"}`}>
                      {p.roas.toFixed(2)}x
                    </td>
                    <td className="px-3 py-2 text-right text-slate-400">{fmt(p.impressions)}</td>
                    <td className="px-3 py-2 text-right text-slate-400">{fmt(p.clicks)}</td>
                    <td className="px-3 py-2 text-right text-slate-400">{fmt(p.conversions)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Tab: E-commerce ───────────────────────────────────────────────────────────

function EcommerceTab({ days }: { days: number }) {
  const { data, isLoading } = useQuery<MarketingStoresDetail>({
    queryKey: ["mkt-stores", days],
    queryFn: () => analyticsApi.mktStores(days),
  });

  return (
    <div className="space-y-6">
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiTile label="E-com Revenue" value={fmtKES(data.total_revenue)} accent="text-teal-400" />
          <KpiTile label="Total Orders" value={fmt(data.total_orders)} />
          <KpiTile label="Avg Conversion" value={`${(data.avg_conversion_rate * 100).toFixed(1)}%`} />
          <KpiTile label="Avg Return Rate" value={`${(data.avg_return_rate * 100).toFixed(1)}%`}
            accent={data.avg_return_rate > 0.1 ? "text-red-400" : "text-slate-200"} />
        </div>
      )}

      {data && data.by_platform.length > 0 && (
        <Section title="Revenue by Platform">
          <Card>
            <div className="space-y-2">
              {data.by_platform.map(p => (
                <BarRow key={p.label} label={p.label} value={p.value}
                  max={data.by_platform[0]?.value || 1} formatted={fmtKES(p.value)} />
              ))}
            </div>
          </Card>
        </Section>
      )}

      {data && (
        <Section title="Revenue Trend">
          <Card>
            <TrendLineChart data={data.revenue_trend} color="#14b8a6" formatY={fmtKES} />
          </Card>
        </Section>
      )}

      <Section title="Top Stores" href="/dashboard/marketing/stores">
        {isLoading ? <LoadingSkeleton rows={6} /> : data && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/50 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">Store</th>
                  <th className="px-3 py-2 text-left font-medium">Platform</th>
                  <th className="px-3 py-2 text-left font-medium">Region</th>
                  <th className="px-3 py-2 text-right font-medium">Revenue</th>
                  <th className="px-3 py-2 text-right font-medium">Orders</th>
                  <th className="px-3 py-2 text-right font-medium">CVR</th>
                  <th className="px-3 py-2 text-right font-medium">Return Rate</th>
                </tr>
              </thead>
              <tbody>
                {data.stores.map((s) => (
                  <tr key={s.id} className="border-t border-slate-700/30 hover:bg-slate-800/20">
                    <td className="px-3 py-2 text-slate-200">{s.store_name}</td>
                    <td className="px-3 py-2 text-teal-400">{s.platform}</td>
                    <td className="px-3 py-2 text-slate-400">{s.region ?? "—"}</td>
                    <td className="px-3 py-2 text-right text-emerald-400">{fmtKES(s.total_revenue)}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmt(s.total_orders)}</td>
                    <td className="px-3 py-2 text-right text-slate-400">{(s.conversion_rate * 100).toFixed(1)}%</td>
                    <td className={`px-3 py-2 text-right ${s.return_rate > 0.1 ? "text-red-400" : "text-slate-400"}`}>
                      {(s.return_rate * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Tab: CRM ──────────────────────────────────────────────────────────────────

function CrmTab({ kpi }: { kpi: MarketingBIKPIs }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiTile label="CRM Profiles" value={fmt(kpi.total_crm_profiles)} />
        <KpiTile label="At-Risk" value={fmt(kpi.at_risk_customers)} accent="text-orange-400" sub="Churn risk ≥ 60" />
        <KpiTile label="VIP" value={fmt(kpi.vip_customers)} accent="text-yellow-300" />
        <KpiTile label="Avg Engagement" value={kpi.avg_engagement_score.toFixed(1)} sub="/ 100" />
        <KpiTile label="Survey Sentiment" value={`${kpi.avg_survey_sentiment.toFixed(1)}/10`}
          accent={kpi.avg_survey_sentiment >= 7 ? "text-emerald-400" : kpi.avg_survey_sentiment >= 5 ? "text-yellow-400" : "text-red-400"} />
        <KpiTile label="Surveys (period)" value={fmt(kpi.survey_count)} />
      </div>

      <Section title="Campaign-Linked Attribution">
        <div className="grid grid-cols-2 gap-3">
          <KpiTile label="Campaign-Linked Orders" value={fmt(kpi.campaign_linked_orders)}
            sub="Sales orders with campaign_id" accent="text-indigo-400" />
          <KpiTile label="Promotion-Linked Orders" value={fmt(kpi.promotion_linked_orders)}
            sub="Sales orders with promotion_id" accent="text-violet-400" />
        </div>
      </Section>

      {kpi.by_influencer_platform.length > 0 && (
        <Section title="Influencer Revenue by Platform">
          <Card>
            <div className="space-y-2">
              {kpi.by_influencer_platform.map(p => (
                <BarRow key={p.label} label={p.label} value={p.value}
                  max={kpi.by_influencer_platform[0]?.value || 1} formatted={fmtKES(p.value)} />
              ))}
            </div>
          </Card>
        </Section>
      )}

      <div className="flex gap-3 flex-wrap">
        <Link href="/dashboard/marketing/crm"
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800 transition-colors">
          CRM Profiles →
        </Link>
        <Link href="/dashboard/marketing/surveys"
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800 transition-colors">
          Survey Responses →
        </Link>
        <Link href="/dashboard/marketing/segments"
          className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800 transition-colors">
          Customer Segments →
        </Link>
      </div>
    </div>
  );
}

// ── Tab: Returns ──────────────────────────────────────────────────────────────

function ReturnsTab({ days }: { days: number }) {
  const { data, isLoading } = useQuery<MarketingReturnsDetail>({
    queryKey: ["mkt-returns", days],
    queryFn: () => analyticsApi.mktReturns(days),
  });

  return (
    <div className="space-y-6">
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KpiTile label="Total Returns" value={fmt(data.total_returns)} accent="text-red-400" />
          <KpiTile label="Avg Return Rate" value={`${(data.avg_return_rate * 100).toFixed(1)}%`}
            accent={data.avg_return_rate > 0.1 ? "text-red-400" : "text-slate-200"} />
          <KpiTile label="Return Reasons" value={fmt(data.by_reason.length)} sub="distinct reasons" />
        </div>
      )}

      {data && (
        <Section title="Returns Trend">
          <Card>
            <TrendLineChart data={data.trend} color="#ef4444" height={180} />
          </Card>
        </Section>
      )}

      {data && data.by_reason.length > 0 && (
        <Section title="Top Return Reasons">
          <Card>
            <div className="space-y-2">
              {data.by_reason.map(r => (
                <BarRow key={r.label} label={r.label} value={r.value}
                  max={data.by_reason[0]?.value || 1} formatted={fmt(r.count)} />
              ))}
            </div>
          </Card>
        </Section>
      )}

      <Section title="Return Log" href="/dashboard/marketing/returns">
        {isLoading ? <LoadingSkeleton rows={6} /> : data && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800/50 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">Date</th>
                  <th className="px-3 py-2 text-left font-medium">Reason</th>
                  <th className="px-3 py-2 text-right font-medium">Count</th>
                  <th className="px-3 py-2 text-right font-medium">Return Rate</th>
                </tr>
              </thead>
              <tbody>
                {data.returns.slice(0, 20).map((r, i) => (
                  <tr key={i} className="border-t border-slate-700/30 hover:bg-slate-800/20">
                    <td className="px-3 py-2 text-slate-400">{r.return_date}</td>
                    <td className="px-3 py-2 text-slate-300">{r.return_reason ?? "—"}</td>
                    <td className="px-3 py-2 text-right text-red-400">{r.return_count}</td>
                    <td className="px-3 py-2 text-right text-slate-400">{(r.return_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MarketingBIPage() {
  const [days, setDays] = useState(30);
  const [tab, setTab] = useState<TabId>("overview");

  const { data: kpi, isLoading, error } = useQuery<MarketingBIKPIs>({
    queryKey: ["analytics-marketing", days],
    queryFn: () => analyticsApi.marketing(days),
  });

  return (
    <div className="min-h-screen bg-[#0b1120] p-6 text-white">
      {/* Header */}
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Marketing BI</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Cross-module marketing KPIs — campaigns, spend, influencers, ads, social, e-commerce, CRM, surveys
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-slate-700 bg-[#131c2e] px-3 py-2 text-sm text-white shrink-0"
        >
          {[7, 14, 30, 60, 90].map((d) => (
            <option key={d} value={d}>Last {d} days</option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 overflow-x-auto rounded-xl border border-slate-700/50 bg-[#131c2e] p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={[
              "shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              tab === t.id
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200",
            ].join(" ")}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-800/50" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
          Failed to load marketing analytics. Check your permissions.
        </div>
      )}

      {/* Tab content */}
      {!isLoading && !error && kpi && (
        <>
          {tab === "overview"    && <OverviewTab kpi={kpi} days={days} />}
          {tab === "campaigns"  && <CampaignsTab days={days} />}
          {tab === "spend"      && <SpendTab kpi={kpi} />}
          {tab === "influencers" && <InfluencersTab days={days} />}
          {tab === "social"     && <SocialTab days={days} />}
          {tab === "ads"        && <AdsTab days={days} />}
          {tab === "ecommerce"  && <EcommerceTab days={days} />}
          {tab === "crm"        && <CrmTab kpi={kpi} />}
          {tab === "returns"    && <ReturnsTab days={days} />}
        </>
      )}
    </div>
  );
}
