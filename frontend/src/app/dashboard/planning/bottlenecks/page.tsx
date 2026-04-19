"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  planningApi, ScenarioSummary, BottleneckOut,
  BN_SEVERITY_COLOR, AGENT_COLOR, AGENT_LABEL, AIRecOut,
} from "@/lib/planning";

export default function BottlenecksPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewBn, setViewBn] = useState<BottleneckOut | null>(null);

  const { data: scenarios = [] } = useQuery<ScenarioSummary[]>({
    queryKey: ["planning-scenarios"],
    queryFn: () => planningApi.listScenarios(),
  });

  const { data: bottlenecks = [], isLoading } = useQuery<BottleneckOut[]>({
    queryKey: ["planning-bottlenecks", selectedId],
    queryFn: () => planningApi.listBottlenecks(selectedId!),
    enabled: !!selectedId,
  });

  const { data: aiRecs = [] } = useQuery<AIRecOut[]>({
    queryKey: ["planning-ai", selectedId],
    queryFn: () => planningApi.listAI(selectedId!),
    enabled: !!selectedId,
  });

  const runAI = useMutation({
    mutationFn: () => planningApi.runAI(selectedId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["planning-ai", selectedId] }),
  });

  const resolvebn = useMutation({
    mutationFn: (bnId: string) => planningApi.resolveBottleneck(bnId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["planning-bottlenecks", selectedId] });
      setViewBn(null);
    },
  });

  const actionAI = useMutation({
    mutationFn: ({ recId, status }: { recId: string; status: "ACCEPTED" | "REJECTED" }) =>
      planningApi.actionAI(recId, status, ""),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["planning-ai", selectedId] }),
  });

  const open = bottlenecks.filter((b) => !b.is_resolved);
  const resolved = bottlenecks.filter((b) => b.is_resolved);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Bottleneck Explorer</h1>
        <a href="/dashboard/planning" className="text-xs text-blue-600 hover:underline">← Planning Dashboard</a>
      </div>

      {/* Selector + actions */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap items-center gap-3">
        <select
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm min-w-64"
          value={selectedId || ""}
          onChange={(e) => setSelectedId(e.target.value || null)}
        >
          <option value="">-- select scenario --</option>
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>{s.scenario_no} — {s.scenario_name}</option>
          ))}
        </select>
        {selectedId && (
          <button
            onClick={() => runAI.mutate()}
            disabled={runAI.isPending}
            className="px-3 py-1.5 text-xs font-medium bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg"
          >
            {runAI.isPending ? "Running AI…" : "Run AI Agents"}
          </button>
        )}
      </div>

      {selectedId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bottleneck List */}
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Open", value: open.length, color: open.length > 0 ? "text-red-600" : "text-green-600" },
                { label: "Critical", value: open.filter((b) => b.severity === "CRITICAL").length, color: "text-red-700" },
                { label: "Resolved", value: resolved.length, color: "text-green-600" },
              ].map((k) => (
                <div key={k.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-3 text-center">
                  <p className="text-xs text-gray-400">{k.label}</p>
                  <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
                </div>
              ))}
            </div>

            {isLoading ? (
              <div className="text-center text-gray-400 py-8">Loading…</div>
            ) : open.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
                No open bottlenecks detected.
              </div>
            ) : (
              open.map((bn) => (
                <div
                  key={bn.id}
                  className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 cursor-pointer hover:border-indigo-200"
                  onClick={() => setViewBn(bn)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${BN_SEVERITY_COLOR[bn.severity]}`}>
                        {bn.severity}
                      </span>
                      <p className="text-sm font-semibold text-gray-800">{bn.work_center_name || "Unknown WC"}</p>
                    </div>
                    <p className="text-lg font-bold text-red-600">{Number(bn.peak_utilization_pct).toFixed(0)}%</p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-3 text-xs text-gray-500">
                    <div>
                      <p className="text-gray-400">Overloaded days</p>
                      <p className="font-medium text-red-500">{bn.overloaded_days}d</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Excess hours</p>
                      <p className="font-medium text-red-500">{Number(bn.total_overload_hrs).toFixed(1)}h</p>
                    </div>
                    <div>
                      <p className="text-gray-400">Blocked ops</p>
                      <p className="font-medium">{bn.blocked_op_count}</p>
                    </div>
                  </div>

                  {bn.recommendation && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2">{bn.recommendation}</p>
                  )}
                </div>
              ))
            )}
          </div>

          {/* AI Recommendations */}
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700">AI Recommendations ({aiRecs.length})</h2>
              </div>
              {aiRecs.length === 0 ? (
                <div className="p-6 text-center text-sm text-gray-400">No recommendations yet. Run AI agents.</div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {aiRecs.map((rec) => (
                    <div key={rec.id} className="px-5 py-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs px-1.5 py-0.5 rounded ${AGENT_COLOR[rec.agent_type]}`}>
                              {AGENT_LABEL[rec.agent_type]}
                            </span>
                            {rec.confidence_score && (
                              <span className="text-xs text-gray-400">{(Number(rec.confidence_score) * 100).toFixed(0)}% confidence</span>
                            )}
                          </div>
                          <p className="text-sm font-medium text-gray-800">{rec.title}</p>
                          {rec.impact_summary && (
                            <p className="text-xs text-gray-500 mt-0.5">{rec.impact_summary}</p>
                          )}
                        </div>
                        {rec.status === "PENDING" && (
                          <div className="flex gap-1 shrink-0">
                            <button
                              onClick={() => actionAI.mutate({ recId: rec.id, status: "ACCEPTED" })}
                              className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                            >
                              Accept
                            </button>
                            <button
                              onClick={() => actionAI.mutate({ recId: rec.id, status: "REJECTED" })}
                              className="px-2 py-1 text-xs bg-red-100 text-red-600 rounded hover:bg-red-200"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                        {rec.status !== "PENDING" && (
                          <span className={`text-xs px-2 py-0.5 rounded ${rec.status === "ACCEPTED" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                            {rec.status}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Bottleneck detail modal */}
      {viewBn && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{viewBn.work_center_name || "Bottleneck Detail"}</h2>
              <button onClick={() => setViewBn(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              {[
                { label: "Severity", value: viewBn.severity },
                { label: "Peak Utilization", value: `${Number(viewBn.peak_utilization_pct).toFixed(1)}%` },
                { label: "Overloaded Days", value: `${viewBn.overloaded_days}d` },
                { label: "Excess Hours", value: `${Number(viewBn.total_overload_hrs).toFixed(1)}h` },
                { label: "Blocked Ops", value: String(viewBn.blocked_op_count) },
                { label: "Detected", value: viewBn.detected_at ? new Date(viewBn.detected_at).toLocaleString() : "—" },
              ].map((k) => (
                <div key={k.label} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-400">{k.label}</p>
                  <p className="text-sm font-semibold text-gray-800">{k.value}</p>
                </div>
              ))}
            </div>
            {viewBn.recommendation && (
              <div className="bg-blue-50 rounded-lg p-3 mb-4">
                <p className="text-xs font-semibold text-blue-600 mb-1">Recommendation</p>
                <p className="text-sm text-blue-800">{viewBn.recommendation}</p>
              </div>
            )}
            {!viewBn.is_resolved && (
              <button
                onClick={() => resolvebn.mutate(viewBn.id)}
                disabled={resolvebn.isPending}
                className="w-full bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40"
              >
                {resolvebn.isPending ? "Resolving…" : "Mark as Resolved"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
