"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  execApi, ProdExecOrderOut, ExecWorkOrderOut, ExecOrderMaterialOut,
  ExecAIRecOut, WOExecStatus,
  STATUS_COLOR, WO_STATUS_COLOR, LIFECYCLE_NEXT, fmtKES, fmtMins,
} from "@/lib/productionExecution";

const TABS = ["Overview", "Work Orders", "Materials", "AI Recs", "Batch Record"] as const;
type Tab = typeof TABS[number];

const SCRAP_CATEGORIES = ["PROCESS", "QUALITY", "DAMAGE", "HANDLING"];

export default function ProdExecOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("Overview");

  // Complete order modal
  const [showComplete, setShowComplete] = useState(false);
  const [completeForm, setCompleteForm] = useState({ completed_qty: "", scrap_qty: "0", remarks: "" });

  // WO complete modal
  const [completeWoId, setCompleteWoId] = useState<string | null>(null);
  const [woCompleteForm, setWoCompleteForm] = useState({
    completed_qty: "", scrap_qty: "0", rework_qty: "0",
    run_time_actual: "", scrap_category: "", scrap_reason: "", qc_passed: "",
  });

  // Split modal
  const [showSplit, setShowSplit] = useState(false);
  const [splitQtys, setSplitQtys] = useState("500,500");
  const [splitReason, setSplitReason] = useState("");

  // Rework modal
  const [showRework, setShowRework] = useState(false);
  const [reworkForm, setReworkForm] = useState({ qty: "", reason: "" });

  // Issue material modal
  const [issueMat, setIssueMat] = useState<ExecOrderMaterialOut | null>(null);
  const [issueQty, setIssueQty] = useState("");
  const [issueLot, setIssueLot] = useState("");

  const { data: order, isLoading } = useQuery<ProdExecOrderOut>({
    queryKey: ["exec-order", id],
    queryFn: () => execApi.get(id),
  });

  const { data: aiRecs = [] } = useQuery<ExecAIRecOut[]>({
    queryKey: ["exec-ai", id],
    queryFn: () => execApi.listAI(id),
    enabled: tab === "AI Recs",
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["exec-order", id] });
    qc.invalidateQueries({ queryKey: ["exec-orders"] });
    qc.invalidateQueries({ queryKey: ["exec-dashboard"] });
  };

  const advance    = useMutation({ mutationFn: () => execApi.advance(id),    onSuccess: invalidate });
  const pauseOrder = useMutation({ mutationFn: () => execApi.pause(id),      onSuccess: invalidate });
  const closeOrder = useMutation({ mutationFn: () => execApi.close(id),      onSuccess: invalidate });
  const cancelOrder = useMutation({ mutationFn: () => execApi.cancel(id),    onSuccess: invalidate });
  const runAI      = useMutation({ mutationFn: () => execApi.runAI(id),      onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-ai", id] }) });

  const completeOrder = useMutation({
    mutationFn: () => execApi.complete(id, {
      completed_qty: Number(completeForm.completed_qty),
      scrap_qty: Number(completeForm.scrap_qty),
      remarks: completeForm.remarks,
    }),
    onSuccess: () => { invalidate(); setShowComplete(false); },
  });

  const startWO = useMutation({
    mutationFn: (woId: string) => execApi.startWorkOrder(woId),
    onSuccess: invalidate,
  });

  const completeWO = useMutation({
    mutationFn: () => execApi.completeWorkOrder(completeWoId!, {
      completed_qty: Number(woCompleteForm.completed_qty),
      scrap_qty: Number(woCompleteForm.scrap_qty),
      rework_qty: Number(woCompleteForm.rework_qty),
      run_time_actual: woCompleteForm.run_time_actual ? Number(woCompleteForm.run_time_actual) : undefined,
      scrap_category: woCompleteForm.scrap_category || undefined,
      scrap_reason: woCompleteForm.scrap_reason || undefined,
      qc_passed: woCompleteForm.qc_passed === "true" ? true : woCompleteForm.qc_passed === "false" ? false : undefined,
    }),
    onSuccess: () => { invalidate(); setCompleteWoId(null); },
  });

  const doSplit = useMutation({
    mutationFn: () => execApi.split(
      id,
      splitQtys.split(",").map((q) => Number(q.trim())),
      splitReason,
    ),
    onSuccess: () => { setShowSplit(false); router.push("/dashboard/production-execution"); },
  });

  const doRework = useMutation({
    mutationFn: () => execApi.rework(id, Number(reworkForm.qty), reworkForm.reason),
    onSuccess: (newOrder) => {
      setShowRework(false);
      invalidate();
      router.push(`/dashboard/production-execution/${newOrder.id}`);
    },
  });

  const doIssue = useMutation({
    mutationFn: () => execApi.issueMaterial(id, {
      material_id: issueMat!.id,
      qty: Number(issueQty),
      lot_no: issueLot || undefined,
      action: "issue",
    }),
    onSuccess: () => { invalidate(); setIssueMat(null); setIssueQty(""); setIssueLot(""); },
  });

  const actionAI = useMutation({
    mutationFn: ({ recId, status }: { recId: string; status: string }) => execApi.actionAI(recId, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-ai", id] }),
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400">Loading order…</div>;
  if (!order) return <div className="p-8 text-center text-red-400">Order not found.</div>;

  const progressPct = order.planned_qty > 0
    ? Math.min(100, Math.round((order.completed_qty / order.planned_qty) * 100))
    : 0;

  const nextAction = LIFECYCLE_NEXT[order.status];
  const pendingAI = aiRecs.filter((r) => r.status === "PENDING").length;

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <button onClick={() => router.push("/dashboard/production-execution")} className="text-sm text-gray-400 hover:text-gray-600">← Orders</button>
            <span className="text-gray-300">/</span>
            <span className="text-sm text-gray-600 font-mono">{order.order_no}</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{order.product_name || order.order_no}</h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLOR[order.status]}`}>{order.status}</span>
            {order.batch_no && <span className="text-xs font-mono text-gray-400">Batch: {order.batch_no}</span>}
            {order.is_rework && <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded">REWORK</span>}
            {order.is_split && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">SPLIT</span>}
            <span className="text-xs text-gray-400">Priority: {order.priority}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <a href={`/dashboard/production-execution/${id}/genealogy`} className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">Genealogy</a>
          <button onClick={() => runAI.mutate()} disabled={runAI.isPending} className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-40">
            {runAI.isPending ? "Running AI…" : "Run AI"}
          </button>
          {order.status === "IN_PROGRESS" && (
            <button onClick={() => pauseOrder.mutate()} className="px-3 py-1.5 text-xs border border-orange-200 text-orange-600 rounded-lg hover:bg-orange-50">Pause</button>
          )}
          {order.status === "IN_PROGRESS" && (
            <button onClick={() => { setCompleteForm({ ...completeForm, completed_qty: String(order.planned_qty) }); setShowComplete(true); }} className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700">Complete</button>
          )}
          {order.status === "COMPLETED" && (
            <button onClick={() => closeOrder.mutate()} className="px-3 py-1.5 text-xs bg-teal-600 text-white rounded-lg hover:bg-teal-700">Close</button>
          )}
          {["COMPLETED", "CLOSED"].includes(order.status) && (
            <button onClick={() => setShowRework(true)} className="px-3 py-1.5 text-xs border border-orange-200 text-orange-600 rounded-lg hover:bg-orange-50">Create Rework</button>
          )}
          {["DRAFT", "PLANNED", "RELEASED"].includes(order.status) && (
            <button onClick={() => setShowSplit(true)} className="px-3 py-1.5 text-xs border rounded-lg text-gray-600 hover:bg-gray-50">Split</button>
          )}
          {nextAction && !["COMPLETED", "IN_PROGRESS"].includes(order.status) && (
            <button onClick={() => advance.mutate()} disabled={advance.isPending} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40">
              {advance.isPending ? "…" : nextAction}
            </button>
          )}
          {!["COMPLETED", "CLOSED", "CANCELLED"].includes(order.status) && (
            <button onClick={() => cancelOrder.mutate()} className="px-3 py-1.5 text-xs border border-red-200 text-red-500 rounded-lg hover:bg-red-50">Cancel</button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-500">Production Progress</span>
          <span className="font-medium">{Number(order.completed_qty).toLocaleString()} / {Number(order.planned_qty).toLocaleString()} {order.uom} ({progressPct}%)</span>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${progressPct >= 100 ? "bg-green-500" : "bg-indigo-500"}`} style={{ width: `${progressPct}%` }} />
        </div>
        <div className="flex items-center gap-6 mt-2 text-xs text-gray-400">
          {order.scrap_qty > 0 && <span className="text-red-500">Scrap: {Number(order.scrap_qty)} {order.uom}</span>}
          {order.rework_qty > 0 && <span className="text-orange-500">Rework: {Number(order.rework_qty)} {order.uom}</span>}
          {order.actual_start && <span>Started: {new Date(order.actual_start).toLocaleString()}</span>}
          {order.actual_end && <span>Ended: {new Date(order.actual_end).toLocaleString()}</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {t}
            {t === "AI Recs" && pendingAI > 0 && (
              <span className="ml-1 text-xs bg-purple-100 text-purple-700 px-1.5 rounded-full">{pendingAI}</span>
            )}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === "Overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Order Details</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-gray-400">Order #</dt><dd className="font-mono">{order.order_no}</dd>
              <dt className="text-gray-400">Product</dt><dd>{order.product_name || "—"}</dd>
              <dt className="text-gray-400">BOM</dt><dd className="font-mono">{order.bom_code || "—"}</dd>
              <dt className="text-gray-400">Source</dt><dd>{order.source_type}</dd>
              <dt className="text-gray-400">Planned Start</dt><dd>{order.planned_start ? new Date(order.planned_start).toLocaleString() : "—"}</dd>
              <dt className="text-gray-400">Planned End</dt><dd>{order.planned_end ? new Date(order.planned_end).toLocaleString() : "—"}</dd>
              <dt className="text-gray-400">Plant</dt><dd>{order.plant_id || "—"}</dd>
              <dt className="text-gray-400">Section</dt><dd>{order.section_id || "—"}</dd>
            </dl>
            {order.remarks && <p className="text-sm text-gray-500 border-t mt-3 pt-3">{order.remarks}</p>}
          </div>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Costing Summary</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-gray-400">Planned Mat. Cost</dt><dd>{fmtKES(Number(order.planned_material_cost))}</dd>
              <dt className="text-gray-400">Actual Mat. Cost</dt><dd>{fmtKES(Number(order.actual_material_cost))}</dd>
              <dt className="text-gray-400">Planned Labor</dt><dd>{fmtKES(Number(order.planned_labor_cost))}</dd>
              <dt className="text-gray-400">Actual Labor</dt><dd>{fmtKES(Number(order.actual_labor_cost))}</dd>
              <dt className="text-gray-400">Overhead</dt><dd>{fmtKES(Number(order.overhead_cost))}</dd>
              <dt className="text-gray-400 font-medium">Total Cost</dt><dd className="font-bold text-green-700">{fmtKES(Number(order.total_actual_cost))}</dd>
              <dt className="text-gray-400">Cost / UOM</dt><dd>{order.cost_per_uom ? fmtKES(Number(order.cost_per_uom)) : "—"}</dd>
            </dl>
          </div>
        </div>
      )}

      {/* Work Orders Tab */}
      {tab === "Work Orders" && (
        <div className="space-y-3">
          {order.work_orders.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No work orders. Attach a routing to auto-generate steps.
            </div>
          ) : order.work_orders.map((wo) => (
            <div key={wo.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 text-sm font-bold flex items-center justify-center shrink-0">
                    {wo.step_sequence}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="font-medium text-gray-800">{wo.step_name}</p>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${WO_STATUS_COLOR[wo.status]}`}>{wo.status}</span>
                      {wo.qc_required_flag && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 rounded">QC</span>}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-400">
                      <span>Planned: {fmtMins(Number(wo.run_time_planned))}</span>
                      {wo.run_time_actual !== null && <span className="text-gray-600">Actual: {fmtMins(Number(wo.run_time_actual))}</span>}
                      <span>Qty: {Number(wo.planned_qty).toLocaleString()}</span>
                      {wo.completed_qty > 0 && <span className="text-green-600">Done: {Number(wo.completed_qty).toLocaleString()}</span>}
                      {wo.scrap_qty > 0 && <span className="text-red-500">Scrap: {Number(wo.scrap_qty).toLocaleString()}</span>}
                    </div>
                    {wo.started_at && <p className="text-xs text-gray-400 mt-0.5">Started: {new Date(wo.started_at).toLocaleString()}</p>}
                    {wo.completed_at && <p className="text-xs text-green-600 mt-0.5">Completed: {new Date(wo.completed_at).toLocaleString()}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {wo.status === "READY" && (
                    <button onClick={() => startWO.mutate(wo.id)} disabled={startWO.isPending} className="px-3 py-1 text-xs bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-40">Start</button>
                  )}
                  {wo.status === "IN_PROGRESS" && (
                    <button onClick={() => { setCompleteWoId(wo.id); setWoCompleteForm({ ...woCompleteForm, completed_qty: String(wo.planned_qty) }); }} className="px-3 py-1 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700">Complete</button>
                  )}
                </div>
              </div>
              {wo.qc_passed !== null && (
                <div className={`mt-2 text-xs px-2 py-1 rounded ${wo.qc_passed ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                  QC: {wo.qc_passed ? "PASSED" : "FAILED"}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Materials Tab */}
      {tab === "Materials" && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Item", "Code", "Required", "Reserved", "Issued", "Consumed", "Returned", "Cost", "Status", ""].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left font-medium text-gray-400 text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {order.materials.length === 0 ? (
                <tr><td colSpan={10} className="px-3 py-8 text-center text-gray-400 text-sm">No materials tracked yet.</td></tr>
              ) : order.materials.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{m.item_name || "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-400">{m.item_code || "—"}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs">{Number(m.required_qty).toFixed(3)}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs">{Number(m.reserved_qty).toFixed(3)}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-indigo-600">{Number(m.issued_qty).toFixed(3)}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-green-600">{Number(m.consumed_qty).toFixed(3)}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs">{Number(m.returned_qty).toFixed(3)}</td>
                  <td className="px-3 py-2 text-right text-xs">{m.extended_cost ? fmtKES(Number(m.extended_cost)) : "—"}</td>
                  <td className="px-3 py-2"><span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{m.status}</span></td>
                  <td className="px-3 py-2">
                    {["IN_PROGRESS", "RELEASED"].includes(order.status) && (
                      <button onClick={() => { setIssueMat(m); setIssueQty(String(Number(m.required_qty) - Number(m.issued_qty))); }} className="text-xs text-indigo-600 hover:underline">Issue</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {order.materials.some((m) => m.lot_numbers?.length) && (
            <div className="p-4 border-t border-gray-50">
              <p className="text-xs font-medium text-gray-500 mb-2">Lot Traceability</p>
              <div className="flex flex-wrap gap-2">
                {order.materials.flatMap((m) => (m.lot_numbers || []).map((lot) => (
                  <span key={`${m.id}-${lot}`} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">
                    {m.item_name}: <strong>{lot}</strong>
                  </span>
                )))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Recs Tab */}
      {tab === "AI Recs" && (
        <div className="space-y-3">
          {aiRecs.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
              No AI recommendations. Click "Run AI" to analyze this order.
            </div>
          ) : aiRecs.map((rec) => (
            <div key={rec.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${rec.agent_type === "EXECUTION_ANALYZER" ? "bg-indigo-100 text-indigo-700" : "bg-orange-100 text-orange-700"}`}>
                      {rec.agent_type.replace(/_/g, " ")}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${rec.status === "PENDING" ? "bg-yellow-100 text-yellow-700" : rec.status === "ACCEPTED" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {rec.status}
                    </span>
                    {rec.confidence_score && <span className="text-xs text-gray-400">{Math.round(Number(rec.confidence_score) * 100)}%</span>}
                  </div>
                  <p className="font-medium text-gray-800 text-sm">{rec.title}</p>
                  {rec.explanation && <p className="text-xs text-gray-500 mt-1">{rec.explanation}</p>}
                  {rec.impact_summary && <p className="text-xs text-indigo-600 mt-1">Impact: {rec.impact_summary}</p>}
                </div>
                {rec.status === "PENDING" && (
                  <div className="flex gap-2">
                    <button onClick={() => actionAI.mutate({ recId: rec.id, status: "ACCEPTED" })} className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">Accept</button>
                    <button onClick={() => actionAI.mutate({ recId: rec.id, status: "REJECTED" })} className="px-2 py-1 text-xs border text-gray-600 rounded hover:bg-gray-50">Reject</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Batch Record Tab */}
      {tab === "Batch Record" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-800">Digital Batch Record</h3>
              <span className="text-xs text-gray-400">Generated: {new Date().toLocaleString()}</span>
            </div>
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase mb-1">Order Information</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    ["Order #", order.order_no],
                    ["Batch No", order.batch_no || "—"],
                    ["Product", order.product_name || "—"],
                    ["Status", order.status],
                    ["Planned Qty", `${Number(order.planned_qty).toLocaleString()} ${order.uom}`],
                    ["Completed Qty", `${Number(order.completed_qty).toLocaleString()} ${order.uom}`],
                    ["Scrap Qty", `${Number(order.scrap_qty).toLocaleString()} ${order.uom}`],
                    ["Total Cost", fmtKES(Number(order.total_actual_cost))],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400">{label}</p>
                      <p className="font-medium text-gray-800">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase mb-1">Operations Log</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {["Step", "Operation", "Status", "Planned (min)", "Actual (min)", "Completed", "Scrap", "QC"].map((h) => (
                          <th key={h} className="px-2 py-1.5 text-left text-gray-400">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {order.work_orders.map((wo) => (
                        <tr key={wo.id}>
                          <td className="px-2 py-1.5">{wo.step_sequence}</td>
                          <td className="px-2 py-1.5 font-medium">{wo.step_name}</td>
                          <td className="px-2 py-1.5">{wo.status}</td>
                          <td className="px-2 py-1.5 text-right">{Number(wo.run_time_planned).toFixed(0)}</td>
                          <td className="px-2 py-1.5 text-right">{wo.run_time_actual !== null ? Number(wo.run_time_actual).toFixed(0) : "—"}</td>
                          <td className="px-2 py-1.5 text-right">{Number(wo.completed_qty).toFixed(3)}</td>
                          <td className="px-2 py-1.5 text-right text-red-500">{Number(wo.scrap_qty) > 0 ? Number(wo.scrap_qty).toFixed(3) : "—"}</td>
                          <td className="px-2 py-1.5">{wo.qc_passed === true ? "✓ PASS" : wo.qc_passed === false ? "✗ FAIL" : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase mb-1">Materials Used</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {["Material", "Code", "Required", "Issued", "UOM", "Lot Numbers"].map((h) => (
                          <th key={h} className="px-2 py-1.5 text-left text-gray-400">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {order.materials.map((m) => (
                        <tr key={m.id}>
                          <td className="px-2 py-1.5 font-medium">{m.item_name || "—"}</td>
                          <td className="px-2 py-1.5 font-mono">{m.item_code || "—"}</td>
                          <td className="px-2 py-1.5 text-right">{Number(m.required_qty).toFixed(3)}</td>
                          <td className="px-2 py-1.5 text-right">{Number(m.issued_qty).toFixed(3)}</td>
                          <td className="px-2 py-1.5">{m.uom}</td>
                          <td className="px-2 py-1.5 text-indigo-600">{(m.lot_numbers || []).join(", ") || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Complete Order Modal */}
      {showComplete && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-3">Complete Production Order</h2>
            <div className="space-y-3">
              <div><label className="text-xs text-gray-500 mb-1 block">Completed Qty ({order.uom})</label>
                <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={completeForm.completed_qty} onChange={(e) => setCompleteForm({ ...completeForm, completed_qty: e.target.value })} /></div>
              <div><label className="text-xs text-gray-500 mb-1 block">Scrap Qty ({order.uom})</label>
                <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={completeForm.scrap_qty} onChange={(e) => setCompleteForm({ ...completeForm, scrap_qty: e.target.value })} /></div>
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Remarks" value={completeForm.remarks} onChange={(e) => setCompleteForm({ ...completeForm, remarks: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => completeOrder.mutate()} disabled={!completeForm.completed_qty || completeOrder.isPending} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40">
                {completeOrder.isPending ? "…" : "Mark Complete"}
              </button>
              <button onClick={() => setShowComplete(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Complete WO Modal */}
      {completeWoId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-3">Complete Work Order</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div><label className="text-xs text-gray-500 mb-1 block">Completed Qty</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={woCompleteForm.completed_qty} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, completed_qty: e.target.value })} /></div>
                <div><label className="text-xs text-gray-500 mb-1 block">Scrap Qty</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={woCompleteForm.scrap_qty} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, scrap_qty: e.target.value })} /></div>
                <div><label className="text-xs text-gray-500 mb-1 block">Rework Qty</label>
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={woCompleteForm.rework_qty} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, rework_qty: e.target.value })} /></div>
              </div>
              <div><label className="text-xs text-gray-500 mb-1 block">Actual Run Time (min)</label>
                <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={woCompleteForm.run_time_actual} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, run_time_actual: e.target.value })} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs text-gray-500 mb-1 block">Scrap Category</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={woCompleteForm.scrap_category} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, scrap_category: e.target.value })}>
                    <option value="">None</option>
                    {SCRAP_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div><label className="text-xs text-gray-500 mb-1 block">QC Result</label>
                  <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={woCompleteForm.qc_passed} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, qc_passed: e.target.value })}>
                    <option value="">Not checked</option>
                    <option value="true">PASSED</option>
                    <option value="false">FAILED</option>
                  </select>
                </div>
              </div>
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Scrap reason" value={woCompleteForm.scrap_reason} onChange={(e) => setWoCompleteForm({ ...woCompleteForm, scrap_reason: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => completeWO.mutate()} disabled={!woCompleteForm.completed_qty || completeWO.isPending} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40">
                {completeWO.isPending ? "…" : "Complete Step"}
              </button>
              <button onClick={() => setCompleteWoId(null)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Split Modal */}
      {showSplit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-1">Split Order</h2>
            <p className="text-sm text-gray-500 mb-3">Total: {Number(order.planned_qty).toLocaleString()} {order.uom}. Comma-separated quantities must sum to total.</p>
            <div className="space-y-3">
              <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono" placeholder="e.g. 500,500" value={splitQtys} onChange={(e) => setSplitQtys(e.target.value)} />
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={2} placeholder="Reason" value={splitReason} onChange={(e) => setSplitReason(e.target.value)} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => doSplit.mutate()} disabled={!splitQtys || doSplit.isPending} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40">
                {doSplit.isPending ? "Splitting…" : "Split Order"}
              </button>
              <button onClick={() => setShowSplit(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Rework Modal */}
      {showRework && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-3">Create Rework Order</h2>
            <div className="space-y-3">
              <div><label className="text-xs text-gray-500 mb-1 block">Rework Qty ({order.uom})</label>
                <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={reworkForm.qty} onChange={(e) => setReworkForm({ ...reworkForm, qty: e.target.value })} /></div>
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={3} placeholder="Rework reason *" value={reworkForm.reason} onChange={(e) => setReworkForm({ ...reworkForm, reason: e.target.value })} />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => doRework.mutate()} disabled={!reworkForm.qty || !reworkForm.reason || doRework.isPending} className="flex-1 bg-orange-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-orange-700 disabled:opacity-40">
                {doRework.isPending ? "…" : "Create Rework Order"}
              </button>
              <button onClick={() => setShowRework(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Issue Material Modal */}
      {issueMat && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-1">Issue Material</h2>
            <p className="text-sm text-gray-500 mb-3">{issueMat.item_name} — Required: {Number(issueMat.required_qty).toFixed(3)} {issueMat.uom}</p>
            <div className="space-y-3">
              <div><label className="text-xs text-gray-500 mb-1 block">Qty to Issue</label>
                <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" value={issueQty} onChange={(e) => setIssueQty(e.target.value)} /></div>
              <div><label className="text-xs text-gray-500 mb-1 block">Lot Number (optional)</label>
                <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="e.g. LOT-2026-001" value={issueLot} onChange={(e) => setIssueLot(e.target.value)} /></div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => doIssue.mutate()} disabled={!issueQty || doIssue.isPending} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40">
                {doIssue.isPending ? "…" : "Issue Material"}
              </button>
              <button onClick={() => setIssueMat(null)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
