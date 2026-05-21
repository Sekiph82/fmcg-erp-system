"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  lcApi, LCAIRec, LCAIRecStatus, AI_AGENT_LABEL, AI_REC_STATUS_COLOR,
} from "@/lib/landed_cost";

const STATUSES: { value: LCAIRecStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "PENDING", label: "Pending" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "REJECTED", label: "Rejected" },
];

export default function LandedCostAIPage() {
  const [statusFilter, setStatusFilter] = useState<LCAIRecStatus | "">("");
  const qc = useQueryClient();

  const { data: recs = [], isLoading } = useQuery<LCAIRec[]>({
    queryKey: ["lc-ai-recs", statusFilter],
    queryFn: () => lcApi.listAIRecs(statusFilter ? { status: statusFilter } : undefined),
  });

  const runAI = useMutation({
    mutationFn: () => lcApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-ai-recs"] }),
  });

  const action = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "ACCEPTED" | "REJECTED" }) =>
      lcApi.actionAIRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lc-ai-recs"] }),
  });

  const pending = recs.filter((r) => r.status === "PENDING").length;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Recommendations</h1>
          {pending > 0 && (
            <p className="text-sm text-yellow-600 mt-1">
              {pending} pending recommendation{pending > 1 ? "s" : ""} awaiting review
            </p>
          )}
        </div>
        <button
          onClick={() => runAI.mutate()}
          disabled={runAI.isPending}
          className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {runAI.isPending ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      {runAI.data && (
        <p className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded">
          Created {(runAI.data as { recommendations_created: number }).recommendations_created} new recommendation(s).
        </p>
      )}

      {/* Status filter */}
      <div className="flex gap-1">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(s.value)}
            className={`px-3 py-1.5 text-xs rounded-lg border ${
              statusFilter === s.value
                ? "bg-purple-600 text-white border-purple-600"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Recs list */}
      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : recs.length === 0 ? (
        <p className="text-gray-400 text-sm">No recommendations found. Run AI agents to generate insights.</p>
      ) : (
        <div className="space-y-3">
          {recs.map((rec) => (
            <div key={rec.id} className="bg-white border rounded-xl p-5 space-y-2">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                      {AI_AGENT_LABEL[rec.agent_type as keyof typeof AI_AGENT_LABEL] ?? rec.agent_type}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${AI_REC_STATUS_COLOR[rec.status as LCAIRecStatus]}`}>
                      {rec.status}
                    </span>
                    {rec.confidence_score != null && (
                      <span className="text-xs text-gray-400">
                        Confidence: {Math.round(Number(rec.confidence_score) * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{rec.title}</p>
                  {rec.explanation && <p className="text-sm text-gray-600">{rec.explanation}</p>}
                  {rec.impact_summary && (
                    <p className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded">
                      Impact: {rec.impact_summary}
                    </p>
                  )}
                  {rec.suggested_action && (
                    <p className="text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded">
                      Suggestion: {rec.suggested_action}
                    </p>
                  )}
                </div>
                {rec.status === "PENDING" && (
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => action.mutate({ id: rec.id, status: "ACCEPTED" })}
                      className="px-3 py-1 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => action.mutate({ id: rec.id, status: "REJECTED" })}
                      className="px-3 py-1 text-xs border rounded-lg text-red-600 hover:bg-red-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-400">
                Created {new Date(rec.created_at).toLocaleString()}
                {rec.actioned_at && ` · Actioned ${new Date(rec.actioned_at).toLocaleString()}`}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
