"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scApi, fmt, orderStatusBadge } from "@/lib/subcontracting";

function Kpi({ label, value, warn, sub }: { label: string; value: string|number; warn?: boolean; sub?: string }) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${warn ? "border-red-200" : "border-gray-200"}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${warn ? "text-red-600" : "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function SubcontractingDashboard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["sc-dashboard"], queryFn: scApi.getDashboard });
  const { data: orders } = useQuery({ queryKey: ["sc-orders"], queryFn: () => scApi.listOrders({ limit: 10 }) });

  const runAI = useMutation({
    mutationFn: () => scApi.runAI(),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["sc-dashboard"] }); alert(`AI ran — ${r.generated} recommendation(s) generated`); },
  });

  if (isLoading) return <div className="p-8 text-gray-400">Loading…</div>;
  if (!data) return <div className="p-8 text-red-500">Failed to load dashboard.</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Subcontracting</h1>
          <p className="text-sm text-gray-500">External manufacturing · Material control · Yield tracking</p>
        </div>
        <div className="flex gap-2">
          <a href="/dashboard/subcontracting/locations" className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50">
            Manage Locations
          </a>
          <button onClick={() => runAI.mutate()} disabled={runAI.isPending}
            className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50 disabled:opacity-50">
            {runAI.isPending ? "Running AI…" : "Run AI Agents"}
          </button>
          <a href="/dashboard/subcontracting/orders" className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
            + New Order
          </a>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <Kpi label="Total Orders" value={data.total_orders} />
        <Kpi label="Active" value={data.active_orders} />
        <Kpi label="Overdue" value={data.overdue_orders} warn={data.overdue_orders > 0} />
        <Kpi label="Completed" value={data.completed_orders} />
        <Kpi label="Avg Yield" value={data.avg_yield_pct != null ? `${fmt(data.avg_yield_pct, 1)}%` : "—"} />
        <Kpi label="Scrap Cost" value={`KES ${fmt(data.total_scrap_cost, 0)}`} warn={data.total_scrap_cost > 0} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Material Issued Value" value={`KES ${fmt(data.total_material_issued_value, 0)}`} />
        <Kpi label="AI Recommendations" value={data.ai_recs_count} />
        <Kpi label="Suppliers" value={data.supplier_count} />
        <Kpi label="SC Locations" value={data.locations_count} />
      </div>

      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Recent Orders</h2>
          <a href="/dashboard/subcontracting/orders" className="text-xs text-blue-600 hover:underline">View all →</a>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-4 py-2">Order No</th>
              <th className="text-left px-4 py-2">Supplier</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-right px-4 py-2">Due Date</th>
              <th className="text-right px-4 py-2">Service Cost</th>
              <th className="text-left px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(orders ?? []).map((o) => (
              <tr key={o.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono font-medium text-blue-700">{o.order_no}</td>
                <td className="px-4 py-2">{o.supplier_name}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${orderStatusBadge(o.status)}`}>{o.status}</span>
                </td>
                <td className="px-4 py-2 text-right text-gray-600">{o.expected_completion_date ?? "—"}</td>
                <td className="px-4 py-2 text-right">{o.total_service_cost ? `KES ${fmt(o.total_service_cost, 0)}` : "—"}</td>
                <td className="px-4 py-2">
                  <a href={`/dashboard/subcontracting/orders?id=${o.id}`} className="text-blue-600 hover:underline text-xs">Manage →</a>
                </td>
              </tr>
            ))}
            {!orders?.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No orders yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Orders", href: "/dashboard/subcontracting/orders", desc: "Create & manage subcontract orders" },
          { label: "Subcontractor Stock", href: "/dashboard/subcontracting/stock", desc: "Materials at subcontractor sites" },
          { label: "Yield Analysis", href: "/dashboard/subcontracting/yield", desc: "Yield vs expected · Scrap tracking" },
          { label: "AI Agents", href: "/dashboard/subcontracting/ai", desc: "Performance · Cost · Risk insights" },
        ].map((l) => (
          <a key={l.href} href={l.href} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors block">
            <p className="font-medium text-gray-800 text-sm">{l.label}</p>
            <p className="text-xs text-gray-500 mt-1">{l.desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
