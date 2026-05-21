"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scApi, SCAIRecOut, SCAIAgentType, agentLabel, riskBadge, fmt } from "@/lib/subcontracting";

const AGENT_COLORS: Record<SCAIAgentType, string> = {
  PERFORMANCE_ANALYZER: "bg-blue-50 border-blue-200 text-blue-900",
  COST_OPTIMIZER:       "bg-green-50 border-green-200 text-green-900",
  RISK_DETECTOR:        "bg-red-50 border-red-200 text-red-900",
};
const AGENT_ICON: Record<SCAIAgentType, string> = {
  PERFORMANCE_ANALYZER: "📊",
  COST_OPTIMIZER:       "💰",
  RISK_DETECTOR:        "⚠️",
};

function RecCard({ rec, onAction }: { rec: SCAIRecOut; onAction: (id: string, notes: string) => void }) {
  const [notes, setNotes] = useState("");
  const [expanded, setExpanded] = useState(false);
  return (
    <div className={`border rounded-lg p-4 space-y-2 ${rec.is_actioned ? "opacity-50" : ""} ${AGENT_COLORS[rec.agent_type]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <span className="text-xl">{AGENT_ICON[rec.agent_type]}</span>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold uppercase opacity-70">{agentLabel(rec.agent_type)}</span>
              {rec.risk_level && (
                <span className={`text-xs px-1.5 py-0.5 rounded border ${riskBadge(rec.risk_level)}`}>{rec.risk_level}</span>
              )}
              <span className="text-xs opacity-60">Priority {rec.priority}</span>
              {rec.is_actioned && <span className="text-xs bg-white bg-opacity-70 px-1.5 py-0.5 rounded text-green-700">Actioned ✓</span>}
            </div>
            <p className="font-semibold mt-0.5">{rec.title}</p>
            {rec.order_no && <p className="text-xs opacity-70">Order: {rec.order_no}</p>}
            {rec.supplier_name && <p className="text-xs opacity-70">Supplier: {rec.supplier_name}</p>}
          </div>
        </div>
        {rec.potential_saving && (
          <div className="shrink-0 text-right">
            <p className="text-xs opacity-60">Potential Saving</p>
            <p className="font-bold">KES {fmt(rec.potential_saving, 0)}</p>
          </div>
        )}
      </div>
      <p className="text-sm opacity-90">{rec.recommendation}</p>
      {rec.rationale && (
        <>
          <button onClick={() => setExpanded(!expanded)} className="text-xs underline opacity-70">
            {expanded ? "Hide rationale" : "Show rationale"}
          </button>
          {expanded && <p className="text-xs italic opacity-80 border-t border-current border-opacity-20 pt-2">{rec.rationale}</p>}
        </>
      )}
      {!rec.is_actioned && (
        <div className="flex gap-2 pt-1">
          <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Action notes…"
            className="flex-1 border border-current border-opacity-30 rounded px-2 py-1 text-xs bg-white bg-opacity-50" />
          <button onClick={() => onAction(rec.id, notes)}
            className="px-3 py-1 text-xs bg-white bg-opacity-70 rounded border border-current border-opacity-30 hover:bg-opacity-100 font-medium">
            Mark Actioned
          </button>
        </div>
      )}
    </div>
  );
}

export default function SCAIPage() {
  const qc = useQueryClient();
  const [filterAgent, setFilterAgent] = useState<SCAIAgentType|"">("");

  const { data: recs, isLoading } = useQuery({ queryKey: ["sc-ai-recs"], queryFn: () => scApi.listAIRecs() });
  const runAll = useMutation({
    mutationFn: () => scApi.runAI(),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["sc-ai-recs"] }); alert(`${r.generated} recommendation(s) generated`); },
  });
  const action = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) => scApi.actionAIRec(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sc-ai-recs"] }),
  });

  const filtered = (recs ?? []).filter((r) => !filterAgent || r.agent_type === filterAgent);
  const agents: SCAIAgentType[] = ["PERFORMANCE_ANALYZER","COST_OPTIMIZER","RISK_DETECTOR"];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Subcontracting AI Agents</h1>
          <p className="text-sm text-gray-500">Performance analysis · Cost optimization · Risk detection</p>
        </div>
        <button onClick={() => runAll.mutate()} disabled={runAll.isPending}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {runAll.isPending ? "Running…" : "Run All AI Agents"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {agents.map((a) => (
          <div key={a} className={`border rounded-lg p-4 ${AGENT_COLORS[a]}`}>
            <p className="font-semibold text-sm">{AGENT_ICON[a]} {agentLabel(a)}</p>
            <p className="text-xs mt-1 opacity-80">
              {a === "PERFORMANCE_ANALYZER" && "Detects poor yield, delays, and quality rejection issues per order."}
              {a === "COST_OPTIMIZER" && "Flags high wastage costs and suggests cost-reduction strategies."}
              {a === "RISK_DETECTOR" && "Predicts delivery delays, missing location configs, and material loss risk."}
            </p>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilterAgent("")}
          className={`px-3 py-1.5 text-xs rounded border ${!filterAgent ? "bg-gray-800 text-white border-gray-800" : "hover:bg-gray-50"}`}>
          All ({recs?.length ?? 0})
        </button>
        {agents.map((a) => (
          <button key={a} onClick={() => setFilterAgent(a)}
            className={`px-3 py-1.5 text-xs rounded border ${filterAgent === a ? "bg-gray-800 text-white border-gray-800" : "hover:bg-gray-50"}`}>
            {agentLabel(a)} ({(recs ?? []).filter((r) => r.agent_type === a).length})
          </button>
        ))}
      </div>

      {isLoading && <div className="text-gray-400">Loading…</div>}
      {!isLoading && filtered.length === 0 && (
        <div className="text-center py-12 text-gray-400">No recommendations yet. Click &ldquo;Run All AI Agents&rdquo; to generate insights.</div>
      )}

      <div className="space-y-3">
        {filtered.map((r) => (
          <RecCard key={r.id} rec={r} onAction={(id, notes) => action.mutate({ id, notes })} />
        ))}
      </div>
    </div>
  );
}
