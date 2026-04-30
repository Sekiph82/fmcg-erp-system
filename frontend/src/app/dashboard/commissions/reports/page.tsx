"use client";
import { useQuery } from "@tanstack/react-query";
import { commissionsApi } from "@/lib/commissions";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function CommissionsReportsPage() {
  const { data: summary } = useQuery({ queryKey: ["cm-summary"], queryFn: () => commissionsApi.reportSummary() });
  const { data: byPeriod = [] } = useQuery({ queryKey: ["cm-by-period"], queryFn: () => commissionsApi.reportByPeriod() });
  const s = summary as any;

  // Aggregate by period for chart
  const periodAgg: Record<string, number> = {};
  byPeriod.forEach((r: any) => {
    periodAgg[r.period] = (periodAgg[r.period] || 0) + r.total_commission;
  });
  const chartData = Object.entries(periodAgg).map(([period, total]) => ({ period, total })).sort((a, b) => a.period.localeCompare(b.period));

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Commission Reports</h1>
        <p className="text-slate-500 text-sm mt-0.5">Performance and payout analytics</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Total Transactions", value: s?.total_txns ?? 0, color: "text-white" },
          { label: "Pending", value: s?.pending ?? 0, color: "text-amber-400" },
          { label: "Approved", value: s?.approved ?? 0, color: "text-blue-400" },
          { label: "Total Commission", value: `KES ${(s?.total_commission ?? 0).toLocaleString()}`, color: "text-emerald-400" },
          { label: "Paid Out", value: `KES ${(s?.paid_commission ?? 0).toLocaleString()}`, color: "text-white" },
        ].map((c) => (
          <div key={c.label} className="glow-card p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{c.label}</p>
            <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Commission by Period</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <XAxis dataKey="period" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#0d1829", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                formatter={(v: any) => [`KES ${Number(v).toLocaleString()}`, "Commission"]}
              />
              <Bar dataKey="total" radius={[4, 4, 0, 0]} fill="#10b981" />
            </BarChart>
          </ResponsiveContainer>
        ) : <p className="text-slate-600 text-center py-10">No data yet</p>}
      </div>

      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">By Rep / Period</h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-2 text-left">Period</th>
              <th className="px-4 py-2 text-left">Rep ID</th>
              <th className="px-4 py-2 text-right">Commission</th>
              <th className="px-4 py-2 text-right">Transactions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {byPeriod.sort((a: any, b: any) => b.period.localeCompare(a.period)).map((r: any, i: number) => (
              <tr key={i} className="hover:bg-white/[0.02]">
                <td className="px-4 py-2 text-slate-300 font-mono text-xs">{r.period}</td>
                <td className="px-4 py-2 text-slate-400 font-mono text-xs">{r.sales_rep_id ? r.sales_rep_id.slice(0, 8) + "…" : "—"}</td>
                <td className="px-4 py-2 text-right text-emerald-400 font-medium">KES {r.total_commission.toLocaleString()}</td>
                <td className="px-4 py-2 text-right text-slate-400">{r.txn_count}</td>
              </tr>
            ))}
            {byPeriod.length === 0 && <tr><td colSpan={4} className="text-center py-6 text-slate-600">No data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
