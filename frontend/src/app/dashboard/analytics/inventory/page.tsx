"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { KPICard } from "@/components/dashboard/KPICard";
import { LineChart } from "@/components/analytics/LineChart";
import { DistributionBar } from "@/components/analytics/DistributionBar";
import { ExceptionList } from "@/components/analytics/ExceptionList";
import { ChartCard } from "@/components/analytics/ChartCard";
import { DaysSelector } from "@/components/analytics/DaysSelector";
import { RequirePermission } from "@/components/PermissionGuard";

export default function InventoryAnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-inventory", days],
    queryFn: () => analyticsApi.inventory(days),
    staleTime: 60_000,
  });

  return (
    <RequirePermission permission="inventory.view">
      <div className="max-w-2xl mx-auto space-y-5 pb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Inventory Dashboard</h1>
            <p className="text-xs text-gray-400 mt-0.5">Stock levels, movements &amp; alerts</p>
          </div>
          <DaysSelector value={days} onChange={setDays} />
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 gap-3">
          <KPICard
            label="Stock Value"
            value={fmtKES(data?.total_stock_value ?? 0)}
            subtext={`${data?.total_sku_count ?? 0} SKUs`}
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label="Low Stock Items"
            value={data?.low_stock_count ?? 0}
            subtext={`${data?.zero_stock_count ?? 0} zero stock`}
            status={
              (data?.low_stock_count ?? 0) > 5 ? "critical"
              : (data?.low_stock_count ?? 0) > 0 ? "warning" : "ok"
            }
            href="/dashboard/inventory"
            loading={isLoading}
          />
          <KPICard
            label="Products"
            value={data?.product_count ?? 0}
            status="ok"
            loading={isLoading}
          />
          <KPICard
            label="Blocked Stock"
            value={data?.blocked_stock_count ?? 0}
            status={(data?.blocked_stock_count ?? 0) > 0 ? "warning" : "ok"}
            loading={isLoading}
          />
        </div>

        {/* Movement trends */}
        <ChartCard title="Net Stock Movement" subtitle={`Last ${days} days (receipts − issues)`}>
          <LineChart
            series={[
              { name: "Net Movement", color: "#6366f1", data: data?.movement_trend_30d ?? [] },
              { name: "Receipts", color: "#10b981", data: data?.receipts_trend_30d ?? [] },
              { name: "Issues", color: "#ef4444", data: data?.issues_trend_30d ?? [], dashed: true },
            ]}
            formatY={(v) => fmt(v, 0)}
          />
        </ChartCard>

        {/* Movement type distribution */}
        <ChartCard title="By Movement Type" subtitle="Volume distribution">
          <DistributionBar
            data={data?.by_movement_type ?? []}
            formatValue={(v) => fmt(v, 0)}
          />
        </ChartCard>

        {/* Low stock exceptions */}
        <ChartCard title="Low Stock Alerts" subtitle="Items at or below reorder point">
          <ExceptionList
            items={data?.low_stock_items ?? []}
            title=""
            maxItems={10}
          />
        </ChartCard>
      </div>
    </RequirePermission>
  );
}
