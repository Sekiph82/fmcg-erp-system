"use client";
import { useCallback, useEffect, useState } from "react";
import { portalApi, PortalAIRec, PortalAIAgentType, AI_AGENT_LABELS } from "@/lib/portal";

const PRIORITY_COLORS: Record<string, string> = {
  HIGH: "bg-red-100 text-red-700",
  MEDIUM: "bg-yellow-100 text-yellow-700",
  LOW: "bg-green-100 text-green-700",
};

export default function PortalAIPage() {
  const [recs, setRecs] = useState<PortalAIRec[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<PortalAIAgentType | null>(null);
  const [agentFilter, setAgentFilter] = useState<PortalAIAgentType | "">("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  const loadRecs = useCallback(() => {
    portalApi.getAIRecs({ agent_type: agentFilter || undefined, status: statusFilter || undefined })
      .then(d => setRecs(d as PortalAIRec[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [agentFilter, statusFilter]);

  useEffect(() => { setLoading(true); loadRecs(); }, [loadRecs]);

  const runAgent = async (agent: PortalAIAgentType) => {
    setRunning(agent);
    try {
      const map = {
        SUPPORT_ASSISTANT: portalApi.runSupportAssistant,
        FRICTION_MONITOR: portalApi.runFrictionMonitor,
        COMMERCIAL_OPPORTUNITY: portalApi.runCommercialOpportunity,
      };
      const result = await map[agent]();
      alert((result as { message: string }).message);
      loadRecs();
    } catch (e) { console.error(e); }
    setRunning(null);
  };

  const handleAck = async (id: string, status: string) => {
    try {
      await portalApi.ackAIRec(id, { status, acknowledged_by: "admin" });
      loadRecs();
    } catch (e) { console.error(e); }
  };

  const agents: { type: PortalAIAgentType; icon: string; desc: string; color: string }[] = [
    {
      type: "SUPPORT_ASSISTANT",
      icon: "🎧",
      desc: "Identifies portal accounts with multiple open claims that need proactive support intervention.",
      color: "from-blue-50 to-cyan-50 border-blue-200",
    },
    {
      type: "FRICTION_MONITOR",
      icon: "🔍",
      desc: "Detects accounts browsing the portal frequently without placing orders — possible friction points.",
      color: "from-orange-50 to-yellow-50 border-orange-200",
    },
    {
      type: "COMMERCIAL_OPPORTUNITY",
      icon: "💡",
      desc: "Identifies portal accounts that haven't ordered in 45+ days and should be nudged to reorder.",
      color: "from-green-50 to-emerald-50 border-green-200",
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Portal AI Agents</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          AI never auto-submits orders or actions. All recommendations require human review.
        </p>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {agents.map(agent => (
          <div key={agent.type} className={`rounded-xl border bg-gradient-to-br p-4 ${agent.color}`}>
            <div className="text-2xl mb-2">{agent.icon}</div>
            <div className="font-semibold text-gray-800 text-sm mb-1">{AI_AGENT_LABELS[agent.type]}</div>
            <p className="text-xs text-gray-600 mb-3">{agent.desc}</p>
            <button onClick={() => runAgent(agent.type)} disabled={running !== null}
              className="w-full py-2 bg-white border shadow-sm rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50">
              {running === agent.type ? "Running…" : "Run Agent"}
            </button>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-800">Recommendations</h2>
          <div className="flex gap-2">
            <select value={agentFilter} onChange={e => setAgentFilter(e.target.value as PortalAIAgentType | "")}
              className="text-sm border rounded-lg px-2 py-1.5">
              <option value="">All Agents</option>
              {Object.entries(AI_AGENT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="text-sm border rounded-lg px-2 py-1.5">
              <option value="">All</option>
              <option value="PENDING">Pending</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="ACTIONED">Actioned</option>
              <option value="DISMISSED">Dismissed</option>
            </select>
          </div>
        </div>

        {loading && <div className="text-gray-400 py-6 text-center">Loading…</div>}
        {!loading && recs.length === 0 && (
          <div className="bg-gray-50 rounded-xl border p-6 text-center text-gray-400 text-sm">
            No recommendations. Run an agent above to generate insights.
          </div>
        )}

        <div className="space-y-3">
          {recs.map(rec => (
            <div key={rec.id} className="bg-white rounded-xl border shadow-sm p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-400">{AI_AGENT_LABELS[rec.agent_type]}</span>
                    {rec.priority && (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[rec.priority] || "bg-gray-100 text-gray-600"}`}>
                        {rec.priority}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">{rec.created_at ? new Date(rec.created_at).toLocaleDateString() : ""}</span>
                  </div>
                  <div className="font-medium text-gray-800 mt-1">{rec.title}</div>
                  <p className="text-xs text-gray-600 mt-1 leading-relaxed">{rec.body}</p>
                </div>
                {rec.status === "PENDING" && (
                  <div className="flex flex-col gap-1 flex-shrink-0">
                    <button onClick={() => handleAck(rec.id, "ACTIONED")}
                      className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">
                      {rec.action_label || "Action"}
                    </button>
                    <button onClick={() => handleAck(rec.id, "ACKNOWLEDGED")}
                      className="text-xs border text-gray-600 px-3 py-1 rounded hover:bg-gray-50">
                      Acknowledge
                    </button>
                    <button onClick={() => handleAck(rec.id, "DISMISSED")}
                      className="text-xs text-gray-400 hover:underline text-center">
                      Dismiss
                    </button>
                  </div>
                )}
                {rec.status !== "PENDING" && (
                  <span className="text-xs text-gray-400 flex-shrink-0">{rec.status}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
