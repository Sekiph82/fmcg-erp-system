"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dimApi, DimAIAgentType, DimAIRecStatus, AGENT_LABEL, SEVERITY_BADGE } from "@/lib/dimensions";

export default function DimAIPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<DimAIRecStatus | "">("");

  const { data: recs = [], isLoading } = useQuery({
    queryKey: ["dim-ai-recs", statusFilter],
    queryFn: () => dimApi.getAIRecs((statusFilter as DimAIRecStatus) || undefined),
  });

  const runAgents = useMutation({
    mutationFn: () => dimApi.runAgents(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dim-ai-recs"] }),
  });

  const ack = useMutation({
    mutationFn: ({ id, status }: { id: string; status: DimAIRecStatus }) =>
      dimApi.ackAIRec(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dim-ai-recs"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Agents — Accounting Dimensions</h1>
          <p className="text-sm text-gray-500">
            Completeness Monitor · Allocation Optimizer · Profitability Lens
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as DimAIRecStatus | "")}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All Statuses</option>
            {(["PENDING","ACKNOWLEDGED","ACTIONED","DISMISSED"] as DimAIRecStatus[]).map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button onClick={() => runAgents.mutate()} disabled={runAgents.isPending} className="glow-button">
            {runAgents.isPending ? "Running…" : "Run AI Agents"}
          </button>
        </div>
      </div>

      {runAgents.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          ✓ AI agents completed. New recommendations generated.
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        {(Object.keys(AGENT_LABEL) as DimAIAgentType[]).map((agent) => {
          const count = recs.filter((r) => r.agent_type === agent && r.status === "PENDING").length;
          return (
            <div key={agent} className="glow-card p-4 text-center">
              <p className="text-xs text-gray-500">{AGENT_LABEL[agent]}</p>
              <p className="text-2xl font-bold text-indigo-400 mt-1">{count}</p>
              <p className="text-xs text-gray-400">pending</p>
            </div>
          );
        })}
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="text-gray-400 text-sm p-6 text-center">Loading…</div>
        ) : recs.length === 0 ? (
          <div className="liquid-glass p-8 text-center text-gray-400">
            No recommendations. Click "Run AI Agents" to analyse the system.
          </div>
        ) : recs.map((rec) => (
          <div key={rec.id} className="liquid-glass p-4 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-semibold text-indigo-400">{AGENT_LABEL[rec.agent_type]}</span>
                {rec.severity && (
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEVERITY_BADGE[rec.severity] ?? "bg-gray-100 text-gray-600"}`}>
                    {rec.severity}
                  </span>
                )}
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  rec.status === "PENDING" ? "bg-yellow-100 text-yellow-700"
                  : rec.status === "ACTIONED" ? "bg-green-100 text-green-700"
                  : rec.status === "DISMISSED" ? "bg-gray-100 text-gray-500"
                  : "bg-blue-100 text-blue-700"
                }`}>{rec.status}</span>
              </div>
            </div>
            <p className="text-sm font-medium text-gray-900">{rec.title}</p>
            {rec.detail && <p className="text-xs text-gray-500">{rec.detail}</p>}
            {rec.status === "PENDING" && (
              <div className="flex gap-2">
                <button onClick={() => ack.mutate({ id: rec.id, status: "ACKNOWLEDGED" })}
                  className="glow-button-secondary text-xs !py-1">Acknowledge</button>
                <button onClick={() => ack.mutate({ id: rec.id, status: "ACTIONED" })}
                  className="glow-button text-xs !py-1">Mark Actioned</button>
                <button onClick={() => ack.mutate({ id: rec.id, status: "DISMISSED" })}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2">Dismiss</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
