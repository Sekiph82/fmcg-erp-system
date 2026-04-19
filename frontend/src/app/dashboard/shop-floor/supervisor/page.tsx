"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  sfApi, LiveWOItem, SFAIRec, SupervisorOverride,
  LIVE_STATUS_COLOR, DOWNTIME_CAT_LABEL,
} from "@/lib/shopFloor";

const OVERRIDE_TYPES = [
  "APPROVE_OVERPRODUCTION", "APPROVE_SCRAP", "UNBLOCK",
  "ASSIGN", "REASSIGN", "PAUSE_ORDER", "RESUME_ORDER", "ESCALATE",
];

export default function SupervisorConsole() {
  const qc = useQueryClient();
  const [supervisorName, setSupervisorName] = useState("");
  const [selectedWO, setSelectedWO] = useState<LiveWOItem | null>(null);
  const [overrideType, setOverrideType] = useState("UNBLOCK");
  const [overrideReason, setOverrideReason] = useState("");
  const [showOverrideModal, setShowOverrideModal] = useState(false);

  const { data: queue = [] } = useQuery<LiveWOItem[]>({
    queryKey: ["sf-live-queue-sv"],
    queryFn: () => sfApi.getLiveQueue(),
    refetchInterval: 20_000,
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["sf-alerts-sv"],
    queryFn: () => sfApi.getAlerts(),
    refetchInterval: 20_000,
  });

  const { data: aiRecs = [] } = useQuery<SFAIRec[]>({
    queryKey: ["sf-ai-recs"],
    queryFn: () => sfApi.listAIRecs({ status: "PENDING" }),
    refetchInterval: 60_000,
  });

  const { data: overrides = [] } = useQuery<SupervisorOverride[]>({
    queryKey: ["sf-overrides"],
    queryFn: () => sfApi.listOverrides(),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["sf-live-queue-sv"] });
    qc.invalidateQueries({ queryKey: ["sf-overrides"] });
    qc.invalidateQueries({ queryKey: ["sf-dashboard"] });
  };

  const overrideMut = useMutation({
    mutationFn: () => sfApi.createOverride({
      work_order_id: selectedWO?.work_order_id || null,
      supervisor_name: supervisorName,
      override_type: overrideType,
      reason: overrideReason,
    }),
    onSuccess: () => {
      setShowOverrideModal(false);
      setOverrideReason("");
      invalidate();
    },
  });

  const actionRec = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "ACCEPTED" | "REJECTED" }) =>
      sfApi.actionAIRec(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sf-ai-recs"] }),
  });

  const runAI = useMutation({
    mutationFn: sfApi.runAI,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sf-ai-recs"] }),
  });

  const criticalAlerts = (alerts as any[]).filter((a) => a.severity === "HIGH" || a.severity === "CRITICAL");
  const blocked = queue.filter((w) => w.live_status === "BLOCKED");
  const qcHold = queue.filter((w) => w.live_status === "QC_HOLD");
  const supervisorReview = queue.filter((w) => w.live_status === "SUPERVISOR_REVIEW");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <a href="/dashboard/shop-floor" className="text-sm text-gray-400 hover:text-gray-600">← Dashboard</a>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Supervisor Console</h1>
          <p className="text-sm text-gray-500 mt-0.5">Monitor and intervene across all lines</p>
        </div>
        <div className="flex gap-2 items-center">
          <input
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
            placeholder="Supervisor name"
            value={supervisorName}
            onChange={(e) => setSupervisorName(e.target.value)}
          />
          <button onClick={() => runAI.mutate()} disabled={runAI.isPending} className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
            {runAI.isPending ? "Running…" : "Run AI"}
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Alerts", value: criticalAlerts.length, color: "text-red-600", bg: criticalAlerts.length > 0 ? "bg-red-50 border-red-200" : "bg-white border-gray-100" },
          { label: "Blocked",  value: blocked.length,  color: "text-red-500",    bg: "bg-white border-gray-100" },
          { label: "QC Hold",  value: qcHold.length,   color: "text-purple-600", bg: "bg-white border-gray-100" },
          { label: "Need Review", value: supervisorReview.length, color: "text-orange-600", bg: "bg-white border-gray-100" },
        ].map((k) => (
          <div key={k.label} className={`rounded-xl border shadow-sm p-3 text-center ${k.bg}`}>
            <p className="text-xs text-gray-400">{k.label}</p>
            <p className={`text-2xl font-bold mt-0.5 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Alerts */}
      {criticalAlerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-2">
          <p className="text-sm font-semibold text-red-700">Critical Alerts</p>
          {criticalAlerts.map((a: any, i: number) => (
            <div key={i} className="flex items-start gap-2 text-sm text-red-800 bg-white/60 rounded-lg p-2">
              <span className="text-xs font-bold bg-red-200 px-1.5 py-0.5 rounded">{a.type}</span>
              <span>{a.message}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Work Orders Needing Attention */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Work Orders Needing Attention</h2>
          {[...blocked, ...qcHold, ...supervisorReview].length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">All clear</p>
          ) : (
            <div className="space-y-2">
              {[...blocked, ...qcHold, ...supervisorReview].map((wo) => (
                <div
                  key={wo.id}
                  className={`p-3 rounded-xl border cursor-pointer ${selectedWO?.id === wo.id ? "border-indigo-300 bg-indigo-50" : "border-gray-100 hover:bg-gray-50"}`}
                  onClick={() => setSelectedWO(selectedWO?.id === wo.id ? null : wo)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{wo.step_name}</p>
                      <p className="text-xs text-gray-400">{wo.product_name || "—"} · {wo.line_id || "No line"}</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${LIVE_STATUS_COLOR[wo.live_status]}`}>
                        {wo.live_status}
                      </span>
                      {wo.operator_name && <p className="text-xs text-gray-400 mt-0.5">{wo.operator_name}</p>}
                    </div>
                  </div>
                  {selectedWO?.id === wo.id && (
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); setShowOverrideModal(true); }}
                        className="flex-1 py-1.5 bg-orange-500 text-white rounded-lg text-xs font-medium hover:bg-orange-600"
                      >
                        Supervisor Override
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* All Live Orders */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">All Live Work Orders ({queue.length})</h2>
          <div className="space-y-1.5 max-h-72 overflow-y-auto">
            {queue.map((wo) => (
              <div key={wo.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${LIVE_STATUS_COLOR[wo.live_status]}`}>{wo.live_status}</span>
                  <div>
                    <p className="text-sm font-medium">{wo.step_name}</p>
                    <p className="text-xs text-gray-400">{wo.line_id || "—"} · {wo.operator_name || "No operator"}</p>
                  </div>
                </div>
                <p className="text-xs font-mono text-gray-500">{wo.completed_qty.toFixed(0)}/{wo.planned_qty.toFixed(0)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      {aiRecs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">AI Recommendations ({aiRecs.length} pending)</h2>
          <div className="space-y-2">
            {aiRecs.map((rec) => (
              <div key={rec.id} className="p-3 rounded-xl bg-indigo-50 border border-indigo-100">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-indigo-900">{rec.title}</p>
                    {rec.explanation && <p className="text-xs text-indigo-700 mt-1">{rec.explanation}</p>}
                    {rec.impact_summary && <p className="text-xs text-indigo-600 mt-0.5 italic">{rec.impact_summary}</p>}
                    <div className="flex gap-2 mt-1">
                      <span className="text-xs text-indigo-400">{rec.agent_type.replace(/_/g, " ")}</span>
                      {rec.confidence_score && (
                        <span className="text-xs text-indigo-400">· {(Number(rec.confidence_score) * 100).toFixed(0)}% confidence</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => actionRec.mutate({ id: rec.id, status: "ACCEPTED" })} className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700">Accept</button>
                    <button onClick={() => actionRec.mutate({ id: rec.id, status: "REJECTED" })} className="px-2 py-1 bg-gray-300 text-gray-700 text-xs rounded hover:bg-gray-400">Dismiss</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Overrides */}
      {overrides.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent Supervisor Overrides</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 border-b border-gray-50">
                  {["Type", "Supervisor", "Target", "Reason", "Time"].map((h) => <th key={h} className="py-1.5 pr-4">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {overrides.slice(0, 10).map((ov) => (
                  <tr key={ov.id} className="border-b border-gray-50">
                    <td className="py-1.5 pr-4 text-xs font-medium text-orange-600">{ov.override_type}</td>
                    <td className="py-1.5 pr-4 text-xs">{ov.supervisor_name}</td>
                    <td className="py-1.5 pr-4 text-xs text-gray-500">{ov.target_operator_name || "—"}</td>
                    <td className="py-1.5 pr-4 text-xs text-gray-500 max-w-32 truncate">{ov.reason || "—"}</td>
                    <td className="py-1.5 text-xs text-gray-400">{new Date(ov.approved_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Override Modal */}
      {showOverrideModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Supervisor Override</h2>
            {selectedWO && <p className="text-sm text-gray-500">WO: {selectedWO.step_name}</p>}
            <div>
              <label className="text-xs text-gray-500">Override Type</label>
              <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={overrideType} onChange={(e) => setOverrideType(e.target.value)}>
                {OVERRIDE_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Reason</label>
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" rows={2} value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowOverrideModal(false)} className="flex-1 py-2 border border-gray-200 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => overrideMut.mutate()}
                disabled={!supervisorName || overrideMut.isPending}
                className="flex-1 py-2 bg-orange-600 text-white rounded-lg text-sm font-medium disabled:opacity-40"
              >
                Apply Override
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
