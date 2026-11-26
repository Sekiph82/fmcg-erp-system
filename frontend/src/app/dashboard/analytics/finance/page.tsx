"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES } from "@/lib/analytics";
import { KPICard } from "@/components/dashboard/KPICard";
import { LineChart } from "@/components/analytics/LineChart";
import { ExceptionList } from "@/components/analytics/ExceptionList";
import { ChartCard } from "@/components/analytics/ChartCard";
import { DaysSelector } from "@/components/analytics/DaysSelector";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx } from "@/lib/i18n/core";

export default function FinanceAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-finance", days],
    queryFn: () => analyticsApi.finance(days),
    staleTime: 60_000,
  });

  return (
    <RequirePermission permission="finance.view">
      <div className="max-w-2xl mx-auto space-y-5 pb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{tx("Finance Dashboard")}</h1>
            <p className="text-xs text-gray-400 mt-0.5">{tx("Cash, receivables & payables")}</p>
          </div>
          <DaysSelector value={days} onChange={setDays} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <KPICard
            label={tx("Cash on Hand")}
            value={fmtKES(data?.cash_on_hand ?? 0)}
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label={tx("Bank Balance")}
            value={fmtKES(data?.bank_balance ?? 0)}
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label={tx("Open Receivables")}
            value={fmtKES(data?.open_receivables ?? 0)}
            subtext="Issued + partially paid"
            status={(data?.open_receivables ?? 0) > 0 ? "warning" : "ok"}
            href="/dashboard/finance/receivables"
            loading={isLoading}
          />
          <KPICard
            label={tx("Overdue Receivables")}
            value={fmtKES(data?.overdue_receivables ?? 0)}
            subtext="Past due"
            status={(data?.overdue_receivables ?? 0) > 0 ? "critical" : "ok"}
            href="/dashboard/finance/receivables"
            loading={isLoading}
          />
          <KPICard
            label={tx("Open Payables")}
            value={fmtKES(data?.open_payables ?? 0)}
            subtext="Unpaid POs"
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label={tx("MTD Net")}
            value={fmtKES((data?.mtd_revenue ?? 0) - (data?.mtd_expenses ?? 0))}
            subtext={`Rev: ${fmtKES(data?.mtd_revenue ?? 0)}`}
            status={
              ((data?.mtd_revenue ?? 0) - (data?.mtd_expenses ?? 0)) >= 0 ? "ok" : "critical"
            }
            loading={isLoading}
          />
        </div>

        {/* Cash flow trend */}
        <ChartCard title={tx("Cash Flow")} subtitle={`Last ${days} days`}>
          <LineChart
            series={[
              { name: "Receipts", color: "#10b981", data: data?.cash_receipts_trend ?? [] },
              { name: "Payments", color: "#ef4444", data: data?.cash_payments_trend ?? [], dashed: true },
            ]}
            formatY={(v) => fmtKES(v)}
          />
        </ChartCard>

        {/* Exceptions */}
        <ChartCard title={tx("Exceptions")}>
          <ExceptionList items={data?.exceptions ?? []} title="" />
        </ChartCard>
      </div>
    </RequirePermission>
  );
}
