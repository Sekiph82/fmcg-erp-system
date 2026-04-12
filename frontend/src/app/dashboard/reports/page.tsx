"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { Sparkline } from "@/components/bi/Charts";

const MODULES = [
  {
    id: "inventory",
    label: "Inventory",
    href: "/dashboard/reports/inventory",
    desc: "Stock value, low stock, movements",
    permission: "inventory.view",
    color: "border-blue-500/20 hover:border-blue-500/40",
    accent: "text-blue-400",
  },
  {
    id: "production",
    label: "Production / MES",
    href: "/dashboard/reports/production",
    desc: "Plan vs actual, downtime, rejections",
    permission: "production.view",
    color: "border-purple-500/20 hover:border-purple-500/40",
    accent: "text-purple-400",
  },
  {
    id: "procurement",
    label: "Procurement",
    href: "/dashboard/reports/procurement",
    desc: "Open POs, overdue, supplier performance",
    permission: "procurement.view",
    color: "border-amber-500/20 hover:border-amber-500/40",
    accent: "text-amber-400",
  },
  {
    id: "sales",
    label: "Sales & Revenue",
    href: "/dashboard/reports/sales",
    desc: "Revenue trends, channel mix, top customers",
    permission: "sales.view",
    color: "border-emerald-500/20 hover:border-emerald-500/40",
    accent: "text-emerald-400",
  },
  {
    id: "finance",
    label: "Finance",
    href: "/dashboard/reports/finance",
    desc: "Cash position, receivables, payables",
    permission: "finance.view",
    color: "border-indigo-500/20 hover:border-indigo-500/40",
    accent: "text-indigo-400",
  },
  {
    id: "payments",
    label: "M-Pesa Payments",
    href: "/dashboard/reports/payments",
    desc: "Collections, success rate, failure analysis",
    permission: "mpesa.view_transactions",
    color: "border-green-500/20 hover:border-green-500/40",
    accent: "text-green-400",
  },
  {
    id: "marketing",
    label: "Marketing BI",
    href: "/dashboard/reports/marketing",
    desc: "Campaigns, spend, influencers, social, ads, CRM",
    permission: "marketing_analytics.view",
    color: "border-pink-500/20 hover:border-pink-500/40",
    accent: "text-pink-400",
  },
];

function HubContent() {
  const router = useRouter();

  // Pre-fetch quick summaries for the hub
  const { data: sales } = useQuery({ queryKey: ["analytics-sales-7"], queryFn: () => analyticsApi.sales(7) });
  const { data: inv }   = useQuery({ queryKey: ["analytics-inv-7"],   queryFn: () => analyticsApi.inventory(7) });
  const { data: mpesa } = useQuery({ queryKey: ["analytics-mpesa-7"], queryFn: () => analyticsApi.mpesa(7) });
  const { data: prod }  = useQuery({ queryKey: ["analytics-prod-7"],  queryFn: () => analyticsApi.production(7) });

  const quickKpis = [
    {
      label: "Today's Revenue",
      value: sales ? fmtKES(sales.today_revenue) : "—",
      sub: `${sales?.today_orders ?? "—"} orders`,
      color: "text-emerald-400",
      trend: sales?.revenue_trend ?? [],
      trendColor: "#10b981",
    },
    {
      label: "Stock Value",
      value: inv ? fmtKES(inv.total_stock_value) : "—",
      sub: `${inv?.low_stock_count ?? "—"} low stock`,
      color: "text-blue-400",
      trend: inv?.receipts_trend_30d ?? [],
      trendColor: "#3b82f6",
    },
    {
      label: "M-Pesa Today",
      value: mpesa ? fmtKES(mpesa.today_collected) : "—",
      sub: `${mpesa?.today_success_rate?.toFixed(1) ?? "—"}% success rate`,
      color: "text-green-400",
      trend: mpesa?.daily_collection_trend ?? [],
      trendColor: "#22c55e",
    },
    {
      label: "Production",
      value: prod ? `${prod.active_orders} active` : "—",
      sub: `${prod?.completion_rate?.toFixed(1) ?? "—"}% completion`,
      color: "text-purple-400",
      trend: prod?.production_trend ?? [],
      trendColor: "#a855f7",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-white">Reports & Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Live metrics from all ERP modules. Click a dashboard to drill in.</p>
      </div>

      {/* Quick KPI strip */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {quickKpis.map((k) => (
          <div key={k.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{k.label}</p>
            <p className={`mt-1.5 text-xl font-semibold leading-none ${k.color}`}>{k.value}</p>
            <p className="text-[11px] text-slate-600 mt-1">{k.sub}</p>
            <div className="mt-3 opacity-70">
              <Sparkline data={k.trend.slice(-14)} color={k.trendColor} />
            </div>
          </div>
        ))}
      </div>

      {/* Module cards */}
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 mb-3">Module Dashboards</p>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {MODULES.map((m) => (
            <button
              key={m.id}
              onClick={() => router.push(m.href)}
              className={[
                "rounded-xl border bg-white/[0.02] p-5 text-left transition-all duration-150 hover:bg-white/[0.04]",
                m.color,
              ].join(" ")}
            >
              <p className={`text-sm font-semibold ${m.accent}`}>{m.label}</p>
              <p className="text-[12px] text-slate-500 mt-1">{m.desc}</p>
              <span className="mt-3 inline-block text-[11px] text-slate-600">Open →</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <RequirePermission permission="inventory.view">
      <HubContent />
    </RequirePermission>
  );
}
