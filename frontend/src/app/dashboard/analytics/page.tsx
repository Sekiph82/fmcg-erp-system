"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt, DailyKPIs } from "@/lib/analytics";
import { KPICard } from "@/components/dashboard/KPICard";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx, lx } from "@/lib/i18n/core";

const MODULES = lx(() => [
  {
    href: "/dashboard/analytics/inventory",
    label: tx("Inventory"),
    icon: "📦",
    color: "bg-blue-50 border-blue-200",
    textColor: "text-blue-700",
    desc: tx("Stock value, movements, low stock"),
    permission: "inventory.view",
  },
  {
    href: "/dashboard/analytics/production",
    label: tx("Production"),
    icon: "🏭",
    color: "bg-emerald-50 border-emerald-200",
    textColor: "text-emerald-700",
    desc: tx("Plan vs actual, downtime, rejections"),
    permission: "production.view",
  },
  {
    href: "/dashboard/analytics/procurement",
    label: tx("Procurement"),
    icon: "🛒",
    color: "bg-purple-50 border-purple-200",
    textColor: "text-purple-700",
    desc: tx("PO status, delays, supplier spend"),
    permission: "procurement.view",
  },
  {
    href: "/dashboard/analytics/sales",
    label: tx("Sales"),
    icon: "📈",
    color: "bg-orange-50 border-orange-200",
    textColor: "text-orange-700",
    desc: tx("Revenue, orders, overdue invoices"),
    permission: "sales.view",
  },
  {
    href: "/dashboard/analytics/finance",
    label: tx("Finance"),
    icon: "💰",
    color: "bg-yellow-50 border-yellow-200",
    textColor: "text-yellow-700",
    desc: tx("Cash, receivables, payables"),
    permission: "finance.view",
  },
  {
    href: "/dashboard/analytics/payments",
    label: tx("Payments / M-Pesa"),
    icon: "📱",
    color: "bg-green-50 border-green-200",
    textColor: "text-green-700",
    desc: tx("Collections, success rate, failures"),
    permission: "mpesa.view_transactions",
  },
]);

function KPISkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 animate-pulse">
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="h-20 bg-slate-800/50 rounded-xl" />
      ))}
    </div>
  );
}

function KPIGrid({ d }: { d: DailyKPIs }) {
  const prodStatus = d.production_completion_pct >= 90
    ? "ok" : d.production_completion_pct >= 70
    ? "warning" : "critical";

  const mpesaStatus = d.mpesa_success_rate >= 95
    ? "ok" : d.mpesa_success_rate >= 80
    ? "warning" : "critical";

  return (
    <div className="grid grid-cols-2 gap-3">
      <KPICard
        label={tx("Today Sales")}
        value={fmtKES(d.daily_sales_amount)}
        subtext={`${d.daily_sales_orders} orders`}
        status="ok"
        trend={d.sales_trend_7d}
        href="/dashboard/analytics/sales"
      />
      <KPICard
        label={tx("Stock Value")}
        value={fmtKES(d.stock_value)}
        subtext={`${d.low_stock_count} low stock`}
        status={d.low_stock_count > 5 ? "warning" : "ok"}
        href="/dashboard/analytics/inventory"
      />
      <KPICard
        label={tx("Low Stock Items")}
        value={d.low_stock_count}
        subtext={`${d.zero_stock_count} zero stock`}
        status={d.low_stock_count > 5 ? "critical" : d.low_stock_count > 0 ? "warning" : "ok"}
        href="/dashboard/analytics/inventory"
      />
      <KPICard
        label={tx("Production vs Plan")}
        value={`${fmt(d.production_completion_pct, 1)}%`}
        subtext={`${fmtKES(d.production_actual_qty)} / ${fmtKES(d.production_plan_qty)} units`}
        status={prodStatus}
        trend={d.production_trend_7d}
        href="/dashboard/analytics/production"
      />
      <KPICard
        label={tx("Purchase Delays")}
        value={d.purchase_delay_count}
        subtext="POs past delivery date"
        status={d.purchase_delay_count > 3 ? "critical" : d.purchase_delay_count > 0 ? "warning" : "ok"}
        href="/dashboard/analytics/procurement"
      />
      <KPICard
        label={tx("Collections Today")}
        value={fmtKES(d.payment_collection_today)}
        subtext={`${d.failed_payment_count} failed payments`}
        status={d.failed_payment_count > 0 ? "warning" : "ok"}
        href="/dashboard/analytics/payments"
      />
      <KPICard
        label={tx("M-Pesa Today")}
        value={fmtKES(d.mpesa_collected_today)}
        subtext={`${fmt(d.mpesa_success_rate, 1)}% success rate`}
        status={mpesaStatus}
        trend={d.mpesa_trend_7d}
        href="/dashboard/analytics/payments"
      />
      <KPICard
        label={tx("Open Receivables")}
        value={fmtKES(d.open_receivables)}
        subtext={`${fmtKES(d.open_receivables_overdue)} overdue`}
        status={d.open_receivables_overdue > 0 ? "warning" : "ok"}
        href="/dashboard/analytics/finance"
      />
      <KPICard
        label={tx("Machines Down")}
        value={d.machines_down}
        subtext={`${d.open_breakdowns} open breakdowns`}
        status={d.machines_down >= 3 ? "critical" : d.machines_down > 0 ? "warning" : "ok"}
        href="/dashboard/production"
      />
    </div>
  );
}

function AnalyticsHubTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-kpi-daily"],
    queryFn: analyticsApi.kpiDaily,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  return (
    <RequirePermission permission="analytics.view">
      <div className="max-w-2xl mx-auto space-y-6 pb-10">
        <div>
          <h1 className="text-xl font-bold text-slate-100">{tx("Analytics & BI")}</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            {data ? `Updated ${new Date(data.as_of).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : tx("Daily KPI snapshot")}
          </p>
        </div>

        {/* Daily KPI Grid */}
        <section>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
            {tx("Today's KPIs")}
          </p>
          {isLoading || !data ? <KPISkeleton /> : <KPIGrid d={data} />}
        </section>

        {/* Module dashboards */}
        <section>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
            {tx("Module Dashboards")}
          </p>
          <div className="grid grid-cols-2 gap-3">
            {MODULES.map((m) => (
              <Link
                key={m.href}
                href={m.href}
                className={`rounded-xl border p-4 ${m.color} hover:shadow-md transition-shadow active:scale-[0.98]`}
              >
                <div className="text-2xl mb-1">{m.icon}</div>
                <p className={`font-semibold text-sm ${m.textColor}`}>{m.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{m.desc}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </RequirePermission>
  );
}

const AnalyticsInventoryPage  = dynamic(() => import("@/app/dashboard/analytics/inventory/page"),  { ssr: false });
const AnalyticsSalesPage      = dynamic(() => import("@/app/dashboard/analytics/sales/page"),      { ssr: false });
const AnalyticsProductionPage = dynamic(() => import("@/app/dashboard/analytics/production/page"), { ssr: false });
const AnalyticsProcurementPage= dynamic(() => import("@/app/dashboard/analytics/procurement/page"),{ ssr: false });
const AnalyticsFinancePage    = dynamic(() => import("@/app/dashboard/analytics/finance/page"),    { ssr: false });
const AnalyticsPaymentsPage   = dynamic(() => import("@/app/dashboard/analytics/payments/page"),   { ssr: false });
const ReportsPage             = dynamic(() => import("@/app/dashboard/reports/page"),              { ssr: false });
const ReportBuilderPage       = dynamic(() => import("@/app/dashboard/report-builder/page"),       { ssr: false });

export default function AnalyticsPage() {
  const tabs = [
    { key: "overview",     label: tx("Overview"),     permission: "analytics.view", content: <AnalyticsHubTab /> },
    { key: "inventory",    label: tx("Inventory"),    permission: "inventory.view", exact: true, content: <AnalyticsInventoryPage /> },
    { key: "sales",        label: tx("Sales"),        permission: "sales.view", exact: true,     content: <AnalyticsSalesPage /> },
    { key: "production",   label: tx("Production"),   permission: "production.view", exact: true,content: <AnalyticsProductionPage /> },
    { key: "procurement",  label: tx("Procurement"),  permission: "procurement.view", exact: true,content: <AnalyticsProcurementPage /> },
    { key: "finance",      label: tx("Finance"),      permission: "finance.view", exact: true,   content: <AnalyticsFinancePage /> },
    { key: "payments",     label: tx("Payments"),     permission: "mpesa.view_transactions", content: <AnalyticsPaymentsPage /> },
    { key: "reports",      label: tx("Reports"),      permission: "analytics.view", content: <ReportsPage /> },
    { key: "report-builder",label:tx("Report Builder"),permission:"reports.view", content: <ReportBuilderPage /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Analytics")}
      description="KPIs, module analytics, reports, report builder"
      permission="analytics.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
