"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketingApi } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx } from "@/lib/i18n/core";

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

export default function MarketingAnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data, isLoading } = useQuery({
    queryKey: ["marketing-analytics", days],
    queryFn: () => marketingApi.analytics.summary(days).then((r) => r.data),
  });

  return (
    <RequirePermission permission="marketing_analytics.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">{tx("Marketing Analytics")}</h1>
            <p className="text-slate-400 text-sm mt-1">{tx("Consolidated KPIs across all marketing channels")}</p>
          </div>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
          >
            {[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{tx("Last")} {d} {tx("days")}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">{tx("Loading...")}</p>
        ) : data ? (
          <div className="space-y-8">
            {/* Spend overview */}
            <section>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("Spend Overview")}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI label={tx("Total Spend")} value={`KES ${Number(data.total_spend).toLocaleString()}`} />
                <KPI label={tx("Trade Spend")} value={`KES ${Number(data.total_trade_spend).toLocaleString()}`} />
                <KPI label={tx("Brand Spend")} value={`KES ${Number(data.total_brand_spend).toLocaleString()}`} />
                <KPI label={tx("Ad Spend")} value={`KES ${Number(data.total_ad_spend).toLocaleString()}`} />
              </div>
            </section>

            {/* Revenue & ROI */}
            <section>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("Revenue & ROI")}</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <KPI label={tx("Campaign Revenue")} value={`KES ${Number(data.campaign_revenue).toLocaleString()}`} color="text-emerald-400" />
                <KPI
                  label={tx("Overall Marketing ROI")}
                  value={data.total_spend > 0 ? `${(data.campaign_revenue / data.total_spend).toFixed(2)}x` : "—"}
                  color={data.total_spend > 0 && data.campaign_revenue / data.total_spend >= 2 ? "text-emerald-400" : "text-yellow-400"}
                />
                <KPI label={tx("Avg Campaign ROI")} value={`${Number(data.campaign_roi_avg).toFixed(2)}x`} color="text-sky-400" />
              </div>
            </section>

            {/* Campaigns */}
            <section>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("Campaigns")}</h2>
              <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
                <KPI label={tx("Active Campaigns")} value={data.active_campaigns} color="text-emerald-400" />
                <KPI label={tx("Active Influencers")} value={data.active_influencers} />
              </div>
            </section>

            {/* CRM */}
            <section>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("CRM & Customer Health")}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI label={tx("CRM Profiles")} value={data.crm_profiles} />
                <KPI label={tx("VIP Customers")} value={data.vip_customers} color="text-yellow-300" />
                <KPI
                  label={tx("At-Risk Customers")}
                  value={data.at_risk_customers}
                  color={data.at_risk_customers > 0 ? "text-orange-400" : "text-white"}
                  sub="need engagement"
                />
                <KPI label={tx("Field Visits")} value={data.visits_this_period} sub={`last ${data.period_days}d`} />
              </div>
            </section>

            {/* E-commerce */}
            <section>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">{tx("E-commerce")}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <KPI label={tx("Store GMV")} value={`KES ${Number(data.store_gmv).toLocaleString()}`} color="text-sky-400" sub="gross merchandise value" />
              </div>
            </section>
          </div>
        ) : (
          <p className="text-slate-400">{tx("No data available.")}</p>
        )}
      </div>
    </RequirePermission>
  );
}
