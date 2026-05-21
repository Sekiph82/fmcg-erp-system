"use client";
import { useEffect, useState } from "react";
import { essApi, ESSAIRecommendation, ESSAIAgentType, ESSAIRecStatus, AI_AGENT_LABEL } from "@/lib/ess";

const AGENTS: { type: ESSAIAgentType; desc: string; fn: () => Promise<{ generated: number }> }[] = [
  { type: "employee_assistant", desc: "Surfaces pending tasks, low leave balances, and long-pending leave requests for each employee.", fn: () => essApi.runEmployeeAssistant() },
  { type: "hr_support_assistant", desc: "Detects request backlogs, high leave rejection rates, and systemic HR service issues.", fn: () => essApi.runHRSupportAssistant() },
];

const agentColor: Record<ESSAIAgentType, string> = {
  employee_assistant: "bg-blue-500/20 text-blue-300",
  hr_support_assistant: "bg-purple-500/20 text-purple-300",
};

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
    await loadRecs(); setRunning(null); setTimeout(() => setMsg(""), 3000);
  };
  const ack = async (id: string, status: ESSAIRecStatus) => { await essApi.ackRec(id, { status }); loadRecs(); };
  const pendingRecs = recs.filter((r) => r.status === "pending");

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">AI ESS Insights</h1>
        <p className="text-slate-500 text-sm mt-0.5">2 agents monitoring employee wellbeing and HR efficiency</p>
      </div>
      {msg && <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-3 text-sm text-indigo-300">{msg}</div>}

      <div className="grid grid-cols-2 gap-4">
        {AGENTS.map((a) => (
          <div key={a.type} className="glow-card p-5 space-y-3">
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${agentColor[a.type]}`}>{AI_AGENT_LABEL[a.type]}</span>
            <p className="text-xs text-slate-500">{a.desc}</p>
            <button onClick={() => runAgent(a)} disabled={running === a.type}
              className="w-full px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm disabled:opacity-50">
              {running === a.type ? "Running…" : "Run Agent"}
            </button>
          </div>
        ))}
      </div>

      <div>
        <h2 className="text-sm font-semibold text-white mb-3">Pending Recommendations ({pendingRecs.length})</h2>
        <div className="space-y-3">
          {pendingRecs.map((r) => (
            <div key={r.rec_id} className="glow-card p-4 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${agentColor[r.agent_type]}`}>{AI_AGENT_LABEL[r.agent_type]}</span>
                  <p className="text-sm text-white font-medium">{r.subject}</p>
                </div>
                <span className="text-xs text-slate-600 shrink-0">{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
              <p className="text-xs text-slate-400">{r.body}</p>
              <div className="flex gap-2">
                <button onClick={() => ack(r.rec_id, "acknowledged")} className="px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-xs">Acknowledge</button>
                <button onClick={() => ack(r.rec_id, "actioned")} className="px-3 py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-xs">Actioned</button>
                <button onClick={() => ack(r.rec_id, "dismissed")} className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 text-xs">Dismiss</button>
              </div>
            </div>
          ))}
          {pendingRecs.length === 0 && <div className="glow-card p-8 text-center text-slate-600">No pending recommendations — run an agent above.</div>}
        </div>
      </div>
    </div>
  );
}
