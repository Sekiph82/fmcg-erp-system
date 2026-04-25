"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, severityColor, type ANAIRecommendation } from "@/lib/allergen";

export default function AllergenAIPage() {
  const qc = useQueryClient();
  const [agentFilter, setAgentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  const { data: recs, isLoading } = useQuery({
    queryKey: ["an-ai-recs", agentFilter, statusFilter],
    queryFn: () => allergenApi.listRecommendations(agentFilter || undefined, statusFilter || undefined),
  });

  const runMonitor = useMutation({ mutationFn: allergenApi.runAllergenMonitor, onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["an-ai-recs"] }); alert(`Allergen Risk Monitor: ${r.generated} recommendation(s)`); } });
  const runNutrition = useMutation({ mutationFn: allergenApi.runNutritionAnalyzer, onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["an-ai-recs"] }); alert(`Nutrition Change Analyzer: ${r.generated} recommendation(s)`); } });
  const runLabel = useMutation({ mutationFn: allergenApi.runLabelAssistant, onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["an-ai-recs"] }); alert(`Label Compliance Assistant: ${r.generated} recommendation(s)`); } });

  const review = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => allergenApi.reviewRecommendation(id, status, "user"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["an-ai-recs"] }),
  });

  const agents = {
    ALLERGEN_RISK_MONITOR: { name: "Allergen Risk Monitor", color: "text-red-600", desc: "Detects missing profiles, stale summaries, high cross-contact risk materials, and newly introduced allergens." },
    NUTRITION_CHANGE_ANALYZER: { name: "Nutrition Change Analyzer", color: "text-blue-600", desc: "Identifies stale nutrition summaries, missing nutrition profiles, and significant formula changes affecting declared values." },
    LABEL_COMPLIANCE_ASSISTANT: { name: "Label Compliance Assistant", color: "text-purple-600", desc: "Flags products missing serving size, open allergen change reviews, and potential label declaration mismatches." },
  };

  const statusColors: Record<string, string> = { PENDING: "bg-yellow-100 text-yellow-800", ACCEPTED: "bg-green-100 text-green-800", REJECTED: "bg-red-100 text-red-800", APPLIED: "bg-blue-100 text-blue-800" };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Allergen + Nutrition AI Agents</h1>
          <p className="text-sm text-gray-500">3 AI agents monitoring compliance, risk, and label readiness</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => runMonitor.mutate()} disabled={runMonitor.isPending} className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">{runMonitor.isPending ? "…" : "Allergen Monitor"}</button>
          <button onClick={() => runNutrition.mutate()} disabled={runNutrition.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">{runNutrition.isPending ? "…" : "Nutrition Analyzer"}</button>
          <button onClick={() => runLabel.mutate()} disabled={runLabel.isPending} className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50">{runLabel.isPending ? "…" : "Label Compliance"}</button>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(agents).map(([key, agent]) => (
          <div key={key} className="bg-white border rounded-lg p-4">
            <h3 className={`text-sm font-medium ${agent.color} mb-1`}>{agent.name}</h3>
            <p className="text-xs text-gray-500">{agent.desc}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex gap-1">
          {["", ...Object.keys(agents)].map((a) => (
            <button key={a} onClick={() => setAgentFilter(a)} className={`px-3 py-1 text-xs rounded border ${agentFilter === a ? "bg-gray-900 text-white" : "bg-white hover:bg-gray-50"}`}>
              {a ? agents[a as keyof typeof agents]?.name.split(" ")[0] : "All"}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {["", "PENDING", "ACCEPTED", "REJECTED", "APPLIED"].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`px-3 py-1 text-xs rounded border ${statusFilter === s ? "bg-gray-900 text-white" : "bg-white hover:bg-gray-50"}`}>{s || "All"}</button>
          ))}
        </div>
      </div>

      {isLoading && <div className="text-gray-400 text-sm">Loading…</div>}
      <div className="space-y-3">
        {!recs?.length && !isLoading && (
          <div className="bg-white border rounded-lg p-8 text-center text-gray-400">
            <p className="text-2xl mb-2">🤖</p>
            <p className="text-sm">No recommendations. Run an AI agent to detect issues.</p>
          </div>
        )}
        {recs?.map((rec) => (
          <div key={rec.id} className="bg-white border rounded-lg p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusColors[rec.status] || ""}`}>{rec.status}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${severityColor[rec.severity] || "bg-gray-100 text-gray-600"}`}>{rec.severity}</span>
                  <span className="text-xs text-gray-400">{agents[rec.agent_type as keyof typeof agents]?.name || rec.agent_type}</span>
                </div>
                <h3 className="text-sm font-medium text-gray-900">{rec.title}</h3>
                <p className="text-xs text-gray-500 mt-0.5">{rec.description}</p>
                <div className="mt-2 bg-blue-50 rounded p-2 text-xs text-blue-800">
                  <span className="font-medium">Action: </span>{rec.recommendation}
                </div>
              </div>
              {rec.status === "PENDING" && (
                <div className="flex gap-1.5 shrink-0">
                  <button onClick={() => review.mutate({ id: rec.id, status: "ACCEPTED" })} disabled={review.isPending} className="px-2 py-1 text-xs bg-green-50 text-green-700 border border-green-200 rounded hover:bg-green-100 disabled:opacity-50">Accept</button>
                  <button onClick={() => review.mutate({ id: rec.id, status: "REJECTED" })} disabled={review.isPending} className="px-2 py-1 text-xs bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 disabled:opacity-50">Reject</button>
                </div>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-2">{new Date(rec.created_at).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
