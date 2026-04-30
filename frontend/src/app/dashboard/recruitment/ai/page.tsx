"use client";
import { useEffect, useState } from "react";
import { recruitmentApi, RTAIRecommendation, RTAIAgentType, RTAIRecStatus, AI_AGENT_LABEL } from "@/lib/recruitment";

const AGENTS: { type: RTAIAgentType; desc: string; fn: () => Promise<{ generated: number }> }[] = [
  { type: "candidate_matcher", desc: "Identifies open requisitions with too few active candidates in pipeline and suggests sourcing actions.", fn: () => recruitmentApi.runCandidateMatcher() },
  { type: "hiring_risk_detector", desc: "Flags offers pending too long and candidates with repeated interview failures.", fn: () => recruitmentApi.runHiringRiskDetector() },
  { type: "pipeline_optimizer", desc: "Detects stage bottlenecks and requisitions open 60+ days without a hire.", fn: () => recruitmentApi.runPipelineOptimizer() },
];

const agentColor: Record<RTAIAgentType, string> = {
  candidate_matcher: "bg-blue-500/20 text-blue-300",
  hiring_risk_detector: "bg-red-500/20 text-red-300",
  pipeline_optimizer: "bg-amber-500/20 text-amber-300",
};

export default function RecruitmentAIPage() {
  const [recs, setRecs] = useState<RTAIRecommendation[]>([]);
  const [running, setRunning] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const loadRecs = () => recruitmentApi.listRecs().then(setRecs).catch(console.error);
  useEffect(() => { loadRecs(); }, []);

  const runAgent = async (agent: (typeof AGENTS)[0]) => {
    setRunning(agent.type);
    const result = await agent.fn();
    setMsg(`${AI_AGENT_LABEL[agent.type]}: ${result.generated} recommendation(s) generated`);
    await loadRecs(); setRunning(null); setTimeout(() => setMsg(""), 3000);
  };
  const ack = async (id: string, status: RTAIRecStatus) => { await recruitmentApi.ackRec(id, { status }); loadRecs(); };
  const pendingRecs = recs.filter((r) => r.status === "pending");

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">AI Recruitment Insights</h1>
        <p className="text-slate-500 text-sm mt-0.5">3 agents monitoring pipeline, risks, and bottlenecks</p>
      </div>
      {msg && <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-3 text-sm text-indigo-300">{msg}</div>}

      <div className="grid grid-cols-3 gap-4">
        {AGENTS.map((a) => (
          <div key={a.type} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
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
            <div key={r.rec_id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 space-y-2">
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
          {pendingRecs.length === 0 && <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-8 text-center text-slate-600">No pending recommendations — run an agent above.</div>}
        </div>
      </div>
    </div>
  );
}
