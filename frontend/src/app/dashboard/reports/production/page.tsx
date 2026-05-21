"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { PlanVsActualChart, TrendLineChart, HBarChart } from "@/components/bi/Charts";
import { ExceptionList } from "@/components/bi/ExceptionList";

function ProductionDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-production", days],
    queryFn: () => analyticsApi.production(days),
  });

  return (
    <DashboardShell
      title="Production / MES Analytics"
      subtitle="Plan vs actual, downtime, quality rejections"
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title="Production KPIs">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label="Active Orders" value={data ? fmt(data.active_orders) : "—"} color="indigo" />
          <KpiCard
            label="Completion Rate"
            value={data ? `${data.completion_rate.toFixed(1)}%` : "—"}
            color={data && data.completion_rate >= 90 ? "green" : data && data.completion_rate >= 70 ? "amber" : "red"}
            trend={data && data.completion_rate >= 90 ? "up" : "down"}
          />
          <KpiCard
            label="Avg Downtime (hrs)"
            value={data ? data.avg_downtime_hours.toFixed(1) : "—"}
            color={data && data.avg_downtime_hours < 10 ? "green" : "amber"}
            sub="Per breakdown"
          />
          <KpiCard
            label="Delayed Orders"
            value={data ? String(data.delayed_orders) : "—"}
            color={data && data.delayed_orders === 0 ? "green" : data && data.delayed_orders < 5 ? "amber" : "red"}
            trend={data && data.delayed_orders === 0 ? "up" : "down"}
          />
        </div>
      </Section>

      <Section title="Plan vs Actual Output">
        <ChartCard title={`Units Planned vs Produced — Last ${days}d`}>
          {data?.plan_vs_actual && data?.plan_vs_actual_actual ? (
            <PlanVsActualChart
              planned={data.plan_vs_actual}
              actual={data.plan_vs_actual_actual}
              height={220}
              formatY={(v) => fmt(v)}
            />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-600 text-sm">No data</div>
          )}
        </ChartCard>
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Section title="Downtime Trend">
          <ChartCard title={`Downtime Hours — Last ${days}d`}>
            {data?.downtime_trend ? (
              <TrendLineChart
                data={data.downtime_trend}
                color="#f59e0b"
                label="Downtime (hrs)"
                height={180}
                formatY={(v) => `${v.toFixed(1)}h`}
              />
            ) : (
              <div className="h-[180px] flex items-center justify-center text-slate-600 text-sm">No data</div>
            )}
          </ChartCard>
        </Section>

        <Section title="Status Distribution">
          <ChartCard title="Orders by Status">
            {data?.by_status?.length ? (
              <HBarChart
                data={data.by_status.map((s) => ({ label: s.label, value: s.count }))}
                color="#a855f7"
                height={180}
                formatY={(v) => fmt(v)}
              />
            ) : (
              <div className="h-[180px] flex items-center justify-center text-slate-600 text-sm">No data</div>
            )}
          </ChartCard>
        </Section>
      </div>

      <Section title="Production Exceptions">
        <ExceptionList
          items={data?.exceptions ?? []}
          title="Overdue Orders & Alerts"
        />
      </Section>
    </DashboardShell>
  );
}

export default function ProductionReportPage() {
  return (
    <RequirePermission permission="production.view">
      <ProductionDashboard />
    </RequirePermission>
  );
}
