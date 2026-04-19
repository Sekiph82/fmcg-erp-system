"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sfApi, LiveWOItem, LIVE_STATUS_COLOR, DOWNTIME_CAT_LABEL } from "@/lib/shopFloor";

const DOWNTIME_CATS = [
  "MACHINE_BREAKDOWN", "MATERIAL_SHORTAGE", "PACKAGING_SHORTAGE", "QC_WAITING",
  "CHANGEOVER", "CLEANING", "POWER_ISSUE", "LABOR_SHORTAGE", "MAINTENANCE_STOP", "OTHER",
];

export default function OperatorTerminal() {
  const qc = useQueryClient();
  const [operatorName, setOperatorName] = useState("");
  const [lineId, setLineId] = useState("");
  const [selectedWO, setSelectedWO] = useState<LiveWOItem | null>(null);
  const [qtyGood, setQtyGood] = useState("");
  const [qtyScrap, setQtyScrap] = useState("0");
  const [qtyRework, setQtyRework] = useState("0");
  const [remarkText, setRemarkText] = useState("");
  const [showDowntime, setShowDowntime] = useState(false);
  const [dtCategory, setDtCategory] = useState("MACHINE_BREAKDOWN");
  const [dtReason, setDtReason] = useState("");
  const [activeTab, setActiveTab] = useState<"queue" | "finish" | "scrap" | "note">("queue");

  const { data: queue = [] } = useQuery<LiveWOItem[]>({
    queryKey: ["sf-live-queue", lineId],
    queryFn: () => sfApi.getLiveQueue(lineId ? { line_id: lineId } : undefined),
    refetchInterval: 15_000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["sf-live-queue"] });
    qc.invalidateQueries({ queryKey: ["sf-dashboard"] });
  };

  const startMut = useMutation({
    mutationFn: (woId: string) => sfApi.startWO(woId, { operator_name: operatorName, line_id: lineId }),
    onSuccess: invalidate,
  });

  const pauseMut = useMutation({
    mutationFn: (woId: string) => sfApi.pauseWO(woId, { operator_name: operatorName }),
    onSuccess: invalidate,
  });

  const resumeMut = useMutation({
    mutationFn: (woId: string) => sfApi.resumeWO(woId, { operator_name: operatorName }),
    onSuccess: invalidate,
  });

  const qtyMut = useMutation({
    mutationFn: (woId: string) => sfApi.updateQty(woId, {
      qty_good: parseFloat(qtyGood) || 0,
      qty_scrap: parseFloat(qtyScrap) || 0,
      qty_rework: parseFloat(qtyRework) || 0,
      operator_name: operatorName,
    }),
    onSuccess: () => { setQtyGood(""); invalidate(); },
  });

  const finishMut = useMutation({
    mutationFn: (woId: string) => sfApi.finishWO(woId, {
      qty_good: parseFloat(qtyGood) || 0,
      qty_scrap: parseFloat(qtyScrap) || 0,
      qty_rework: parseFloat(qtyRework) || 0,
      operator_name: operatorName,
    }),
    onSuccess: () => { setSelectedWO(null); setQtyGood(""); invalidate(); },
  });

  const scrapMut = useMutation({
    mutationFn: ({ woId, qty }: { woId: string; qty: number }) =>
      sfApi.recordScrap(woId, { qty_scrap: qty, operator_name: operatorName, reason_code: remarkText }),
    onSuccess: () => { setQtyScrap("0"); setRemarkText(""); invalidate(); },
  });

  const helpMut = useMutation({
    mutationFn: (woId: string) => sfApi.requestHelp(woId, remarkText || "Operator needs help", operatorName),
    onSuccess: () => { setRemarkText(""); invalidate(); },
  });

  const qcMut = useMutation({
    mutationFn: (woId: string) => sfApi.triggerQC(woId, { operator_name: operatorName }),
    onSuccess: invalidate,
  });

  const noteMut = useMutation({
    mutationFn: (woId: string) => sfApi.addNote(woId, remarkText, operatorName),
    onSuccess: () => { setRemarkText(""); invalidate(); },
  });

  const dtMut = useMutation({
    mutationFn: () => sfApi.startDowntime({
      work_order_id: selectedWO?.work_order_id || null,
      line_id: lineId || null,
      operator_name: operatorName,
      downtime_category: dtCategory,
      root_reason: dtReason,
      impact_level: "MEDIUM",
    }),
    onSuccess: () => { setShowDowntime(false); setDtReason(""); invalidate(); },
  });

  const runningWO = selectedWO && queue.find((w) => w.id === selectedWO.id);
  const isAnyPending = startMut.isPending || pauseMut.isPending || resumeMut.isPending ||
    finishMut.isPending || helpMut.isPending || qcMut.isPending;

  return (
    <div className="p-4 max-w-2xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <a href="/dashboard/shop-floor" className="text-sm text-gray-400 hover:text-gray-600">← Dashboard</a>
      </div>
      <h1 className="text-xl font-bold text-gray-900">Operator Terminal</h1>

      {/* Operator Setup */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-600 mb-2">Operator Info</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400">Your Name</label>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5"
              placeholder="Enter name"
              value={operatorName}
              onChange={(e) => setOperatorName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Line / Station</label>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5"
              placeholder="e.g. LINE-1"
              value={lineId}
              onChange={(e) => setLineId(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Work Order Queue */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-600 mb-3">Work Order Queue ({queue.length})</p>
        {queue.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">No work orders for this line</p>
        ) : (
          <div className="space-y-2">
            {queue.map((wo) => (
              <button
                key={wo.id}
                onClick={() => setSelectedWO(selectedWO?.id === wo.id ? null : wo)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedWO?.id === wo.id
                    ? "border-indigo-300 bg-indigo-50"
                    : "border-gray-100 bg-gray-50 hover:bg-gray-100"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-sm text-gray-900">{wo.step_name}</p>
                    <p className="text-xs text-gray-400">{wo.product_name || "—"} • Batch: {wo.batch_no || "—"}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${LIVE_STATUS_COLOR[wo.live_status]}`}>
                      {wo.live_status}
                    </span>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {wo.completed_qty.toFixed(0)} / {wo.planned_qty.toFixed(0)}
                    </p>
                  </div>
                </div>
                {wo.has_active_downtime && (
                  <p className="text-xs text-red-600 mt-1">⚠ Active downtime</p>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Action Panel */}
      {selectedWO && (
        <div className="bg-white rounded-xl border border-indigo-200 shadow-sm p-4 space-y-4">
          <p className="text-sm font-semibold text-gray-700">
            Actions for: <span className="text-indigo-700">{selectedWO.step_name}</span>
          </p>

          {/* Primary Actions */}
          <div className="grid grid-cols-2 gap-3">
            {(selectedWO.live_status === "READY" || selectedWO.live_status === "WAITING") && (
              <button
                onClick={() => startMut.mutate(selectedWO.work_order_id)}
                disabled={isAnyPending || !operatorName}
                className="p-4 bg-green-500 text-white rounded-xl font-bold text-lg hover:bg-green-600 disabled:opacity-40 col-span-2"
              >
                START
              </button>
            )}
            {selectedWO.live_status === "RUNNING" && (
              <>
                <button
                  onClick={() => pauseMut.mutate(selectedWO.work_order_id)}
                  disabled={isAnyPending}
                  className="p-4 bg-yellow-500 text-white rounded-xl font-bold text-lg hover:bg-yellow-600 disabled:opacity-40"
                >
                  PAUSE
                </button>
                <button
                  onClick={() => helpMut.mutate(selectedWO.work_order_id)}
                  disabled={isAnyPending}
                  className="p-4 bg-orange-500 text-white rounded-xl font-bold text-base hover:bg-orange-600 disabled:opacity-40"
                >
                  HELP!
                </button>
                {selectedWO.qc_required_flag && (
                  <button
                    onClick={() => qcMut.mutate(selectedWO.work_order_id)}
                    disabled={isAnyPending}
                    className="p-4 bg-purple-500 text-white rounded-xl font-bold text-base hover:bg-purple-600 disabled:opacity-40"
                  >
                    QC CHECK
                  </button>
                )}
                <button
                  onClick={() => setShowDowntime(true)}
                  className="p-4 bg-red-500 text-white rounded-xl font-bold text-base hover:bg-red-600"
                >
                  DOWNTIME
                </button>
              </>
            )}
            {selectedWO.live_status === "PAUSED" && (
              <button
                onClick={() => resumeMut.mutate(selectedWO.work_order_id)}
                disabled={isAnyPending}
                className="p-4 bg-blue-500 text-white rounded-xl font-bold text-lg hover:bg-blue-600 disabled:opacity-40 col-span-2"
              >
                RESUME
              </button>
            )}
          </div>

          {/* Tabs: Qty / Scrap / Note / Finish */}
          {(selectedWO.live_status === "RUNNING" || selectedWO.live_status === "PAUSED") && (
            <>
              <div className="flex border-b border-gray-100">
                {(["queue", "finish", "scrap", "note"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveTab(t)}
                    className={`px-3 py-1.5 text-xs font-medium capitalize ${activeTab === t ? "border-b-2 border-indigo-500 text-indigo-600" : "text-gray-400"}`}
                  >
                    {t === "queue" ? "Update Qty" : t}
                  </button>
                ))}
              </div>

              {activeTab === "queue" && (
                <div className="space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-xs text-gray-400">Good Qty</label>
                      <input type="number" className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" value={qtyGood} onChange={(e) => setQtyGood(e.target.value)} min="0" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400">Scrap Qty</label>
                      <input type="number" className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" value={qtyScrap} onChange={(e) => setQtyScrap(e.target.value)} min="0" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400">Rework</label>
                      <input type="number" className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" value={qtyRework} onChange={(e) => setQtyRework(e.target.value)} min="0" />
                    </div>
                  </div>
                  <button onClick={() => qtyMut.mutate(selectedWO.work_order_id)} disabled={!qtyGood || qtyMut.isPending} className="w-full py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-40">
                    Update Quantity
                  </button>
                </div>
              )}

              {activeTab === "finish" && (
                <div className="space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-xs text-gray-400">Final Good Qty</label>
                      <input type="number" className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" value={qtyGood} onChange={(e) => setQtyGood(e.target.value)} min="0" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400">Scrap</label>
                      <input type="number" className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" value={qtyScrap} onChange={(e) => setQtyScrap(e.target.value)} min="0" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400">Rework</label>
                      <input type="number" className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" value={qtyRework} onChange={(e) => setQtyRework(e.target.value)} min="0" />
                    </div>
                  </div>
                  <button onClick={() => finishMut.mutate(selectedWO.work_order_id)} disabled={!qtyGood || finishMut.isPending} className="w-full py-3 bg-teal-600 text-white rounded-xl font-bold text-base disabled:opacity-40">
                    FINISH WORK ORDER
                  </button>
                </div>
              )}

              {activeTab === "scrap" && (
                <div className="space-y-2">
                  <input type="number" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Scrap quantity" value={qtyScrap} onChange={(e) => setQtyScrap(e.target.value)} min="0" />
                  <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Reason (optional)" value={remarkText} onChange={(e) => setRemarkText(e.target.value)} />
                  <button onClick={() => scrapMut.mutate({ woId: selectedWO.work_order_id, qty: parseFloat(qtyScrap) || 0 })} disabled={!qtyScrap || scrapMut.isPending} className="w-full py-2 bg-red-600 text-white rounded-lg font-medium disabled:opacity-40">
                    Record Scrap
                  </button>
                </div>
              )}

              {activeTab === "note" && (
                <div className="space-y-2">
                  <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" rows={3} placeholder="Enter note…" value={remarkText} onChange={(e) => setRemarkText(e.target.value)} />
                  <button onClick={() => noteMut.mutate(selectedWO.work_order_id)} disabled={!remarkText || noteMut.isPending} className="w-full py-2 bg-gray-700 text-white rounded-lg font-medium disabled:opacity-40">
                    Add Note
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Downtime Modal */}
      {showDowntime && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-red-700">Log Downtime</h2>
            <div>
              <label className="text-xs text-gray-500">Category</label>
              <select className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" value={dtCategory} onChange={(e) => setDtCategory(e.target.value)}>
                {DOWNTIME_CATS.map((c) => <option key={c} value={c}>{DOWNTIME_CAT_LABEL[c as keyof typeof DOWNTIME_CAT_LABEL] || c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Root Reason (optional)</label>
              <textarea className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-0.5" rows={2} value={dtReason} onChange={(e) => setDtReason(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowDowntime(false)} className="flex-1 py-2 border border-gray-200 rounded-lg text-sm">Cancel</button>
              <button onClick={() => dtMut.mutate()} disabled={dtMut.isPending} className="flex-1 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-40">
                Start Downtime
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
