"use client";
import { useQuery } from "@tanstack/react-query";
import { subscriptionApi, GEN_STATUS_COLORS } from "@/lib/subscription";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { tx } from "@/lib/i18n/core";

const BAR_COLORS: Record<string, string> = {
  GENERATED: "#10b981",
  FAILED: "#ef4444",
  SKIPPED: "#f59e0b",
  PENDING_APPROVAL: "#3b82f6",
  CANCELLED: "#64748b",
};

export default function ReportsPage() {
  const { data: stats } = useQuery({
    queryKey: ["sub-report-templates"],
    queryFn: () => subscriptionApi.reportTemplates(),
  });
  const { data: genReport = [] } = useQuery({
    queryKey: ["sub-gen-report-30"],
    queryFn: () => subscriptionApi.reportGeneration(30),
  });
  const { data: failed = [] } = useQuery({
    queryKey: ["sub-failed"],
    queryFn: () => subscriptionApi.reportFailed(30),
  });

  const s = stats as any;

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">{tx("Recurring Orders Reports")}</h1>
        <p className="text-slate-500 text-sm mt-0.5">{tx("30-day generation summary and template health")}</p>
      </div>

      {/* Template health */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: tx("Total"), value: s?.total ?? 0, color: "text-white" },
          { label: tx("Active"), value: s?.active ?? 0, color: "text-emerald-400" },
          { label: tx("Paused"), value: s?.paused ?? 0, color: "text-amber-400" },
          { label: tx("Expired"), value: s?.expired ?? 0, color: "text-red-400" },
        ].map((card) => (
          <div key={card.label} className="glow-card p-5">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{card.label}</p>
            <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Generation chart */}
      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">{tx("Generation by Status (30 days)")}</h2>
        {genReport.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={genReport}>
              <XAxis dataKey="status" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#0d1829", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {genReport.map((entry: any) => (
                  <Cell key={entry.status} fill={BAR_COLORS[entry.status] ?? "#6366f1"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-slate-600 text-center py-10">{tx("No generation data")}</p>
        )}
      </div>

      {/* Failed generations */}
      <div className="glow-card p-5">
        <h2 className="text-sm font-semibold text-white mb-4">{tx("Failed Generations (30 days)")}</h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-2 text-left">{tx("Template")}</th>
              <th className="px-4 py-2 text-left">{tx("Scheduled")}</th>
              <th className="px-4 py-2 text-left">{tx("Failure Reason")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {failed.map((l) => (
              <tr key={l.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-2 text-slate-400 font-mono text-xs">{l.template_id.slice(0, 8)}…</td>
                <td className="px-4 py-2 text-slate-300 text-xs">{l.scheduled_date}</td>
                <td className="px-4 py-2 text-red-400 text-xs">{l.failure_reason ?? "—"}</td>
              </tr>
            ))}
            {failed.length === 0 && (
              <tr><td colSpan={3} className="text-center py-6 text-slate-600">{tx("No failures in the last 30 days")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
