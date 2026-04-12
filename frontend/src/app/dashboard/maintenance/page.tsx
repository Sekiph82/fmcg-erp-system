"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { maintenanceApi } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";

export default function MaintenanceDashboardPage() {
  const router = useRouter();

  const { data: assets = [] } = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
  });

  const { data: overduePM = [] } = useQuery({
    queryKey: ["maint-overdue-pm"],
    queryFn: () => maintenanceApi.reportOverduePM(),
  });

  const { data: breakdowns = [] } = useQuery({
    queryKey: ["maint-breakdowns"],
    queryFn: () => maintenanceApi.listBreakdowns(),
  });

  const { data: spareParts = [] } = useQuery({
    queryKey: ["maint-spares"],
    queryFn: () => maintenanceApi.listSpareParts(),
  });

  const underMaintenance = assets.filter((a) => a.status === "UNDER_MAINTENANCE");
  const openBreakdowns = breakdowns.filter((b) => b.status === "OPEN" || b.status === "IN_REPAIR");
  const lowStock = spareParts.filter((s) => s.reorder_level != null && s.current_stock <= s.reorder_level!);

  const tiles = [
    { label: "Total Assets", value: assets.length, sub: `${underMaintenance.length} under maintenance`, color: "text-gray-900", href: "/dashboard/maintenance/assets" },
    { label: "Open Breakdowns", value: openBreakdowns.length, sub: "active / in-repair", color: openBreakdowns.length > 0 ? "text-red-600" : "text-gray-700", href: "/dashboard/maintenance/breakdowns" },
    { label: "Overdue PMs", value: overduePM.length, sub: "past due date", color: overduePM.length > 0 ? "text-orange-600" : "text-gray-700", href: "/dashboard/maintenance/plans" },
    { label: "Low Stock Spares", value: lowStock.length, sub: "at or below reorder level", color: lowStock.length > 0 ? "text-yellow-600" : "text-gray-700", href: "/dashboard/maintenance/spares" },
  ];

  const severityColor = (s: string) =>
    s === "CRITICAL" ? "red" : s === "HIGH" ? "red" : s === "MEDIUM" ? "yellow" : "gray";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Maintenance</h1>
          <p className="text-sm text-gray-500 mt-1">Asset register, preventive maintenance & breakdowns</p>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-4 gap-4">
        {tiles.map((tile) => (
          <button
            key={tile.label}
            onClick={() => router.push(tile.href)}
            className="bg-white rounded-lg border p-5 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tile.label}</p>
            <p className={`text-3xl font-bold mt-1 ${tile.color}`}>{tile.value}</p>
            <p className="text-xs text-gray-400 mt-1">{tile.sub}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Open breakdowns */}
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Open Breakdowns</h2>
            <button className="text-xs text-indigo-600 hover:underline" onClick={() => router.push("/dashboard/maintenance/breakdowns")}>View all</button>
          </div>
          {openBreakdowns.length === 0 ? (
            <p className="px-5 py-8 text-sm text-gray-400 text-center">No open breakdowns</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-5 py-2 text-left">Asset</th>
                  <th className="px-5 py-2 text-left">Reason</th>
                  <th className="px-5 py-2 text-left">Severity</th>
                  <th className="px-5 py-2 text-left">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {openBreakdowns.slice(0, 8).map((bd) => (
                  <tr key={bd.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => router.push("/dashboard/maintenance/breakdowns")}>
                    <td className="px-5 py-2 font-medium">{bd.asset_name || bd.asset_no}</td>
                    <td className="px-5 py-2 text-gray-600 truncate max-w-xs">{bd.reason}</td>
                    <td className="px-5 py-2"><Badge label={bd.severity} variant={severityColor(bd.severity) as "red" | "yellow" | "gray"} /></td>
                    <td className="px-5 py-2 text-gray-500 text-xs">{new Date(bd.start_time).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Overdue PMs */}
        <div className="bg-white rounded-lg border">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Overdue PM Plans</h2>
            <button className="text-xs text-indigo-600 hover:underline" onClick={() => router.push("/dashboard/maintenance/plans")}>View all</button>
          </div>
          {overduePM.length === 0 ? (
            <p className="px-5 py-8 text-sm text-gray-400 text-center">All PMs are up to date</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                  <th className="px-5 py-2 text-left">Asset</th>
                  <th className="px-5 py-2 text-left">Plan</th>
                  <th className="px-5 py-2 text-left">Due</th>
                  <th className="px-5 py-2 text-right">Days Overdue</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {overduePM.slice(0, 8).map((r) => (
                  <tr key={r.plan_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => router.push("/dashboard/maintenance/plans")}>
                    <td className="px-5 py-2 font-medium">{r.asset_name}</td>
                    <td className="px-5 py-2 text-gray-600">{r.plan_name}</td>
                    <td className="px-5 py-2 text-gray-500">{r.next_due_date}</td>
                    <td className="px-5 py-2 text-right">
                      <span className={`font-semibold ${r.days_overdue > 14 ? "text-red-600" : "text-orange-500"}`}>{r.days_overdue}d</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Asset Register", desc: "Manage machines, equipment and production lines", href: "/dashboard/maintenance/assets" },
          { label: "PM Plans & Work Orders", desc: "Preventive maintenance schedules and completion tracking", href: "/dashboard/maintenance/plans" },
          { label: "Breakdown Records", desc: "Log and resolve equipment failures with MES linkage", href: "/dashboard/maintenance/breakdowns" },
          { label: "Spare Parts", desc: "Spare part inventory with reorder alerts", href: "/dashboard/maintenance/spares" },
          { label: "Maintenance Reports", desc: "MTBF, MTTR, downtime by machine, overdue PM list", href: "/dashboard/maintenance/reports" },
        ].map((item) => (
          <button
            key={item.href}
            onClick={() => router.push(item.href)}
            className="bg-white rounded-lg border p-4 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="font-semibold text-sm text-gray-800">{item.label}</p>
            <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
