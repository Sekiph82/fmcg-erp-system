"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contractsApi, SEVERITY_COLORS } from "@/lib/contracts";

const AGENT_LABELS: Record<string, string> = {
  RISK_MONITOR:       "Contract Risk Monitor",
  RENEWAL_ADVISOR:    "Renewal Advisor",
  COMPLIANCE_MONITOR: "Compliance Monitor",
};

export default function ContractAIPage() {
  const qc = useQueryClient();
  const { data: recs = [], isLoading } = useQuery({
    queryKey: ["ct-ai-recs-all"],
    queryFn: () => contractsApi.aiRecs(),
  });
  const runMut = useMutation({
    mutationFn: () => contractsApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ct-ai-recs-all"] }),
  });
  const ackMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => contractsApi.ackRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ct-ai-recs-all"] }),
  });

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">AI Intelligence — Contracts</h1>
          <p className="text-slate-500 text-sm mt-0.5">3 AI agents monitoring contract health, risk, and compliance</p>
        </div>
        <button onClick={() => runMut.mutate()} disabled={runMut.isPending}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
          {runMut.isPending ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { key: "RISK_MONITOR", desc: "Detects underperforming contracts (<60% achievement), high rebate cost exposure, and missed volume targets." },
          { key: "RENEWAL_ADVISOR", desc: "Flags contracts expiring within 45 days without auto-renew. Suggests commercial terms to review before renewal." },
          { key: "COMPLIANCE_MONITOR", desc: "Detects large unsettled rebate balances, pricing violations, and deviation from contracted terms." },
        ].map((a) => (
          <div key={a.key} className="glow-card p-4">
            <p className="text-sm font-semibold text-indigo-300 mb-1">{AGENT_LABELS[a.key]}</p>
            <p className="text-xs text-slate-500">{a.desc}</p>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {isLoading && <p className="text-slate-500 text-sm">Loading…</p>}
        {!isLoading && recs.length === 0 && (
          <div className="glow-card p-8 text-center text-slate-600">
            No recommendations — click &quot;Run AI Agents&quot; to generate insights.
          </div>
        )}
        {recs.map((r) => (
          <div key={r.id} className="glow-card p-4">
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
