"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmt } from "@/lib/analytics";
import { KPICard } from "@/components/dashboard/KPICard";
import { LineChart } from "@/components/analytics/LineChart";
import { DistributionBar } from "@/components/analytics/DistributionBar";
import { ExceptionList } from "@/components/analytics/ExceptionList";
import { ChartCard } from "@/components/analytics/ChartCard";
import { DaysSelector } from "@/components/analytics/DaysSelector";
import { RequirePermission } from "@/components/PermissionGuard";

export default function ProductionAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-production", days],
    queryFn: () => analyticsApi.production(days),
    staleTime: 60_000,
  });

  return (
    <RequirePermission permission="production.view">
      <div className="max-w-2xl mx-auto space-y-5 pb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Production Dashboard</h1>
            <p className="text-xs text-gray-400 mt-0.5">Output, downtime &amp; QC rejections</p>
          </div>
          <DaysSelector value={days} onChange={setDays} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <KPICard
            label="Completion Rate"
            value={`${fmt(data?.completion_rate ?? 0, 1)}%`}
            subtext={`${data?.active_orders ?? 0} active orders`}
            status={
              (data?.completion_rate ?? 100) >= 90 ? "ok"
              : (data?.completion_rate ?? 100) >= 70 ? "warning" : "critical"
            }
            loading={isLoading}
          />
          <KPICard
            label="Delayed Orders"
            value={data?.delayed_orders ?? 0}
            subtext="Past scheduled end"
            status={(data?.delayed_orders ?? 0) > 0 ? "critical" : "ok"}
            href="/dashboard/production/orders"
            loading={isLoading}
          />
          <KPICard
            label="Machines Down"
            value={data?.machines_down ?? 0}
            subtext={`${data?.open_breakdowns ?? 0} open breakdowns`}
            status={
              (data?.machines_down ?? 0) >= 3 ? "critical"
              : (data?.machines_down ?? 0) > 0 ? "warning" : "ok"
            }
            href="/dashboard/maintenance/assets"
            loading={isLoading}
          />
          <KPICard
            label="Avg Downtime"
            value={`${fmt(data?.avg_downtime_hours ?? 0, 1)}h`}
            subtext="Per downtime day"
            status={
              (data?.avg_downtime_hours ?? 0) > 4 ? "critical"
              : (data?.avg_downtime_hours ?? 0) > 1 ? "warning" : "ok"
            }
            loading={isLoading}
          />
        </div>

        {/* Plan vs Actual */}
        <ChartCard title="Plan vs Actual Production" subtitle={`Last ${days} days`}>
          <LineChart
            series={[
              { name: "Planned", color: "#6366f1", data: data?.plan_vs_actual ?? [], dashed: true },
              { name: "Actual", color: "#10b981", data: data?.plan_vs_actual_actual ?? [] },
            ]}
            formatY={(v) => fmt(v, 0)}
          />
        </ChartCard>

        {/* Downtime trend */}
        <ChartCard title="Downtime Trend" subtitle="Hours per day">
          <LineChart
            series={[{ name: "Downtime (h)", color: "#ef4444", data: data?.downtime_trend ?? [] }]}
            formatY={(v) => `${fmt(v, 1)}h`}
            showLegend={false}
          />
        </ChartCard>

        {/* QC Rejection trend */}
        <ChartCard title="QC Rejection Trend" subtitle="Failed inspections per day">
          <LineChart
            series={[{ name: "Rejections", color: "#f59e0b", data: data?.rejection_trend ?? [] }]}
            formatY={(v) => fmt(v, 0)}
            showLegend={false}
          />
        </ChartCard>

        {/* Status distribution */}
        <ChartCard title="Order Status Distribution">
          <DistributionBar data={data?.by_status ?? []} />
        </ChartCard>

        {/* Exceptions */}
        <ChartCard title="Exceptions">
          <ExceptionList items={data?.exceptions ?? []} title="" />
        </ChartCard>
      </div>
    </RequirePermission>
  );
}
