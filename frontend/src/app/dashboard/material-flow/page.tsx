"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  mfApi, MFDashboard, MFAIRec,
  FLOW_TYPE_LABELS, FLOW_STATUS_COLORS, QUALITY_STATUS_COLORS,
  AI_AGENT_LABELS, SEVERITY_COLORS,
} from "@/lib/materialFlow";

function KPI({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function Badge({ label, cls }: { label: string; cls: string }) {
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{label}</span>;
}

export default function MaterialFlowDashboard() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery<MFDashboard>({
    queryKey: ["mf-dashboard"],
    queryFn: () => mfApi.getDashboard().then((r) => r.data),
    refetchInterval: 30000,
    retry: 1,
  });

  const runAI = useMutation({
    mutationFn: () => mfApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mf-dashboard"] }),
  });

  const actionRec = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "ACCEPTED" | "REJECTED" }) =>
      mfApi.actionAIRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mf-dashboard"] }),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading material flow dashboard…</div>;
  if (isError) return <div className="p-8 text-red-500">Failed to load dashboard: {(error as Error)?.message ?? "Unknown error"}</div>;
  if (!data) return <div className="p-8 text-red-500">Failed to load Material Flow dashboard. Ensure the backend is running.</div>;
  const d = data;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Material Flow Engine</h1>
          <p className="text-sm text-gray-500 mt-0.5">Staged FMCG material movement — issue, transfer, consume, receive</p>
        </div>
        <button
          onClick={() => runAI.mutate()}
          disabled={runAI.isPending}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {runAI.isPending ? "Running AI…" : "Run AI Analysis"}
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Flows Today" value={d.total_flows_today} color="text-blue-700" />
        <KPI label="Issued Today (kg)" value={Number(d.total_issued_today).toLocaleString()} color="text-green-700" />
        <KPI label="Active Reservations" value={d.active_reservations} color="text-purple-700" />
        <KPI label="Open Reconciliations" value={d.open_reconciliations} color={d.open_reconciliations > 0 ? "text-orange-600" : "text-gray-800"} />
        <KPI label="Tanks In Use" value={d.tanks_in_use} color="text-emerald-700" />
        <KPI label="Tanks on QC Hold" value={d.tanks_qc_hold} color={d.tanks_qc_hold > 0 ? "text-orange-600" : "text-gray-800"} />
        <KPI label="Pending AI Recs" value={d.pending_ai_recs} color={d.pending_ai_recs > 0 ? "text-red-600" : "text-gray-800"} />
        <KPI label="WIP Quantity (kg)" value={Number(d.total_wip_quantity).toLocaleString()} />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Issue to Production", href: "/dashboard/material-flow/issue", color: "bg-blue-50 text-blue-700 border-blue-200" },
          { label: "Stage Transfer", href: "/dashboard/material-flow/wip-transfer", color: "bg-green-50 text-green-700 border-green-200" },
          { label: "Bulk Transfer", href: "/dashboard/material-flow/bulk-transfer", color: "bg-purple-50 text-purple-700 border-purple-200" },
          { label: "FG Receipt", href: "/dashboard/material-flow/fg-receipt", color: "bg-orange-50 text-orange-700 border-orange-200" },
          { label: "Reservations", href: "/dashboard/material-flow/reservations", color: "bg-teal-50 text-teal-700 border-teal-200" },
          { label: "Tank Occupancy", href: "/dashboard/material-flow/tanks", color: "bg-cyan-50 text-cyan-700 border-cyan-200" },
          { label: "Returns & Reversals", href: "/dashboard/material-flow/returns", color: "bg-rose-50 text-rose-700 border-rose-200" },
          { label: "Reconciliation", href: "/dashboard/material-flow/reconciliation", color: "bg-amber-50 text-amber-700 border-amber-200" },
        ].map((q) => (
          <a key={q.href} href={q.href} className={`border rounded-lg p-3 text-sm font-medium text-center hover:opacity-80 ${q.color}`}>
            {q.label}
          </a>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Flows */}
        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Flows</h2>
            <a href="/dashboard/material-flow/history" className="text-xs text-indigo-600 hover:underline">View all</a>
          </div>
          <div className="divide-y">
            {d.recent_flows.length === 0 && (
              <p className="p-4 text-sm text-gray-400">No flows recorded yet.</p>
            )}
            {d.recent_flows.slice(0, 8).map((f) => (
              <div key={f.id} className="px-4 py-2.5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{f.flow_no}</p>
                  <p className="text-xs text-gray-500">{FLOW_TYPE_LABELS[f.flow_type]} · {new Date(f.transaction_datetime).toLocaleString()}</p>
                </div>
                <Badge label={f.status} cls={FLOW_STATUS_COLORS[f.status] || "bg-gray-100 text-gray-600"} />
              </div>
            ))}
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">AI Recommendations</h2>
            <span className="text-xs text-gray-400">{d.pending_ai_recs} pending</span>
          </div>
          <div className="divide-y">
            {d.ai_recommendations.length === 0 && (
              <p className="p-4 text-sm text-gray-400">No pending AI recommendations.</p>
            )}
            {d.ai_recommendations.map((r: MFAIRec) => (
              <div key={r.id} className="p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge label={AI_AGENT_LABELS[r.agent_type]} cls="bg-indigo-50 text-indigo-700" />
                      <Badge label={r.severity} cls={SEVERITY_COLORS[r.severity] || "bg-gray-100 text-gray-600"} />
                    </div>
                    <p className="text-sm font-medium text-gray-900">{r.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{r.description}</p>
                  </div>
                  {r.status === "PENDING" && (
                    <div className="flex gap-1 shrink-0 mt-1">
                      <button
                        onClick={() => actionRec.mutate({ id: r.id, status: "ACCEPTED" })}
                        className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200"
                      >Accept</button>
                      <button
                        onClick={() => actionRec.mutate({ id: r.id, status: "REJECTED" })}
                        className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200"
                      >Reject</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
