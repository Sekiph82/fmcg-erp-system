"use client";
import { useEffect, useState } from "react";
import { essApi, ESSAIRecommendation, ESSAIAgentType, ESSAIRecStatus, AI_AGENT_LABEL } from "@/lib/ess";

const AGENTS: { type: ESSAIAgentType; desc: string; fn: () => Promise<{ generated: number }> }[] = [
  {
    type: "employee_assistant",
    desc: "Surfaces pending tasks, low leave balances, and long-pending leave requests for each employee.",
    fn: () => essApi.runEmployeeAssistant(),
  },
  {
    type: "hr_support_assistant",
    desc: "Detects request backlogs, high leave rejection rates, and systemic HR service issues.",
    fn: () => essApi.runHRSupportAssistant(),
  },
];

export default function ESSAIPage() {
  const [recs, setRecs] = useState<ESSAIRecommendation[]>([]);
  const [running, setRunning] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const loadRecs = () => essApi.listRecs().then(setRecs).catch(console.error);
  useEffect(() => { loadRecs(); }, []);

  const runAgent = async (agent: (typeof AGENTS)[0]) => {
    setRunning(agent.type);
    const result = await agent.fn();
    setMsg(`${AI_AGENT_LABEL[agent.type]}: ${result.generated} recommendation(s) generated`);
    await loadRecs();
    setRunning(null);
    setTimeout(() => setMsg(""), 3000);
  };

  const ack = async (id: string, status: ESSAIRecStatus) => {
    await essApi.ackRec(id, { status });
    loadRecs();
  };

  const agentColor: Record<ESSAIAgentType, string> = {
    employee_assistant: "bg-blue-100 text-blue-700",
    hr_support_assistant: "bg-purple-100 text-purple-700",
  };

  const pendingRecs = recs.filter((r) => r.status === "pending");

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold">AI ESS Insights</h1>
      {msg && <div className="bg-blue-50 text-blue-700 text-sm px-4 py-2 rounded">{msg}</div>}

      <div className="grid grid-cols-2 gap-4">
        {AGENTS.map((a) => (
          <div key={a.type} className="bg-white border rounded-xl p-5 space-y-3">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${agentColor[a.type]}`}>
              {AI_AGENT_LABEL[a.type]}
            </span>
            <p className="text-xs text-gray-500">{a.desc}</p>
            <button onClick={() => runAgent(a)} disabled={running === a.type}
              className="w-full bg-indigo-600 text-white text-sm py-2 rounded hover:bg-indigo-700 disabled:opacity-50">
              {running === a.type ? "Running…" : "Run Agent"}
            </button>
          </div>
        ))}
      </div>

      <div>
        <h2 className="text-sm font-semibold mb-3">Pending Recommendations ({pendingRecs.length})</h2>
        <div className="space-y-3">
          {pendingRecs.map((r) => (
            <div key={r.rec_id} className="bg-white border rounded-xl p-4 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${agentColor[r.agent_type]}`}>
                    {AI_AGENT_LABEL[r.agent_type]}
                  </span>
                  <p className="font-semibold text-sm">{r.subject}</p>
                </div>
                <span className="text-xs text-gray-400 shrink-0">{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
              <p className="text-sm text-gray-600">{r.body}</p>
              <div className="flex gap-2">
                <button onClick={() => ack(r.rec_id, "acknowledged")} className="text-xs bg-green-50 text-green-700 px-3 py-1 rounded hover:bg-green-100">Acknowledge</button>
                <button onClick={() => ack(r.rec_id, "actioned")} className="text-xs bg-blue-50 text-blue-700 px-3 py-1 rounded hover:bg-blue-100">Actioned</button>
                <button onClick={() => ack(r.rec_id, "dismissed")} className="text-xs bg-gray-50 text-gray-500 px-3 py-1 rounded hover:bg-gray-100">Dismiss</button>
              </div>
            </div>
          ))}
          {pendingRecs.length === 0 && <p className="text-sm text-gray-400">No pending recommendations — run an agent above.</p>}
        </div>
      </div>
    </div>
  );
}
