"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard, DistTable } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { TrendLineChart, HBarChart } from "@/components/bi/Charts";
import { tx } from "@/lib/i18n/core";

function SalesDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-sales", days],
    queryFn: () => analyticsApi.sales(days),
  });

  return (
    <DashboardShell
      title={tx("Sales & Revenue Analytics")}
      subtitle={tx("Revenue trends, channel mix, and top customers")}
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title={tx("Revenue KPIs")}>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label={tx("Today's Revenue")} value={data ? fmtKES(data.today_revenue) : "—"} color="green" sub={`${data?.today_orders ?? "—"} orders`} />
          <KpiCard label={tx("MTD Revenue")} value={data ? fmtKES(data.mtd_revenue) : "—"} color="green" />
          <KpiCard label={tx("Avg Order Value")} value={data ? fmtKES(data.avg_order_value) : "—"} color="blue" />
          <KpiCard label={tx("YTD Revenue")} value={data ? fmtKES(data.ytd_revenue) : "—"} color="indigo" />
        </div>
      </Section>

      <Section title={tx("Revenue Trend")}>
        <ChartCard title={tx("Daily Revenue — Last {days}d", { days })}>
          {data?.revenue_trend ? (
            <TrendLineChart
              data={data.revenue_trend}
              color="#10b981"
              label={tx("Revenue (KES)")}
              height={220}
              formatY={(v) => fmtKES(v)}
            />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-600 text-sm">{tx("No data")}</div>
          )}
        </ChartCard>
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Section title={tx("Channel Mix")}>
          <ChartCard title={tx("Revenue by Sales Channel")}>
            {data?.by_channel?.length ? (
              <HBarChart
                data={data.by_channel.map((c) => ({ label: c.label, value: c.value }))}
                color="#6366f1"
                height={200}
                formatY={(v) => fmtKES(v)}
              />
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">{tx("No channel data")}</div>
            )}
          </ChartCard>
        </Section>

        <Section title={tx("Top Customers")}>
          <ChartCard title={tx("Customer Revenue Ranking")}>
            {data?.top_customers?.length ? (
              <DistTable items={data.top_customers} valueLabel="Revenue (KES)" />
            ) : (
              <p className="text-sm text-slate-600">{tx("No customer data")}</p>
            )}
          </ChartCard>
        </Section>
      </div>

      <Section title={tx("Order Status Breakdown")}>
        <ChartCard title={tx("Orders by Status")}>
          {data?.by_status?.length ? (
            <HBarChart
              data={data.by_status.map((s) => ({ label: s.label, value: s.value }))}
              color="#6366f1"
              height={200}
              formatY={(v) => fmt(v)}
            />
          ) : (
            <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">{tx("No data")}</div>
          )}
        </ChartCard>
      </Section>
    </DashboardShell>
  );
}

export default function SalesReportPage() {
  return (
    <RequirePermission permission="sales.view">
      <SalesDashboard />
    </RequirePermission>
  );
}
