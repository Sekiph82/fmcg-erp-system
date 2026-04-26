"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningAIRec, DunningAIAgentType, DunningAIRecStatus, SEVERITY_COLORS } from "@/lib/dunning";

const AGENT_LABELS: Record<DunningAIAgentType, string> = {
  COLLECTION_PRIORITIZATION: "Collection Prioritization",
  PAYMENT_RISK_MONITOR: "Payment Risk Monitor",
  EFFECTIVENESS_ASSISTANT: "Effectiveness Assistant",
};

const AGENT_DESCS: Record<DunningAIAgentType, string> = {
  COLLECTION_PRIORITIZATION: "Suggests which overdue accounts to chase first and flags unassigned high-priority cases.",
  PAYMENT_RISK_MONITOR: "Detects customers showing worsening payment behavior, rising disputes, or repeated broken promises.",
  EFFECTIVENESS_ASSISTANT: "Identifies stale dunning cases where levels are not advancing or actions have not been taken.",
};

const STATUS_COLORS: Record<DunningAIRecStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACKNOWLEDGED: "bg-blue-100 text-blue-800",
  ACTIONED: "bg-green-100 text-green-800",
  DISMISSED: "bg-gray-100 text-gray-500",
};

export default function DunningAIPage() {
  const [recs, setRecs] = useState<DunningAIRec[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [agentFilter, setAgentFilter] = useState<DunningAIAgentType | "">("");
  const [statusFilter, setStatusFilter] = useState<DunningAIRecStatus | "">("");

  const load = () => {
    setLoading(true);
    dunningApi.listAIRecs().then(setRecs).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const runAI = async () => {
    setRunning(true);
    const res = await dunningApi.runAI();
    setRunning(false);
    load();
    alert(`AI agents generated ${res.generated} recommendation(s).`);
  };

  const ack = (rec: DunningAIRec, status: DunningAIRecStatus) =>
    dunningApi.ackAIRec(rec.id, status, "collections_team").then(load);

  const filtered = recs.filter((r) =>
    (!agentFilter || r.agent_type === agentFilter) &&
    (!statusFilter || r.status === statusFilter)
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Dunning AI Agents</h1>
          <p className="text-sm text-gray-500 mt-1">3 agents monitoring collection health, payment risk, and dunning effectiveness</p>
        </div>
        <button onClick={runAI} disabled={running}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {running ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {(["COLLECTION_PRIORITIZATION", "PAYMENT_RISK_MONITOR", "EFFECTIVENESS_ASSISTANT"] as DunningAIAgentType[]).map((agent) => (
          <div key={agent} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="text-sm font-semibold text-gray-900">{AGENT_LABELS[agent]}</span>
            </div>
            <p className="text-xs text-gray-500">{AGENT_DESCS[agent]}</p>
            <div className="mt-3 text-xl font-bold text-gray-800">
              {recs.filter((r) => r.agent_type === agent && r.status === "PENDING").length}
              <span className="text-xs font-normal text-gray-500 ml-1">pending</span>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Agents</option>
          {(["COLLECTION_PRIORITIZATION", "PAYMENT_RISK_MONITOR", "EFFECTIVENESS_ASSISTANT"] as DunningAIAgentType[]).map((a) => (
            <option key={a} value={a}>{AGENT_LABELS[a]}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {(["PENDING", "ACKNOWLEDGED", "ACTIONED", "DISMISSED"] as DunningAIRecStatus[]).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="px-3 py-2 text-sm text-gray-500">{filtered.length} recommendations</span>
      </div>

      <div className="space-y-3">
        {loading ? (
          <div className="text-gray-400 text-sm">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400 text-sm">
            No recommendations. Click "Run AI Agents" to analyze your dunning cases.
          </div>
        ) : filtered.map((rec) => (
          <div key={rec.id} className={`bg-white border rounded-xl p-4 ${rec.severity === "CRITICAL" ? "border-red-300" : rec.severity === "WARNING" ? "border-yellow-300" : "border-gray-200"}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SEVERITY_COLORS[rec.severity] || "bg-gray-100"}`}>{rec.severity}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{AGENT_LABELS[rec.agent_type]}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_COLORS[rec.status]}`}>{rec.status}</span>
                </div>
                <div className="font-semibold text-gray-900 text-sm">{rec.title}</div>
                <div className="text-sm text-gray-600 mt-1">{rec.body}</div>
                {rec.reference_type && (
                  <div className="text-xs text-gray-400 mt-1">{rec.reference_type}: {rec.reference_id?.slice(0, 12)}</div>
                )}
                {rec.case_id && (
                  <a href={`/dashboard/dunning/cases/${rec.case_id}`} className="text-xs text-blue-600 hover:underline mt-1 block">
                    Open Case →
                  </a>
                )}
              </div>
              {rec.status === "PENDING" && (
                <div className="flex flex-col gap-2 shrink-0">
                  <button onClick={() => ack(rec, "ACKNOWLEDGED")}
                    className="px-3 py-1.5 bg-blue-100 text-blue-800 rounded-lg text-xs font-medium hover:bg-blue-200">Acknowledge</button>
                  <button onClick={() => ack(rec, "ACTIONED")}
                    className="px-3 py-1.5 bg-green-100 text-green-800 rounded-lg text-xs font-medium hover:bg-green-200">Mark Actioned</button>
                  <button onClick={() => ack(rec, "DISMISSED")}
                    className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200">Dismiss</button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
