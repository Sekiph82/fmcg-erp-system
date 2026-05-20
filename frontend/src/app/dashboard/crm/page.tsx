"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, CRMDashboard, fmtCurrency, STATUS_COLORS, TEMPERATURE_COLORS } from "@/lib/crm_pipeline";

function CRMDashboardTab() {
  const [data, setData] = useState<CRMDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    crmApi.getDashboard().then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading CRM Dashboard…</div>;
  if (!data) return <div className="p-6 text-red-500">Failed to load dashboard.</div>;

  const kpis = [
    { label: "Total Leads", value: data.total_leads, color: "bg-blue-50 border-blue-200", text: "text-blue-700" },
    { label: "Opportunities", value: data.total_opportunities, color: "bg-purple-50 border-purple-200", text: "text-purple-700" },
    { label: "Open Records", value: data.open_records, color: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
    { label: "Won This Month", value: data.won_this_month, color: "bg-green-50 border-green-200", text: "text-green-700" },
    { label: "Lost This Month", value: data.lost_this_month, color: "bg-red-50 border-red-200", text: "text-red-700" },
    { label: "Hot Records", value: data.hot_records, color: "bg-orange-50 border-orange-200", text: "text-orange-700" },
    { label: "Overdue Activities", value: data.overdue_activities, color: "bg-yellow-50 border-yellow-200", text: "text-yellow-700" },
    { label: "Win Rate", value: `${data.conversion_rate_pct}%`, color: "bg-indigo-50 border-indigo-200", text: "text-indigo-700" },
  ];

  const quickLinks = [
    { href: "/dashboard/crm/leads", label: "Lead List" },
    { href: "/dashboard/crm/opportunities", label: "Opportunities" },
    { href: "/dashboard/crm/pipeline", label: "Pipeline Board" },
    { href: "/dashboard/crm/activities", label: "Activity Timeline" },
    { href: "/dashboard/crm/forecast", label: "Forecast" },
    { href: "/dashboard/crm/win-loss", label: "Win/Loss Analysis" },
    { href: "/dashboard/crm?tab=pipeline", label: "Overdue Queue" },
    { href: "/dashboard/crm?tab=overview", label: "AI Agents" },
    { href: "/dashboard/crm/stages", label: "Stage Config" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CRM Pipeline</h1>
          <p className="text-gray-500 text-sm mt-0.5">Sales intelligence from lead capture to won deal</p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/crm/leads" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + New Lead
          </Link>
          <Link href="/dashboard/crm/pipeline" className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
            Pipeline Board
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className={`rounded-xl border p-4 ${k.color}`}>
            <div className="text-xs text-gray-500 mb-1">{k.label}</div>
            <div className={`text-2xl font-bold ${k.text}`}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Revenue Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <div className="text-xs text-gray-500">Total Pipeline Value</div>
          <div className="text-xl font-bold text-gray-800 mt-1">{fmtCurrency(data.total_pipeline_value)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <div className="text-xs text-gray-500">Weighted Pipeline</div>
          <div className="text-xl font-bold text-indigo-700 mt-1">{fmtCurrency(data.weighted_pipeline_value)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <div className="text-xs text-gray-500">Avg Deal Size</div>
          <div className="text-xl font-bold text-gray-800 mt-1">{fmtCurrency(data.avg_deal_size)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Stage Distribution */}
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Pipeline by Stage</h2>
          <div className="space-y-2">
            {data.stage_distribution.length === 0 && (
              <p className="text-sm text-gray-400">No open records</p>
            )}
            {data.stage_distribution.map((s) => (
              <div key={s.stage} className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: s.color || "#6B7280" }} />
                <div className="flex-1 text-sm text-gray-700">{s.stage}</div>
                <div className="text-sm font-medium text-gray-500">{s.count}</div>
                <div className="text-sm text-gray-400">{fmtCurrency(s.value)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Reps */}
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Top Reps by Pipeline</h2>
          <div className="space-y-2">
            {data.top_reps.length === 0 && (
              <p className="text-sm text-gray-400">No assigned records</p>
            )}
            {data.top_reps.map((rep, i) => (
              <div key={rep.rep} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </div>
                <div className="flex-1 text-sm text-gray-700">{rep.rep}</div>
                <div className="text-sm text-gray-500">{rep.count} deals</div>
                <div className="text-sm font-medium text-indigo-700">{fmtCurrency(rep.value)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Quick Links</h2>
        <div className="flex flex-wrap gap-2">
          {quickLinks.map((l) => (
            <Link key={l.href} href={l.href}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700">
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

const CRMPipelinePage    = dynamic(() => import("@/app/dashboard/crm/pipeline/page"),    { ssr: false });
const CRMLeadsPage       = dynamic(() => import("@/app/dashboard/crm/leads/page"),       { ssr: false });
const CRMOppsPage        = dynamic(() => import("@/app/dashboard/crm/opportunities/page"),{ ssr: false });
const CRMActivitiesPage  = dynamic(() => import("@/app/dashboard/crm/activities/page"),  { ssr: false });
const CRMForecastPage    = dynamic(() => import("@/app/dashboard/crm/forecast/page"),    { ssr: false });
const CRMTerritoryPage   = dynamic(() => import("@/app/dashboard/crm/territory/page"),   { ssr: false });
const CRMStagesPage      = dynamic(() => import("@/app/dashboard/crm/stages/page"),      { ssr: false });
const CRMWinLossPage     = dynamic(() => import("@/app/dashboard/crm/win-loss/page"),    { ssr: false });
const LoyaltyPage        = dynamic(() => import("@/app/dashboard/loyalty/page"),         { ssr: false });
const NPSPage            = dynamic(() => import("@/app/dashboard/nps/page"),             { ssr: false });
const SurveysPage        = dynamic(() => import("@/app/dashboard/surveys/page"),         { ssr: false });

export default function CRMPage() {
  const tabs = [
    { key: "overview",    label: "Overview",    permission: "crm.view", content: <CRMDashboardTab /> },
    { key: "pipeline",    label: "Pipeline",    permission: "crm.view", content: <CRMPipelinePage /> },
    { key: "leads",       label: "Leads",       permission: "crm.view", content: <CRMLeadsPage /> },
    { key: "opportunities",label:"Opportunities",permission: "crm.view", content: <CRMOppsPage /> },
    { key: "activities",  label: "Activities",  permission: "crm.view", content: <CRMActivitiesPage /> },
    { key: "forecast",    label: "Forecast",    permission: "crm.view", content: <CRMForecastPage /> },
    { key: "territory",   label: "Territory",   permission: "crm.view", content: <CRMTerritoryPage /> },
    { key: "stages",      label: "Stages",      permission: "crm.view", content: <CRMStagesPage /> },
    { key: "win-loss",    label: "Win / Loss",  permission: "crm.view", content: <CRMWinLossPage /> },
    { key: "loyalty",     label: "Loyalty",     permission: "crm.view", content: <LoyaltyPage /> },
    { key: "nps",         label: "NPS",         permission: "crm.view", content: <NPSPage /> },
    { key: "surveys",     label: "Surveys",     permission: "crm.view", content: <SurveysPage /> },
  ];
  return (
    <ModuleWorkspace
      title="CRM"
      description="Pipeline, leads, opportunities, forecast, loyalty, NPS"
      permission="crm.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
