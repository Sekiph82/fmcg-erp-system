"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { TrendLineChart, MultiBarChart } from "@/components/bi/Charts";
import { ExceptionList } from "@/components/bi/ExceptionList";

function FinanceDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-finance", days],
    queryFn: () => analyticsApi.finance(days),
  });

  return (
    <DashboardShell
      title="Finance Analytics"
      subtitle="Cash position, receivables, payables, and cash flow"
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title="Financial Position">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            label="Cash Position"
            value={data ? fmtKES(data.cash_on_hand + data.bank_balance) : "—"}
            color={data && (data.cash_on_hand + data.bank_balance) >= 0 ? "green" : "red"}
            trend={data && (data.cash_on_hand + data.bank_balance) >= 0 ? "up" : "down"}
          />
          <KpiCard label="Receivables" value={data ? fmtKES(data.open_receivables) : "—"} color="blue" sub="Outstanding" />
          <KpiCard label="Payables" value={data ? fmtKES(data.open_payables) : "—"} color="amber" sub="Outstanding" />
          <KpiCard
            label="Overdue Receivables"
            value={data ? fmtKES(data.overdue_receivables) : "—"}
            color={data && data.overdue_receivables > 0 ? "red" : "green"}
            trend={data && data.overdue_receivables > 0 ? "down" : "up"}
          />
        </div>
      </Section>

      <Section title="Cash Flow Trend">
        <ChartCard title={`Receipts vs Payments — Last ${days}d`}>
          {data?.cash_receipts_trend && data?.cash_payments_trend ? (
            <MultiBarChart
              data={data.cash_receipts_trend.map((r, i) => ({
                date: r.date,
                Receipts: r.value,
                Payments: data.cash_payments_trend[i]?.value ?? 0,
              }))}
              series={[
                { key: "Receipts", color: "#10b981" },
                { key: "Payments", color: "#ef4444" },
              ]}
              height={220}
              formatY={(v) => fmtKES(v)}
            />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-600 text-sm">No data</div>
          )}
        </ChartCard>
      </Section>

      <Section title="Overdue Alerts">
        <ExceptionList
          items={data?.exceptions ?? []}
          title="Overdue Receivables & Payables"
        />
      </Section>
    </DashboardShell>
  );
}

export default function FinanceReportPage() {
  return (
    <RequirePermission permission="finance.view">
      <FinanceDashboard />
    </RequirePermission>
  );
}
