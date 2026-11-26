"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { productionApi } from "@/lib/production";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { tx } from "@/lib/i18n/core";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function ProductionReportsPage() {
  const { toasts, toast, dismiss } = useToast();

  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

  const [dateFrom, setDateFrom] = useState(firstOfMonth.toISOString().slice(0, 16));
  const [dateTo, setDateTo] = useState(today.toISOString().slice(0, 16));
  const [submitted, setSubmitted] = useState(true);

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["production-report", dateFrom, dateTo],
    queryFn: () => productionApi.getReport({ date_from: dateFrom, date_to: dateTo }),
    enabled: submitted,
    retry: false,
  });

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-2">
        <h1 className="text-2xl font-bold text-gray-900">{tx("Production Reports")}</h1>
        <p className="text-sm text-gray-500 mt-1">{tx("Planned vs actual, downtime, and OEE summary")}</p>
      </div>

      {/* Date filter */}
      <div className="flex gap-3 items-end flex-wrap rounded-xl border border-gray-200 bg-white p-4">
        <Input
          label={tx("From")}
          type="datetime-local"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="w-56"
        />
        <Input
          label={tx("To")}
          type="datetime-local"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="w-56"
        />
        <Button onClick={() => setSubmitted(true)}>{tx("Run Report")}</Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-600">
          {extractApiError(error)}
        </div>
      )}

      {report && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label={tx("Total Orders")} value={report.total_orders} />
            <StatCard
              label={tx("Completed")}
              value={report.completed_orders}
              sub={`${report.in_progress_orders} in progress`}
            />
            <StatCard
              label={tx("Avg OEE")}
              value={report.avg_oee != null ? String((report.avg_oee * 100).toFixed(1)) + "%" : "—"}
            />
            <StatCard
              label={tx("Total Downtime")}
              value={`${report.total_downtime_minutes.toFixed(0)} min`}
              sub={`${(report.total_downtime_minutes / 60).toFixed(1)} hours`}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              label={tx("Planned Qty Total")}
              value={Number(report.planned_quantity_total).toLocaleString()}
            />
            <StatCard
              label={tx("Actual Qty Total")}
              value={Number(report.actual_quantity_total).toLocaleString()}
            />
            <StatCard
              label={tx("Overall Variance")}
              value={`${Number(report.overall_variance) >= 0 ? "+" : ""}${Number(report.overall_variance).toLocaleString()}`}
            />
          </div>

          {/* Orders table */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">{tx("Order Detail")}</h2>
            <Table
              keyField="order_no"
              data={report.orders}
              emptyMessage="No orders in this period."
              columns={[
                { header: tx("Date"), accessor: "date" },
                { header: tx("Order No"), accessor: "order_no", className: "font-mono text-xs" },
                {
                  header: tx("Product"),
                  accessor: (r) => (
                    <span>
                      <span className="font-mono text-xs text-gray-500">{r.product_sku}</span>{" "}
                      {r.product_name}
                    </span>
                  ),
                },
                { header: tx("Batch"), accessor: (r) => r.batch_no ?? "—" },
                {
                  header: tx("Planned"),
                  accessor: (r) => Number(r.planned_quantity).toLocaleString(),
                },
                {
                  header: tx("Actual"),
                  accessor: (r) =>
                    r.actual_quantity != null ? Number(r.actual_quantity).toLocaleString() : "—",
                },
                {
                  header: tx("Variance"),
                  accessor: (r) => {
                    if (r.variance == null) return "—";
                    const v = Number(r.variance);
                    const pct = r.variance_pct != null ? ` (${r.variance_pct > 0 ? "+" : ""}${r.variance_pct}%)` : "";
                    return (
                      <span className={v > 0 ? "text-green-600" : v < 0 ? "text-red-500" : "text-gray-500"}>
                        {v > 0 ? "+" : ""}{v.toLocaleString()}{pct}
                      </span>
                    );
                  },
                },
                {
                  header: tx("Downtime"),
                  accessor: (r) => r.downtime_minutes > 0 ? `${r.downtime_minutes} min` : "—",
                },
                {
                  header: tx("Status"),
                  accessor: (r) => (
                    <Badge
                      label={r.status}
                      variant={
                        r.status === "COMPLETED" ? "green"
                        : r.status === "CANCELLED" ? "red"
                        : "blue"
                      }
                    />
                  ),
                },
              ]}
            />
          </div>

          {/* Downtime summary */}
          {report.downtime_summary.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">{tx("Downtime Summary")}</h2>
              <Table
                keyField="reason"
                data={report.downtime_summary}
                emptyMessage=""
                columns={[
                  { header: tx("Reason"), accessor: (d) => d.reason.replace(/_/g, " ") },
                  { header: tx("Machine / Line"), accessor: (d) => d.machine_id ?? "—" },
                  { header: tx("Occurrences"), accessor: "count" },
                  {
                    header: tx("Total Duration"),
                    accessor: (d) => `${d.total_minutes.toFixed(0)} min (${(d.total_minutes / 60).toFixed(1)} h)`,
                  },
                ]}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
