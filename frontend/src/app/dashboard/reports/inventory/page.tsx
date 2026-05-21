"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard, DistTable } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { TrendLineChart, HBarChart } from "@/components/bi/Charts";
import { ExceptionList } from "@/components/bi/ExceptionList";

function InventoryDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-inventory", days],
    queryFn: () => analyticsApi.inventory(days),
  });

  return (
    <DashboardShell
      title="Inventory Analytics"
      subtitle="Stock value, movements, and reorder alerts"
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title="Stock Overview">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label="Total Stock Value" value={data ? fmtKES(data.total_stock_value) : "—"} color="blue" />
          <KpiCard label="Total SKUs" value={data ? fmt(data.total_sku_count) : "—"} color="default" />
          <KpiCard
            label="Low Stock Items"
            value={data ? fmt(data.low_stock_count) : "—"}
            color={data && data.low_stock_count > 0 ? "amber" : "green"}
            sub={data && data.low_stock_count > 0 ? "Need reorder" : "All stocked"}
            trend={data && data.low_stock_count > 0 ? "down" : "neutral"}
          />
          <KpiCard
            label="Out of Stock"
            value={data ? fmt(data.zero_stock_count) : "—"}
            color={data && data.zero_stock_count > 0 ? "red" : "green"}
            sub={data && data.zero_stock_count > 0 ? "Stockouts" : "None"}
            trend={data && data.zero_stock_count > 0 ? "down" : "neutral"}
          />
        </div>
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Section title="Movement Trends">
          <ChartCard title={`Receipts vs Issues — Last ${days}d`}>
            {data?.receipts_trend_30d && data?.issues_trend_30d ? (
              <TrendLineChart
                data={data.receipts_trend_30d}
                color="#3b82f6"
                label="Receipts"
                height={200}
                formatY={(v) => fmtKES(v)}
              />
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">No data</div>
            )}
          </ChartCard>
        </Section>

        <Section title="Movement Type Breakdown">
          <ChartCard title="Stock by Movement Type">
            {data?.by_movement_type?.length ? (
              <DistTable items={data.by_movement_type} valueLabel="Value (KES)" />
            ) : (
              <p className="text-sm text-slate-600">No movement data</p>
            )}
          </ChartCard>
        </Section>
      </div>

      <Section title="Issues Trend">
        <ChartCard title={`Stock Issues — Last ${days}d`}>
          {data?.issues_trend_30d?.length ? (
            <HBarChart
              data={data.issues_trend_30d.map((w) => ({ label: w.date.slice(5), value: w.value }))}
              color="#6366f1"
              height={200}
              formatY={(v) => fmtKES(v)}
            />
          ) : (
            <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">No issue data</div>
          )}
        </ChartCard>
      </Section>

      <Section title="Alerts">
        <ExceptionList
          items={data?.low_stock_items ?? []}
          title="Low Stock & Stockout Alerts"
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
