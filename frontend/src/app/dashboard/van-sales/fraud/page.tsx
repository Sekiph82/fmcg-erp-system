"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motoSalesApi, FRAUD_SEVERITY_COLORS, FRAUD_STATUS_COLORS, FraudSeverity, FraudAlertStatus } from "@/lib/moto_sales";

const SEVERITIES: FraudSeverity[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const STATUSES: FraudAlertStatus[] = ["OPEN", "REVIEWED", "DISMISSED", "ESCALATED", "CONFIRMED"];

export default function FraudAlertsPage() {
  const qc = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("OPEN");
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [resolution, setResolution] = useState("");

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ["fraud-alerts", severityFilter, statusFilter],
    queryFn: () => motoSalesApi.listFraudAlerts({
      severity: severityFilter || undefined,
      status: statusFilter || undefined,
    }),
  });

  const scanMut = useMutation({
    mutationFn: () => motoSalesApi.runFraudScan(7),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fraud-alerts"] }),
  });

  const reviewMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      motoSalesApi.reviewAlert(id, { status, resolution: resolution || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fraud-alerts"] });
      setReviewingId(null);
      setResolution("");
    },
  });

  const open = alerts.filter((a) => a.status === "OPEN").length;
  const critical = alerts.filter((a) => a.severity === "CRITICAL").length;
  const high = alerts.filter((a) => a.severity === "HIGH").length;

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Fraud Alerts</h1>
          <p className="text-slate-500 text-sm mt-0.5">Real-time fraud detection for field sales</p>
        </div>
        <button onClick={() => scanMut.mutate()} disabled={scanMut.isPending}
          className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium disabled:opacity-50">
          {scanMut.isPending ? "Scanning…" : "Run Fraud Scan"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Open Alerts</p>
          <p className="text-3xl font-bold text-red-400">{open}</p>
        </div>
        <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-4">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Critical</p>
          <p className="text-3xl font-bold text-orange-300">{critical}</p>
        </div>
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">High</p>
          <p className="text-3xl font-bold text-amber-300">{high}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <div className="flex gap-1">
          {["", ...STATUSES].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${statusFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
              {s || "All Status"}
            </button>
          ))}
        </div>
        <div className="w-px h-6 bg-white/[0.07] self-center" />
        {["", ...SEVERITIES].map((s) => (
          <button key={s} onClick={() => setSeverityFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${severityFilter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {s || "All Severity"}
          </button>
        ))}
      </div>

      {/* Alerts */}
      <div className="space-y-3">
        {isLoading && <p className="text-slate-500 text-sm">Loading…</p>}
        {!isLoading && alerts.length === 0 && (
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-8 text-center text-slate-600">
            No fraud alerts matching current filters
          </div>
        )}
        {alerts.map((a) => (
          <div key={a.id} className={`rounded-xl border p-4 ${a.severity === "CRITICAL" ? "border-red-500/40 bg-red-500/5" : a.severity === "HIGH" ? "border-orange-500/30 bg-[#0d1829]" : "border-white/[0.07] bg-[#0d1829]"}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${FRAUD_SEVERITY_COLORS[a.severity]}`}>{a.severity}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${FRAUD_STATUS_COLORS[a.status]}`}>{a.status}</span>
                  <span className="text-[10px] text-slate-500">{a.fraud_type.replace(/_/g, " ")}</span>
                  <span className="text-[10px] text-slate-600 ml-auto">{new Date(a.created_at).toLocaleString()}</span>
                </div>
                <p className="text-sm text-white font-medium">{a.description}</p>
                <div className="flex gap-4 mt-1 text-xs text-slate-500">
                  <span>Risk score: <span className="text-amber-400 font-medium">{a.risk_score}</span></span>
                  {a.txn_id && <span>Txn: {a.txn_id.slice(0, 8)}…</span>}
                  {a.driver_id && <span>Driver: {a.driver_id.slice(0, 8)}…</span>}
                </div>
                {a.resolution && <p className="text-xs text-slate-500 mt-1 italic">Resolution: {a.resolution}</p>}
              </div>

              {a.status === "OPEN" && reviewingId !== a.id && (
                <button onClick={() => setReviewingId(a.id)}
                  className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 text-xs shrink-0">
                  Review
                </button>
              )}
            </div>

            {reviewingId === a.id && (
              <div className="mt-3 space-y-2 border-t border-white/[0.07] pt-3">
                <input value={resolution} onChange={(e) => setResolution(e.target.value)}
                  placeholder="Resolution notes (optional)"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none" />
                <div className="flex gap-2">
                  {["DISMISSED", "CONFIRMED", "ESCALATED"].map((s) => (
                    <button key={s} onClick={() => reviewMut.mutate({ id: a.id, status: s })}
                      disabled={reviewMut.isPending}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-50 ${
                        s === "CONFIRMED" ? "bg-red-600 hover:bg-red-500 text-white"
                        : s === "ESCALATED" ? "bg-orange-600 hover:bg-orange-500 text-white"
                        : "border border-white/[0.08] text-slate-400 hover:border-white/20"
                      }`}>
                      {s}
                    </button>
                  ))}
                  <button onClick={() => setReviewingId(null)} className="px-3 py-1.5 rounded-lg text-xs text-slate-600 hover:text-slate-400">Cancel</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
