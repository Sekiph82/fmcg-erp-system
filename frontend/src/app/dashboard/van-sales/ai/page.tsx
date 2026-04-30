"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vanSalesApi, SEVERITY_COLORS } from "@/lib/van_sales";

const AGENT_LABELS: Record<string, string> = {
  ROUTE_OPTIMIZER: "Route Optimizer",
  SALES_ASSISTANT: "Sales Assistant",
  RISK_MONITOR:    "Risk Monitor",
};

export default function VanSalesAIPage() {
  const qc = useQueryClient();
  const { data: recs = [], isLoading } = useQuery({
    queryKey: ["vs-ai-recs-all"],
    queryFn: () => vanSalesApi.aiRecs(),
  });

  const runMut = useMutation({
    mutationFn: () => vanSalesApi.runAI(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vs-ai-recs-all"] }),
  });

  const ackMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => vanSalesApi.ackRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vs-ai-recs-all"] }),
  });

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">AI Intelligence — Van Sales</h1>
          <p className="text-slate-500 text-sm mt-0.5">3 AI agents monitoring route, sales, and risk</p>
        </div>
        <button onClick={() => runMut.mutate()} disabled={runMut.isPending}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
          {runMut.isPending ? "Running…" : "Run AI Agents"}
        </button>
      </div>

      {/* Agent descriptions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { key: "ROUTE_OPTIMIZER", desc: "Suggests better route sequencing, flags vans with high missed-visit rates, recommends visit priority based on customer value." },
          { key: "SALES_ASSISTANT", desc: "Detects vans with no recent sales, suggests upsell opportunities, flags customers overdue for a reorder visit." },
          { key: "RISK_MONITOR", desc: "Detects unusual discounts, stock discrepancies, missed collections, and unauthorized payment patterns." },
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
            No AI recommendations — click "Run AI Agents" to generate insights.
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
