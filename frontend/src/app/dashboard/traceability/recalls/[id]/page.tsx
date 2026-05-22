"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  traceApi, RecallDetail, RECALL_STATUS_BG, SEVERITY_BG,
  RISK_BG, ACTION_STATUS_BG, RECALL_ACTION_LABEL, AI_AGENT_LABEL,
  RecallActionType,
} from "@/lib/traceability";

const ACTION_TYPES: RecallActionType[] = [
  "quarantine","shipment_block","customer_notify","distributor_notify",
  "internal_hold","return_request","destroy","rework","regulatory_report",
  "followup_call","closeout_verification",
];

export default function RecallDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [recall, setRecall] = useState<RecallDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview"|"scope"|"actions"|"customers"|"returns"|"ai">("overview");
  const [calculating, setCalculating] = useState(false);
  const [containing, setContaining] = useState(false);
  const [showAction, setShowAction] = useState(false);
  const [actionForm, setActionForm] = useState({ action_type: "quarantine", notes: "" });

  const load = () => {
    setLoading(true);
    traceApi.getRecallDetail(id).then(setRecall).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleCalculateScope = async () => {
    setCalculating(true);
    try { await traceApi.calculateScope(id); load(); } finally { setCalculating(false); }
  };

  const handleContain = async () => {
    setContaining(true);
    try { const r = await traceApi.containRecall(id); alert(`${r.holds_placed} holds placed.`); load(); }
    finally { setContaining(false); }
  };

  const handleRunAI = async () => {
    const r = await traceApi.runAIAgents(id);
    alert(`Generated ${r.generated} AI recommendations.`); load();
  };

  const handleCreateAction = async () => {
    await traceApi.createAction(id, { action_type: actionForm.action_type, notes: actionForm.notes || undefined });
    setShowAction(false); load();
  };

  if (loading) return <div className="p-8 text-gray-400">Loading recall…</div>;
  if (!recall) return <div className="p-8 text-red-500">Recall not found</div>;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900">{recall.recall_no}</h1>
            <span className={`px-2 py-0.5 rounded text-sm ${SEVERITY_BG[recall.severity_level]}`}>{recall.severity_level}</span>
            <span className={`px-2 py-0.5 rounded text-sm ${RECALL_STATUS_BG[recall.status]}`}>{recall.status.replace("_"," ")}</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">{recall.recall_reason}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleCalculateScope} disabled={calculating}
            className="px-3 py-1.5 text-xs border border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50 disabled:opacity-50">
            {calculating ? "Calculating…" : "Calculate Scope"}
          </button>
          <button onClick={handleContain} disabled={containing}
            className="px-3 py-1.5 text-xs bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50">
            {containing ? "Containing…" : "Place All Holds"}
          </button>
          <button onClick={handleRunAI}
            className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
            Run AI Agents
          </button>
          <a href={`/dashboard/traceability/regulatory?recall_id=${id}`}
            className="px-3 py-1.5 text-xs border border-teal-200 text-teal-700 rounded-lg hover:bg-teal-50">
            Reg Report
          </a>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
        {[
          { label: "Trigger", value: recall.trigger_source.replace("_"," ") },
          { label: "Type", value: recall.recall_type.replace("_"," ") },
          { label: "Scope Lines", value: recall.scope_lines.length },
          { label: "Actions", value: recall.actions.length },
          { label: "Customers", value: recall.customer_impacts.length },
          { label: "Recovery", value: recall.recovery_pct ? `${parseFloat(recall.recovery_pct).toFixed(1)}%` : "—" },
          { label: "Trace Time", value: recall.time_to_trace_hours ? `${parseFloat(recall.time_to_trace_hours).toFixed(2)}h` : "—" },
          { label: "AI Recs", value: recall.ai_recs.length },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-3 text-center">
            <p className="text-lg font-bold text-gray-800">{s.value}</p>
            <p className="text-xs text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg flex-wrap">
        {(["overview","scope","actions","customers","returns","ai"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm font-medium capitalize ${tab === t ? "bg-white shadow text-gray-800" : "text-gray-500"}`}>
            {t === "ai" ? "AI Recs" : t.replace("-"," ")}
            {t === "ai" && recall.ai_recs.filter(r => r.status === "pending").length > 0 &&
              <span className="ml-1 bg-red-500 text-white text-xs rounded-full px-1">{recall.ai_recs.filter(r => r.status === "pending").length}</span>}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          {[
            ["Recall No", recall.recall_no],
            ["Reason", recall.recall_reason],
            ["Source Lot", recall.source_lot_id || "—"],
            ["Target Market", recall.target_market || "—"],
            ["Country Scope", recall.country_scope || "—"],
            ["Scope Calculated", recall.scope_calculated_at ? new Date(recall.scope_calculated_at).toLocaleString() : "Not yet"],
            ["Contained At", recall.contained_at ? new Date(recall.contained_at).toLocaleString() : "—"],
            ["Total Affected Qty", recall.total_affected_qty || "—"],
            ["Total Customers", recall.total_affected_customers ?? "—"],
            ["Notes", recall.notes || "—"],
          ].map(([k, v]) => (
            <div key={k} className="flex gap-4 text-sm border-b border-gray-50 pb-2">
              <span className="text-gray-500 w-36 shrink-0">{k}</span>
              <span className="text-gray-800 break-all">{String(v)}</span>
            </div>
          ))}
        </div>
      )}

      {tab === "scope" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Recall Scope Lines ({recall.scope_lines.length})</h2>
          </div>
          {recall.scope_lines.length === 0 ? (
            <p className="px-5 py-8 text-gray-400 text-sm">No scope lines — run &quot;Calculate Scope&quot; first</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  {["Lot","Risk","In Stock","Shipped","Returned","Quarantined","Customers","Hold"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recall.scope_lines.map(sl => (
                  <tr key={sl.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{sl.affected_lot_id ? sl.affected_lot_id.slice(0,10) : "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${RISK_BG[sl.risk_status]}`}>{sl.risk_status}</span>
                    </td>
                    <td className="px-4 py-3">{parseFloat(sl.affected_qty_in_stock).toLocaleString()}</td>
                    <td className="px-4 py-3">{parseFloat(sl.affected_qty_shipped).toLocaleString()}</td>
                    <td className="px-4 py-3">{parseFloat(sl.affected_qty_returned).toLocaleString()}</td>
                    <td className="px-4 py-3">{parseFloat(sl.affected_qty_quarantined).toLocaleString()}</td>
                    <td className="px-4 py-3">{sl.affected_customer_count}</td>
                    <td className="px-4 py-3">
                      {sl.hold_placed
                        ? <span className="text-green-600 font-medium">✓ Placed</span>
                        : <span className="text-red-600">Pending</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "actions" && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button onClick={() => setShowAction(true)}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
              + Add Action
            </button>
          </div>
          {recall.actions.length === 0 ? (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-400">No actions created</div>
          ) : (
            <div className="space-y-2">
              {recall.actions.map(a => (
                <div key={a.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800">{RECALL_ACTION_LABEL[a.action_type]}</p>
                    {a.notes && <p className="text-xs text-gray-500 mt-0.5">{a.notes}</p>}
                    {a.due_date && <p className="text-xs text-gray-400">Due: {a.due_date}</p>}
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs ${ACTION_STATUS_BG[a.status]}`}>{a.status}</span>
                  {a.status === "pending" && (
                    <button onClick={async () => {
                      await traceApi.completeAction(a.id, { completed_by_id: "00000000-0000-0000-0000-000000000001" });
                      load();
                    }} className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                      Mark Done
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {showAction && (
            <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
                <h3 className="font-semibold text-gray-800">Add Recall Action</h3>
                <div>
                  <label className="text-xs font-medium text-gray-600">Action Type</label>
                  <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                    value={actionForm.action_type} onChange={e => setActionForm(f => ({ ...f, action_type: e.target.value }))}>
                    {ACTION_TYPES.map(t => <option key={t} value={t}>{RECALL_ACTION_LABEL[t]}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Notes</label>
                  <textarea rows={2} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                    value={actionForm.notes} onChange={e => setActionForm(f => ({ ...f, notes: e.target.value }))} />
                </div>
                <div className="flex gap-2 justify-end">
                  <button onClick={() => setShowAction(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
                  <button onClick={handleCreateAction} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Add</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "customers" && (
        <div className="space-y-3">
          <div className="flex justify-end gap-2">
            <button onClick={async () => { await traceApi.buildCustomerImpact(id); load(); }}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
              Rebuild Impact List
            </button>
          </div>
          {recall.customer_impacts.length === 0 ? (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              No customer impacts — run &quot;Rebuild Impact List&quot; after scope calculation
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    {["Customer","Lot","Qty Delivered","Risk","Notified","Return Status","Priority"].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {recall.customer_impacts.map(ci => (
                    <tr key={ci.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs">{ci.customer_id ? ci.customer_id.slice(0,8) : ci.customer_name || "—"}</td>
                      <td className="px-4 py-3 font-mono text-xs">{ci.affected_lot_id ? ci.affected_lot_id.slice(0,10) : "—"}</td>
                      <td className="px-4 py-3">{ci.qty_delivered ? parseFloat(ci.qty_delivered).toLocaleString() : "—"}</td>
                      <td className="px-4 py-3">
                        {ci.risk_level && <span className={`px-2 py-0.5 rounded text-xs ${RISK_BG[ci.risk_level]}`}>{ci.risk_level}</span>}
                      </td>
                      <td className="px-4 py-3">
                        {ci.notification_sent
                          ? <span className="text-green-600 text-xs">✓ Sent</span>
                          : <button onClick={async () => { await traceApi.notifyCustomer(ci.id); load(); }}
                              className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">
                              Notify
                            </button>}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {ci.return_confirmed ? "Confirmed" : ci.return_requested ? "Requested" : "—"}
                      </td>
                      <td className="px-4 py-3">{ci.priority_rank ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "returns" && (
        <div className="space-y-3">
          {recall.returns.length === 0 ? (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-400">No returns recorded</div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    {["Customer","Return Ref","Requested","Received","Destroyed","Discrepancy","Follow-up"].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {recall.returns.map(ret => (
                    <tr key={ret.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs">{ret.customer_id ? ret.customer_id.slice(0,8) : "—"}</td>
                      <td className="px-4 py-3">{ret.return_ref || "—"}</td>
                      <td className="px-4 py-3">{ret.qty_requested ? parseFloat(ret.qty_requested).toLocaleString() : "—"}</td>
                      <td className="px-4 py-3">{ret.qty_received ? parseFloat(ret.qty_received).toLocaleString() : "—"}</td>
                      <td className="px-4 py-3">{ret.qty_destroyed_at_customer ? parseFloat(ret.qty_destroyed_at_customer).toLocaleString() : "—"}</td>
                      <td className="px-4 py-3">
                        {ret.discrepancy && parseFloat(ret.discrepancy) > 0
                          ? <span className="text-amber-700 font-medium">{parseFloat(ret.discrepancy).toLocaleString()}</span>
                          : "—"}
                      </td>
                      <td className="px-4 py-3">{ret.follow_up_required ? <span className="text-red-600 font-medium">Required</span> : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "ai" && (
        <div className="space-y-3">
          {recall.ai_recs.length === 0 ? (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              No AI recommendations — click &quot;Run AI Agents&quot; to generate
            </div>
          ) : recall.ai_recs.map(r => (
            <div key={r.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                      {AI_AGENT_LABEL[r.agent_type]}
                    </span>
                    {r.priority_score !== null && (
                      <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">P{r.priority_score}</span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded ${r.status === "pending" ? "bg-amber-100 text-amber-700" : r.status === "accepted" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="font-semibold text-gray-800">{r.title}</p>
                  <p className="text-sm text-gray-600 mt-1">{r.explanation}</p>
                  <p className="text-sm text-indigo-700 mt-2 font-medium">{r.recommendation}</p>
                </div>
              </div>
              {r.status === "pending" && (
                <div className="flex gap-2 mt-3">
                  <button onClick={async () => {
                    await traceApi.reviewAIRec(r.id, { status: "accepted", reviewed_by_id: "00000000-0000-0000-0000-000000000001" });
                    load();
                  }} className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">Accept</button>
                  <button onClick={async () => {
                    await traceApi.reviewAIRec(r.id, { status: "rejected", reviewed_by_id: "00000000-0000-0000-0000-000000000001" });
                    load();
                  }} className="px-3 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50">Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
