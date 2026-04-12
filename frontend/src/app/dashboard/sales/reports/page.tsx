"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { salesApi } from "@/lib/sales";
import { fieldSalesApi } from "@/lib/field_sales";
import { distributorsApi } from "@/lib/distribution";

type ReportView = "overview" | "by_rep" | "by_region" | "by_product" | "by_customer";

export default function SalesReportsPage() {
  const [view, setView] = useState<ReportView>("overview");
  const [from, setFrom] = useState(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().split("T")[0];
  });
  const [to, setTo] = useState(new Date().toISOString().split("T")[0]);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["sales-report-orders", from, to],
    queryFn: () => salesApi.listOrders({ from_date: from, to_date: to }),
  });

  const { data: reps = [] } = useQuery({
    queryKey: ["sales-reps"],
    queryFn: () => fieldSalesApi.listReps(),
  });

  const { data: distributors = [] } = useQuery({
    queryKey: ["distributors"],
    queryFn: () => distributorsApi.list(),
  });

  // Aggregate helpers
  type ExtendedOrder = typeof orders[0] & { total_amount?: number; sales_rep_id?: string; customer_city?: string };
  const extOrders = orders as ExtendedOrder[];

  const totalRevenue = extOrders.reduce((s, o) => s + (o.total_value ?? o.total_amount ?? 0), 0);
  const totalOrders = orders.length;
  const avgOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0;
  const confirmedOrders = orders.filter((o) => o.status !== "CANCELLED" && o.status !== "DRAFT").length;

  // By rep
  const repMap: Record<string, { name: string; orders: number; revenue: number }> = {};
  extOrders.forEach((o) => {
    if (o.sales_rep_id) {
      const rep = reps.find((r) => r.id === o.sales_rep_id);
      const name = rep?.name ?? o.sales_rep_id.slice(0, 8);
      if (!repMap[o.sales_rep_id]) repMap[o.sales_rep_id] = { name, orders: 0, revenue: 0 };
      repMap[o.sales_rep_id].orders++;
      repMap[o.sales_rep_id].revenue += o.total_value ?? o.total_amount ?? 0;
    }
  });
  const byRep = Object.values(repMap).sort((a, b) => b.revenue - a.revenue);

  // By region (customer city as proxy)
  const regionMap: Record<string, { orders: number; revenue: number }> = {};
  extOrders.forEach((o) => {
    const region = o.customer_city ?? "Unknown";
    if (!regionMap[region]) regionMap[region] = { orders: 0, revenue: 0 };
    regionMap[region].orders++;
    regionMap[region].revenue += o.total_value ?? o.total_amount ?? 0;
  });
  const byRegion = Object.entries(regionMap)
    .map(([region, v]) => ({ region, ...v }))
    .sort((a, b) => b.revenue - a.revenue);

  // By product
  const productMap: Record<string, { name: string; qty: number; revenue: number }> = {};
  extOrders.forEach((o) => {
    (o.lines ?? []).forEach((l) => {
      if (!productMap[l.product_id]) productMap[l.product_id] = { name: l.product_name ?? l.product_id.slice(0, 8), qty: 0, revenue: 0 };
      productMap[l.product_id].qty += l.shipped_quantity || l.ordered_quantity || 0;
      productMap[l.product_id].revenue += l.line_total ?? 0;
    });
  });
  const byProduct = Object.values(productMap).sort((a, b) => b.revenue - a.revenue).slice(0, 20);

  // By customer
  const custMap: Record<string, { name: string; orders: number; revenue: number }> = {};
  extOrders.forEach((o) => {
    const key = o.customer_id;
    if (!custMap[key]) custMap[key] = { name: o.customer_name ?? key.slice(0, 8), orders: 0, revenue: 0 };
    custMap[key].orders++;
    custMap[key].revenue += o.total_value ?? o.total_amount ?? 0;
  });
  const byCustomer = Object.values(custMap).sort((a, b) => b.revenue - a.revenue).slice(0, 20);

  const views: { id: ReportView; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "by_rep", label: "By Rep" },
    { id: "by_region", label: "By Region" },
    { id: "by_product", label: "By Product" },
    { id: "by_customer", label: "By Customer" },
  ];

  const maxRevenue = Math.max(
    ...([...byRep, ...byRegion, ...byProduct, ...byCustomer].map((x) => x.revenue)),
    1,
  );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sales Reports</h1>
          <p className="text-sm text-gray-500 mt-1">Revenue · Volume · Rep performance · Regional breakdown</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <span className="text-gray-400 text-sm">→</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Overview KPIs — always visible */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total Revenue", value: `KES ${totalRevenue.toLocaleString()}`, color: "text-indigo-600" },
          { label: "Orders", value: totalOrders, color: "text-gray-800" },
          { label: "Confirmed", value: confirmedOrders, color: "text-green-600" },
          { label: "Avg. Order Value", value: `KES ${Math.round(avgOrderValue).toLocaleString()}`, color: "text-blue-600" },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            <p className="text-xs text-gray-500 mt-1">{k.label}</p>
          </div>
        ))}
      </div>

      {/* View tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {views.map((v) => (
          <button
            key={v.id}
            onClick={() => setView(v.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              view === v.id
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <>
          {/* Overview */}
          {view === "overview" && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <StatCard label="Reps Active" value={reps.filter((r) => r.is_active).length} icon="🏍️" />
                <StatCard label="Distributors" value={distributors.length} icon="🏭" />
                <StatCard label="Cancelled Orders" value={orders.filter((o) => o.status === "CANCELLED").length} icon="❌" />
              </div>

              {/* Order status breakdown */}
              <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-gray-700 mb-3">Orders by Status</p>
                {(["DRAFT", "CONFIRMED", "ALLOCATED", "PICKING", "SHIPPED", "INVOICED", "CANCELLED"] as const).map((status) => {
                  const count = orders.filter((o) => o.status === status).length;
                  const pct = totalOrders > 0 ? (count / totalOrders) * 100 : 0;
                  const colors: Record<string, string> = {
                    DRAFT: "bg-gray-300",
                    CONFIRMED: "bg-blue-400",
                    ALLOCATED: "bg-yellow-400",
                    PICKING: "bg-orange-400",
                    SHIPPED: "bg-indigo-400",
                    INVOICED: "bg-green-500",
                    CANCELLED: "bg-red-400",
                  };
                  return (
                    <div key={status} className="flex items-center gap-3 mb-2">
                      <span className="text-xs text-gray-500 w-20">{status}</span>
                      <div className="flex-1 h-2 rounded-full bg-gray-100">
                        <div className={`h-2 rounded-full ${colors[status]}`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs font-medium text-gray-700 w-8 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* By Rep */}
          {view === "by_rep" && (
            byRep.length === 0 ? (
              <p className="text-gray-400 text-sm py-8 text-center">No field sales orders in this period.</p>
            ) : (
              <RevenueTable
                rows={byRep.map((r) => ({ label: r.name, orders: r.orders, revenue: r.revenue }))}
                maxRevenue={maxRevenue}
              />
            )
          )}

          {/* By Region */}
          {view === "by_region" && (
            byRegion.length === 0 ? (
              <p className="text-gray-400 text-sm py-8 text-center">No regional data available.</p>
            ) : (
              <RevenueTable
                rows={byRegion.map((r) => ({ label: r.region, orders: r.orders, revenue: r.revenue }))}
                maxRevenue={maxRevenue}
              />
            )
          )}

          {/* By Product */}
          {view === "by_product" && (
            byProduct.length === 0 ? (
              <p className="text-gray-400 text-sm py-8 text-center">No product data available.</p>
            ) : (
              <div className="space-y-2">
                {byProduct.map((p, i) => (
                  <div key={i} className="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-sm font-medium text-gray-800">{p.name}</p>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-gray-400">{p.qty.toLocaleString()} units</span>
                        <span className="font-bold text-gray-900">KES {p.revenue.toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-gray-100">
                      <div
                        className="h-1.5 rounded-full bg-indigo-500"
                        style={{ width: `${(p.revenue / maxRevenue) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )
          )}

          {/* By Customer */}
          {view === "by_customer" && (
            byCustomer.length === 0 ? (
              <p className="text-gray-400 text-sm py-8 text-center">No customer data available.</p>
            ) : (
              <RevenueTable
                rows={byCustomer.map((c) => ({ label: c.name, orders: c.orders, revenue: c.revenue }))}
                maxRevenue={maxRevenue}
              />
            )
          )}
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm flex items-center gap-3">
      <span className="text-3xl">{icon}</span>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}

function RevenueTable({
  rows,
  maxRevenue,
}: {
  rows: { label: string; orders: number; revenue: number }[];
  maxRevenue: number;
}) {
  return (
    <div className="space-y-2">
      {rows.map((r, i) => (
        <div key={i} className="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 w-5 text-right">{i + 1}</span>
              <p className="text-sm font-medium text-gray-800">{r.label}</p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-400">{r.orders} order{r.orders !== 1 ? "s" : ""}</span>
              <span className="font-bold text-gray-900 min-w-[100px] text-right">
                KES {r.revenue.toLocaleString()}
              </span>
            </div>
          </div>
          <div className="h-1.5 rounded-full bg-gray-100 ml-7">
            <div
              className="h-1.5 rounded-full bg-indigo-500"
              style={{ width: `${(r.revenue / maxRevenue) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
