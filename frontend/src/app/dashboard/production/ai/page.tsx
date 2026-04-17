"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  productionAiApi,
  AGENT_LABELS, AGENT_COLORS, AGENT_BG,
  SEVERITY_COLORS, SEVERITY_BG,
  RISK_COLORS, RISK_BG,
  fmtConfidence, confidenceColor,
  type AnomalyRead, type SuggestionRead, type PredictionRead,
  type AgentType, type SeverityType, type RiskLevel,
} from "@/lib/productionAi";
import { extractApiError } from "@/lib/inventory";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

// ── helpers ────────────────────────────────────────────────────────────────────

const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleString("en-KE", { dateStyle: "short", timeStyle: "short" }) : "—";

const fmtPct = (v: number | null | undefined) =>
  v != null ? `${v > 0 ? "+" : ""}${v.toFixed(1)}%` : "—";

// ── sub-components ─────────────────────────────────────────────────────────────

function AgentCard({
  type, anomalyCount, suggestionCount, pendingCount, onClick,
}: {
  type: AgentType;
  anomalyCount: number;
  suggestionCount: number;
  pendingCount: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl border p-4 text-left w-full hover:opacity-90 transition-opacity ${AGENT_BG[type]}`}
    >
      <div className={`text-xs font-semibold uppercase tracking-wide mb-2 ${AGENT_COLORS[type]}`}>
        {AGENT_LABELS[type]}
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
        <div><span className="block text-lg font-bold text-white">{anomalyCount}</span>Anomalies</div>
        <div><span className="block text-lg font-bold text-white">{suggestionCount}</span>Suggestions</div>
        <div><span className="block text-lg font-bold text-amber-400">{pendingCount}</span>Pending</div>
      </div>
    </button>
  );
}

function SeverityBadge({ s }: { s: string }) {
  const sev = (s || "medium") as SeverityType;
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${SEVERITY_BG[sev]} ${SEVERITY_COLORS[sev]}`}>
      {sev}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const lvl = (level || "GREEN") as RiskLevel;
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${RISK_BG[lvl]} ${RISK_COLORS[lvl]}`}>
      {lvl}
    </span>
  );
}

function ConfidenceBar({ score }: { score: number }) {
  const w = Math.round(score * 100);
  const color = score >= 0.8 ? "bg-emerald-500" : score >= 0.6 ? "bg-amber-500" : "bg-slate-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
      </div>
      <span className={`text-xs ${confidenceColor(score)}`}>{fmtConfidence(score)}</span>
    </div>
  );
}

// ── tabs ───────────────────────────────────────────────────────────────────────

type Tab = "overview" | "anomalies" | "suggestions" | "predictions" | "maintenance";

// ── page ──────────────────────────────────────────────────────────────────────

export default function ProductionAIPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [tab, setTab]               = useState<Tab>("overview");
  const [runOrderId, setRunOrderId] = useState("");
  const [anomalyFilter, setAnomalyFilter] = useState<"all" | "unresolved">("unresolved");
  const [sugFilter, setSugFilter]   = useState("pending");
  const [resolveId, setResolveId]   = useState("");
  const [resolveBy, setResolveBy]   = useState("");
  const [resolveNotes, setResolveNotes] = useState("");
  const [resolveOpen, setResolveOpen] = useState(false);
  const [rejectId, setRejectId]     = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["ai-dashboard"],
    queryFn: productionAiApi.dashboard,
    refetchInterval: 60_000,
  });

  const { data: anomalies = [], isLoading: anomLoading } = useQuery({
    queryKey: ["ai-anomalies", anomalyFilter],
    queryFn: () => productionAiApi.listAnomalies({
      is_resolved: anomalyFilter === "unresolved" ? false : undefined,
      limit: 100,
    }),
    enabled: tab === "anomalies" || tab === "overview",
  });

  const { data: suggestions = [], isLoading: sugLoading } = useQuery({
    queryKey: ["ai-suggestions", sugFilter],
    queryFn: () => productionAiApi.listSuggestions({
      status: sugFilter !== "all" ? sugFilter : undefined,
      limit: 100,
    }),
    enabled: tab === "suggestions" || tab === "overview",
  });

  const { data: predictions = [] } = useQuery({
    queryKey: ["ai-predictions"],
    queryFn: () => productionAiApi.listPredictions({ limit: 50 }),
    enabled: tab === "predictions",
  });

  const { data: maintSuggestions = [] } = useQuery({
    queryKey: ["ai-maintenance"],
    queryFn: () => productionAiApi.listSuggestions({ agent_type: "MAINTENANCE", limit: 50 }),
    enabled: tab === "maintenance",
  });

  // ── Mutations ─────────────────────────────────────────────────────────────────

  const runAllMut = useMutation({
    mutationFn: () => productionAiApi.runAll(runOrderId || undefined),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["ai-dashboard"] });
      qc.invalidateQueries({ queryKey: ["ai-anomalies"] });
      qc.invalidateQueries({ queryKey: ["ai-suggestions"] });
      qc.invalidateQueries({ queryKey: ["ai-predictions"] });
      const { summary } = data;
      toast("success", "AI scan complete",
        `${summary.anomaly_count} anomalies · ${summary.suggestion_count} suggestions · ${summary.critical_anomalies} critical`);
    },
    onError: (err) => toast("error", "Scan failed", extractApiError(err)),
  });

  const resolveMut = useMutation({
    mutationFn: ({ id, by, notes }: { id: string; by: string; notes: string }) =>
      productionAiApi.resolveAnomaly(id, by, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-anomalies"] });
      qc.invalidateQueries({ queryKey: ["ai-dashboard"] });
      setResolveOpen(false);
      toast("success", "Anomaly resolved");
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const acceptMut = useMutation({
    mutationFn: (id: string) => productionAiApi.actionSuggestion(id, "accepted"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-suggestions"] });
      qc.invalidateQueries({ queryKey: ["ai-dashboard"] });
      toast("success", "Suggestion accepted");
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  const rejectMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      productionAiApi.actionSuggestion(id, "rejected", undefined, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-suggestions"] });
      qc.invalidateQueries({ queryKey: ["ai-dashboard"] });
      setRejectOpen(false);
      toast("success", "Suggestion rejected");
    },
    onError: (err) => toast("error", "Failed", extractApiError(err)),
  });

  // ── Render helpers ────────────────────────────────────────────────────────────

  const unresolved = anomalies.filter(a => !a.is_resolved);
  const criticalCount = unresolved.filter(a => a.severity === "critical" || a.severity === "high").length;

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: "overview",     label: "Overview" },
    { id: "anomalies",    label: "Anomalies",   badge: unresolved.length },
    { id: "suggestions",  label: "Suggestions", badge: suggestions.filter(s => s.status === "pending").length },
    { id: "predictions",  label: "Predictions" },
    { id: "maintenance",  label: "Maintenance",  badge: maintSuggestions.filter(s => s.status === "pending").length },
  ];

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Production AI Intelligence</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            6-agent digital factory brain · predictions · anomaly detection · optimization
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={runOrderId} onChange={e => setRunOrderId(e.target.value)}
            placeholder="Order ID (optional)"
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white w-56"
          />
          <button
            onClick={() => runAllMut.mutate()}
            disabled={runAllMut.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
          >
            {runAllMut.isPending ? "Scanning…" : "Run All Agents"}
          </button>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b border-slate-700/50">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium relative ${
              tab === t.id
                ? "text-white border-b-2 border-indigo-500"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {t.label}
            {t.badge ? (
              <span className="ml-1.5 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                {t.badge}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* OVERVIEW TAB */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {tab === "overview" && (
        <div className="space-y-6">
          {/* Dashboard KPIs */}
          {dashboard && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Anomalies 7d */}
              <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <h3 className="text-sm font-medium text-slate-300">Anomalies (7 days)</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {(["critical","high","medium","low"] as SeverityType[]).map(s => (
                    <div key={s} className="flex justify-between">
                      <span className="capitalize text-slate-400">{s}</span>
                      <span className={`font-semibold ${SEVERITY_COLORS[s]}`}>
                        {dashboard.anomalies_7d[s as keyof typeof dashboard.anomalies_7d]}
                      </span>
                    </div>
                  ))}
                  <div className="col-span-2 pt-1 border-t border-slate-700 flex justify-between font-semibold">
                    <span className="text-slate-300">Total unresolved</span>
                    <span className={criticalCount > 0 ? "text-red-400" : "text-white"}>
                      {dashboard.anomalies_7d.total}
                    </span>
                  </div>
                </div>
              </div>

              {/* Suggestions */}
              <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <h3 className="text-sm font-medium text-slate-300">AI Suggestions</h3>
                <div className="space-y-2 text-sm">
                  {[
                    { label: "Pending Review",  val: dashboard.suggestions.pending,  color: "text-amber-400" },
                    { label: "Accepted",        val: dashboard.suggestions.accepted,  color: "text-emerald-400" },
                    { label: "Rejected",        val: dashboard.suggestions.rejected,  color: "text-slate-400" },
                  ].map(r => (
                    <div key={r.label} className="flex justify-between">
                      <span className="text-slate-400">{r.label}</span>
                      <span className={`font-semibold ${r.color}`}>{r.val}</span>
                    </div>
                  ))}
                  {dashboard.suggestions.accepted + dashboard.suggestions.rejected > 0 && (
                    <div className="pt-1 border-t border-slate-700 text-xs text-slate-400">
                      Acceptance rate:{" "}
                      {Math.round(
                        dashboard.suggestions.accepted /
                        (dashboard.suggestions.accepted + dashboard.suggestions.rejected) * 100
                      )}%
                    </div>
                  )}
                </div>
              </div>

              {/* Predictions */}
              <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <h3 className="text-sm font-medium text-slate-300">Predictions (7 days)</h3>
                <div className="space-y-2 text-sm">
                  {(["green","yellow","red"] as Lowercase<RiskLevel>[]).map(r => {
                    const lvl = r.toUpperCase() as RiskLevel;
                    return (
                      <div key={r} className="flex justify-between">
                        <span className="capitalize text-slate-400">{r}</span>
                        <span className={`font-semibold ${RISK_COLORS[lvl]}`}>
                          {dashboard.predictions_7d[r]}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Recent critical anomalies */}
          {unresolved.filter(a => ["critical","high"].includes(a.severity)).length > 0 && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-semibold text-red-400">Critical / High Alerts</h3>
              <div className="space-y-2">
                {unresolved
                  .filter(a => ["critical","high"].includes(a.severity))
                  .slice(0, 5)
                  .map(a => (
                    <div key={a.id} className="flex items-start gap-3 text-sm">
                      <SeverityBadge s={a.severity} />
                      <div className="flex-1 min-w-0">
                        <div className="text-white capitalize">{a.anomaly_type.replace(/_/g," ")}</div>
                        <div className="text-slate-400 text-xs truncate">{a.explanation}</div>
                      </div>
                      <span className="text-xs text-slate-500 shrink-0">{fmtDate(a.created_at)}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Pending suggestions preview */}
          {suggestions.filter(s => s.status === "pending").length > 0 && (
            <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-white">Pending Suggestions</h3>
              <div className="space-y-3">
                {suggestions
                  .filter(s => s.status === "pending")
                  .slice(0, 4)
                  .map(s => (
                    <div key={s.id} className={`rounded-lg border p-3 ${AGENT_BG[s.agent_type]}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs font-semibold uppercase ${AGENT_COLORS[s.agent_type]}`}>
                          {AGENT_LABELS[s.agent_type]}
                        </span>
                        <ConfidenceBar score={s.confidence_score} />
                      </div>
                      <div className="text-sm text-white">{s.issue_detected}</div>
                      <div className="text-xs text-slate-400 mt-0.5">{s.suggested_change}</div>
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => acceptMut.mutate(s.id)}
                          disabled={acceptMut.isPending}
                          className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded"
                        >Accept</button>
                        <button
                          onClick={() => { setRejectId(s.id); setRejectOpen(true); }}
                          className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1 rounded"
                        >Reject</button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* ANOMALIES TAB */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {tab === "anomalies" && (
        <div className="space-y-4">
          <div className="flex gap-3 items-center">
            <select
              value={anomalyFilter} onChange={e => setAnomalyFilter(e.target.value as any)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white"
            >
              <option value="unresolved">Unresolved only</option>
              <option value="all">All anomalies</option>
            </select>
            <span className="text-xs text-slate-400">{anomalies.length} records</span>
          </div>

          {anomLoading ? (
            <div className="text-slate-400 text-sm p-4">Loading…</div>
          ) : anomalies.length === 0 ? (
            <div className="text-center text-slate-500 py-12">No anomalies found. Run agents to scan.</div>
          ) : (
            <div className="space-y-2">
              {anomalies.map(a => (
                <div key={a.id}
                  className={`rounded-xl border p-4 ${a.is_resolved ? "opacity-50" : ""} ${SEVERITY_BG[a.severity as SeverityType]}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <SeverityBadge s={a.severity} />
                      <span className="text-sm font-medium text-white capitalize">
                        {a.anomaly_type.replace(/_/g," ")}
                      </span>
                      {a.affected_area && (
                        <span className="text-xs text-slate-400">{a.affected_area}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <ConfidenceBar score={a.confidence_score} />
                      {!a.is_resolved && (
                        <button
                          onClick={() => { setResolveId(a.id); setResolveOpen(true); }}
                          className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-2 py-1 rounded"
                        >Resolve</button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-slate-300 mt-2">{a.explanation}</p>
                  {(a.actual_value != null || a.expected_value != null) && (
                    <div className="flex gap-4 mt-1 text-xs text-slate-400">
                      {a.actual_value   != null && <span>Actual: <strong className="text-white">{a.actual_value}</strong></span>}
                      {a.expected_value != null && <span>Expected: <strong className="text-white">{a.expected_value}</strong></span>}
                      {a.deviation_pct  != null && <span>Deviation: <strong className={a.deviation_pct > 0 ? "text-red-400":"text-emerald-400"}>{fmtPct(a.deviation_pct)}</strong></span>}
                    </div>
                  )}
                  <div className="text-xs text-slate-500 mt-1">
                    {fmtDate(a.created_at)}
                    {a.is_resolved && a.resolved_by && ` · Resolved by ${a.resolved_by}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* SUGGESTIONS TAB */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {tab === "suggestions" && (
        <div className="space-y-4">
          <div className="flex gap-3 items-center">
            {["pending","accepted","rejected","all"].map(f => (
              <button
                key={f}
                onClick={() => setSugFilter(f)}
                className={`text-sm px-3 py-1.5 rounded-lg capitalize ${
                  sugFilter === f ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white"
                }`}
              >{f}</button>
            ))}
          </div>

          {sugLoading ? (
            <div className="text-slate-400 text-sm p-4">Loading…</div>
          ) : suggestions.length === 0 ? (
            <div className="text-center text-slate-500 py-12">No suggestions. Run agents to generate.</div>
          ) : (
            <div className="space-y-3">
              {suggestions.map(s => (
                <div key={s.id} className={`rounded-xl border p-4 ${AGENT_BG[s.agent_type]}`}>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <span className={`text-xs font-semibold uppercase ${AGENT_COLORS[s.agent_type]}`}>
                        {AGENT_LABELS[s.agent_type]}
                      </span>
                      <span className="text-xs text-slate-500 ml-2 capitalize">
                        {s.suggestion_type.replace(/_/g," ")}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ConfidenceBar score={s.confidence_score} />
                      <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${
                        s.status === "accepted" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : s.status === "rejected" ? "bg-slate-500/10 border-slate-500/20 text-slate-400"
                        : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                      }`}>{s.status}</span>
                    </div>
                  </div>

                  <div className="text-sm font-medium text-white">{s.issue_detected}</div>
                  <div className="text-sm text-slate-400 mt-0.5">{s.suggested_change}</div>
                  <p className="text-xs text-slate-500 mt-1 italic">{s.explanation}</p>

                  {/* Impact metrics */}
                  <div className="flex flex-wrap gap-4 mt-2 text-xs">
                    {s.expected_cost_reduction_pct != null && (
                      <span className="text-emerald-400">
                        Cost reduction: {s.expected_cost_reduction_pct.toFixed(1)}%
                      </span>
                    )}
                    {s.expected_efficiency_gain_pct != null && (
                      <span className="text-cyan-400">
                        Efficiency gain: {s.expected_efficiency_gain_pct.toFixed(1)}%
                      </span>
                    )}
                    {s.estimated_kes_saving != null && (
                      <span className="text-amber-400">
                        Est. saving: KES {s.estimated_kes_saving.toLocaleString()}
                      </span>
                    )}
                    {s.hours_to_failure != null && (
                      <span className={s.hours_to_failure < 24 ? "text-red-400" : "text-amber-400"}>
                        Failure in ~{s.hours_to_failure.toFixed(0)}h
                      </span>
                    )}
                    {s.current_value != null && s.recommended_value != null && (
                      <span className="text-slate-400">
                        {s.current_value} → {s.recommended_value} {s.value_unit}
                      </span>
                    )}
                  </div>

                  {s.status === "pending" && (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => acceptMut.mutate(s.id)}
                        disabled={acceptMut.isPending}
                        className="text-xs bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-3 py-1.5 rounded"
                      >Accept</button>
                      <button
                        onClick={() => { setRejectId(s.id); setRejectOpen(true); }}
                        className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded"
                      >Reject</button>
                    </div>
                  )}
                  {s.status !== "pending" && s.actioned_by && (
                    <div className="text-xs text-slate-500 mt-2">
                      {s.status === "accepted" ? "Accepted" : "Rejected"} by {s.actioned_by} · {fmtDate(s.actioned_at)}
                      {s.rejection_reason && ` — "${s.rejection_reason}"`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* PREDICTIONS TAB */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {tab === "predictions" && (
        <div className="space-y-4">
          {predictions.length === 0 ? (
            <div className="text-center text-slate-500 py-12">
              No predictions yet. Run agents or trigger Agent 1 for a specific order.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-800/60">
                    {["Prediction #","Risk","Delay Risk","Output Qty","Conf.","Efficiency","Sample","Created","Error%"].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-xs text-slate-400 font-medium whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {predictions.map(p => (
                    <tr key={p.id} className="border-t border-slate-800 hover:bg-slate-800/40">
                      <td className="px-3 py-2 font-mono text-indigo-400 text-xs">{p.prediction_no}</td>
                      <td className="px-3 py-2"><RiskBadge level={p.risk_level || "GREEN"} /></td>
                      <td className={`px-3 py-2 font-semibold ${
                        (p.delay_risk_pct || 0) >= 70 ? "text-red-400"
                        : (p.delay_risk_pct || 0) >= 35 ? "text-amber-400"
                        : "text-emerald-400"
                      }`}>{p.delay_risk_pct?.toFixed(1)}%</td>
                      <td className="px-3 py-2 text-slate-300">
                        {p.predicted_output_qty?.toFixed(1)} {p.predicted_output_uom}
                      </td>
                      <td className="px-3 py-2"><ConfidenceBar score={p.confidence_score} /></td>
                      <td className="px-3 py-2 text-slate-300">
                        {p.efficiency_forecast_pct != null ? `${p.efficiency_forecast_pct.toFixed(0)}%` : "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-400 text-center">{p.historical_sample_size}</td>
                      <td className="px-3 py-2 text-slate-400 text-xs whitespace-nowrap">{fmtDate(p.created_at)}</td>
                      <td className={`px-3 py-2 text-xs ${p.prediction_error_pct != null ? "text-amber-400" : "text-slate-500"}`}>
                        {p.prediction_error_pct != null ? `${p.prediction_error_pct.toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* MAINTENANCE TAB */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {tab === "maintenance" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-slate-400">
              MTBF-based failure predictions. Alerts when machine reaches 85% of historical mean time between failures.
            </p>
            <button
              onClick={() => productionAiApi.maintenancePredict().then(() => {
                qc.invalidateQueries({ queryKey: ["ai-maintenance"] });
                toast("success", "Maintenance scan complete");
              })}
              className="bg-orange-600 hover:bg-orange-700 text-white text-xs px-3 py-2 rounded-lg"
            >
              Run Maintenance Scan
            </button>
          </div>

          {maintSuggestions.length === 0 ? (
            <div className="text-center text-slate-500 py-12">
              No maintenance predictions. Requires downtime event history in work centers.
            </div>
          ) : (
            <div className="space-y-3">
              {maintSuggestions.map(s => (
                <div key={s.id} className="bg-orange-500/5 border border-orange-500/20 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-orange-400">{s.issue_detected}</span>
                    <ConfidenceBar score={s.confidence_score} />
                  </div>
                  <p className="text-sm text-slate-300">{s.explanation}</p>
                  <div className="flex flex-wrap gap-4 mt-2 text-xs">
                    {s.hours_to_failure != null && (
                      <span className={s.hours_to_failure < 24 ? "text-red-400 font-semibold" : "text-amber-400"}>
                        Predicted failure in {s.hours_to_failure.toFixed(0)}h
                      </span>
                    )}
                    {s.mtbf_hours != null && (
                      <span className="text-slate-400">MTBF: {s.mtbf_hours.toFixed(0)}h</span>
                    )}
                    {s.pct_of_mtbf != null && (
                      <span className="text-slate-400">{s.pct_of_mtbf.toFixed(0)}% of MTBF elapsed</span>
                    )}
                    {s.predicted_next_failure && (
                      <span className="text-slate-400">Predicted: {fmtDate(s.predicted_next_failure)}</span>
                    )}
                  </div>
                  <div className="text-sm text-white mt-2 font-medium">{s.suggested_change}</div>
                  {s.status === "pending" && (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => acceptMut.mutate(s.id)}
                        className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded"
                      >Accept & Schedule</button>
                      <button
                        onClick={() => { setRejectId(s.id); setRejectOpen(true); }}
                        className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded"
                      >Dismiss</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Modals ─────────────────────────────────────────────────────────────── */}

      {/* Resolve anomaly */}
      {resolveOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">Resolve Anomaly</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400">Resolved by</label>
                <input value={resolveBy} onChange={e => setResolveBy(e.target.value)}
                  className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-400">Resolution notes</label>
                <textarea value={resolveNotes} onChange={e => setResolveNotes(e.target.value)}
                  rows={3}
                  className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setResolveOpen(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">
                Cancel
              </button>
              <button
                onClick={() => resolveMut.mutate({ id: resolveId, by: resolveBy, notes: resolveNotes })}
                disabled={!resolveBy || resolveMut.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
              >
                {resolveMut.isPending ? "Saving…" : "Resolve"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject suggestion */}
      {rejectOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">Reject Suggestion</h2>
            <div>
              <label className="text-xs text-slate-400">Reason (optional)</label>
              <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                rows={3}
                className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setRejectOpen(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">
                Cancel
              </button>
              <button
                onClick={() => rejectMut.mutate({ id: rejectId, reason: rejectReason })}
                disabled={rejectMut.isPending}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
              >
                {rejectMut.isPending ? "Saving…" : "Confirm Reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
