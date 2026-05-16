"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { salesApi } from "@/lib/sales";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

function SalesDashboardTab() {
  const router = useRouter();

  const { data: summary } = useQuery({
    queryKey: ["sales-summary"],
    queryFn: () => salesApi.getSalesSummary(),
  });

  const { data: outstanding = [] } = useQuery({
    queryKey: ["sales-outstanding"],
    queryFn: () => salesApi.getOutstandingInvoices(),
  });

  const { data: recentOrders = [] } = useQuery({
    queryKey: ["sales-orders-recent"],
    queryFn: () => salesApi.listOrders({}),
  });

  const overdueItems = outstanding.filter((r) => r.days_overdue && r.days_overdue > 0);

  const tiles = [
    { label: "Total Orders", value: summary?.total_orders ?? "—", sub: `${summary?.confirmed_orders ?? 0} active`, color: "text-gray-900", href: "/dashboard/sales/orders" },
    { label: "Order Value", value: summary ? `$${Number(summary.total_order_value).toLocaleString(undefined, { minimumFractionDigits: 0 })}` : "—", sub: "confirmed orders", color: "text-blue-700", href: "/dashboard/sales/orders" },
    { label: "Total Invoiced", value: summary ? `$${Number(summary.total_invoiced).toLocaleString(undefined, { minimumFractionDigits: 0 })}` : "—", sub: "all invoices", color: "text-gray-900", href: "/dashboard/sales/invoices" },
    { label: "Collected", value: summary ? `$${Number(summary.total_collected).toLocaleString(undefined, { minimumFractionDigits: 0 })}` : "—", sub: "payments received", color: "text-green-700", href: "/dashboard/sales/invoices" },
    { label: "Outstanding", value: summary ? `$${Number(summary.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 0 })}` : "—", sub: "to be collected", color: "text-orange-600", href: "/dashboard/sales/invoices" },
    { label: "Overdue Invoices", value: summary?.overdue_invoices ?? "—", sub: "past due date", color: summary?.overdue_invoices ? "text-red-600" : "text-gray-900", href: "/dashboard/sales/invoices?status=OVERDUE" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sales & Distribution</h1>
          <p className="text-sm text-gray-500 mt-1">Order to invoice workflow</p>
        </div>
        <Button onClick={() => router.push("/dashboard/sales/orders")}>New Sales Order</Button>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-3 gap-4">
        {tiles.map((tile) => (
          <button
            key={tile.label}
            onClick={() => router.push(tile.href)}
            className="bg-white rounded-lg border p-5 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tile.label}</p>
            <p className={`text-2xl font-bold mt-1 ${tile.color}`}>{tile.value}</p>
            <p className="text-xs text-gray-400 mt-1">{tile.sub}</p>
          </button>
        ))}
      </div>

      {/* Overdue alert */}
      {overdueItems.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-red-800">{overdueItems.length} Overdue Invoice(s)</p>
            <Button variant="secondary" onClick={() => router.push("/dashboard/sales/invoices")}>View All</Button>
          </div>
          <div className="space-y-1">
            {overdueItems.slice(0, 5).map((r) => (
              <div key={r.invoice_id} className="flex justify-between text-xs text-red-700">
                <span className="font-medium">{r.invoice_no}</span>
                <span>{r.customer_name}</span>
                <span>{r.days_overdue}d overdue</span>
                <span className="font-semibold">${Number(r.outstanding_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Manage Orders", desc: "Create, confirm, allocate", href: "/dashboard/sales/orders" },
          { label: "Customers", desc: "Customer master data", href: "/dashboard/sales/customers" },
          { label: "Dispatch Board", desc: "Pick, pack and dispatch", href: "/dashboard/sales/shipments" },
          { label: "Invoice & AR", desc: "Invoice and payment tracking", href: "/dashboard/sales/invoices" },
        ].map((link) => (
          <button
            key={link.href}
            onClick={() => router.push(link.href)}
            className="bg-white rounded-lg border p-4 text-left hover:border-indigo-300 hover:shadow-sm transition-all"
          >
            <p className="font-medium text-gray-900">{link.label}</p>
            <p className="text-xs text-gray-500 mt-1">{link.desc}</p>
          </button>
        ))}
      </div>

      {/* Recent orders */}
      {recentOrders.length > 0 && (
        <div className="bg-white rounded-lg border">
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Orders</h2>
            <Button variant="secondary" onClick={() => router.push("/dashboard/sales/orders")}>View All</Button>
          </div>
          <div className="divide-y">
            {recentOrders.slice(0, 8).map((so) => {
              const statusColor = so.status === "INVOICED" || so.status === "SHIPPED" ? "green"
                : so.status === "CONFIRMED" || so.status === "ALLOCATED" ? "blue"
                : so.status === "PICKING" ? "yellow"
                : so.status === "CANCELLED" ? "red" : "blue";
              return (
                <div
                  key={so.id}
                  onClick={() => router.push(`/dashboard/sales/orders/${so.id}`)}
                  className="px-6 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                >
                  <div>
                    <span className="font-medium text-sm">{so.order_no}</span>
                    <span className="text-sm text-gray-500 ml-3">{so.customer_name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-500">{so.requested_delivery_date}</span>
                    {so.total_value !== undefined && (
                      <span className="text-sm font-medium">{so.currency} {Number(so.total_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    )}
                    <Badge label={so.status} variant={statusColor as "green" | "blue" | "yellow" | "red"} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const SalesOrdersPage       = dynamic(() => import("@/app/dashboard/sales/orders/page"),        { ssr: false });
const SalesInvoicesPage     = dynamic(() => import("@/app/dashboard/sales/invoices/page"),      { ssr: false });
const SalesCustomersPage    = dynamic(() => import("@/app/dashboard/sales/customers/page"),     { ssr: false });
const SalesQuotesPage       = dynamic(() => import("@/app/dashboard/sales/quotes/page"),        { ssr: false });
const SalesShipmentsPage    = dynamic(() => import("@/app/dashboard/sales/shipments/page"),     { ssr: false });
const SalesDeliveryPage     = dynamic(() => import("@/app/dashboard/sales/delivery/page"),      { ssr: false });
const SalesCollectionsPage  = dynamic(() => import("@/app/dashboard/sales/collections/page"),   { ssr: false });
const SalesReturnsPage      = dynamic(() => import("@/app/dashboard/sales/returns/page"),       { ssr: false });
const SalesPricingPage      = dynamic(() => import("@/app/dashboard/sales/pricing/page"),       { ssr: false });
const SalesMarginPage       = dynamic(() => import("@/app/dashboard/sales/margin/page"),        { ssr: false });
const SalesDistributorsPage = dynamic(() => import("@/app/dashboard/sales/distributors/page"),  { ssr: false });
const SalesFieldSalesPage   = dynamic(() => import("@/app/dashboard/sales/field-sales/page"),   { ssr: false });
const SalesReportsPage      = dynamic(() => import("@/app/dashboard/sales/reports/page"),       { ssr: false });
const PriceListsPage        = dynamic(() => import("@/app/dashboard/price-lists/page"),         { ssr: false });
const DynamicPricingPage    = dynamic(() => import("@/app/dashboard/dynamic-pricing/page"),     { ssr: false });
const ContractsPage         = dynamic(() => import("@/app/dashboard/contracts/page"),           { ssr: false });
const RecurringOrdersPage   = dynamic(() => import("@/app/dashboard/recurring-orders/page"),    { ssr: false });
const CommissionsPage       = dynamic(() => import("@/app/dashboard/commissions/page"),         { ssr: false });
const SecondarySalesPage    = dynamic(() => import("@/app/dashboard/secondary-sales/page"),     { ssr: false });
const VanSalesPage          = dynamic(() => import("@/app/dashboard/van-sales/page"),           { ssr: false });
const PortalPage            = dynamic(() => import("@/app/dashboard/portal/page"),              { ssr: false });

export default function SalesPage() {
  const tabs = [
    { key: "overview",       label: "Overview",        permission: "sales.view", content: <SalesDashboardTab /> },
    { key: "orders",         label: "Orders",          permission: "sales.view", content: <SalesOrdersPage /> },
    { key: "invoices",       label: "Invoices",        permission: "sales.view", content: <SalesInvoicesPage /> },
    { key: "customers",      label: "Customers",       permission: "sales.view", content: <SalesCustomersPage /> },
    { key: "quotes",         label: "Quotes",          permission: "sales.view", content: <SalesQuotesPage /> },
    { key: "shipments",      label: "Shipments",       permission: "sales.view", content: <SalesShipmentsPage /> },
    { key: "delivery",       label: "Delivery",        permission: "sales.view", content: <SalesDeliveryPage /> },
    { key: "collections",    label: "Collections",     permission: "sales.view", content: <SalesCollectionsPage /> },
    { key: "returns",        label: "Returns",         permission: "sales.view", content: <SalesReturnsPage /> },
    { key: "pricing",        label: "Pricing",         permission: "sales.view", content: <SalesPricingPage /> },
    { key: "price-lists",    label: "Price Lists",     permission: "sales.view", content: <PriceListsPage /> },
    { key: "dynamic-pricing",label: "Dynamic Pricing", permission: "sales.view", content: <DynamicPricingPage /> },
    { key: "contracts",      label: "Contracts",       permission: "sales.view", content: <ContractsPage /> },
    { key: "recurring",      label: "Recurring",       permission: "sales.view", content: <RecurringOrdersPage /> },
    { key: "commissions",    label: "Commissions",     permission: "sales.view", content: <CommissionsPage /> },
    { key: "secondary",      label: "Secondary Sales", permission: "sales.view", content: <SecondarySalesPage /> },
    { key: "van-sales",      label: "Van Sales",       permission: "sales.view", content: <VanSalesPage /> },
    { key: "distributors",   label: "Distributors",    permission: "sales.view", content: <SalesDistributorsPage /> },
    { key: "field-sales",    label: "Field Sales",     permission: "sales.view", content: <SalesFieldSalesPage /> },
    { key: "margin",         label: "Margin",          permission: "sales.view", content: <SalesMarginPage /> },
    { key: "portal",         label: "Customer Portal", permission: "sales.view", content: <PortalPage /> },
    { key: "reports",        label: "Reports",         permission: "sales.view", content: <SalesReportsPage /> },
  ];
  return (
    <ModuleWorkspace
      title="Sales"
      description="Orders, invoices, customers, pricing, collections, van sales"
      permission="sales.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
