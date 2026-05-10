"use client";
import { useState, useEffect } from "react";
import { spApi, SPAIRec, SPAIAgentType, SPAIRecStatus, SP_SEVERITY_COLORS } from "@/lib/supplier_portal";

const AGENT_LABELS: Record<SPAIAgentType, string> = {
  COLLABORATION_MONITOR: "Collaboration Monitor",
  FRICTION_ASSISTANT: "Friction Assistant",
  RISK_SIGNAL: "Risk Signal",
};

const AGENT_DESCS: Record<SPAIAgentType, string> = {
  COLLABORATION_MONITOR: "Detects suppliers who delay PO acknowledgment or frequently revise ETAs.",
  FRICTION_ASSISTANT: "Identifies low-adoption suppliers needing onboarding help or workflow improvements.",
  RISK_SIGNAL: "Flags compliance document expiry risk, invoice anomalies, and delivery behavior patterns.",
};

const STATUS_COLORS: Record<SPAIRecStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACKNOWLEDGED: "bg-blue-100 text-blue-800",
  ACTIONED: "bg-green-100 text-green-800",
  DISMISSED: "bg-gray-100 text-gray-500",
};

export default function SPAIPage() {
  const [recs, setRecs] = useState<SPAIRec[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState<SPAIAgentType | "">("");
  const [statusFilter, setStatusFilter] = useState<SPAIRecStatus | "">("");

  const load = () => {
    setLoading(true);
    spApi.listAIRecs().then(setRecs).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const runAI = async () => {
    setRunning(true);
    const res = await spApi.runAI();
    setRunning(false);
    load();
    alert(`AI agents generated ${res.generated} recommendation(s).`);
  };

  const ack = async (rec: SPAIRec, status: SPAIRecStatus) => {
    await spApi.ackAIRec(rec.id, { status, actioned_by: "procurement_team" });
    load();
  };

  const filtered = recs.filter((r) =>
    (filter ? r.agent_type === filter : true) &&
    (statusFilter ? r.status === statusFilter : true)
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Supplier Portal AI Agents</h1>
          <p className="text-sm text-gray-500 mt-1">3 autonomous agents monitoring supplier collaboration health</p>
        </div>
        <button onClick={runAI} disabled={running}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {running ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {(["COLLABORATION_MONITOR", "FRICTION_ASSISTANT", "RISK_SIGNAL"] as SPAIAgentType[]).map((agent) => (
          <div key={agent} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="text-sm font-semibold text-gray-900">{AGENT_LABELS[agent]}</span>
            </div>
            <p className="text-xs text-gray-500">{AGENT_DESCS[agent]}</p>
            <div className="mt-3 text-lg font-bold text-gray-800">
              {recs.filter((r) => r.agent_type === agent && r.status === "PENDING").length}
              <span className="text-xs font-normal text-gray-500 ml-1">pending</span>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        <select value={filter} onChange={(e) => setFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Agents</option>
          {(["COLLABORATION_MONITOR", "FRICTION_ASSISTANT", "RISK_SIGNAL"] as SPAIAgentType[]).map((a) => (
            <option key={a} value={a}>{AGENT_LABELS[a]}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {(["PENDING", "ACKNOWLEDGED", "ACTIONED", "DISMISSED"] as SPAIRecStatus[]).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="space-y-3">
        {loading ? (
          <div className="text-gray-400 text-sm p-4">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400 text-sm">
            No recommendations found. Click &quot;Run AI Agents&quot; to generate insights.
          </div>
        ) : filtered.map((rec) => (
          <div key={rec.id} className={`bg-white border rounded-xl p-4 ${rec.severity === "CRITICAL" ? "border-red-300" : rec.severity === "WARNING" ? "border-yellow-300" : "border-gray-200"}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${SP_SEVERITY_COLORS[rec.severity] || "bg-gray-100"}`}>{rec.severity}</span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{AGENT_LABELS[rec.agent_type]}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_COLORS[rec.status]}`}>{rec.status}</span>
                </div>
                <div className="font-semibold text-gray-900 text-sm">{rec.title}</div>
                <div className="text-sm text-gray-600 mt-1">{rec.body}</div>
                {rec.reference_type && (
                  <div className="text-xs text-gray-400 mt-1">{rec.reference_type}: {rec.reference_id?.slice(0, 12)}</div>
                )}
                {rec.actioned_by && (
                  <div className="text-xs text-gray-400 mt-1">Actioned by: {rec.actioned_by}</div>
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
