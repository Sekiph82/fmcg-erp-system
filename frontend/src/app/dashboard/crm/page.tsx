"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, CRMDashboard, fmtCurrency, STATUS_COLORS, TEMPERATURE_COLORS } from "@/lib/crm_pipeline";
import { tx } from "@/lib/i18n/core";

function CRMDashboardTab() {
  const [data, setData] = useState<CRMDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    crmApi.getDashboard().then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">{tx("Loading CRM Dashboard…")}</div>;
  if (!data) return <div className="p-6 text-red-500">{tx("Failed to load dashboard.")}</div>;

  const kpis = [
    { label: tx("Total Leads"), value: data.total_leads, color: "bg-blue-50 border-blue-200", text: "text-blue-700" },
    { label: tx("Opportunities"), value: data.total_opportunities, color: "bg-purple-50 border-purple-200", text: "text-purple-700" },
    { label: tx("Open Records"), value: data.open_records, color: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
    { label: tx("Won This Month"), value: data.won_this_month, color: "bg-green-50 border-green-200", text: "text-green-700" },
    { label: tx("Lost This Month"), value: data.lost_this_month, color: "bg-red-50 border-red-200", text: "text-red-700" },
    { label: tx("Hot Records"), value: data.hot_records, color: "bg-orange-50 border-orange-200", text: "text-orange-700" },
    { label: tx("Overdue Activities"), value: data.overdue_activities, color: "bg-yellow-50 border-yellow-200", text: "text-yellow-700" },
    { label: tx("Win Rate"), value: `${data.conversion_rate_pct}%`, color: "bg-indigo-50 border-indigo-200", text: "text-indigo-700" },
  ];

  const quickLinks = [
    { href: "/dashboard/crm/leads", label: tx("Lead List") },
    { href: "/dashboard/crm/opportunities", label: tx("Opportunities") },
    { href: "/dashboard/crm/pipeline", label: tx("Pipeline Board") },
    { href: "/dashboard/crm/activities", label: tx("Activity Timeline") },
    { href: "/dashboard/crm/forecast", label: tx("Forecast") },
    { href: "/dashboard/crm/funnel", label: tx("Funnel Analytics") },
    { href: "/dashboard/crm/scoring", label: tx("Lead Scoring") },
    { href: "/dashboard/crm/lead-forms", label: tx("Website Lead Forms") },
    { href: "/dashboard/crm/automation", label: tx("Automation") },
    { href: "/dashboard/crm/inbox", label: tx("Conversations Inbox") },
    { href: "/dashboard/crm/outbox", label: tx("E-mail Outbox & Consent") },
    { href: "/dashboard/crm/sequences", label: tx("Sales Sequences") },
    { href: "/dashboard/crm/email-campaigns", label: tx("E-mail Campaigns") },
    { href: "/dashboard/crm/win-loss", label: tx("Win/Loss Analysis") },
    { href: "/dashboard/crm?tab=pipeline", label: tx("Overdue Queue") },
    { href: "/dashboard/crm?tab=overview", label: tx("AI Agents") },
    { href: "/dashboard/crm/stages", label: tx("Stage Config") },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("CRM Pipeline")}</h1>
          <p className="text-gray-500 text-sm mt-0.5">{tx("Sales intelligence from lead capture to won deal")}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/crm/leads" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {tx("+ New Lead")}
          </Link>
          <Link href="/dashboard/crm/pipeline" className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
            {tx("Pipeline Board")}
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
          <div className="text-xs text-gray-500">{tx("Total Pipeline Value")}</div>
          <div className="text-xl font-bold text-gray-800 mt-1">{fmtCurrency(data.total_pipeline_value)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <div className="text-xs text-gray-500">{tx("Weighted Pipeline")}</div>
          <div className="text-xl font-bold text-indigo-700 mt-1">{fmtCurrency(data.weighted_pipeline_value)}</div>
        </div>
        <div className="bg-white rounded-xl border p-4 shadow-sm">
          <div className="text-xs text-gray-500">{tx("Avg Deal Size")}</div>
          <div className="text-xl font-bold text-gray-800 mt-1">{fmtCurrency(data.avg_deal_size)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Stage Distribution */}
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">{tx("Pipeline by Stage")}</h2>
          <div className="space-y-2">
            {data.stage_distribution.length === 0 && (
              <p className="text-sm text-gray-400">{tx("No open records")}</p>
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
          <h2 className="font-semibold text-gray-800 mb-3">{tx("Top Reps by Pipeline")}</h2>
          <div className="space-y-2">
            {data.top_reps.length === 0 && (
              <p className="text-sm text-gray-400">{tx("No assigned records")}</p>
            )}
            {data.top_reps.map((rep, i) => (
              <div key={rep.rep} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </div>
                <div className="flex-1 text-sm text-gray-700">{rep.rep}</div>
                <div className="text-sm text-gray-500">{rep.count} {tx("deals")}</div>
                <div className="text-sm font-medium text-indigo-700">{fmtCurrency(rep.value)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <h2 className="font-semibold text-gray-800 mb-3">{tx("Quick Links")}</h2>
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
const CRMFunnelPage      = dynamic(() => import("@/app/dashboard/crm/funnel/page"),      { ssr: false });
const CRMScoringPage     = dynamic(() => import("@/app/dashboard/crm/scoring/page"),     { ssr: false });
const CRMLeadFormsPage   = dynamic(() => import("@/app/dashboard/crm/lead-forms/page"),  { ssr: false });
const CRMAutomationPage  = dynamic(() => import("@/app/dashboard/crm/automation/page"),  { ssr: false });
const CRMOutboxPage      = dynamic(() => import("@/app/dashboard/crm/outbox/page"),      { ssr: false });
const CRMEngagementPage  = dynamic(() => import("@/app/dashboard/crm/engagement/page"),  { ssr: false });
const CRMQuotasPage      = dynamic(() => import("@/app/dashboard/crm/quotas/page"),      { ssr: false });
const CRMPlaybooksPage   = dynamic(() => import("@/app/dashboard/crm/playbooks/page"),   { ssr: false });
const CRMContactsPage    = dynamic(() => import("@/app/dashboard/crm/contacts/page"),    { ssr: false });
const CRMViewsPage       = dynamic(() => import("@/app/dashboard/crm/views/page"),       { ssr: false });
const CRMWorkspacePage   = dynamic(() => import("@/app/dashboard/crm/workspace/page"),   { ssr: false });
const CRMRoutingPage     = dynamic(() => import("@/app/dashboard/crm/routing/page"),     { ssr: false });
const MsgChannelsPage    = dynamic(() => import("@/app/dashboard/crm/messaging-channels/page"), { ssr: false });
const SuccessPage        = dynamic(() => import("@/app/dashboard/crm/success/page"), { ssr: false });
const AIAccessPage       = dynamic(() => import("@/app/dashboard/crm/ai-access/page"), { ssr: false });
const DataHubPage        = dynamic(() => import("@/app/dashboard/crm/data-hub/page"), { ssr: false });
const DuplicatesPage     = dynamic(() => import("@/app/dashboard/crm/duplicates/page"), { ssr: false });
const ObjectsPage        = dynamic(() => import("@/app/dashboard/crm/objects/page"), { ssr: false });
const SensitivePage      = dynamic(() => import("@/app/dashboard/crm/sensitive/page"), { ssr: false });
const SalesDocsPage      = dynamic(() => import("@/app/dashboard/crm/sales-docs/page"), { ssr: false });
const PlatformDepthPage  = dynamic(() => import("@/app/dashboard/crm/platform-depth/page"), { ssr: false });   // M47
const DataSyncPage       = dynamic(() => import("@/app/dashboard/crm/data-sync/page"), { ssr: false });
const ProspectingPage    = dynamic(() => import("@/app/dashboard/crm/prospecting/page"), { ssr: false });   // M50.S01.T001-T004
const AddinSessionsPage  = dynamic(() => import("@/app/dashboard/crm/addin-sessions/page"), { ssr: false });   // M50.S01.T011
const SocialPage         = dynamic(() => import("@/app/dashboard/crm/social/page"), { ssr: false });
const AdsPage            = dynamic(() => import("@/app/dashboard/crm/ads/page"), { ssr: false });
const AudiencesPage      = dynamic(() => import("@/app/dashboard/crm/audiences/page"), { ssr: false });
const WebAnalyticsPage   = dynamic(() => import("@/app/dashboard/crm/web-analytics/page"), { ssr: false });
const EmailDesignerPage  = dynamic(() => import("@/app/dashboard/crm/email-designer/page"), { ssr: false });
const CRMInboxPage       = dynamic(() => import("@/app/dashboard/crm/inbox/page"),       { ssr: false });
const CRMLandingPages = dynamic(() => import("@/app/dashboard/crm/landing/page"), { ssr: false });
const CRMInsights = dynamic(() => import("@/app/dashboard/crm/insights/page"), { ssr: false });
const CRMWorkflows = dynamic(() => import("@/app/dashboard/crm/workflows/page"), { ssr: false });
const CRMABMPage = dynamic(() => import("@/app/dashboard/crm/abm/page"), { ssr: false });
const CRMAttributionPage = dynamic(() => import("@/app/dashboard/crm/attribution/page"), { ssr: false });
const CRMSequencesPage   = dynamic(() => import("@/app/dashboard/crm/sequences/page"),   { ssr: false });
const CRMCampaignsPage   = dynamic(() => import("@/app/dashboard/crm/email-campaigns/page"), { ssr: false });
const LoyaltyPage        = dynamic(() => import("@/app/dashboard/loyalty/page"),         { ssr: false });
const NPSPage            = dynamic(() => import("@/app/dashboard/nps/page"),             { ssr: false });
const SurveysPage        = dynamic(() => import("@/app/dashboard/surveys/page"),         { ssr: false });

export default function CRMPage() {
  const tabs = [
    { key: "overview",    label: tx("Overview"),    permission: "crm.view", content: <CRMDashboardTab /> },
    { key: "workspace",   label: tx("My work"),     permission: "crm.view", content: <CRMWorkspacePage /> },
    { key: "pipeline",    label: tx("Pipeline"),    permission: "crm.view", content: <CRMPipelinePage /> },
    { key: "contacts",    label: tx("Contacts"),    permission: "crm.view", content: <CRMContactsPage /> },
    { key: "leads",       label: tx("Leads"),       permission: "crm.view", content: <CRMLeadsPage /> },
    { key: "opportunities",label:tx("Opportunities"),permission: "crm.view", content: <CRMOppsPage /> },
    { key: "activities",  label: tx("Activities"),  permission: "crm.view", content: <CRMActivitiesPage /> },
    { key: "forecast",    label: tx("Forecast"),    permission: "crm.view", content: <CRMForecastPage /> },
    { key: "quotas",      label: tx("Quotas"),      permission: "crm.view", content: <CRMQuotasPage /> },
    { key: "playbooks",   label: tx("Playbooks"),   permission: "crm.view", content: <CRMPlaybooksPage /> },
    { key: "territory",   label: tx("Territory"),   permission: "crm.view", content: <CRMTerritoryPage /> },
    { key: "stages",      label: tx("Stages"),      permission: "crm.view", content: <CRMStagesPage /> },
    { key: "views",       label: tx("Teams & views"), permission: "crm.view", content: <CRMViewsPage /> },
    { key: "win-loss",    label: tx("Win / Loss"),  permission: "crm.view", content: <CRMWinLossPage /> },
    { key: "funnel",      label: tx("Funnel"),      permission: "crm.view", content: <CRMFunnelPage /> },
    { key: "attribution", label: tx("Attribution"), permission: "crm.view_all", content: <CRMAttributionPage /> },
    { key: "abm", label: tx("Key accounts"), permission: "crm.view_all", content: <CRMABMPage /> },
    { key: "landing", label: tx("Landing pages"), permission: "marketing.view", content: <CRMLandingPages /> },
    { key: "insights", label: tx("Conversation insights"), permission: "crm.view", content: <CRMInsights /> },
    { key: "workflows", label: tx("Workflows"), permission: "crm.view_all", content: <CRMWorkflows /> },
    { key: "scoring",     label: tx("Lead Scoring"), permission: "crm.view", content: <CRMScoringPage /> },
    { key: "lead-forms",  label: tx("Lead Forms"),  permission: "crm.view", content: <CRMLeadFormsPage /> },
    { key: "automation",  label: tx("Automation"),  permission: "crm.view", content: <CRMAutomationPage /> },
    { key: "routing",     label: tx("Routing & approvals"), permission: "crm.view", content: <CRMRoutingPage /> },
    { key: "inbox",       label: tx("Inbox"),       permission: "crm.view", content: <CRMInboxPage /> },
    { key: "outbox",      label: tx("E-mail"),      permission: "crm.view", content: <CRMOutboxPage /> },
    { key: "engagement",  label: tx("Engagement"),  permission: "crm.view", content: <CRMEngagementPage /> },
    { key: "sequences",   label: tx("Sequences"),   permission: "crm.view", content: <CRMSequencesPage /> },
    { key: "email-campaigns", label: tx("Campaigns"), permission: "crm.view", content: <CRMCampaignsPage /> },
    { key: "email-designer", label: tx("E-mail designer"), permission: "marketing.view", content: <EmailDesignerPage /> },
    { key: "web-analytics", label: tx("Website analytics"), permission: "marketing.view", content: <WebAnalyticsPage /> },
    { key: "audiences", label: tx("Audiences"), permission: "marketing.view", content: <AudiencesPage /> },
    { key: "ads", label: tx("Ads"), permission: "marketing.view", content: <AdsPage /> },
    { key: "social", label: tx("Social"), permission: "marketing.view", content: <SocialPage /> },
    { key: "channels", label: tx("Messaging channels"), permission: "crm.view", content: <MsgChannelsPage /> },
    { key: "success", label: tx("Customer success"), permission: "crm.view", content: <SuccessPage /> },
    { key: "data-hub", label: tx("Prospecting & data"), permission: "crm.view", content: <DataHubPage /> },
    { key: "prospecting", label: tx("Prospecting agent"), permission: "crm.view", content: <ProspectingPage /> },
    { key: "addin-sessions", label: tx("Mail add-in sessions"), permission: "crm.view", content: <AddinSessionsPage /> },
    { key: "duplicates", label: tx("Duplicates"), permission: "crm.view_all", content: <DuplicatesPage /> },
    { key: "data-sync", label: tx("Data sync & quality"), permission: "crm.view", content: <DataSyncPage /> },
    { key: "objects", label: tx("Custom objects"), permission: "crm.view", content: <ObjectsPage /> },
    { key: "sales-docs", label: tx("Sales documents"), permission: "crm.view", content: <SalesDocsPage /> },
    { key: "sensitive", label: tx("Sensitive data"), permission: "roles.manage", content: <SensitivePage /> },
    { key: "ai-access", label: tx("Add-ins & AI access"), permission: "crm.view", content: <AIAccessPage /> },
    { key: "platform-depth", label: tx("Platform settings"), permission: "crm.edit_all", content: <PlatformDepthPage /> },
    { key: "loyalty",     label: tx("Loyalty"),     permission: "crm.view", content: <LoyaltyPage /> },
    { key: "nps",         label: "NPS",         permission: "crm.view", content: <NPSPage /> },
    { key: "surveys",     label: tx("Surveys"),     permission: "crm.view", content: <SurveysPage /> },
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
