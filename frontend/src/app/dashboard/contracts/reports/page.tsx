"use client";
import { useQuery } from "@tanstack/react-query";
import { contractsApi } from "@/lib/contracts";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function ContractReportsPage() {
  const { data: summary } = useQuery({ queryKey: ["ct-summary"], queryFn: () => contractsApi.reportSummary() });
  const { data: perf = [] } = useQuery({ queryKey: ["ct-perf-report"], queryFn: () => contractsApi.reportPerformance() });
  const s = summary as any;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Contract Reports</h1>
        <p className="text-slate-500 text-sm mt-0.5">Portfolio health and performance analytics</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Total", value: s?.total ?? 0, color: "text-white" },
          { label: "Active", value: s?.active ?? 0, color: "text-emerald-400" },
          { label: "Expiring 30d", value: s?.expiring_30_days ?? 0, color: "text-amber-400" },
          { label: "Draft", value: s?.draft ?? 0, color: "text-slate-400" },
          { label: "Under Review", value: s?.under_review ?? 0, color: "text-blue-400" },
        ].map((c) => (
          <div key={c.label} className="glow-card p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{c.label}</p>
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Contract Performance — Average Achievement %</h2>
        {perf.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={perf}>
              <XAxis dataKey="contract_id" tick={{ fill: "#64748b", fontSize: 10 }}
                tickFormatter={(v) => v.slice(0, 6) + "…"} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ background: "#0d1829", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                formatter={(v: any) => [`${Number(v).toFixed(1)}%`, "Achievement"]}
              />
              <Bar dataKey="avg_achievement_pct" radius={[4, 4, 0, 0]} fill="#6366f1" />
            </BarChart>
          </ResponsiveContainer>
        ) : <p className="text-slate-600 text-center py-10">No performance data yet</p>}
      </div>

      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Rebate Earned by Contract</h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-2 text-left">Contract ID</th>
              <th className="px-4 py-2 text-right">Avg Achievement %</th>
              <th className="px-4 py-2 text-right">Total Rebate Earned</th>
              <th className="px-4 py-2 text-right">Periods Tracked</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {perf.sort((a, b) => b.total_rebate_earned - a.total_rebate_earned).map((p) => (
              <tr key={p.contract_id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-2 font-mono text-xs text-indigo-300">{p.contract_id.slice(0, 8)}…</td>
                <td className="px-4 py-2 text-right">
                  <span className={`font-medium ${p.avg_achievement_pct >= 100 ? "text-emerald-400" : p.avg_achievement_pct >= 60 ? "text-amber-400" : "text-red-400"}`}>
                    {p.avg_achievement_pct.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-2 text-right text-emerald-400 font-medium">KES {p.total_rebate_earned.toLocaleString()}</td>
                <td className="px-4 py-2 text-right text-slate-400">{p.periods}</td>
              </tr>
            ))}
            {perf.length === 0 && <tr><td colSpan={4} className="text-center py-6 text-slate-600">No data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
