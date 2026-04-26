"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { subscriptionApi, STATUS_COLORS, GEN_STATUS_COLORS, RECURRENCE_LABELS } from "@/lib/subscription";
import Link from "next/link";
import { useState } from "react";

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
      <p className="text-[11px] text-slate-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export default function RecurringOrdersDashboard() {
  const qc = useQueryClient();
  const { data: stats } = useQuery({
    queryKey: ["sub-report-templates"],
    queryFn: () => subscriptionApi.reportTemplates(),
  });
  const { data: templates = [] } = useQuery({
    queryKey: ["sub-templates"],
    queryFn: () => subscriptionApi.listTemplates({ limit: 10 }),
  });
  const { data: genReport = [] } = useQuery({
    queryKey: ["sub-gen-report"],
    queryFn: () => subscriptionApi.reportGeneration(30),
  });
  const { data: aiRecs = [] } = useQuery({
    queryKey: ["sub-ai-recs"],
    queryFn: () => subscriptionApi.aiRecs({ status: "PENDING" }),
  });

  const schedulerMut = useMutation({
    mutationFn: () => subscriptionApi.runScheduler(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sub-"] }),
  });

  const s = stats as any;

  return (
    <div className="p-6 space-y-6 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Recurring Orders</h1>
          <p className="text-slate-500 text-sm mt-0.5">Subscription & recurring order engine</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => schedulerMut.mutate()}
            disabled={schedulerMut.isPending}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50"
          >
            {schedulerMut.isPending ? "Running..." : "Run Scheduler"}
          </button>
          <Link
            href="/dashboard/recurring-orders/templates/new"
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
          >
            + New Template
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Templates" value={s?.total ?? 0} color="text-white" />
        <StatCard label="Active" value={s?.active ?? 0} color="text-emerald-400" />
        <StatCard label="Paused" value={s?.paused ?? 0} color="text-amber-400" />
        <StatCard label="Expired" value={s?.expired ?? 0} color="text-red-400" />
      </div>

      {/* Scheduler result */}
      {schedulerMut.data && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
          Scheduler ran: {schedulerMut.data.generated} generated · {schedulerMut.data.skipped} skipped · {schedulerMut.data.failed} failed
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent templates */}
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Recent Templates</h2>
            <Link href="/dashboard/recurring-orders/templates" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
          </div>
          <div className="space-y-2">
            {templates.map((t) => (
              <Link key={t.id} href={`/dashboard/recurring-orders/templates/${t.id}`}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025] hover:bg-white/[0.05] transition-colors">
                <div>
                  <p className="text-sm text-white font-medium">{t.template_code}</p>
                  <p className="text-xs text-slate-500">{t.template_name} · {RECURRENCE_LABELS[t.recurrence_type]}</p>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[t.status]}`}>
                  {t.status}
                </span>
              </Link>
            ))}
            {templates.length === 0 && (
              <p className="text-sm text-slate-600 text-center py-4">No templates yet</p>
            )}
          </div>
        </div>

        {/* Generation stats */}
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">Generation Stats (30 days)</h2>
            <Link href="/dashboard/recurring-orders/reports" className="text-xs text-indigo-400 hover:text-indigo-300">Reports</Link>
          </div>
          <div className="space-y-2">
            {genReport.map((r: any) => (
              <div key={r.status} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.025]">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${GEN_STATUS_COLORS[r.status as keyof typeof GEN_STATUS_COLORS] ?? "bg-slate-500/20 text-slate-400"}`}>
                  {r.status}
                </span>
                <span className="text-sm font-bold text-white">{r.count}</span>
              </div>
            ))}
            {genReport.length === 0 && (
              <p className="text-sm text-slate-600 text-center py-4">No generation data</p>
            )}
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      {aiRecs.length > 0 && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white">AI Insights</h2>
            <Link href="/dashboard/recurring-orders/ai" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
          </div>
          <div className="space-y-2">
            {aiRecs.slice(0, 3).map((r) => (
              <div key={r.id} className="p-3 rounded-lg bg-white/[0.025] border border-white/[0.04]">
                <p className="text-sm text-white font-medium">{r.title}</p>
                <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{r.body}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
