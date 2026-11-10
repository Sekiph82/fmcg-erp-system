"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { describeShopFloorError, sfApi, LiveWOItem, SFOperationMaterial, SFSession, WOActivityLog, LIVE_STATUS_COLOR, DOWNTIME_CAT_LABEL } from "@/lib/shopFloor";
import { ShopFloorConnectionNotice, useShopFloorConnectionState } from "@/components/shop-floor/ShopFloorConnectionNotice";
import { advProductionApi, Shift, WorkCenter } from "@/lib/productionAdvanced";
import { Machine, moApi, OperatorProfile } from "@/lib/machineOperator";
import { useAuth } from "@/context/AuthContext";

const DOWNTIME_CATS = [
  "MACHINE_BREAKDOWN", "MATERIAL_SHORTAGE", "PACKAGING_SHORTAGE", "QC_WAITING",
  "CHANGEOVER", "CLEANING", "POWER_ISSUE", "LABOR_SHORTAGE", "MAINTENANCE_STOP", "OTHER",
];
const ACTIVE_SESSION_STORAGE_KEY = "shop-floor-active-session-id";

export default function OperatorTerminal() {
  const qc = useQueryClient();
  const { user, canPerformInScope, refreshUser } = useAuth();
  const connection = useShopFloorConnectionState();
  const [refreshingState, setRefreshingState] = useState(false);
  const [requiresStateRefresh, setRequiresStateRefresh] = useState(false);
  const [operatorName, setOperatorName] = useState("");
  const [operatorId, setOperatorId] = useState("");
  const [lineId, setLineId] = useState("");
  const [machineId, setMachineId] = useState("");
  const [workCenterId, setWorkCenterId] = useState("");
  const [shiftId, setShiftId] = useState("");
  const [activeSession, setActiveSession] = useState<SFSession | null>(null);
  const [restoringSession, setRestoringSession] = useState(true);
  const [selectedWOId, setSelectedWOId] = useState<string | null>(null);
  const [qtyGood, setQtyGood] = useState("");
  const [qtyScrap, setQtyScrap] = useState("0");
  const [qtyRework, setQtyRework] = useState("0");
  const [runTimeActual, setRunTimeActual] = useState("");
  const [scrapCategory, setScrapCategory] = useState<"" | "normal" | "abnormal">("");
  const [scrapReason, setScrapReason] = useState("");
  const [remarkText, setRemarkText] = useState("");
  const [showDowntime, setShowDowntime] = useState(false);
  const [dtCategory, setDtCategory] = useState("MACHINE_BREAKDOWN");
  const [dtReason, setDtReason] = useState("");
  const [materialQtyById, setMaterialQtyById] = useState<Record<string, string>>({});
  const [materialLotById, setMaterialLotById] = useState<Record<string, string>>({});
  const [qcCheckpointName, setQCCheckpointName] = useState("");
  const [qcResult, setQCResult] = useState<"" | "PASS" | "FAIL">("");
  const [qcMeasuredValue, setQCMeasuredValue] = useState("");
  const [qcUnit, setQCUnit] = useState("");
  const [qcNotes, setQCNotes] = useState("");
  const [activeTab, setActiveTab] = useState<"queue" | "materials" | "qc" | "finish" | "scrap" | "note">("queue");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string; requiresRefresh?: boolean } | null>(null);

  const { data: queue = [], isLoading, isFetching, isError } = useQuery<LiveWOItem[]>({
    queryKey: ["sf-live-queue", lineId],
    queryFn: () => sfApi.getLiveQueue(lineId ? { line_id: lineId } : undefined),
    refetchInterval: 15_000,
  });

  const { data: operators = [] } = useQuery<OperatorProfile[]>({
    queryKey: ["shop-floor-operator-profiles"],
    queryFn: () => moApi.listOperators(),
  });
  const { data: machines = [] } = useQuery<Machine[]>({
    queryKey: ["shop-floor-machines"],
    queryFn: () => moApi.listMachines(),
  });
  const { data: workCenters = [] } = useQuery<WorkCenter[]>({
    queryKey: ["shop-floor-work-centers"],
    queryFn: () => advProductionApi.listWorkCenters({ status: "ACTIVE" }),
  });
  const { data: shifts = [] } = useQuery<Shift[]>({
    queryKey: ["shop-floor-shifts"],
    queryFn: () => advProductionApi.listShifts(),
  });

  useEffect(() => {
    let mounted = true;
    let savedSessionId: string | null = null;
    try {
      savedSessionId = window.sessionStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);
    } catch {
      // The terminal still works for this page lifetime when browser storage is unavailable.
    }

    if (!savedSessionId) {
      setRestoringSession(false);
      return () => { mounted = false; };
    }

    sfApi.getSession(savedSessionId)
      .then((session) => {
        if (!mounted) return;
        if (session.status === "ACTIVE") {
          setActiveSession(session);
          setOperatorName(session.operator_name);
          setOperatorId(session.operator_id ?? "");
          setLineId(session.line_id ?? "");
          setMachineId(session.machine_id ?? "");
          setWorkCenterId(session.work_center_id ?? "");
          setShiftId(session.shift_id ?? "");
        }
        else window.sessionStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
      })
      .catch(() => {
        try { window.sessionStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY); } catch { /* storage may be unavailable */ }
      })
      .finally(() => { if (mounted) setRestoringSession(false); });

    return () => { mounted = false; };
  }, []);

  const selectedWO = queue.find((wo) => wo.id === selectedWOId) ?? null;
  const hasOperator = operatorName.trim().length > 0;
  const hasActiveSession = activeSession?.status === "ACTIVE";
  const permissionCodes = new Set(user?.permission_codes ?? []);
  const materialsQuery = useQuery<SFOperationMaterial[]>({
    queryKey: ["sf-work-order-materials", selectedWO?.work_order_id],
    queryFn: () => sfApi.getWorkOrderMaterials(selectedWO!.work_order_id, activeSession!.id),
    enabled: Boolean(
      selectedWO && hasActiveSession &&
      activeSession?.current_work_order_id === selectedWO.work_order_id &&
      ["RUNNING", "PAUSED"].includes(selectedWO.live_status),
    ),
  });
  const canViewQC = ["quality.view", "quality.view_all", "quality.view_own_scope"].some((code) => permissionCodes.has(code));
  const canRecordQC = canViewQC && ["quality.edit", "quality.edit_all", "quality.edit_own_scope"].some((code) => permissionCodes.has(code));
  const qcCheckpointsQuery = useQuery<WOActivityLog[]>({
    queryKey: ["sf-work-order-qc-checkpoints", selectedWO?.work_order_id],
    queryFn: () => sfApi.getWorkOrderQCCheckpoints(selectedWO!.work_order_id, activeSession!.id),
    enabled: Boolean(
      selectedWO && hasActiveSession && canViewQC &&
      activeSession?.current_work_order_id === selectedWO.work_order_id &&
      ["RUNNING", "PAUSED"].includes(selectedWO.live_status),
    ),
  });
  const hasGlobalEdit = Boolean(user?.is_superuser || permissionCodes.has("production.edit") || permissionCodes.has("production.edit_all"));
  const hasScopedExecution = Boolean(permissionCodes.has("production.edit_own_scope") || permissionCodes.has("production_execution.update_own_line"));
  const selectedLineId = activeSession?.line_id ?? lineId.trim();
  const canExecuteOnSelectedLine = hasGlobalEdit || Boolean(
    hasScopedExecution && selectedLineId && canPerformInScope("production_line", selectedLineId, "edit")
  );
  const queueUnavailable = isLoading || isError || connection.state !== "online" || requiresStateRefresh;
  const reportError = (error: unknown) => {
    const detail = describeShopFloorError(error);
    if (detail.requiresRefresh) setRequiresStateRefresh(true);
    setFeedback({ type: "error", ...detail });
  };
  const reportSuccess = (message: string) => setFeedback({ type: "success", message });

  const refreshShopFloorState = async () => {
    setRefreshingState(true);
    try {
      await refreshUser();
      await qc.invalidateQueries({
        predicate: (query) => typeof query.queryKey[0] === "string" &&
          query.queryKey[0].startsWith("sf-"),
      }, { throwOnError: true });
      connection.acknowledgeRefresh();
      setRequiresStateRefresh(false);
      setFeedback({
        type: "success",
        message: "Latest Shop Floor state loaded. Check whether the previous action was recorded before submitting it again.",
      });
    } catch (error) {
      reportError(error);
    } finally {
      setRefreshingState(false);
    }
  };

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["sf-live-queue"] });
    qc.invalidateQueries({ queryKey: ["sf-dashboard"] });
  };

  const sessionMut = useMutation({
    mutationFn: () => sfApi.createSession({
      operator_name: operatorName.trim(),
      operator_id: operatorId || undefined,
      line_id: lineId.trim() || undefined,
      machine_id: machineId || undefined,
      work_center_id: workCenterId || undefined,
      shift_id: shiftId || undefined,
    }),
    onSuccess: (session) => {
      setActiveSession(session);
      try { window.sessionStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, session.id); } catch { /* retain context in memory for this page lifetime */ }
      reportSuccess(`Operator session ${session.session_code} started.`);
      invalidate();
    },
    onError: reportError,
  });

  const logoutMut = useMutation({
    mutationFn: (sessionId: string) => sfApi.logoutSession(sessionId),
    onSuccess: () => {
      setActiveSession(null);
      try { window.sessionStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY); } catch { /* storage may be unavailable */ }
      setSelectedWOId(null);
      reportSuccess("Operator session ended.");
      invalidate();
    },
    onError: reportError,
  });

  const startMut = useMutation({
    mutationFn: (woId: string) => sfApi.startWO(woId, {
      session_id: activeSession?.id,
      operator_name: activeSession?.operator_name,
      line_id: activeSession?.line_id,
      machine_id: activeSession?.machine_id,
    }),
    onSuccess: (entry) => {
      setActiveSession((session) => session ? { ...session, current_work_order_id: entry.work_order_id } : session);
      reportSuccess("Work order started.");
      invalidate();
    },
    onError: reportError,
  });

  const pauseMut = useMutation({
    mutationFn: (woId: string) => sfApi.pauseWO(woId, { session_id: activeSession?.id, operator_name: activeSession?.operator_name }),
    onSuccess: () => { reportSuccess("Work order paused."); invalidate(); },
    onError: reportError,
  });

  const resumeMut = useMutation({
    mutationFn: (woId: string) => sfApi.resumeWO(woId, { session_id: activeSession?.id, operator_name: activeSession?.operator_name }),
    onSuccess: () => { reportSuccess("Work order resumed."); invalidate(); },
    onError: reportError,
  });

  const qtyMut = useMutation({
    mutationFn: (woId: string) => sfApi.updateQty(woId, {
      qty_good: parseFloat(qtyGood) || 0,
      qty_scrap: parseFloat(qtyScrap) || 0,
      qty_rework: parseFloat(qtyRework) || 0,
      scrap_category: scrapCategory || undefined,
      scrap_reason: scrapReason.trim() || undefined,
      session_id: activeSession?.id,
      operator_name: activeSession?.operator_name,
    }),
    onSuccess: () => { setQtyGood(""); reportSuccess("Production quantities updated."); invalidate(); },
    onError: reportError,
  });

  const finishMut = useMutation({
    mutationFn: (woId: string) => sfApi.finishWO(woId, {
      qty_good: parseFloat(qtyGood) || 0,
      qty_scrap: parseFloat(qtyScrap) || 0,
      qty_rework: parseFloat(qtyRework) || 0,
      run_time_actual: runTimeActual.trim() ? Number(runTimeActual) : undefined,
      scrap_category: scrapCategory || undefined,
      scrap_reason: scrapReason.trim() || undefined,
      session_id: activeSession?.id,
      operator_name: activeSession?.operator_name,
    }),
    onSuccess: () => {
      setSelectedWOId(null);
      setActiveSession((session) => session ? { ...session, current_work_order_id: null } : session);
      setQtyGood("");
      setRunTimeActual("");
      setScrapCategory("");
      setScrapReason("");
      reportSuccess("Work order completed.");
      invalidate();
    },
    onError: reportError,
  });

  const scrapMut = useMutation({
    mutationFn: ({ woId, qty }: { woId: string; qty: number }) =>
      sfApi.recordScrap(woId, {
        qty_scrap: qty,
        scrap_category: scrapCategory || undefined,
        scrap_reason: scrapReason.trim() || undefined,
        session_id: activeSession?.id,
        operator_name: activeSession?.operator_name,
      }),
    onSuccess: () => { setQtyScrap("0"); setScrapCategory(""); setScrapReason(""); reportSuccess("Scrap / waste recorded."); invalidate(); },
    onError: reportError,
  });

  const helpMut = useMutation({
    mutationFn: (woId: string) => sfApi.requestHelp(woId, remarkText || "Operator needs help", activeSession?.operator_name, activeSession?.id),
    onSuccess: () => { setRemarkText(""); reportSuccess("Help request sent."); invalidate(); },
    onError: reportError,
  });

  const qcMut = useMutation({
    mutationFn: (woId: string) => sfApi.triggerQC(woId, { session_id: activeSession?.id, operator_name: activeSession?.operator_name }),
    onSuccess: () => { reportSuccess("Quality check requested."); invalidate(); },
    onError: reportError,
  });

  const noteMut = useMutation({
    mutationFn: (woId: string) => sfApi.addNote(woId, remarkText, activeSession?.operator_name, activeSession?.id),
    onSuccess: () => { setRemarkText(""); reportSuccess("Note added."); invalidate(); },
    onError: reportError,
  });

  const dtMut = useMutation({
    mutationFn: () => sfApi.startDowntime({
      work_order_id: selectedWO?.work_order_id || null,
      session_id: activeSession?.id,
      operator_id: activeSession?.operator_id,
      team_id: activeSession?.team_id,
      shift_id: activeSession?.shift_id,
      machine_id: activeSession?.machine_id,
      line_id: activeSession?.line_id || null,
      operator_name: activeSession?.operator_name,
      downtime_category: dtCategory,
      root_reason: dtReason,
      impact_level: "MEDIUM",
    }),
    onSuccess: () => { setShowDowntime(false); setDtReason(""); reportSuccess("Downtime recorded."); invalidate(); },
    onError: reportError,
  });

  const materialConsumptionMut = useMutation({
    mutationFn: ({ woId, materialId, qty, lotNo }: { woId: string; materialId: string; qty: number; lotNo?: string }) =>
      sfApi.consumeWorkOrderMaterial(woId, materialId, {
        qty,
        session_id: activeSession!.id,
        lot_no: lotNo,
      }),
    onSuccess: (_material, variables) => {
      setMaterialQtyById((quantities) => ({ ...quantities, [variables.materialId]: "" }));
      reportSuccess("Material consumption recorded for this operation.");
      qc.invalidateQueries({ queryKey: ["sf-work-order-materials", variables.woId] });
      qc.invalidateQueries({ queryKey: ["sf-activity", variables.woId] });
      invalidate();
    },
    onError: reportError,
  });

  const qcCheckpointMut = useMutation({
    mutationFn: (woId: string) => sfApi.recordWorkOrderQCCheckpoint(woId, {
      session_id: activeSession!.id,
      checkpoint_name: qcCheckpointName.trim(),
      result: qcResult as "PASS" | "FAIL",
      measured_value: qcMeasuredValue.trim() || undefined,
      unit: qcUnit.trim() || undefined,
      notes: qcNotes.trim() || undefined,
    }),
    onSuccess: () => {
      setQCCheckpointName("");
      setQCResult("");
      setQCMeasuredValue("");
      setQCUnit("");
      setQCNotes("");
      reportSuccess("In-process QC checkpoint recorded.");
      qc.invalidateQueries({ queryKey: ["sf-work-order-qc-checkpoints", selectedWO?.work_order_id] });
      invalidate();
    },
    onError: reportError,
  });

  const isAnyPending = startMut.isPending || pauseMut.isPending || resumeMut.isPending ||
    qtyMut.isPending || finishMut.isPending || scrapMut.isPending || helpMut.isPending ||
    qcMut.isPending || noteMut.isPending || dtMut.isPending || materialConsumptionMut.isPending || qcCheckpointMut.isPending ||
    sessionMut.isPending || logoutMut.isPending || connection.state !== "online" || requiresStateRefresh;
  const activeMachine = machines.find((machine) => machine.id === activeSession?.machine_id);
  const activeWorkCenter = workCenters.find((workCenter) => workCenter.id === activeSession?.work_center_id);
  const activeShift = shifts.find((shift) => shift.id === activeSession?.shift_id);

  return (
    <main className="min-h-screen p-3 sm:p-4 pb-8 max-w-3xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <a href="/dashboard/shop-floor" className="inline-flex min-h-11 items-center text-sm text-gray-500 hover:text-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 rounded">← Dashboard</a>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-gray-900">Operator Terminal</h1>
        <span className="text-xs text-gray-500" role="status">
          {isFetching ? "Refreshing queue…" : "Queue refreshes every 15 seconds"}
        </span>
      </div>

      {!showDowntime && (
        <ShopFloorConnectionNotice
          state={connection.state}
          onRefresh={() => void refreshShopFloorState()}
          refreshing={refreshingState}
          forceRefresh={Boolean(feedback?.requiresRefresh)}
        />
      )}

      {feedback && (
        <div
          role={feedback.type === "error" ? "alert" : "status"}
          aria-live={feedback.type === "error" ? "assertive" : "polite"}
          className={`rounded-lg border px-3 py-2 text-sm ${feedback.type === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-green-200 bg-green-50 text-green-800"}`}
        >
          <div className="flex items-start justify-between gap-3">
            <p>{feedback.message}</p>
            {feedback.type === "error" && feedback.requiresRefresh && (
              <button type="button" onClick={() => void refreshShopFloorState()} disabled={refreshingState} className="mt-2 min-h-11 rounded-md border border-red-500 px-3 font-semibold disabled:opacity-50">
                {refreshingState ? "Refreshing Shop Floor state…" : "Refresh Shop Floor state"}
              </button>
            )}
            <button type="button" onClick={() => setFeedback(null)} className="min-h-11 min-w-11 -my-2 font-semibold" aria-label="Dismiss message">×</button>
          </div>
        </div>
      )}

      {isError && (
        <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p>Could not refresh the work-order queue. Check the connection. Shop Floor changes are not saved offline.</p>
          <button type="button" onClick={() => void refreshShopFloorState()} className="mt-2 min-h-11 rounded-md border border-amber-500 px-3 font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-700">
            Refresh Shop Floor state
          </button>
        </div>
      )}

      {/* Operator Setup */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
          <div>
            <p className="text-sm font-semibold text-gray-700">Operator Session</p>
            <p className="text-xs text-gray-500 mt-1">Context is attached to each shop-floor action for traceability.</p>
          </div>
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${hasActiveSession ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-700"}`}>
            {hasActiveSession ? "SESSION ACTIVE" : "NO ACTIVE SESSION"}
          </span>
        </div>
        {!hasActiveSession ? (
          <>
            {restoringSession && <p className="text-sm text-gray-600" role="status">Checking for an existing operator session…</p>}
            <fieldset disabled={isAnyPending || restoringSession} className="grid grid-cols-1 sm:grid-cols-2 gap-3 disabled:opacity-70">
              <div>
                <label htmlFor="shop-floor-operator-profile" className="text-xs text-gray-600">Operator profile (optional)</label>
                <select
                  id="shop-floor-operator-profile"
                  className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5"
                  value={operatorId}
                  onChange={(event) => {
                    const nextId = event.target.value;
                    setOperatorId(nextId);
                    const profile = operators.find((item) => item.id === nextId);
                    if (profile) setOperatorName(profile.full_name);
                  }}
                >
                  <option value="">Use entered virtual operator name</option>
                  {operators.filter((operator) => operator.active_flag).map((operator) => (
                    <option key={operator.id} value={operator.id}>{operator.operator_code} — {operator.full_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="shop-floor-operator-name" className="text-xs text-gray-600">Operator name</label>
                <input
                  id="shop-floor-operator-name"
                  className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5"
                  placeholder="Enter virtual operator name"
                  value={operatorName}
                  onChange={(event) => { setOperatorName(event.target.value); setOperatorId(""); }}
                  autoComplete="off"
                  aria-required="true"
                />
              </div>
              <div>
                <label htmlFor="shop-floor-line-id" className="text-xs text-gray-600">Line / station (optional)</label>
                <input
                  id="shop-floor-line-id"
                  className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5"
                  placeholder="Line or station code"
                  value={lineId}
                  onChange={(event) => setLineId(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="shop-floor-work-center" className="text-xs text-gray-600">Work center (optional)</label>
                <select id="shop-floor-work-center" className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5" value={workCenterId} onChange={(event) => setWorkCenterId(event.target.value)}>
                  <option value="">No work center selected</option>
                  {workCenters.filter((workCenter) => workCenter.status === "ACTIVE").map((workCenter) => (
                    <option key={workCenter.id} value={workCenter.id}>{workCenter.work_center_id} — {workCenter.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="shop-floor-machine" className="text-xs text-gray-600">Machine (optional)</label>
                <select
                  id="shop-floor-machine"
                  className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5"
                  value={machineId}
                  onChange={(event) => {
                    const nextId = event.target.value;
                    setMachineId(nextId);
                    const machine = machines.find((item) => item.id === nextId);
                    if (machine?.line_id) setLineId(machine.line_id);
                    if (machine?.work_center_id) setWorkCenterId(machine.work_center_id);
                  }}
                >
                  <option value="">No machine selected</option>
                  {machines.filter((machine) => machine.active_flag && machine.status === "ACTIVE").map((machine) => (
                    <option key={machine.id} value={machine.id}>{machine.machine_code} — {machine.machine_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="shop-floor-shift" className="text-xs text-gray-600">Shift (optional)</label>
                <select id="shop-floor-shift" className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5" value={shiftId} onChange={(event) => setShiftId(event.target.value)}>
                  <option value="">No shift selected</option>
                  {shifts.filter((shift) => shift.is_active).map((shift) => (
                    <option key={shift.id} value={shift.id}>{shift.shift_code} — {shift.name} ({shift.start_time_str}–{shift.end_time_str})</option>
                  ))}
                </select>
              </div>
            </fieldset>
            <button
              type="button"
              onClick={() => sessionMut.mutate()}
              disabled={!hasOperator || !canExecuteOnSelectedLine || isAnyPending || restoringSession}
              className="mt-3 w-full min-h-12 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-800"
            >
              {sessionMut.isPending ? "STARTING SESSION…" : "Start operator session"}
            </button>
          </>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 rounded-lg bg-gray-50 p-3 text-sm">
              <p><span className="text-gray-500">Operator:</span> {activeSession.operator_name}</p>
              <p><span className="text-gray-500">Shift:</span> {activeShift?.name || (activeSession.shift_id ? "Selected shift" : "Not selected")}</p>
              <p><span className="text-gray-500">Work center:</span> {activeWorkCenter?.name || (activeSession.work_center_id ? "Selected work center" : "Not selected")}</p>
              <p><span className="text-gray-500">Machine:</span> {activeMachine?.machine_name || (activeSession.machine_id ? "Selected machine" : "Not selected")}</p>
              <p><span className="text-gray-500">Line:</span> {activeSession.line_id || "Not selected"}</p>
              <p><span className="text-gray-500">Session:</span> {activeSession.session_code}</p>
            </div>
            <button type="button" onClick={() => logoutMut.mutate(activeSession.id)} disabled={isAnyPending} className="min-h-12 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40">
              {logoutMut.isPending ? "ENDING SESSION…" : "End operator session"}
            </button>
          </div>
        )}
      </div>

      {/* Work Order Queue */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-600 mb-3">Work Order Queue ({queue.length})</p>
        {isLoading ? (
          <p className="text-sm text-gray-500 text-center py-6" role="status">Loading work orders…</p>
        ) : queue.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">No work orders for this line</p>
        ) : (
          <div className="space-y-2">
            {queue.map((wo) => (
              <button
                type="button"
                key={wo.id}
                onClick={() => { setSelectedWOId(selectedWOId === wo.id ? null : wo.id); setFeedback(null); }}
                aria-pressed={selectedWOId === wo.id}
                className={`w-full min-h-16 text-left p-3 rounded-xl border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 ${
                  selectedWOId === wo.id
                    ? "border-indigo-300 bg-indigo-50"
                    : "border-gray-100 bg-gray-50 hover:bg-gray-100"
                }`}
              >
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <div className="min-w-0 break-words">
                    <p className="font-semibold text-sm text-gray-900">{wo.step_name}</p>
                    <p className="text-xs text-gray-400">{wo.product_name || "—"} • Batch: {wo.batch_no || "—"}</p>
                  </div>
                  <div className="shrink-0 text-right">
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
          <p className="text-xs text-gray-500">{selectedWO.order_no || selectedWO.work_order_id} · {selectedWO.product_name || "Product not specified"} · Batch {selectedWO.batch_no || "—"}</p>
          {!hasActiveSession && <p className="text-sm text-amber-800" role="status">Start an operator session before recording a shop-floor action.</p>}

          {/* Primary Actions */}
          <div className="grid grid-cols-2 gap-3">
            {(selectedWO.live_status === "READY" || selectedWO.live_status === "WAITING") && (
              <button
                type="button"
                onClick={() => startMut.mutate(selectedWO.work_order_id)}
                disabled={isAnyPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable}
                className="min-h-16 p-4 bg-green-600 text-white rounded-xl font-bold text-lg hover:bg-green-700 disabled:opacity-40 col-span-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-700"
              >
                {startMut.isPending ? "STARTING…" : "START"}
              </button>
            )}
            {selectedWO.live_status === "RUNNING" && (
              <>
                <button
                  type="button"
                  onClick={() => pauseMut.mutate(selectedWO.work_order_id)}
                  disabled={isAnyPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable}
                  className="min-h-16 p-4 bg-amber-500 text-gray-950 rounded-xl font-bold text-lg hover:bg-amber-600 disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700"
                >
                  {pauseMut.isPending ? "PAUSING…" : "PAUSE"}
                </button>
                <button
                  type="button"
                  onClick={() => helpMut.mutate(selectedWO.work_order_id)}
                  disabled={isAnyPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable}
                  className="min-h-16 p-4 bg-orange-600 text-white rounded-xl font-bold text-base hover:bg-orange-700 disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-700"
                >
                  {helpMut.isPending ? "SENDING…" : "HELP!"}
                </button>
                {selectedWO.qc_required_flag && (
                  <button
                    type="button"
                    onClick={() => qcMut.mutate(selectedWO.work_order_id)}
                    disabled={isAnyPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable}
                    className="min-h-16 p-4 bg-purple-600 text-white rounded-xl font-bold text-base hover:bg-purple-700 disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-700"
                  >
                    {qcMut.isPending ? "SENDING…" : "QC CHECK"}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowDowntime(true)}
                  disabled={isAnyPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable}
                  className="min-h-16 p-4 bg-red-600 text-white rounded-xl font-bold text-base hover:bg-red-700 disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700"
                >
                  DOWNTIME
                </button>
              </>
            )}
            {selectedWO.live_status === "PAUSED" && (
              <button
                  type="button"
                onClick={() => resumeMut.mutate(selectedWO.work_order_id)}
                disabled={isAnyPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable}
                  className="min-h-16 p-4 bg-blue-600 text-white rounded-xl font-bold text-lg hover:bg-blue-700 disabled:opacity-40 col-span-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
              >
                  {resumeMut.isPending ? "RESUMING…" : "RESUME"}
              </button>
            )}
          </div>

          {/* Tabs: Qty / Materials / QC / Scrap / Note / Finish */}
          {(selectedWO.live_status === "RUNNING" || selectedWO.live_status === "PAUSED") && (
            <>
              <div className="flex overflow-x-auto border-b border-gray-100" role="group" aria-label="Work-order action panels">
                {(["queue", "materials", "qc", "finish", "scrap", "note"] as const).map((t) => (
                  <button
                    type="button"
                    key={t}
                    onClick={() => setActiveTab(t)}
                    aria-pressed={activeTab === t}
                    className={`min-h-12 shrink-0 px-3 py-1.5 text-sm font-medium capitalize focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 ${activeTab === t ? "border-b-2 border-indigo-500 text-indigo-600" : "text-gray-500"}`}
                  >
                    {t === "queue" ? "Update Qty" : t}
                  </button>
                ))}
              </div>

              {activeTab === "queue" && (
                <div className="space-y-2">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div>
                      <label htmlFor="shop-floor-good-qty" className="text-xs text-gray-600">Good Qty</label>
                      <input id="shop-floor-good-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qtyGood} onChange={(e) => setQtyGood(e.target.value)} min="0" step="any" />
                    </div>
                    <div>
                      <label htmlFor="shop-floor-scrap-qty" className="text-xs text-gray-600">Scrap Qty</label>
                      <input id="shop-floor-scrap-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qtyScrap} onChange={(e) => setQtyScrap(e.target.value)} min="0" step="any" />
                    </div>
                    <div>
                      <label htmlFor="shop-floor-rework-qty" className="text-xs text-gray-600">Rework</label>
                      <input id="shop-floor-rework-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qtyRework} onChange={(e) => setQtyRework(e.target.value)} min="0" step="any" />
                    </div>
                  </div>
                  <button type="button" onClick={() => qtyMut.mutate(selectedWO.work_order_id)} disabled={!hasActiveSession || !canExecuteOnSelectedLine || !isValidNonNegativeNumber(qtyGood) || !isValidNonNegativeNumber(qtyScrap) || !isValidNonNegativeNumber(qtyRework) || isAnyPending || queueUnavailable} className="w-full min-h-12 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700">
                    {qtyMut.isPending ? "UPDATING…" : "Update Quantity"}
                  </button>
                </div>
              )}

              {activeTab === "materials" && (
                <div className="space-y-3" aria-label="Operation material consumption">
                  {!activeSession || activeSession.current_work_order_id !== selectedWO.work_order_id ? (
                    <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900" role="status">
                      Start this operation in the active operator session before viewing or consuming its materials.
                    </p>
                  ) : materialsQuery.isLoading ? (
                    <p className="text-sm text-gray-600" role="status">Loading operation materials…</p>
                  ) : materialsQuery.isError ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
                      Could not load operation materials. <button type="button" className="underline" onClick={() => void materialsQuery.refetch()}>Try again</button>
                    </div>
                  ) : materialsQuery.data?.length ? (
                    materialsQuery.data.map((material) => {
                      const issued = Number(material.issued_qty || 0);
                      const consumed = Number(material.consumed_qty || 0);
                      const returned = Number(material.returned_qty || 0);
                      const outstanding = issued - consumed - returned;
                      const lots = [...new Set((material.lot_numbers || []).filter(Boolean))];
                      const quantity = materialQtyById[material.id] ?? "";
                      const lotNo = materialLotById[material.id] ?? "";
                      return (
                        <article key={material.id} className="rounded-xl border border-gray-200 p-3 space-y-2">
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <h3 className="font-semibold text-gray-900">{material.item_name || material.item_code || "Material"}</h3>
                            <span className="text-xs text-gray-500">{material.item_code || material.item_type}</span>
                          </div>
                          <p className="text-sm text-gray-700">
                            Required {Number(material.required_qty).toLocaleString()} {material.uom} · Issued {issued.toLocaleString()} · Consumed {consumed.toLocaleString()} · Returned {returned.toLocaleString()}
                          </p>
                          <p className="text-sm font-semibold text-indigo-800">Available to consume: {outstanding.toLocaleString()} {material.uom}</p>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <div>
                              <label htmlFor={`material-consume-qty-${material.id}`} className="text-xs text-gray-600">Consumption quantity ({material.uom})</label>
                              <input
                                id={`material-consume-qty-${material.id}`}
                                type="number"
                                inputMode="decimal"
                                min="0"
                                step="any"
                                className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base"
                                value={quantity}
                                onChange={(event) => setMaterialQtyById((values) => ({ ...values, [material.id]: event.target.value }))}
                              />
                            </div>
                            {lots.length > 1 && (
                              <div>
                                <label htmlFor={`material-consume-lot-${material.id}`} className="text-xs text-gray-600">Issued lot</label>
                                <select
                                  id={`material-consume-lot-${material.id}`}
                                  className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base"
                                  value={lotNo}
                                  onChange={(event) => setMaterialLotById((values) => ({ ...values, [material.id]: event.target.value }))}
                                >
                                  <option value="">Select recorded lot</option>
                                  {lots.map((lot) => <option key={lot} value={lot}>{lot}</option>)}
                                </select>
                              </div>
                            )}
                          </div>
                          {lots.length === 0 && <p className="text-xs text-amber-800">No lot was recorded at issue; consumption will retain no lot reference.</p>}
                          {lots.length > 1 && <p className="text-xs text-gray-500">Lots are trace references; this record does not allocate issued quantity per lot.</p>}
                          <button
                            type="button"
                            onClick={() => materialConsumptionMut.mutate({
                              woId: selectedWO.work_order_id,
                              materialId: material.id,
                              qty: Number(quantity),
                              lotNo: lotNo || (lots.length === 1 ? lots[0] : undefined),
                            })}
                            disabled={
                              !hasActiveSession || !canExecuteOnSelectedLine || !isValidNonNegativeNumber(quantity) ||
                              Number(quantity) <= 0 || Number(quantity) > outstanding ||
                              (lots.length > 1 && !lotNo) || outstanding <= 0 || isAnyPending || queueUnavailable
                            }
                            className="w-full min-h-12 py-2 bg-indigo-700 text-white rounded-lg font-semibold disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-800"
                          >
                            {materialConsumptionMut.isPending ? "RECORDING…" : "Record Material Consumption"}
                          </button>
                        </article>
                      );
                    })
                  ) : (
                    <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700" role="status">
                      No materials are assigned to this operation. Order-level materials are not shown here.
                    </p>
                  )}
                </div>
              )}

              {activeTab === "qc" && (
                <div className="space-y-3" aria-label="In-process quality checkpoints">
                  <div className={`rounded-lg p-3 text-sm ${selectedWO.qc_required_flag && selectedWO.qc_passed !== true ? "bg-amber-50 text-amber-900" : "bg-gray-50 text-gray-800"}`} role="status">
                    {selectedWO.qc_required_flag
                      ? selectedWO.qc_passed === true
                        ? "Required QC checkpoints currently pass. New failed checkpoints will block completion."
                        : "This operation requires at least one passing QC checkpoint before completion. Every recorded checkpoint must currently pass."
                      : "QC checkpoints are optional for this operation."}
                  </div>
                  {!canViewQC ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
                      Quality view permission in this product category is required to view checkpoints.
                    </p>
                  ) : !activeSession || activeSession.current_work_order_id !== selectedWO.work_order_id ? (
                    <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900" role="status">
                      Start this operation in the active operator session before recording QC.
                    </p>
                  ) : qcCheckpointsQuery.isLoading ? (
                    <p className="text-sm text-gray-600" role="status">Loading QC history…</p>
                  ) : qcCheckpointsQuery.isError ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
                      Could not load QC history. <button type="button" className="underline" onClick={() => void qcCheckpointsQuery.refetch()}>Try again</button>
                    </div>
                  ) : (
                    <>
                      <div className="space-y-2">
                        {(qcCheckpointsQuery.data || []).map((event) => {
                          const checkpoint = event.extra_data || {};
                          return (
                            <article key={event.id} className="rounded-lg border border-gray-200 p-3 text-sm">
                              <div className="flex flex-wrap justify-between gap-2">
                                <strong>{String(checkpoint.checkpoint_name || "QC checkpoint")}</strong>
                                <span className={checkpoint.result === "PASS" ? "font-semibold text-green-700" : "font-semibold text-red-700"}>
                                  {String(checkpoint.result || "UNKNOWN")}
                                </span>
                              </div>
                              {checkpoint.measured_value != null && (
                                <p className="text-gray-700">Observed: {String(checkpoint.measured_value)} {String(checkpoint.unit || "")}</p>
                              )}
                              {event.remarks && <p className="text-gray-600">{event.remarks}</p>}
                              <p className="mt-1 break-all text-xs text-gray-500">Authenticated user ID: {event.actor_user_id || "not recorded"} · operator context: {event.operator_name || "not provided"} · {new Date(event.created_at).toLocaleString()}</p>
                            </article>
                          );
                        })}
                        {!qcCheckpointsQuery.data?.length && <p className="text-sm text-gray-600">No QC checkpoints have been recorded for this operation.</p>}
                      </div>
                      {canRecordQC ? <div className="rounded-xl border border-gray-200 p-3 space-y-2">
                        <div>
                          <label htmlFor="shop-floor-qc-name" className="text-xs text-gray-600">Checkpoint name</label>
                          <input id="shop-floor-qc-name" maxLength={100} className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qcCheckpointName} onChange={(event) => setQCCheckpointName(event.target.value)} placeholder="For example: fill weight" />
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          <div>
                            <label htmlFor="shop-floor-qc-result" className="text-xs text-gray-600">Observed result</label>
                            <select id="shop-floor-qc-result" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qcResult} onChange={(event) => setQCResult(event.target.value as "" | "PASS" | "FAIL")}>
                              <option value="">Select result</option>
                              <option value="PASS">Pass</option>
                              <option value="FAIL">Fail</option>
                            </select>
                          </div>
                          <div>
                            <label htmlFor="shop-floor-qc-value" className="text-xs text-gray-600">Observed value (optional)</label>
                            <input id="shop-floor-qc-value" maxLength={200} className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qcMeasuredValue} onChange={(event) => setQCMeasuredValue(event.target.value)} />
                          </div>
                          <div>
                            <label htmlFor="shop-floor-qc-unit" className="text-xs text-gray-600">Unit (optional)</label>
                            <input id="shop-floor-qc-unit" maxLength={30} className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qcUnit} onChange={(event) => setQCUnit(event.target.value)} />
                          </div>
                        </div>
                        <div>
                          <label htmlFor="shop-floor-qc-notes" className="text-xs text-gray-600">Notes (optional)</label>
                          <textarea id="shop-floor-qc-notes" maxLength={2000} rows={2} className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qcNotes} onChange={(event) => setQCNotes(event.target.value)} />
                        </div>
                        <button type="button" onClick={() => qcCheckpointMut.mutate(selectedWO.work_order_id)} disabled={!hasActiveSession || !canExecuteOnSelectedLine || !canRecordQC || !qcCheckpointName.trim() || !qcResult || isAnyPending || queueUnavailable} className="w-full min-h-12 py-2 bg-indigo-700 text-white rounded-lg font-semibold disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-800">
                          {qcCheckpointMut.isPending ? "RECORDING…" : "Record QC Checkpoint"}
                        </button>
                        <p className="text-xs text-gray-500">No product limits are assumed here. The observed value and selected result are retained as the authenticated quality user&apos;s checkpoint record.</p>
                      </div> : <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700" role="status">Quality edit permission in this product category is required to record checkpoints.</p>}
                    </>
                  )}
                </div>
              )}

              {activeTab === "finish" && (
                <div className="space-y-2">
                  {selectedWO.qc_required_flag && selectedWO.qc_passed !== true && (
                    <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900" role="status">Required QC checkpoints must all pass before this work order can be completed.</p>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div>
                      <label htmlFor="shop-floor-final-good-qty" className="text-xs text-gray-600">Final Good Qty</label>
                      <input id="shop-floor-final-good-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qtyGood} onChange={(e) => setQtyGood(e.target.value)} min="0" step="any" />
                    </div>
                    <div>
                      <label htmlFor="shop-floor-final-scrap-qty" className="text-xs text-gray-600">Scrap</label>
                      <input id="shop-floor-final-scrap-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qtyScrap} onChange={(e) => setQtyScrap(e.target.value)} min="0" step="any" />
                    </div>
                    <div>
                      <label htmlFor="shop-floor-final-rework-qty" className="text-xs text-gray-600">Rework</label>
                      <input id="shop-floor-final-rework-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={qtyRework} onChange={(e) => setQtyRework(e.target.value)} min="0" step="any" />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label htmlFor="shop-floor-finish-scrap-category" className="text-xs text-gray-600">Waste classification (optional)</label>
                      <select id="shop-floor-finish-scrap-category" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={scrapCategory} onChange={(e) => setScrapCategory(e.target.value as "" | "normal" | "abnormal")}>
                        <option value="">Not classified</option>
                        <option value="normal">Normal</option>
                        <option value="abnormal">Abnormal</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="shop-floor-finish-scrap-reason" className="text-xs text-gray-600">Scrap / waste reason (optional)</label>
                      <input id="shop-floor-finish-scrap-reason" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={scrapReason} onChange={(e) => setScrapReason(e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <label htmlFor="shop-floor-actual-runtime" className="text-xs text-gray-600">Actual run time (minutes, optional)</label>
                    <input id="shop-floor-actual-runtime" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-2 py-1.5 text-base" value={runTimeActual} onChange={(e) => setRunTimeActual(e.target.value)} min="0" step="any" />
                  </div>
                  <button type="button" onClick={() => finishMut.mutate(selectedWO.work_order_id)} disabled={!hasActiveSession || !canExecuteOnSelectedLine || (selectedWO.qc_required_flag && selectedWO.qc_passed !== true) || !isValidNonNegativeNumber(qtyGood) || !isValidNonNegativeNumber(qtyScrap) || !isValidNonNegativeNumber(qtyRework) || (runTimeActual.trim() !== "" && !isValidNonNegativeNumber(runTimeActual)) || isAnyPending || queueUnavailable} className="w-full min-h-14 py-3 bg-teal-700 text-white rounded-xl font-bold text-base disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-800">
                    {finishMut.isPending ? "COMPLETING…" : "FINISH WORK ORDER"}
                  </button>
                </div>
              )}

              {activeTab === "scrap" && (
                <div className="space-y-2">
                  <label htmlFor="shop-floor-record-scrap-qty" className="text-xs text-gray-600">Scrap / waste quantity</label>
                  <input id="shop-floor-record-scrap-qty" type="number" inputMode="decimal" className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base" value={qtyScrap} onChange={(e) => setQtyScrap(e.target.value)} min="0" step="any" />
                  <label htmlFor="shop-floor-scrap-category" className="text-xs text-gray-600">Waste classification (optional)</label>
                  <select id="shop-floor-scrap-category" className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base" value={scrapCategory} onChange={(e) => setScrapCategory(e.target.value as "" | "normal" | "abnormal")}>
                    <option value="">Not classified</option>
                    <option value="normal">Normal</option>
                    <option value="abnormal">Abnormal</option>
                  </select>
                  <label htmlFor="shop-floor-scrap-reason" className="text-xs text-gray-600">Scrap / waste reason (optional)</label>
                  <input id="shop-floor-scrap-reason" className="w-full min-h-11 border border-gray-200 rounded-lg px-3 py-2 text-base" value={scrapReason} onChange={(e) => setScrapReason(e.target.value)} />
                  <button type="button" onClick={() => scrapMut.mutate({ woId: selectedWO.work_order_id, qty: Number(qtyScrap) })} disabled={!hasActiveSession || !canExecuteOnSelectedLine || !isValidNonNegativeNumber(qtyScrap) || Number(qtyScrap) <= 0 || isAnyPending || queueUnavailable} className="w-full min-h-12 py-2 bg-red-700 text-white rounded-lg font-medium disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-800">
                    {scrapMut.isPending ? "RECORDING…" : "Record Scrap"}
                  </button>
                </div>
              )}

              {activeTab === "note" && (
                <div className="space-y-2">
                  <label htmlFor="shop-floor-note" className="text-xs text-gray-600">Work-order note</label>
                  <textarea id="shop-floor-note" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-base" rows={3} placeholder="Enter note…" value={remarkText} onChange={(e) => setRemarkText(e.target.value)} />
                  <button type="button" onClick={() => noteMut.mutate(selectedWO.work_order_id)} disabled={!hasActiveSession || !canExecuteOnSelectedLine || !remarkText.trim() || isAnyPending || queueUnavailable} className="w-full min-h-12 py-2 bg-gray-800 text-white rounded-lg font-medium disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900">
                    {noteMut.isPending ? "SAVING…" : "Add Note"}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Downtime Modal */}
      {showDowntime && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-2 sm:p-4" onKeyDown={(event) => { if (event.key === "Escape" && !dtMut.isPending) setShowDowntime(false); }} onMouseDown={(event) => { if (event.target === event.currentTarget && !dtMut.isPending) setShowDowntime(false); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="shop-floor-downtime-title" className="bg-white rounded-2xl p-4 sm:p-6 w-full max-w-sm shadow-xl space-y-4">
            <h2 id="shop-floor-downtime-title" className="text-lg font-bold text-red-700">Log Downtime</h2>
            <ShopFloorConnectionNotice
              state={connection.state}
              onRefresh={() => void refreshShopFloorState()}
              refreshing={refreshingState}
              forceRefresh={Boolean(feedback?.requiresRefresh)}
            />
            <div>
              <label htmlFor="shop-floor-downtime-category" className="text-xs text-gray-600">Category</label>
              <select id="shop-floor-downtime-category" className="w-full min-h-12 border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5" value={dtCategory} onChange={(e) => setDtCategory(e.target.value)}>
                {DOWNTIME_CATS.map((c) => <option key={c} value={c}>{DOWNTIME_CAT_LABEL[c as keyof typeof DOWNTIME_CAT_LABEL] || c}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="shop-floor-downtime-reason" className="text-xs text-gray-600">Root Reason (optional)</label>
              <textarea id="shop-floor-downtime-reason" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-base mt-0.5" rows={2} value={dtReason} onChange={(e) => setDtReason(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => setShowDowntime(false)} disabled={dtMut.isPending} className="flex-1 min-h-12 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button type="button" onClick={() => dtMut.mutate()} disabled={dtMut.isPending || !hasActiveSession || !canExecuteOnSelectedLine || queueUnavailable} className="flex-1 min-h-12 py-2 bg-red-700 text-white rounded-lg text-sm font-medium disabled:opacity-40">
                {dtMut.isPending ? "SAVING…" : "Start Downtime"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function isValidNonNegativeNumber(value: string) {
  if (!value.trim()) return false;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0;
}
