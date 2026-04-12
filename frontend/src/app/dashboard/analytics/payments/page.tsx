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

export default function PaymentsAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-payments", days],
    queryFn: () => analyticsApi.mpesa(days),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const successStatus =
    (data?.today_success_rate ?? 100) >= 95 ? "ok"
    : (data?.today_success_rate ?? 100) >= 80 ? "warning" : "critical";

  return (
    <RequirePermission permission="mpesa.view_transactions">
      <div className="max-w-2xl mx-auto space-y-5 pb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Payments / M-Pesa</h1>
            <p className="text-xs text-gray-400 mt-0.5">Collections, success rate &amp; failure analysis</p>
          </div>
          <DaysSelector value={days} onChange={setDays} />
        </div>

        {/* Today KPIs */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Today</p>
          <div className="grid grid-cols-2 gap-3">
            <KPICard
              label="M-Pesa Collected"
              value={fmtKES(data?.today_collected ?? 0)}
              subtext={`${data?.today_transactions ?? 0} transactions`}
              status="ok"
              trend={data?.daily_collection_trend}
              loading={isLoading}
            />
            <KPICard
              label="Success Rate"
              value={`${fmt(data?.today_success_rate ?? 100, 1)}%`}
              subtext={`${data?.today_failed ?? 0} failed`}
              status={successStatus}
              loading={isLoading}
            />
            <KPICard
              label="Pending"
              value={data?.today_pending ?? 0}
              subtext="Awaiting callback"
              status={(data?.today_pending ?? 0) > 5 ? "warning" : "ok"}
              href="/dashboard/finance/mpesa"
              loading={isLoading}
            />
            <KPICard
              label="Reversed / Cancelled"
              value={data?.today_reversed ?? 0}
              status={(data?.today_reversed ?? 0) > 0 ? "warning" : "ok"}
              loading={isLoading}
            />
          </div>
        </div>

        {/* Period KPIs */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Last {days} days
          </p>
          <div className="grid grid-cols-2 gap-3">
            <KPICard
              label="Total Collected"
              value={fmtKES(data?.period_collected ?? 0)}
              subtext={`${data?.period_total_transactions ?? 0} transactions`}
              status="ok"
              loading={isLoading}
            />
            <KPICard
              label="Period Success Rate"
              value={`${fmt(data?.period_success_rate ?? 100, 1)}%`}
              subtext={`${data?.period_failed ?? 0} failed`}
              status={
                (data?.period_success_rate ?? 100) >= 95 ? "ok"
                : (data?.period_success_rate ?? 100) >= 80 ? "warning" : "critical"
              }
              loading={isLoading}
            />
            <KPICard
              label="Avg Transaction"
              value={fmtKES(data?.avg_amount ?? 0)}
              status="ok"
              loading={isLoading}
            />
            <KPICard
              label="Avg Completion Time"
              value={`${fmt(data?.avg_completion_time_minutes ?? 0, 1)}m`}
              subtext="Initiated → completed"
              status={
                (data?.avg_completion_time_minutes ?? 0) <= 2 ? "ok"
                : (data?.avg_completion_time_minutes ?? 0) <= 5 ? "warning" : "critical"
              }
              loading={isLoading}
            />
          </div>
        </div>

        {/* Collection trend */}
        <ChartCard title="Daily Collection Trend" subtitle={`Last ${days} days`}>
          <LineChart
            series={[
              { name: "Collected (KES)", color: "#10b981", data: data?.daily_collection_trend ?? [] },
            ]}
            formatY={(v) => fmtKES(v)}
            showLegend={false}
          />
        </ChartCard>

        {/* Transaction volume */}
        <ChartCard title="Daily Transaction Volume" subtitle={`Last ${days} days`}>
          <LineChart
            series={[
              { name: "Total", color: "#6366f1", data: data?.daily_transaction_count ?? [] },
              { name: "Failed", color: "#ef4444", data: data?.daily_failure_count ?? [], dashed: true },
            ]}
            formatY={(v) => fmt(v, 0)}
          />
        </ChartCard>

        {/* Status distribution */}
        <ChartCard title="Transaction Status Distribution" subtitle={`Last ${days} days`}>
          <DistributionBar data={data?.by_status ?? []} formatValue={(v) => fmtKES(v)} />
        </ChartCard>

        {/* Recent failures */}
        <ChartCard title="Recent Failed Transactions">
          <ExceptionList
            items={data?.recent_failures ?? []}
            title=""
            maxItems={10}
          />
        </ChartCard>
      </div>
    </RequirePermission>
  );
}
