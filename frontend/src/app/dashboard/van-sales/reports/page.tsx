"use client";
import { useQuery } from "@tanstack/react-query";
import { vanSalesApi } from "@/lib/van_sales";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function VanSalesReportsPage() {
  const { data: routePerf = [] } = useQuery({
    queryKey: ["vs-route-perf"],
    queryFn: () => vanSalesApi.routePerformance(30),
  });
  const { data: driverPerf = [] } = useQuery({
    queryKey: ["vs-driver-perf"],
    queryFn: () => vanSalesApi.driverPerformance(30),
  });

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Van Sales Reports</h1>
        <p className="text-slate-500 text-sm mt-0.5">30-day performance analytics</p>
      </div>

      {/* Route performance */}
      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Route Performance (Sales)</h2>
        {routePerf.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={routePerf}>
              <XAxis dataKey="route_id" tick={{ fill: "#64748b", fontSize: 10 }}
                tickFormatter={(v) => v.slice(0, 6) + "…"} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#0d1829", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                formatter={(v: any) => [`KES ${Number(v).toLocaleString()}`, "Sales"]}
              />
              <Bar dataKey="total_sales" radius={[4, 4, 0, 0]} fill="#6366f1" />
            </BarChart>
          </ResponsiveContainer>
        ) : <p className="text-slate-600 text-center py-10">No route data</p>}
      </div>

      {/* Driver performance */}
      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Driver Performance</h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-2 text-left">Driver ID</th>
              <th className="px-4 py-2 text-right">Transactions</th>
              <th className="px-4 py-2 text-right">Total Sales</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {driverPerf
              .sort((a, b) => b.total_sales - a.total_sales)
              .map((d) => (
                <tr key={d.driver_id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-2 text-slate-400 font-mono text-xs">{d.driver_id?.slice(0, 8)}…</td>
                  <td className="px-4 py-2 text-right text-white">{d.txn_count}</td>
                  <td className="px-4 py-2 text-right text-emerald-400 font-medium">KES {d.total_sales.toLocaleString()}</td>
                </tr>
              ))}
            {driverPerf.length === 0 && <tr><td colSpan={3} className="text-center py-6 text-slate-600">No driver data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
