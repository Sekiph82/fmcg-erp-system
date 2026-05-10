"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motoSalesApi, scoreColor } from "@/lib/moto_sales";

function ScoreBadge({ score }: { score?: number }) {
  return (
    <span className={`text-lg font-bold ${scoreColor(score)}`}>
      {score != null ? score.toFixed(1) : "—"}
    </span>
  );
}

export default function RiderPerformancePage() {
  const qc = useQueryClient();
  const today = new Date().toISOString().split("T")[0];
  const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().split("T")[0];

  const [tab, setTab] = useState<"leaderboard" | "daily">("leaderboard");
  const [computeForm, setComputeForm] = useState({ driver_id: "", perf_date: today });

  const { data: leaderboard = [] } = useQuery({
    queryKey: ["leaderboard", weekAgo, today],
    queryFn: () => motoSalesApi.leaderboard({ from_date: weekAgo, to_date: today }),
    enabled: tab === "leaderboard",
  });

  const { data: dailyPerf = [] } = useQuery({
    queryKey: ["perf-list"],
    queryFn: () => motoSalesApi.listPerformance({ from_date: weekAgo, to_date: today }),
    enabled: tab === "daily",
  });

  const computeMut = useMutation({
    mutationFn: () => motoSalesApi.computePerformance(computeForm.driver_id, computeForm.perf_date),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
      qc.invalidateQueries({ queryKey: ["perf-list"] });
    },
  });

  const medals = ["🥇", "🥈", "🥉"];

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Rider Performance</h1>
          <p className="text-slate-500 text-sm mt-0.5">7-day scoring, leaderboard, and daily drill-down</p>
        </div>
        <div className="flex gap-2 items-center">
          <input value={computeForm.driver_id} onChange={(e) => setComputeForm((f) => ({ ...f, driver_id: e.target.value }))}
            placeholder="Driver UUID"
            className="w-48 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white focus:outline-none font-mono" />
          <input type="date" value={computeForm.perf_date} onChange={(e) => setComputeForm((f) => ({ ...f, perf_date: e.target.value }))}
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white focus:outline-none" />
          <button onClick={() => computeMut.mutate()} disabled={!computeForm.driver_id || computeMut.isPending}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium disabled:opacity-50">
            {computeMut.isPending ? "Computing…" : "Compute"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/[0.07]">
        {(["leaderboard", "daily"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-indigo-500 text-indigo-300" : "border-transparent text-slate-500 hover:text-slate-300"}`}>
            {t === "leaderboard" ? "Leaderboard (7d)" : "Daily Records"}
          </button>
        ))}
      </div>

      {tab === "leaderboard" && (
        <div className="space-y-3">
          {/* Top 3 podium */}
          {leaderboard.length >= 3 && (
            <div className="grid grid-cols-3 gap-4 mb-6">
              {[1, 0, 2].map((idx) => {
                const r = leaderboard[idx];
                if (!r) return null;
                const isFirst = idx === 0;
                return (
                  <div key={r.driver_id}
                    className={`rounded-xl border p-5 text-center ${isFirst ? "border-amber-500/40 bg-amber-500/10 scale-105" : "border-white/[0.07] glow-card"}`}>
                    <p className="text-3xl mb-2">{medals[idx]}</p>
                    <p className="text-xs text-slate-500 font-mono mb-2">{r.driver_id.slice(0, 8)}…</p>
                    <ScoreBadge score={r.avg_score} />
                    <p className="text-[10px] text-slate-500 mt-1">avg score</p>
                    <div className="mt-3 grid grid-cols-2 gap-1 text-xs">
                      <div><p className="text-slate-600">Sales</p><p className="text-white">KES {r.total_sales.toLocaleString()}</p></div>
                      <div><p className="text-slate-600">Orders</p><p className="text-white">{r.total_orders}</p></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Full leaderboard */}
          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Rank</th>
                  <th className="px-4 py-3 text-left">Driver</th>
                  <th className="px-4 py-3 text-right">Score</th>
                  <th className="px-4 py-3 text-right">Sales</th>
                  <th className="px-4 py-3 text-right">Orders</th>
                  <th className="px-4 py-3 text-right">Route %</th>
                  <th className="px-4 py-3 text-right">Collection %</th>
                  <th className="px-4 py-3 text-right">Fraud Flags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {leaderboard.map((r) => (
                  <tr key={r.driver_id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-slate-400 font-bold">#{r.rank}</td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">{r.driver_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3 text-right"><ScoreBadge score={r.avg_score} /></td>
                    <td className="px-4 py-3 text-right text-white font-medium">KES {r.total_sales.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-slate-300">{r.total_orders}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={scoreColor(r.avg_route_completion)}>{r.avg_route_completion.toFixed(1)}%</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={scoreColor(r.avg_collection_rate)}>{r.avg_collection_rate.toFixed(1)}%</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={r.total_fraud_flags > 0 ? "text-red-400 font-medium" : "text-slate-500"}>
                        {r.total_fraud_flags}
                      </span>
                    </td>
                  </tr>
                ))}
                {leaderboard.length === 0 && (
                  <tr><td colSpan={8} className="text-center py-8 text-slate-600">No performance data for this period. Use &quot;Compute&quot; to generate records.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "daily" && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.03] text-slate-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Driver</th>
                <th className="px-4 py-3 text-right">Score</th>
                <th className="px-4 py-3 text-right">Sales</th>
                <th className="px-4 py-3 text-right">Orders</th>
                <th className="px-4 py-3 text-right">Visits</th>
                <th className="px-4 py-3 text-right">Route%</th>
                <th className="px-4 py-3 text-right">Collect%</th>
                <th className="px-4 py-3 text-right">Fraud</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {dailyPerf.map((p) => (
                <tr key={p.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs">{p.perf_date}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{p.driver_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-right"><ScoreBadge score={p.performance_score} /></td>
                  <td className="px-4 py-3 text-right text-white font-medium">KES {Number(p.total_sales).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-slate-300">{p.total_orders}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{p.completed_visits}/{p.total_visits}</td>
                  <td className="px-4 py-3 text-right"><span className={scoreColor(p.route_completion_pct)}>{p.route_completion_pct?.toFixed(1) ?? "—"}%</span></td>
                  <td className="px-4 py-3 text-right"><span className={scoreColor(p.collection_rate_pct)}>{p.collection_rate_pct?.toFixed(1) ?? "—"}%</span></td>
                  <td className="px-4 py-3 text-right"><span className={p.fraud_flag_count > 0 ? "text-red-400 font-medium" : "text-slate-500"}>{p.fraud_flag_count}</span></td>
                </tr>
              ))}
              {dailyPerf.length === 0 && (
                <tr><td colSpan={9} className="text-center py-8 text-slate-600">No daily records found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
