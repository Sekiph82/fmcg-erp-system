"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { subscriptionApi } from "@/lib/subscription";

export default function UpcomingDemandPage() {
  const today = new Date().toISOString().split("T")[0];
  const in30 = new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0];
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(in30);

  const { data: demand = [], isLoading, refetch } = useQuery({
    queryKey: ["sub-demand", from, to],
    queryFn: () => subscriptionApi.upcomingDemand(from, to),
  });

  // Group by date
  const byDate: Record<string, typeof demand> = {};
  demand.forEach((d) => {
    if (!byDate[d.scheduled_date]) byDate[d.scheduled_date] = [];
    byDate[d.scheduled_date].push(d);
  });
  const dates = Object.keys(byDate).sort();

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">Upcoming Recurring Demand</h1>
        <p className="text-slate-500 text-sm mt-0.5">MRP / planning feed from active recurring templates</p>
      </div>

      {/* Date range */}
      <div className="flex gap-3 items-end">
        <div>
          <label className="text-xs text-slate-400 mb-1 block">From</label>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)}
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="text-xs text-slate-400 mb-1 block">To</label>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)}
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
        </div>
        <button onClick={() => refetch()}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium">
          Refresh
        </button>
      </div>

      <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 text-sm text-indigo-300">
        {isLoading ? "Loading…" : `${demand.length} demand lines across ${dates.length} upcoming dates`}
      </div>

      {/* By date */}
      <div className="space-y-4">
        {dates.map((d) => (
          <div key={d} className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
            <div className="px-4 py-3 bg-white/[0.03] border-b border-white/[0.06]">
              <span className="text-sm font-semibold text-white">{d}</span>
              <span className="ml-2 text-xs text-slate-500">{byDate[d].length} lines</span>
            </div>
            <table className="w-full text-sm">
              <thead className="text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-2 text-left">Template</th>
                  <th className="px-4 py-2 text-left">Customer</th>
                  <th className="px-4 py-2 text-left">Item</th>
                  <th className="px-4 py-2 text-right">Qty</th>
                  <th className="px-4 py-2 text-left">UOM</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {byDate[d].map((line, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-2 text-indigo-300 text-xs font-mono">{line.template_code}</td>
                    <td className="px-4 py-2 text-slate-400 text-xs font-mono">{line.customer_id.slice(0, 8)}…</td>
                    <td className="px-4 py-2 text-slate-400 text-xs font-mono">{line.item_id.slice(0, 8)}…</td>
                    <td className="px-4 py-2 text-right text-white font-medium">{line.quantity}</td>
                    <td className="px-4 py-2 text-slate-400">{line.uom}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {!isLoading && dates.length === 0 && (
          <div className="text-center py-12 text-slate-600">No upcoming recurring demand in selected date range</div>
        )}
      </div>
    </div>
  );
}
