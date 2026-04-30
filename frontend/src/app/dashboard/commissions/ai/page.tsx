"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commissionsApi, SEVERITY_COLORS, AGENT_LABELS } from "@/lib/commissions";

export default function CommissionsAIPage() {
  const qc = useQueryClient();
  const { data: recs = [], isLoading } = useQuery({
    queryKey: ["cm-ai-recs-all"],
    queryFn: () => commissionsApi.aiRecs(),
  });
  const runMut = useMutation({
    mutationFn: () => commissionsApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cm-ai-recs-all"] }),
  });
  const ackMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => commissionsApi.ackRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cm-ai-recs-all"] }),
  });

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">AI Intelligence — Commissions</h1>
          <p className="text-slate-500 text-sm mt-0.5">3 agents monitoring incentives, fraud, and performance</p>
        </div>
        <button onClick={() => runMut.mutate()} disabled={runMut.isPending}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
          {runMut.isPending ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { key: "INCENTIVE_OPTIMIZER", desc: "Identifies gaps in commission coverage, underperforming reps, and suggests better commission structures to improve motivation." },
          { key: "FRAUD_DETECTION", desc: "Flags commission spikes (>3× average), duplicate calculations, and manipulation patterns before they are approved and paid out." },
          { key: "PERFORMANCE_ADVISOR", desc: "Identifies reps below 50% target achievement and suggests coaching actions, territory reviews, or target adjustments." },
        ].map((a) => (
          <div key={a.key} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <p className="text-sm font-semibold text-indigo-300 mb-1">{AGENT_LABELS[a.key]}</p>
            <p className="text-xs text-slate-500">{a.desc}</p>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {isLoading && <p className="text-slate-500 text-sm">Loading…</p>}
        {!isLoading && recs.length === 0 && (
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-8 text-center text-slate-600">
            No recommendations — click "Run AI Agents" to generate insights.
          </div>
        )}
        {recs.map((r) => (
          <div key={r.id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLORS[r.severity] ?? "bg-slate-500/20 text-slate-400"}`}>{r.severity}</span>
                  <span className="text-[10px] text-slate-500">{AGENT_LABELS[r.agent_type] ?? r.agent_type}</span>
                  <span className="text-[10px] text-slate-600">{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-white font-medium mb-1">{r.title}</p>
                <p className="text-xs text-slate-400">{r.body}</p>
              </div>
              {r.status === "PENDING" && (
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => ackMut.mutate({ id: r.id, status: "ACKNOWLEDGED" })}
                    className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 text-xs">Ack</button>
                  <button onClick={() => ackMut.mutate({ id: r.id, status: "DISMISSED" })}
                    className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-500 text-xs">Dismiss</button>
                </div>
              )}
              {r.status !== "PENDING" && <span className="text-xs text-slate-600 shrink-0">{r.status}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
