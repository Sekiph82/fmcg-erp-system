"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { KPICard } from "@/components/dashboard/KPICard";
import { LineChart } from "@/components/analytics/LineChart";
import { BarChart } from "@/components/analytics/BarChart";
import { DistributionBar } from "@/components/analytics/DistributionBar";
import { ExceptionList } from "@/components/analytics/ExceptionList";
import { ChartCard } from "@/components/analytics/ChartCard";
import { DaysSelector } from "@/components/analytics/DaysSelector";
import { RequirePermission } from "@/components/PermissionGuard";

export default function SalesAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-sales", days],
    queryFn: () => analyticsApi.sales(days),
    staleTime: 60_000,
  });

  return (
    <RequirePermission permission="sales.view">
      <div className="max-w-2xl mx-auto space-y-5 pb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Sales Dashboard</h1>
            <p className="text-xs text-gray-400 mt-0.5">Revenue, orders &amp; receivables</p>
          </div>
          <DaysSelector value={days} onChange={setDays} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <KPICard
            label="Today Revenue"
            value={fmtKES(data?.today_revenue ?? 0)}
            subtext={`${data?.today_orders ?? 0} orders`}
            status="ok"
            trend={data?.revenue_trend}
            loading={isLoading}
          />
          <KPICard
            label="MTD Revenue"
            value={fmtKES(data?.mtd_revenue ?? 0)}
            subtext={`YTD: ${fmtKES(data?.ytd_revenue ?? 0)}`}
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label="Overdue Invoices"
            value={data?.overdue_invoices ?? 0}
            subtext={fmtKES(data?.overdue_value ?? 0)}
            status={(data?.overdue_invoices ?? 0) > 0 ? "critical" : "ok"}
            href="/dashboard/sales/invoices"
            loading={isLoading}
          />
          <KPICard
            label="Open Orders"
            value={data?.open_orders ?? 0}
            subtext={`Avg: ${fmtKES(data?.avg_order_value ?? 0)}`}
            status="ok"
            href="/dashboard/sales/orders"
            loading={isLoading}
          />
          <KPICard
            label="Pending Shipments"
            value={data?.pending_shipments ?? 0}
            subtext="Not yet dispatched"
            status={(data?.pending_shipments ?? 0) > 5 ? "warning" : "ok"}
            href="/dashboard/sales/shipments"
            loading={isLoading}
          />
          <KPICard
            label="Overdue Value"
            value={fmtKES(data?.overdue_value ?? 0)}
            subtext="Outstanding balance"
            status={(data?.overdue_value ?? 0) > 0 ? "warning" : "ok"}
            href="/dashboard/sales/invoices"
            loading={isLoading}
          />
        </div>

        {/* Revenue trend */}
        <ChartCard title="Revenue Trend" subtitle={`Last ${days} days (invoiced)`}>
          <LineChart
            series={[
              { name: "Revenue", color: "#f97316", data: data?.revenue_trend ?? [] },
              { name: "Order Count", color: "#6366f1", data: data?.order_count_trend ?? [], dashed: true },
            ]}
            formatY={(v) => fmtKES(v)}
          />
        </ChartCard>

        {/* By channel */}
        <ChartCard title="Sales by Channel" subtitle={`Last ${days} days`}>
          <DistributionBar data={data?.by_channel ?? []} formatValue={(v) => fmtKES(v)} />
        </ChartCard>

        {/* Order count trend as bar */}
        <ChartCard title="Daily Order Count" subtitle={`Last ${days} days`}>
          <BarChart
            data={data?.order_count_trend ?? []}
            color="#6366f1"
            formatY={(v) => fmt(v, 0)}
          />
        </ChartCard>

        {/* Top customers */}
        <ChartCard title="Top Customers" subtitle="By invoice value">
          <DistributionBar data={data?.top_customers ?? []} formatValue={(v) => fmtKES(v)} />
        </ChartCard>

        {/* Exceptions */}
        <ChartCard title="Exceptions">
          <ExceptionList items={data?.exceptions ?? []} title="" />
        </ChartCard>
      </div>
    </RequirePermission>
  );
}
