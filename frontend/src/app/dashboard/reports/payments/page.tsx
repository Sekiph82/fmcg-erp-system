"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { TrendLineChart } from "@/components/bi/Charts";
import { ExceptionList } from "@/components/bi/ExceptionList";

function PaymentsDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-mpesa", days],
    queryFn: () => analyticsApi.mpesa(days),
  });

  return (
    <DashboardShell
      title="M-Pesa Payments Analytics"
      subtitle="Collections, success rates, and failure analysis"
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title="Today">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label="Today Collected" value={data ? fmtKES(data.today_collected) : "—"} color="green" />
          <KpiCard label="Today Transactions" value={data ? fmt(data.today_transactions) : "—"} color="default" />
          <KpiCard
            label="Success Rate"
            value={data ? `${data.today_success_rate.toFixed(1)}%` : "—"}
            color={data && data.today_success_rate >= 95 ? "green" : data && data.today_success_rate >= 80 ? "amber" : "red"}
            trend={data && data.today_success_rate >= 95 ? "up" : "down"}
          />
          <KpiCard label="Failed Today" value={data ? fmt(data.today_failed) : "—"} color={data && data.today_failed > 0 ? "red" : "green"} />
        </div>
      </Section>

      <Section title={`Last ${days} Days`}>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label="Period Collected" value={data ? fmtKES(data.period_collected) : "—"} color="blue" />
          <KpiCard label="Total Transactions" value={data ? fmt(data.period_total_transactions) : "—"} color="default" />
          <KpiCard
            label="Avg Success Rate"
            value={data ? `${data.period_success_rate.toFixed(1)}%` : "—"}
            color={data && data.period_success_rate >= 95 ? "green" : data && data.period_success_rate >= 80 ? "amber" : "red"}
          />
          <KpiCard label="Total Failed" value={data ? fmt(data.period_failed) : "—"} color={data && data.period_failed > 0 ? "amber" : "green"} />
        </div>
      </Section>

      <Section title="Collection Trend">
        <ChartCard title={`Daily Collections — Last ${days}d`}>
          {data?.daily_collection_trend ? (
            <TrendLineChart
              data={data.daily_collection_trend}
              color="#22c55e"
              label="Collected (KES)"
              height={220}
              formatY={(v) => fmtKES(v)}
            />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-600 text-sm">No data</div>
          )}
        </ChartCard>
      </Section>

      <Section title="Failure Analysis">
        <ExceptionList
          items={data?.recent_failures ?? []}
          title="Recent M-Pesa Failures"
        />
      </Section>
    </DashboardShell>
  );
}

export default function PaymentsReportPage() {
  return (
    <RequirePermission permission="mpesa.view_transactions">
      <PaymentsDashboard />
    </RequirePermission>
  );
}
