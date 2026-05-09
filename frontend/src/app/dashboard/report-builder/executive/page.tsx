"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface ExecSummary {
  as_of: string;
  sales: { open_orders: number; orders_this_month: number; by_status: Record<string, number> };
  procurement: { open_purchase_orders: number; by_status: Record<string, number> };
  production: { in_progress: number; planned: number; by_status: Record<string, number> };
  inventory: { zero_stock_items: number; low_stock_items: number };
  approvals: { pending: number };
  helpdesk: { open_tickets: number };
  reports: { total_active: number; scheduled: number };
}

async function fetchSummary(): Promise<ExecSummary> {
  const r = await fetch("/api/v1/reports-builder/executive-summary");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

interface KpiTile {
  label: string;
  value: number;
  color: string;
  href?: string;
  alert?: boolean;
}

export default function ExecutiveDashboardPage() {
  const [data, setData] = useState<ExecSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary().then(setData).catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, []);

  const tiles: KpiTile[] = data
    ? [
        { label: "Open Sales Orders", value: data.sales.open_orders, color: "text-blue-600", href: "/dashboard/sales" },
        { label: "SO This Month", value: data.sales.orders_this_month, color: "text-blue-400", href: "/dashboard/sales" },
        { label: "Open Purchase Orders", value: data.procurement.open_purchase_orders, color: "text-purple-600", href: "/dashboard/procurement" },
        { label: "Production In Progress", value: data.production.in_progress, color: "text-green-600", href: "/dashboard/production" },
        { label: "Planned Production", value: data.production.planned, color: "text-green-400", href: "/dashboard/production" },
        { label: "Zero Stock Items", value: data.inventory.zero_stock_items, color: "text-red-600", href: "/dashboard/inventory", alert: data.inventory.zero_stock_items > 0 },
        { label: "Low Stock Items", value: data.inventory.low_stock_items, color: "text-orange-500", href: "/dashboard/inventory", alert: data.inventory.low_stock_items > 10 },
        { label: "Pending Approvals", value: data.approvals.pending, color: "text-amber-600", href: "/dashboard/approvals", alert: data.approvals.pending > 0 },
        { label: "Open Helpdesk Tickets", value: data.helpdesk.open_tickets, color: "text-red-500", href: "/dashboard/helpdesk", alert: data.helpdesk.open_tickets > 0 },
        { label: "Active Reports", value: data.reports.total_active, color: "text-gray-700", href: "/dashboard/report-builder" },
        { label: "Scheduled Reports", value: data.reports.scheduled, color: "text-gray-500", href: "/dashboard/report-builder/schedules" },
      ]
    : [];

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Executive KPI Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Cross-module summary · {data ? `As of ${data.as_of}` : "Loading…"}
          </p>
        </div>
        <button
          onClick={() => { setLoading(true); fetchSummary().then(setData).finally(() => setLoading(false)); }}
          disabled={loading}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}

      {loading && !data ? (
        <p className="text-gray-400 text-sm">Loading executive summary…</p>
      ) : (
        <>
          {/* KPI tiles */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {tiles.map((t) => (
              <div
                key={t.label}
                className={`bg-white border rounded-lg p-4 shadow-sm relative ${t.alert ? "border-red-300 bg-red-50" : ""}`}
              >
                {t.alert && (
                  <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                )}
                <p className="text-xs text-gray-500">{t.label}</p>
                <p className={`text-3xl font-bold mt-1 ${t.color}`}>{t.value.toLocaleString()}</p>
                {t.href && (
                  <Link href={t.href} className="text-xs text-blue-500 hover:text-blue-700 mt-1 block">
                    View →
                  </Link>
                )}
              </div>
            ))}
          </div>

          {/* Status breakdowns */}
          {data && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {[
                { title: "Sales Order Status", data: data.sales.by_status },
                { title: "Purchase Order Status", data: data.procurement.by_status },
                { title: "Production Order Status", data: data.production.by_status },
              ].map(({ title, data: d }) => (
                <div key={title} className="bg-white border rounded-lg p-4 shadow-sm">
                  <h2 className="text-sm font-semibold text-gray-700 mb-3">{title}</h2>
                  <div className="space-y-1.5">
                    {Object.entries(d).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between">
                        <span className="text-xs text-gray-600 capitalize">{status.toLowerCase().replace(/_/g, " ")}</span>
                        <span className="text-sm font-semibold text-gray-800">{count}</span>
                      </div>
                    ))}
                    {Object.keys(d).length === 0 && (
                      <p className="text-xs text-gray-400">No data</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Quick links */}
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Drill-Down Links</h2>
            <div className="flex flex-wrap gap-2">
              {[
                { href: "/dashboard/analytics", label: "BI Hub" },
                { href: "/dashboard/analytics/sales", label: "Sales Analytics" },
                { href: "/dashboard/analytics/inventory", label: "Inventory BI" },
                { href: "/dashboard/analytics/production", label: "Production BI" },
                { href: "/dashboard/analytics/procurement", label: "Procurement BI" },
                { href: "/dashboard/analytics/finance", label: "Finance BI" },
                { href: "/dashboard/report-builder", label: "Custom Reports" },
                { href: "/dashboard/report-builder/rls", label: "Row-Level Security" },
              ].map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="bg-blue-50 border border-blue-200 text-blue-700 text-xs rounded px-3 py-1.5 hover:bg-blue-100"
                >
                  {l.label}
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
