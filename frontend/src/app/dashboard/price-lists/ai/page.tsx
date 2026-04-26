"use client";
import { useState, useEffect } from "react";
import { plApi, PLAIRec, PLAIAgentType, PLAIRecStatus } from "@/lib/price_list";

const AGENT_LABELS: Record<PLAIAgentType, string> = {
  PRICING_RISK_MONITOR: "Pricing Risk Monitor",
  PRICE_OPTIMIZATION: "Price Optimization",
  DISCOUNT_ABUSE_DETECTOR: "Discount Abuse Detector",
};

const AGENT_DESCS: Record<PLAIAgentType, string> = {
  PRICING_RISK_MONITOR: "Detects expired active price lists, prices below margin threshold, and inconsistent customer pricing.",
  PRICE_OPTIMIZATION: "Identifies overlapping price lists, suggests consolidation, and flags simplification opportunities.",
  DISCOUNT_ABUSE_DETECTOR: "Finds customer-specific lists without margin guards, enabling uncapped discounting.",
};

const SEVERITY_COLORS: Record<string, string> = {
  INFO: "bg-blue-100 text-blue-800",
  WARNING: "bg-yellow-100 text-yellow-800",
  CRITICAL: "bg-red-100 text-red-800",
};

const STATUS_COLORS: Record<PLAIRecStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACKNOWLEDGED: "bg-blue-100 text-blue-800",
  ACTIONED: "bg-green-100 text-green-800",
  DISMISSED: "bg-gray-100 text-gray-500",
};

export default function PLAIPage() {
  const [recs, setRecs] = useState<PLAIRec[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [agentFilter, setAgentFilter] = useState<PLAIAgentType | "">("");
  const [statusFilter, setStatusFilter] = useState<PLAIRecStatus | "">("");

  const load = () => {
    setLoading(true);
    plApi.listAIRecs().then(setRecs).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const runAI = async () => {
    setRunning(true);
    const res = await plApi.runAI();
    setRunning(false);
    load();
    alert(`AI agents generated ${res.generated} recommendation(s).`);
  };

  const ack = (rec: PLAIRec, status: PLAIRecStatus) =>
    plApi.ackAIRec(rec.id, status, "pricing_team").then(load);

  const filtered = recs.filter((r) =>
    (!agentFilter || r.agent_type === agentFilter) &&
    (!statusFilter || r.status === statusFilter)
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Price List AI Agents</h1>
          <p className="text-sm text-gray-500 mt-1">3 agents monitoring pricing risk, optimization, and discount compliance</p>
        </div>
        <button onClick={runAI} disabled={running}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {running ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {(["PRICING_RISK_MONITOR", "PRICE_OPTIMIZATION", "DISCOUNT_ABUSE_DETECTOR"] as PLAIAgentType[]).map((agent) => (
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

      <div className="flex gap-3">
        <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Agents</option>
          {(["PRICING_RISK_MONITOR", "PRICE_OPTIMIZATION", "DISCOUNT_ABUSE_DETECTOR"] as PLAIAgentType[]).map((a) => (
            <option key={a} value={a}>{AGENT_LABELS[a]}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {(["PENDING", "ACKNOWLEDGED", "ACTIONED", "DISMISSED"] as PLAIRecStatus[]).map((s) => (
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
            No recommendations. Click "Run AI Agents" to analyze your price lists.
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
                {rec.header_id && (
                  <a href={`/dashboard/price-lists/${rec.header_id}`} className="text-xs text-blue-600 hover:underline mt-1 block">
                    Open Price List →
                  </a>
                )}
              </div>
              {rec.status === "PENDING" && (
                <div className="flex flex-col gap-2 shrink-0">
                  <button onClick={() => ack(rec, "ACKNOWLEDGED")} className="px-3 py-1.5 bg-blue-100 text-blue-800 rounded-lg text-xs font-medium">Acknowledge</button>
                  <button onClick={() => ack(rec, "ACTIONED")} className="px-3 py-1.5 bg-green-100 text-green-800 rounded-lg text-xs font-medium">Mark Actioned</button>
                  <button onClick={() => ack(rec, "DISMISSED")} className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium">Dismiss</button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
