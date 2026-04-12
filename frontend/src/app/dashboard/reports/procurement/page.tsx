"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, fmtKES, fmt } from "@/lib/analytics";
import { RequirePermission } from "@/components/PermissionGuard";
import { DashboardShell, Section, ChartCard, DistTable } from "@/components/bi/DashboardShell";
import { KpiCard } from "@/components/bi/KpiCard";
import { TrendLineChart } from "@/components/bi/Charts";
import { ExceptionList } from "@/components/bi/ExceptionList";

function ProcurementDashboard() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-procurement", days],
    queryFn: () => analyticsApi.procurement(days),
  });

  return (
    <DashboardShell
      title="Procurement Analytics"
      subtitle="Open POs, overdue orders, and supplier performance"
      days={days}
      onDaysChange={setDays}
      backHref="/dashboard/reports"
      loading={isLoading}
    >
      <Section title="PO Overview">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label="Open POs" value={data ? fmt(data.open_po_count) : "—"} color="indigo" />
          <KpiCard label="Open PO Value" value={data ? fmtKES(data.open_po_value) : "—"} color="blue" />
          <KpiCard
            label="Overdue POs"
            value={data ? fmt(data.overdue_po_count) : "—"}
            color={data && data.overdue_po_count > 0 ? "red" : "green"}
            sub={data && data.overdue_po_count > 0 ? "Needs attention" : "All on time"}
            trend={data && data.overdue_po_count > 0 ? "down" : "up"}
          />
          <KpiCard label="Open PO Value" value={data ? fmtKES(data.open_po_value) : "—"} color="amber" sub="Open orders" />
        </div>
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Section title="Spend Trend">
          <ChartCard title={`PO Spend — Last ${days}d`}>
            {data?.po_value_trend ? (
              <TrendLineChart
                data={data.po_value_trend}
                color="#f59e0b"
                label="Spend (KES)"
                height={200}
                formatY={(v) => fmtKES(v)}
              />
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-600 text-sm">No data</div>
            )}
          </ChartCard>
        </Section>

        <Section title="Top Suppliers by Value">
          <ChartCard title="Supplier Spend Ranking">
            {data?.top_suppliers?.length ? (
              <DistTable items={data.top_suppliers} valueLabel="Spend (KES)" />
            ) : (
              <p className="text-sm text-slate-600">No supplier data</p>
            )}
          </ChartCard>
        </Section>
      </div>

      <Section title="Overdue & Exceptions">
        <ExceptionList
          items={data?.exceptions ?? []}
          title="Overdue Purchase Orders"
        />
      </Section>
    </DashboardShell>
  );
}

export default function ProcurementReportPage() {
  return (
    <RequirePermission permission="procurement.view">
      <ProcurementDashboard />
    </RequirePermission>
  );
}
