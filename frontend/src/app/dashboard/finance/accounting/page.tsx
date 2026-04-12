"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { financeApi, AccountingDashboard } from "@/lib/finance";

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}
function fmtCurrency(n: number) {
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(0)}K`;
  return `KES ${fmt(n)}`;
}

function KpiCard({
  label, value, sub, color,
}: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

const STATUS_PILL: Record<string, string> = {
  PAID: "bg-green-100 text-green-700",
  PARTIALLY_PAID: "bg-yellow-100 text-yellow-700",
  ISSUED: "bg-blue-100 text-blue-700",
  RECEIVED: "bg-blue-100 text-blue-700",
  OVERDUE: "bg-red-100 text-red-700",
  DRAFT: "bg-gray-100 text-gray-500",
  CANCELLED: "bg-gray-100 text-gray-400 line-through",
};

export default function AccountingDashboardPage() {
  const { data, isLoading } = useQuery<AccountingDashboard>({
    queryKey: ["accounting-dashboard"],
    queryFn: financeApi.accountingDashboard,
    staleTime: 30_000,
  });

  const cashFlowPositive = (data?.cash_flow ?? 0) >= 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-10">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Finance &amp; Accounting</h1>
        <p className="text-sm text-gray-400 mt-0.5">Money movement summary — invoices, payments, balances</p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <KpiCard
          label="Total Revenue"
          value={isLoading ? "—" : fmtCurrency(data?.total_revenue ?? 0)}
          sub="All issued invoices"
          color="text-indigo-700"
        />
        <KpiCard
          label="Receivables"
          value={isLoading ? "—" : fmtCurrency(data?.total_receivables ?? 0)}
          sub={data ? `${data.overdue_sales_invoices} overdue` : undefined}
          color={(data?.total_receivables ?? 0) > 0 ? "text-orange-600" : "text-green-600"}
        />
        <KpiCard
          label="Total Cost"
          value={isLoading ? "—" : fmtCurrency(data?.total_cost ?? 0)}
          sub="Purchase invoices"
          color="text-gray-800"
        />
        <KpiCard
          label="Payables"
          value={isLoading ? "—" : fmtCurrency(data?.total_payables ?? 0)}
          sub={data ? `${data.overdue_purchase_invoices} overdue` : undefined}
          color={(data?.total_payables ?? 0) > 0 ? "text-red-600" : "text-green-600"}
        />
        <KpiCard
          label="Net Cash Flow"
          value={isLoading ? "—" : fmtCurrency(data?.cash_flow ?? 0)}
          sub="Receivables − Payables"
          color={cashFlowPositive ? "text-green-600" : "text-red-600"}
        />
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[
          { label: "Customers Ledger", href: "/dashboard/finance/accounting/customers-ledger", icon: "👥" },
          { label: "Suppliers Ledger", href: "/dashboard/finance/accounting/suppliers-ledger", icon: "🏭" },
          { label: "Sales Invoices",   href: "/dashboard/finance/accounting/sales-invoices",   icon: "📄" },
          { label: "Purchase Invoices",href: "/dashboard/finance/accounting/purchase-invoices",icon: "📦" },
          { label: "Payments",         href: "/dashboard/finance/accounting/payments",          icon: "💳" },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 bg-white rounded-xl border border-gray-100 shadow-sm p-4 hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <span className="text-2xl">{item.icon}</span>
            <span className="font-medium text-gray-800 text-sm">{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Recent invoices */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent Sales Invoices */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <h2 className="font-semibold text-gray-800">Recent Sales Invoices</h2>
            <Link href="/dashboard/finance/accounting/sales-invoices"
              className="text-xs text-indigo-600 hover:underline">View all</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {isLoading && (
              <div className="p-4 space-y-2">
                {[1,2,3].map(i => <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />)}
              </div>
            )}
            {!isLoading && (data?.recent_sales_invoices ?? []).length === 0 && (
              <p className="text-sm text-gray-400 p-4">No sales invoices found.</p>
            )}
            {(data?.recent_sales_invoices ?? []).map((inv) => (
              <div key={inv.id} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50">
                <div>
                  <p className="text-sm font-medium text-gray-900">{inv.invoice_no}</p>
                  <p className="text-xs text-gray-400">{inv.customer} · {inv.date}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">{fmtCurrency(inv.total)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[inv.status] ?? "bg-gray-100 text-gray-500"}`}>
                    {inv.status.replace("_", " ")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Purchase Invoices */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
            <h2 className="font-semibold text-gray-800">Recent Purchase Invoices</h2>
            <Link href="/dashboard/finance/accounting/purchase-invoices"
              className="text-xs text-indigo-600 hover:underline">View all</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {isLoading && (
              <div className="p-4 space-y-2">
                {[1,2,3].map(i => <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />)}
              </div>
            )}
            {!isLoading && (data?.recent_purchase_invoices ?? []).length === 0 && (
              <p className="text-sm text-gray-400 p-4">No purchase invoices found.</p>
            )}
            {(data?.recent_purchase_invoices ?? []).map((inv) => (
              <div key={inv.id} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50">
                <div>
                  <p className="text-sm font-medium text-gray-900">{inv.invoice_no}</p>
                  <p className="text-xs text-gray-400">{inv.supplier} · {inv.date}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">{fmtCurrency(inv.total)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_PILL[inv.status] ?? "bg-gray-100 text-gray-500"}`}>
                    {inv.status.replace("_", " ")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
