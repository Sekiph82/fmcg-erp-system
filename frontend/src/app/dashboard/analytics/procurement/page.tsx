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
import { tx } from "@/lib/i18n/core";

export default function ProcurementAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-procurement", days],
    queryFn: () => analyticsApi.procurement(days),
    staleTime: 60_000,
  });

  return (
    <RequirePermission permission="procurement.view">
      <div className="max-w-2xl mx-auto space-y-5 pb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{tx("Procurement Dashboard")}</h1>
            <p className="text-xs text-gray-400 mt-0.5">{tx("PO status, delays & supplier spend")}</p>
          </div>
          <DaysSelector value={days} onChange={setDays} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <KPICard
            label={tx("Open PO Value")}
            value={fmtKES(data?.open_po_value ?? 0)}
            subtext={`${data?.open_po_count ?? 0} open POs`}
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label={tx("Purchase Delays")}
            value={data?.overdue_po_count ?? 0}
            subtext="POs past delivery date"
            status={(data?.overdue_po_count ?? 0) > 0 ? "critical" : "ok"}
            href="/dashboard/procurement/orders"
            loading={isLoading}
          />
          <KPICard
            label={tx("Pending PRs")}
            value={data?.pending_pr_count ?? 0}
            subtext="Awaiting approval"
            status={(data?.pending_pr_count ?? 0) > 0 ? "warning" : "ok"}
            href="/dashboard/procurement"
            loading={isLoading}
          />
          <KPICard
            label={tx("GRNs This Month")}
            value={data?.received_this_month ?? 0}
            subtext="Goods received"
            status="ok"
            loading={isLoading}
          />
        </div>

        {/* PO Value trend */}
        <ChartCard title={tx("PO Value Trend")} subtitle={tx("Last {days} days", { days })}>
          <LineChart
            series={[{ name: tx("PO Value"), color: "#8b5cf6", data: data?.po_value_trend ?? [] }]}
            formatY={(v) => fmtKES(v)}
            showLegend={false}
          />
        </ChartCard>

        {/* GRN trend */}
        <ChartCard title={tx("Goods Receipts")} subtitle={tx("Last {days} days", { days })}>
          <BarChart
            data={data?.grn_trend ?? []}
            color="#10b981"
            formatY={(v) => fmt(v, 0)}
          />
        </ChartCard>

        {/* Top suppliers */}
        <ChartCard title={tx("Top Suppliers by Spend")}>
          <DistributionBar
            data={data?.top_suppliers ?? []}
            formatValue={(v) => fmtKES(v)}
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
