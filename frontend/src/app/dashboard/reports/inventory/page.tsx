"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard, DistTable } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { TrendLineChart, HBarChart } from "@/components/bi/Charts";
import { ExceptionList } from "@/components/bi/ExceptionList";
import { tx } from "@/lib/i18n/core";

function InventoryDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-inventory", days],
    queryFn: () => analyticsApi.inventory(days),
  });

  return (
    <DashboardShell
      title={tx("Inventory Analytics")}
      subtitle={tx("Stock value, movements, and reorder alerts")}
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title={tx("Stock Overview")}>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label={tx("Total Stock Value")} value={data ? fmtKES(data.total_stock_value) : "—"} color="blue" />
          <KpiCard label={tx("Total SKUs")} value={data ? fmt(data.total_sku_count) : "—"} color="default" />
          <KpiCard
            label={tx("Low Stock Items")}
            value={data ? fmt(data.low_stock_count) : "—"}
            color={data && data.low_stock_count > 0 ? "amber" : "green"}
            sub={data && data.low_stock_count > 0 ? tx("Need reorder") : tx("All stocked")}
            trend={data && data.low_stock_count > 0 ? "down" : "neutral"}
          />
          <KpiCard
            label={tx("Out of Stock")}
            value={data ? fmt(data.zero_stock_count) : "—"}
            color={data && data.zero_stock_count > 0 ? "red" : "green"}
            sub={data && data.zero_stock_count > 0 ? "Stockouts" : "None"}
            trend={data && data.zero_stock_count > 0 ? "down" : "neutral"}
          />
        </div>
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Section title={tx("Movement Trends")}>
          <ChartCard title={tx("Receipts vs Issues — Last {days}d", { days })}>
            {data?.receipts_trend_30d && data?.issues_trend_30d ? (
              <TrendLineChart
                data={data.receipts_trend_30d}
                color="#3b82f6"
                label={tx("Receipts")}
                height={200}
                formatY={(v) => fmtKES(v)}
              />
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">{tx("No data")}</div>
            )}
          </ChartCard>
        </Section>

        <Section title={tx("Movement Type Breakdown")}>
          <ChartCard title={tx("Stock by Movement Type")}>
            {data?.by_movement_type?.length ? (
              <DistTable items={data.by_movement_type} valueLabel="Value (KES)" />
            ) : (
              <p className="text-sm text-slate-600">{tx("No movement data")}</p>
            )}
          </ChartCard>
        </Section>
      </div>

      <Section title={tx("Issues Trend")}>
        <ChartCard title={tx("Stock Issues — Last {days}d", { days })}>
          {data?.issues_trend_30d?.length ? (
            <HBarChart
              data={data.issues_trend_30d.map((w) => ({ label: w.date.slice(5), value: w.value }))}
              color="#6366f1"
              height={200}
              formatY={(v) => fmtKES(v)}
            />
          ) : (
            <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">{tx("No issue data")}</div>
          )}
        </ChartCard>
      </Section>

      <Section title={tx("Alerts")}>
        <ExceptionList
          items={data?.low_stock_items ?? []}
          title={tx("Low Stock & Stockout Alerts")}
        />
      </Section>
    </DashboardShell>
  );
}

export default function InventoryReportPage() {
  return (
    <RequirePermission permission="inventory.view">
      <InventoryDashboard />
    </RequirePermission>
  );
}
