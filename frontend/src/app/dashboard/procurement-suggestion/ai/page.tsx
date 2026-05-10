"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { psApi, PSAIRecOut, PSAIAgentType, agentLabel, fmt } from "@/lib/procurement_suggestion";

const AGENT_COLORS: Record<PSAIAgentType, string> = {
  SUPPLIER_OPTIMIZER:    "bg-blue-50 border-blue-200 text-blue-800",
  DEMAND_RISK_PREDICTOR: "bg-red-50 border-red-200 text-red-800",
  COST_OPTIMIZER:        "bg-green-50 border-green-200 text-green-800",
};

const AGENT_ICON: Record<PSAIAgentType, string> = {
  SUPPLIER_OPTIMIZER:    "🏭",
  DEMAND_RISK_PREDICTOR: "⚠️",
  COST_OPTIMIZER:        "💰",
};

function RecCard({ rec, onAction }: { rec: PSAIRecOut; onAction: (id: string, notes: string) => void }) {
  const [notes, setNotes] = useState("");
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`border rounded-lg p-4 space-y-2 ${rec.is_actioned ? "opacity-60" : ""} ${AGENT_COLORS[rec.agent_type]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <span className="text-xl">{AGENT_ICON[rec.agent_type]}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide opacity-70">{agentLabel(rec.agent_type)}</span>
              <span className="text-xs bg-white bg-opacity-60 px-1.5 py-0.5 rounded">Priority {rec.priority}</span>
              {rec.is_actioned && <span className="text-xs bg-white bg-opacity-80 px-1.5 py-0.5 rounded text-green-700">Actioned ✓</span>}
            </div>
            <p className="font-semibold mt-0.5">{rec.title}</p>
          </div>
        </div>
        {rec.potential_saving && (
          <div className="text-right shrink-0">
            <p className="text-xs opacity-70">Potential Saving</p>
            <p className="font-bold">KES {fmt(rec.potential_saving, 0)}</p>
          </div>
        )}
      </div>

      <p className="text-sm opacity-90">{rec.recommendation}</p>

      {rec.material_name && (
        <p className="text-xs opacity-70">Material: {rec.material_name}</p>
      )}
      {rec.supplier_name && (
        <p className="text-xs opacity-70">Supplier: {rec.supplier_name}</p>
      )}

      {rec.rationale && (
        <button onClick={() => setExpanded(!expanded)} className="text-xs underline opacity-70">
          {expanded ? "Hide rationale" : "Show rationale"}
        </button>
      )}
      {expanded && rec.rationale && (
        <p className="text-xs opacity-80 italic border-t border-current border-opacity-20 pt-2">{rec.rationale}</p>
      )}

      {!rec.is_actioned && (
        <div className="flex gap-2 pt-1">
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Action notes (optional)…"
            className="flex-1 border border-current border-opacity-30 rounded px-2 py-1 text-xs bg-white bg-opacity-50"
          />
          <button
            onClick={() => onAction(rec.id, notes)}
            className="px-3 py-1 text-xs bg-white bg-opacity-70 rounded border border-current border-opacity-30 hover:bg-opacity-100 font-medium"
          >
            Mark Actioned
          </button>
        </div>
      )}
      {rec.action_notes && (
        <p className="text-xs opacity-70 italic">Action notes: {rec.action_notes}</p>
      )}
    </div>
  );
}

export default function PSAIPage() {
  const qc = useQueryClient();
  const [runId, setRunId] = useState("");
  const [activeRunId, setActiveRunId] = useState("");
  const [filterAgent, setFilterAgent] = useState<PSAIAgentType | "">("");

  const { data: runs } = useQuery({
    queryKey: ["ps-runs-ai"],
    queryFn: () => psApi.listRuns(0, 20),
  });

  const { data: recs, isLoading } = useQuery({
    queryKey: ["ps-ai-recs", activeRunId],
    queryFn: () => psApi.listAIRecs(activeRunId),
    enabled: !!activeRunId,
  });

  const runAgents = useMutation({
    mutationFn: (id: string) => psApi.runAIAgents(id),
    onSuccess: (res, id) => {
      qc.invalidateQueries({ queryKey: ["ps-ai-recs", id] });
      alert(`AI agents complete — ${res.generated} recommendation(s) generated.`);
    },
  });

  const actionRec = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) => psApi.actionAIRec(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ps-ai-recs", activeRunId] }),
  });

  const filtered = (recs ?? []).filter((r) => !filterAgent || r.agent_type === filterAgent);

  const groupedByAgent = (["SUPPLIER_OPTIMIZER", "DEMAND_RISK_PREDICTOR", "COST_OPTIMIZER"] as PSAIAgentType[]).map(
    (a) => ({ agent: a, items: filtered.filter((r) => r.agent_type === a) })
  );

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Procurement AI Agents</h1>
          <p className="text-sm text-gray-500">Supplier optimizer · Demand risk predictor · Cost optimizer</p>
        </div>
      </div>

      {/* Run selector */}
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-sm text-gray-600 block mb-1">Select Suggestion Run</label>
          <select
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">— Select a run —</option>
            {(runs ?? []).filter((r) => r.status === "COMPLETED").map((r) => (
              <option key={r.id} value={r.id}>{r.run_no} ({r.suggestion_date})</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setActiveRunId(runId)}
          disabled={!runId}
          className="px-4 py-2 border rounded text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          Load Recommendations
        </button>
        <button
          onClick={() => runAgents.mutate(runId)}
          disabled={!runId || runAgents.isPending}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {runAgents.isPending ? "Running…" : "Run All AI Agents"}
        </button>
      </div>

      {/* Agent descriptions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          { type: "SUPPLIER_OPTIMIZER" as PSAIAgentType, desc: "Identifies cheaper or higher-scoring alternative suppliers for each material, flagging cost-saving opportunities." },
          { type: "DEMAND_RISK_PREDICTOR" as PSAIAgentType, desc: "Detects critical shortages, unmapped materials, and supplier risks that could stop production." },
          { type: "COST_OPTIMIZER" as PSAIAgentType, desc: "Spots bulk purchase opportunities where buying more now locks in pricing and reduces per-unit overhead." },
        ].map(({ type, desc }) => (
          <div key={type} className={`border rounded-lg p-4 ${AGENT_COLORS[type]}`}>
            <p className="font-semibold text-sm">{AGENT_ICON[type]} {agentLabel(type)}</p>
            <p className="text-xs mt-1 opacity-80">{desc}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      {activeRunId && (
        <div className="flex gap-2">
          <button
            onClick={() => setFilterAgent("")}
            className={`px-3 py-1.5 text-xs rounded border ${!filterAgent ? "bg-gray-800 text-white border-gray-800" : "hover:bg-gray-50"}`}
          >
            All ({recs?.length ?? 0})
          </button>
          {(["SUPPLIER_OPTIMIZER", "DEMAND_RISK_PREDICTOR", "COST_OPTIMIZER"] as PSAIAgentType[]).map((a) => {
            const count = (recs ?? []).filter((r) => r.agent_type === a).length;
            return (
              <button
                key={a}
                onClick={() => setFilterAgent(a)}
                className={`px-3 py-1.5 text-xs rounded border ${filterAgent === a ? "bg-gray-800 text-white border-gray-800" : "hover:bg-gray-50"}`}
              >
                {agentLabel(a)} ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* Recommendations */}
      {isLoading && <div className="text-gray-400">Loading AI recommendations…</div>}

      {activeRunId && !isLoading && (!recs || recs.length === 0) && (
        <div className="text-center py-12 text-gray-400">
          No AI recommendations yet. Click &quot;Run All AI Agents&quot; to generate insights.
        </div>
      )}

      {activeRunId && !isLoading && recs && recs.length > 0 && (
        <div className="space-y-6">
          {groupedByAgent
            .filter((g) => g.items.length > 0)
            .map((g) => (
              <div key={g.agent}>
                <h3 className="font-semibold text-gray-700 mb-3">{AGENT_ICON[g.agent]} {agentLabel(g.agent)} ({g.items.length})</h3>
                <div className="space-y-3">
                  {g.items.map((rec) => (
                    <RecCard
                      key={rec.id}
                      rec={rec}
                      onAction={(id, notes) => actionRec.mutate({ id, notes })}
                    />
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
