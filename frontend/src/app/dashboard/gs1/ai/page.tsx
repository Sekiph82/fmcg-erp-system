"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, type GS1AIRecommendation, severityColor } from "@/lib/gs1";

export default function GS1AIPage() {
  const qc = useQueryClient();
  const [agentFilter, setAgentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  const { data: recs, isLoading } = useQuery({
    queryKey: ["gs1-ai-recs", agentFilter, statusFilter],
    queryFn: () => gs1Api.listRecommendations(agentFilter || undefined, statusFilter || undefined),
  });

  const runValidator = useMutation({
    mutationFn: gs1Api.runLabelValidator,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["gs1-ai-recs"] }); alert(`Label Validator: ${r.generated} recommendation(s) generated`); },
  });
  const runOptimizer = useMutation({
    mutationFn: gs1Api.runPackagingOptimizer,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["gs1-ai-recs"] }); alert(`Packaging Optimizer: ${r.generated} recommendation(s) generated`); },
  });
  const reviewRec = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => gs1Api.reviewRecommendation(id, status, "user"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["gs1-ai-recs"] }),
  });

  const agentDescriptions: Record<string, { name: string; desc: string; color: string }> = {
    LABEL_VALIDATOR: {
      name: "Label Validator",
      desc: "Detects missing GS1 fields, unconfigured products, invalid GTIN check digits, and incomplete barcode records.",
      color: "text-blue-600",
    },
    PACKAGING_OPTIMIZER: {
      name: "Packaging Optimizer",
      desc: "Suggests optimal packaging hierarchies, detects over-mixed pallets, and identifies products without packaging level definitions.",
      color: "text-purple-600",
    },
  };

  const recStatusColors: Record<string, string> = {
    PENDING:  "bg-yellow-100 text-yellow-800",
    ACCEPTED: "bg-green-100 text-green-800",
    REJECTED: "bg-red-100 text-red-800",
    APPLIED:  "bg-blue-100 text-blue-800",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">GS1 AI Agents</h1>
          <p className="text-sm text-gray-500">Automated GS1 compliance validation and packaging optimization</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => runValidator.mutate()} disabled={runValidator.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            {runValidator.isPending ? "Running…" : "Run Label Validator"}
          </button>
          <button onClick={() => runOptimizer.mutate()} disabled={runOptimizer.isPending} className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50">
            {runOptimizer.isPending ? "Running…" : "Run Packaging Optimizer"}
          </button>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(agentDescriptions).map(([key, agent]) => (
          <div key={key} className="bg-white border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-current opacity-60" />
              <h3 className={`text-sm font-medium ${agent.color}`}>{agent.name}</h3>
            </div>
            <p className="text-xs text-gray-500">{agent.desc}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex gap-1">
          {["", "LABEL_VALIDATOR", "PACKAGING_OPTIMIZER"].map((a) => (
            <button key={a} onClick={() => setAgentFilter(a)} className={`px-3 py-1 text-xs rounded border ${agentFilter === a ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"}`}>
              {a ? agentDescriptions[a]?.name : "All Agents"}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {["", "PENDING", "ACCEPTED", "REJECTED", "APPLIED"].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`px-3 py-1 text-xs rounded border ${statusFilter === s ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"}`}>
              {s || "All Status"}
            </button>
          ))}
        </div>
      </div>

      {/* Recommendations List */}
      {isLoading && <div className="text-gray-400 text-sm">Loading…</div>}
      <div className="space-y-3">
        {!recs?.length && !isLoading && (
          <div className="bg-white border rounded-lg p-8 text-center text-gray-400">
            <p className="text-2xl mb-2">🤖</p>
            <p className="text-sm">No recommendations yet. Run an AI agent to detect issues.</p>
          </div>
        )}
        {recs?.map((rec) => (
          <div key={rec.id} className="bg-white border rounded-lg p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${recStatusColors[rec.status] ?? ""}`}>{rec.status}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${severityColor[rec.severity] ?? "bg-gray-100 text-gray-600"}`}>{rec.severity}</span>
                  <span className="text-xs text-gray-400">{agentDescriptions[rec.agent_type]?.name || rec.agent_type}</span>
                </div>
                <h3 className="text-sm font-medium text-gray-900">{rec.title}</h3>
                <p className="text-xs text-gray-500 mt-0.5">{rec.description}</p>
                <div className="mt-2 bg-blue-50 rounded p-2 text-xs text-blue-800">
                  <span className="font-medium">Recommendation: </span>{rec.recommendation}
                </div>
                {rec.affected_entity_type && (
                  <p className="text-xs text-gray-400 mt-1">Affected: {rec.affected_entity_type}</p>
                )}
              </div>
              {rec.status === "PENDING" && (
                <div className="flex gap-1.5 shrink-0">
                  <button
                    onClick={() => reviewRec.mutate({ id: rec.id, status: "ACCEPTED" })}
                    disabled={reviewRec.isPending}
                    className="px-2 py-1 text-xs bg-green-50 text-green-700 border border-green-200 rounded hover:bg-green-100 disabled:opacity-50"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => reviewRec.mutate({ id: rec.id, status: "REJECTED" })}
                    disabled={reviewRec.isPending}
                    className="px-2 py-1 text-xs bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
            <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
              <span>{new Date(rec.created_at).toLocaleString()}</span>
              {rec.reviewed_by && <span>Reviewed by: {rec.reviewed_by}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
