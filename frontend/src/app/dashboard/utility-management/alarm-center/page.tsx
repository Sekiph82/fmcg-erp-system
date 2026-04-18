"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  alarmApi,
  type AlarmEvent,
  type AlarmSummary,
  type AlarmSeverity,
  type AlarmStatus,
  type UtilityType,
  SEVERITY_BG_CLASS,
  SEVERITY_SOFT_CLASS,
  STATUS_SOFT_CLASS,
  DETECTION_TYPE_LABELS,
  UTILITY_TYPE_LABELS,
  UTILITY_TYPE_ICONS,
  SEVERITY_ICONS,
} from "@/lib/utilityAlarm";
import {
  integrationApi,
  type MaintenanceActionRequest,
} from "@/lib/utilityIntegration";

// ── Helpers ───────────────────────────────────────────────────────────────────

const UTILITY_TYPES: UtilityType[] = [
  "ELECTRICITY","WATER","SOFT_WATER","PROCESS_WATER","STEAM","COMPRESSED_AIR",
  "SOLAR","NATURAL_GAS","WASTEWATER","DIESEL","CHILLED_WATER","OTHER",
];

const SEVERITIES: AlarmSeverity[] = ["INFO","WARNING","ALERT","CRITICAL"];
const STATUSES: AlarmStatus[] = ["ACTIVE","ACKNOWLEDGED","RESOLVED","SUPPRESSED"];

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function fmtDatetime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function fmtNum(n?: number | null, dp = 2): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

const inputCls = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500";

// ── Severity Badge ─────────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: AlarmSeverity }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold ${SEVERITY_BG_CLASS[severity]}`}>
      <span>{SEVERITY_ICONS[severity]}</span>
      <span>{severity}</span>
    </span>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: AlarmStatus }) {
  const labels: Record<AlarmStatus, string> = {
    ACTIVE:       "Active",
    ACKNOWLEDGED: "Acknowledged",
    RESOLVED:     "Resolved",
    SUPPRESSED:   "Suppressed",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${STATUS_SOFT_CLASS[status]}`}>
      {labels[status]}
    </span>
  );
}

// ── Summary Banner ─────────────────────────────────────────────────────────────

function SummaryBanner({
  summary,
  onFilter,
}: {
  summary: AlarmSummary | undefined;
  onFilter: (type: "severity" | "status", value: string) => void;
}) {
  const cards = [
    {
      label: "Critical",
      count: summary?.critical_count ?? 0,
      colorClass: "border-red-400 bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-400",
      onClick: () => onFilter("severity", "CRITICAL"),
    },
    {
      label: "Alert",
      count: summary?.alert_count ?? 0,
      colorClass: "border-orange-400 bg-orange-50 dark:bg-orange-950/20 text-orange-700 dark:text-orange-400",
      onClick: () => onFilter("severity", "ALERT"),
    },
    {
      label: "Warning",
      count: summary?.warning_count ?? 0,
      colorClass: "border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20 text-yellow-700 dark:text-yellow-400",
      onClick: () => onFilter("severity", "WARNING"),
    },
    {
      label: "Info",
      count: summary?.info_count ?? 0,
      colorClass: "border-blue-400 bg-blue-50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-400",
      onClick: () => onFilter("severity", "INFO"),
    },
    {
      label: "Acknowledged",
      count: summary?.total_acknowledged ?? 0,
      colorClass: "border-gray-300 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
      onClick: () => onFilter("status", "ACKNOWLEDGED"),
    },
    {
      label: "Active Total",
      count: summary?.total_active ?? 0,
      colorClass: "border-red-300 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300",
      onClick: () => onFilter("status", "ACTIVE"),
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map(card => (
        <button
          key={card.label}
          onClick={card.onClick}
          className={`rounded-xl border-2 p-4 text-left transition-opacity hover:opacity-80 ${card.colorClass}`}
        >
          <p className="text-xs font-medium opacity-70">{card.label}</p>
          <p className="text-2xl font-bold mt-1">{card.count}</p>
        </button>
      ))}
    </div>
  );
}

// ── Acknowledge Modal ─────────────────────────────────────────────────────────

function AcknowledgeModal({
  event,
  onClose,
  onAck,
  saving,
}: {
  event: AlarmEvent;
  onClose: () => void;
  onAck: (notes?: string) => void;
  saving: boolean;
}) {
  const [notes, setNotes] = useState("");
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Acknowledge Alarm</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Event <strong>{event.event_no}</strong> — {event.rule_name}
        </p>
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Notes (optional)</label>
          <textarea
            className={inputCls + " w-full resize-none"}
            rows={3}
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Add acknowledgment notes…"
          />
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">Cancel</button>
          <button
            onClick={() => onAck(notes || undefined)}
            disabled={saving}
            className="px-4 py-2 text-sm bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 font-medium"
          >
            {saving ? "Acknowledging…" : "Acknowledge"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Resolve Modal ─────────────────────────────────────────────────────────────

function ResolveModal({
  event,
  onClose,
  onResolve,
  saving,
}: {
  event: AlarmEvent;
  onClose: () => void;
  onResolve: (payload: { root_cause: string; corrective_action: string; notes?: string }) => void;
  saving: boolean;
}) {
  const [rootCause, setRootCause] = useState("");
  const [correctiveAction, setCorrectiveAction] = useState("");
  const [notes, setNotes] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onResolve({ root_cause: rootCause, corrective_action: correctiveAction, notes: notes || undefined });
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Mark as Resolved</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Event <strong>{event.event_no}</strong> — {event.rule_name}
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Root Cause *</label>
            <textarea
              className={inputCls + " w-full resize-none"}
              rows={3}
              value={rootCause}
              onChange={e => setRootCause(e.target.value)}
              placeholder="Describe the root cause of this alarm…"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Corrective Action *</label>
            <textarea
              className={inputCls + " w-full resize-none"}
              rows={3}
              value={correctiveAction}
              onChange={e => setCorrectiveAction(e.target.value)}
              placeholder="What action was taken to resolve this?…"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Notes (optional)</label>
            <textarea
              className={inputCls + " w-full resize-none"}
              rows={2}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Additional notes…"
            />
          </div>
          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">Cancel</button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
            >
              {saving ? "Resolving…" : "Mark Resolved"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Maintenance Action Modal ──────────────────────────────────────────────────

function MaintenanceActionModal({
  event,
  onClose,
  onSuccess,
}: {
  event: AlarmEvent;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const qc = useQueryClient();
  const [actionType, setActionType] = useState<"PM_WORK_ORDER" | "BREAKDOWN">("PM_WORK_ORDER");
  const [description, setDescription] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");

  const mut = useMutation({
    mutationFn: (body: MaintenanceActionRequest) =>
      integrationApi.createMaintenanceAction(event.id, body),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["alarm-events"] });
      qc.invalidateQueries({ queryKey: ["alarm-summary"] });
      const ref = result.wo_no ?? result.breakdown_no ?? result.type;
      onSuccess(`Maintenance action created: ${ref}`);
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mut.mutate({
      action_type: actionType,
      description,
      scheduled_date: scheduledDate || undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Create Maintenance Action</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Event <strong>{event.event_no}</strong> — {event.rule_name}
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Action Type *
            </label>
            <select
              className={inputCls + " w-full"}
              value={actionType}
              onChange={e => setActionType(e.target.value as "PM_WORK_ORDER" | "BREAKDOWN")}
            >
              <option value="PM_WORK_ORDER">PM Work Order</option>
              <option value="BREAKDOWN">Breakdown Record</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Description *
            </label>
            <textarea
              className={inputCls + " w-full resize-none"}
              rows={3}
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Describe the maintenance required…"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Scheduled Date (optional)
            </label>
            <input
              type="date"
              className={inputCls + " w-full"}
              value={scheduledDate}
              onChange={e => setScheduledDate(e.target.value)}
            />
          </div>
          {mut.isError && (
            <p className="text-xs text-red-600 dark:text-red-400">
              Failed to create maintenance action. Please try again.
            </p>
          )}
          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mut.isPending || !description.trim()}
              className="px-4 py-2 text-sm bg-slate-700 text-white rounded-lg hover:bg-slate-800 disabled:opacity-50 font-medium"
            >
              {mut.isPending ? "Creating…" : "Create Action"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Event Detail Drawer ───────────────────────────────────────────────────────

function EventDetailDrawer({
  event,
  onClose,
  onAck,
  onResolve,
  onSuppress,
  onMaintenanceSuccess,
  ackSaving,
  resolveSaving,
  suppressSaving,
}: {
  event: AlarmEvent;
  onClose: () => void;
  onAck: (notes?: string) => void;
  onResolve: (payload: { root_cause: string; corrective_action: string; notes?: string }) => void;
  onSuppress: () => void;
  onMaintenanceSuccess: (msg: string) => void;
  ackSaving: boolean;
  resolveSaving: boolean;
  suppressSaving: boolean;
}) {
  const [showAckModal, setShowAckModal] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [showMaintenanceModal, setShowMaintenanceModal] = useState(false);

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-xl bg-white dark:bg-gray-800 shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-5 flex items-start justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            <SeverityBadge severity={event.severity} />
            <code className="text-sm font-mono font-bold text-gray-700 dark:text-gray-300">{event.event_no}</code>
            <StatusBadge status={event.status} />
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl font-bold ml-3">&times;</button>
        </div>

        <div className="p-5 space-y-5">
          {/* Alarm details */}
          <section>
            <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Alarm Details</h4>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div>
                <p className="text-xs text-gray-500">Alarm Name</p>
                <p className="font-semibold text-gray-900 dark:text-white">{event.rule_name ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Rule Code</p>
                <code className="text-xs font-mono bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-700 dark:text-gray-300">{event.rule_code ?? "—"}</code>
              </div>
              <div>
                <p className="text-xs text-gray-500">Utility Type</p>
                <p className="text-gray-800 dark:text-gray-200">
                  {event.alarm_type ? event.alarm_type : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Source Module</p>
                <p className="text-gray-800 dark:text-gray-200">{event.source_module ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Parameter</p>
                <code className="text-xs font-mono text-gray-700 dark:text-gray-300">{event.parameter ?? "—"}</code>
              </div>
              <div>
                <p className="text-xs text-gray-500">Detection Type</p>
                <p className="text-gray-800 dark:text-gray-200">
                  {event.detection_type ? DETECTION_TYPE_LABELS[event.detection_type as keyof typeof DETECTION_TYPE_LABELS] ?? event.detection_type : "—"}
                </p>
              </div>
              {event.device_name && (
                <div>
                  <p className="text-xs text-gray-500">Device</p>
                  <p className="text-gray-800 dark:text-gray-200">{event.device_name}</p>
                </div>
              )}
              {event.asset_name && (
                <div>
                  <p className="text-xs text-gray-500">Asset</p>
                  <p className="text-gray-800 dark:text-gray-200">{event.asset_name}</p>
                </div>
              )}
            </div>
          </section>

          {/* Values */}
          <section>
            <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Measurement Values</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-red-50 dark:bg-red-950/20 rounded-lg p-3">
                <p className="text-[10px] font-medium text-red-600 dark:text-red-400 uppercase">Triggered Value</p>
                <p className="text-lg font-bold text-red-700 dark:text-red-300 mt-0.5">
                  {fmtNum(event.triggered_value)}{event.threshold_unit ? ` ${event.threshold_unit}` : ""}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <p className="text-[10px] font-medium text-gray-500 uppercase">Expected Value</p>
                <p className="text-lg font-bold text-gray-700 dark:text-gray-300 mt-0.5">
                  {fmtNum(event.expected_value)}{event.threshold_unit ? ` ${event.threshold_unit}` : ""}
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <p className="text-[10px] font-medium text-gray-500 uppercase">Threshold</p>
                <p className="text-lg font-bold text-gray-700 dark:text-gray-300 mt-0.5">
                  {fmtNum(event.threshold_value)}{event.threshold_unit ? ` ${event.threshold_unit}` : ""}
                </p>
              </div>
              <div className={`rounded-lg p-3 ${Math.abs(event.deviation_pct ?? 0) > 10 ? "bg-orange-50 dark:bg-orange-950/20" : "bg-gray-50 dark:bg-gray-700/50"}`}>
                <p className="text-[10px] font-medium text-gray-500 uppercase">Deviation</p>
                <p className={`text-lg font-bold mt-0.5 ${Math.abs(event.deviation_pct ?? 0) > 10 ? "text-orange-700 dark:text-orange-300" : "text-gray-700 dark:text-gray-300"}`}>
                  {event.deviation_pct != null ? `${fmtNum(event.deviation_pct, 1)}%` : "—"}
                </p>
              </div>
            </div>
          </section>

          {/* Timeline */}
          <section>
            <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Timeline</h4>
            <div className="space-y-2">
              <div className="flex items-start gap-3">
                <span className="w-2 h-2 rounded-full bg-red-500 mt-1.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Triggered</p>
                  <p className="text-xs text-gray-500">{fmtDatetime(event.triggered_at)}</p>
                </div>
              </div>
              {event.acknowledged_at && (
                <div className="flex items-start gap-3">
                  <span className="w-2 h-2 rounded-full bg-yellow-500 mt-1.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      Acknowledged {event.acknowledged_by_name ? `by ${event.acknowledged_by_name}` : ""}
                    </p>
                    <p className="text-xs text-gray-500">{fmtDatetime(event.acknowledged_at)}</p>
                  </div>
                </div>
              )}
              {event.resolved_at && (
                <div className="flex items-start gap-3">
                  <span className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      Resolved {event.resolved_by_name ? `by ${event.resolved_by_name}` : ""}
                    </p>
                    <p className="text-xs text-gray-500">{fmtDatetime(event.resolved_at)}</p>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Assignment */}
          <section>
            <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Assignment</h4>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {event.assigned_to_name ?? <span className="text-gray-400 italic">Unassigned</span>}
            </p>
          </section>

          {/* Resolution details */}
          {(event.root_cause || event.corrective_action) && (
            <section>
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Resolution Details</h4>
              {event.root_cause && (
                <div className="mb-2">
                  <p className="text-xs text-gray-500 mb-1">Root Cause</p>
                  <p className="text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-700 rounded-lg p-3">{event.root_cause}</p>
                </div>
              )}
              {event.corrective_action && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Corrective Action</p>
                  <p className="text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-700 rounded-lg p-3">{event.corrective_action}</p>
                </div>
              )}
            </section>
          )}

          {/* Notes */}
          {event.notes && (
            <section>
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Notes</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg p-3">{event.notes}</p>
            </section>
          )}

          {/* Action buttons */}
          {event.status !== "RESOLVED" && event.status !== "SUPPRESSED" && (
            <section className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Actions</h4>
              <div className="flex flex-wrap gap-2">
                {event.status === "ACTIVE" && (
                  <>
                    <button
                      onClick={() => setShowAckModal(true)}
                      className="px-4 py-2 text-sm bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 font-medium"
                    >
                      Acknowledge
                    </button>
                    <button
                      onClick={onSuppress}
                      disabled={suppressSaving}
                      className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      {suppressSaving ? "Suppressing…" : "Suppress"}
                    </button>
                  </>
                )}
                {event.status === "ACKNOWLEDGED" && (
                  <>
                    <button
                      onClick={() => setShowResolveModal(true)}
                      className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
                    >
                      Mark Resolved
                    </button>
                    <button
                      onClick={onSuppress}
                      disabled={suppressSaving}
                      className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                    >
                      {suppressSaving ? "Suppressing…" : "Suppress"}
                    </button>
                  </>
                )}
                {/* Maintenance action — available for ACTIVE and ACKNOWLEDGED alarms */}
                {(event.status === "ACTIVE" || event.status === "ACKNOWLEDGED") && (
                  <button
                    onClick={() => setShowMaintenanceModal(true)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 font-medium"
                  >
                    {/* Wrench icon */}
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                        d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
                    </svg>
                    Create Maintenance Action
                  </button>
                )}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Nested modals */}
      {showAckModal && (
        <AcknowledgeModal
          event={event}
          onClose={() => setShowAckModal(false)}
          onAck={notes => { onAck(notes); setShowAckModal(false); }}
          saving={ackSaving}
        />
      )}
      {showResolveModal && (
        <ResolveModal
          event={event}
          onClose={() => setShowResolveModal(false)}
          onResolve={payload => { onResolve(payload); setShowResolveModal(false); }}
          saving={resolveSaving}
        />
      )}
      {showMaintenanceModal && (
        <MaintenanceActionModal
          event={event}
          onClose={() => setShowMaintenanceModal(false)}
          onSuccess={onMaintenanceSuccess}
        />
      )}
    </>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ message, type, onClose }: { message: string; type: "success" | "error" | "info"; onClose: () => void }) {
  const bg = type === "success" ? "bg-green-600" : type === "error" ? "bg-red-600" : "bg-blue-600";
  return (
    <div className={`fixed bottom-6 right-6 z-[100] flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white ${bg}`}>
      <span>{message}</span>
      <button onClick={onClose} className="font-bold text-white/80 hover:text-white">&times;</button>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AlarmCenterPage() {
  const qc = useQueryClient();

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [filterUtility, setFilterUtility] = useState<string>("");
  const [filterDateFrom, setFilterDateFrom] = useState<string>("");
  const [filterDateTo, setFilterDateTo] = useState<string>("");
  const [searchText, setSearchText] = useState<string>("");

  // UI state
  const [selectedEvent, setSelectedEvent] = useState<AlarmEvent | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  function showToast(message: string, type: "success" | "error" | "info" = "success") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  // Queries
  const summaryQ = useQuery({
    queryKey: ["alarm-summary"],
    queryFn: () => alarmApi.getEventsSummary(),
    refetchInterval: 30000,
  });

  const eventsQ = useQuery({
    queryKey: ["alarm-events", filterStatus, filterSeverity, filterUtility, filterDateFrom, filterDateTo],
    queryFn: () => alarmApi.listEvents({
      status: filterStatus ? filterStatus as AlarmStatus : undefined,
      severity: filterSeverity ? filterSeverity as AlarmSeverity : undefined,
      utility_type: filterUtility ? filterUtility as UtilityType : undefined,
      date_from: filterDateFrom || undefined,
      date_to: filterDateTo || undefined,
      limit: 200,
    }),
    refetchInterval: 30000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["alarm-events"] });
    qc.invalidateQueries({ queryKey: ["alarm-summary"] });
  };

  // Mutations
  const ackMut = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) => alarmApi.acknowledgeEvent(id, notes),
    onSuccess: (updated) => {
      invalidate();
      setSelectedEvent(updated);
      showToast("Alarm acknowledged", "success");
    },
    onError: () => showToast("Failed to acknowledge alarm", "error"),
  });

  const resolveMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { root_cause: string; corrective_action: string; notes?: string } }) =>
      alarmApi.resolveEvent(id, payload),
    onSuccess: (updated) => {
      invalidate();
      setSelectedEvent(updated);
      showToast("Alarm resolved", "success");
    },
    onError: () => showToast("Failed to resolve alarm", "error"),
  });

  const suppressMut = useMutation({
    mutationFn: (id: string) => alarmApi.suppressEvent(id),
    onSuccess: (updated) => {
      invalidate();
      setSelectedEvent(updated);
      showToast("Alarm suppressed", "info");
    },
    onError: () => showToast("Failed to suppress alarm", "error"),
  });

  const evaluateMut = useMutation({
    mutationFn: () => alarmApi.evaluate(),
    onSuccess: (data) => {
      invalidate();
      showToast(
        data.new_alarms > 0 ? `${data.new_alarms} new alarm${data.new_alarms !== 1 ? "s" : ""} detected` : "Evaluation complete — no new alarms",
        data.new_alarms > 0 ? "error" : "info",
      );
    },
    onError: () => showToast("Evaluation failed", "error"),
  });

  // Filter summary clicks
  function handleSummaryFilter(type: "severity" | "status", value: string) {
    if (type === "severity") {
      setFilterSeverity(prev => prev === value ? "" : value);
      setFilterStatus("");
    } else {
      setFilterStatus(prev => prev === value ? "" : value);
      setFilterSeverity("");
    }
  }

  // Filtered events (client-side search filter)
  const rawEvents = eventsQ.data ?? [];
  const events = searchText
    ? rawEvents.filter(e =>
        (e.event_no?.toLowerCase().includes(searchText.toLowerCase())) ||
        (e.rule_name?.toLowerCase().includes(searchText.toLowerCase())) ||
        (e.parameter?.toLowerCase().includes(searchText.toLowerCase())) ||
        (e.source_module?.toLowerCase().includes(searchText.toLowerCase()))
      )
    : rawEvents;

  const selectCls = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link href="/dashboard/utility-management/kpi-center" className="text-sm text-gray-500 hover:text-blue-600">← KPI Center</Link>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <Link href="/dashboard/utility-management/alarm-rules" className="text-sm text-gray-500 hover:text-blue-600">Alarm Rules →</Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" style={{ borderLeft: "4px solid #ef4444", paddingLeft: 12 }}>
            Alarm Center
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time monitoring — auto-refreshes every 30 seconds.
          </p>
        </div>
        <button
          onClick={() => evaluateMut.mutate()}
          disabled={evaluateMut.isPending}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
        >
          {evaluateMut.isPending ? "Running…" : "▶ Run Evaluation"}
        </button>
      </div>

      {/* Summary Banner */}
      <SummaryBanner summary={summaryQ.data} onFilter={handleSummaryFilter} />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Status</p>
          <select className={selectCls} value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">All Statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Severity</p>
          <select className={selectCls} value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}>
            <option value="">All Severities</option>
            {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Utility Type</p>
          <select className={selectCls} value={filterUtility} onChange={e => setFilterUtility(e.target.value)}>
            <option value="">All Types</option>
            {UTILITY_TYPES.map(u => <option key={u} value={u}>{UTILITY_TYPE_LABELS[u]}</option>)}
          </select>
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">From</p>
          <input type="date" className={selectCls} value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)} />
        </div>
        <div>
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">To</p>
          <input type="date" className={selectCls} value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)} />
        </div>
        <div className="flex-1 min-w-[200px]">
          <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Search</p>
          <input
            type="text"
            className={selectCls + " w-full"}
            placeholder="Search by event no, name, parameter…"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
          />
        </div>
        {(filterStatus || filterSeverity || filterUtility || filterDateFrom || filterDateTo || searchText) && (
          <div className="flex items-end">
            <button
              onClick={() => { setFilterStatus(""); setFilterSeverity(""); setFilterUtility(""); setFilterDateFrom(""); setFilterDateTo(""); setSearchText(""); }}
              className="px-3 py-2 text-xs text-gray-500 hover:text-red-600 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      {/* Event Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {eventsQ.isLoading ? (
          <p className="text-center text-gray-400 py-14 text-sm">Loading alarms…</p>
        ) : events.length === 0 ? (
          <div className="text-center py-14">
            <p className="text-3xl mb-3">✅</p>
            <p className="text-gray-500 dark:text-gray-400 font-medium">No alarms found</p>
            <p className="text-xs text-gray-400 mt-1">All clear for the selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Severity</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Event No</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Alarm / Parameter</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Utility / Module</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Detection</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Triggered</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Values</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status / Action</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Assigned To</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {events.map(event => (
                  <tr
                    key={event.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedEvent(event)}
                  >
                    {/* Severity */}
                    <td className="px-4 py-3">
                      <SeverityBadge severity={event.severity} />
                    </td>

                    {/* Event No */}
                    <td className="px-4 py-3">
                      <code className="text-xs font-mono text-gray-700 dark:text-gray-300">{event.event_no}</code>
                    </td>

                    {/* Alarm / Parameter */}
                    <td className="px-4 py-3 max-w-[180px]">
                      <p className="font-medium text-gray-900 dark:text-white text-xs truncate">{event.rule_name ?? "—"}</p>
                      {event.parameter && (
                        <code className="text-[10px] text-gray-400 font-mono">{event.parameter}</code>
                      )}
                    </td>

                    {/* Utility / Module */}
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        {event.alarm_type && (
                          <p className="text-xs text-gray-600 dark:text-gray-300">{event.alarm_type}</p>
                        )}
                        {event.source_module && (
                          <p className="text-[10px] text-gray-400">{event.source_module}</p>
                        )}
                      </div>
                    </td>

                    {/* Detection */}
                    <td className="px-4 py-3">
                      {event.detection_type ? (
                        <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                          {DETECTION_TYPE_LABELS[event.detection_type as keyof typeof DETECTION_TYPE_LABELS] ?? event.detection_type}
                        </span>
                      ) : "—"}
                    </td>

                    {/* Triggered */}
                    <td className="px-4 py-3">
                      <p className="text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap" title={fmtDatetime(event.triggered_at)}>
                        {relativeTime(event.triggered_at)}
                      </p>
                      <p className="text-[10px] text-gray-400">{new Date(event.triggered_at).toLocaleDateString()}</p>
                    </td>

                    {/* Values */}
                    <td className="px-4 py-3">
                      {event.triggered_value != null ? (
                        <div className="text-xs text-gray-700 dark:text-gray-300 space-y-0.5">
                          <p className="font-semibold text-red-600 dark:text-red-400">
                            {fmtNum(event.triggered_value, 1)}{event.threshold_unit ? ` ${event.threshold_unit}` : ""}
                          </p>
                          {event.expected_value != null && (
                            <p className="text-gray-400">
                              vs {fmtNum(event.expected_value, 1)}{event.threshold_unit ? ` ${event.threshold_unit}` : ""} expected
                            </p>
                          )}
                          {event.deviation_pct != null && (
                            <p className={`font-medium ${Math.abs(event.deviation_pct) > 10 ? "text-orange-500" : "text-gray-500"}`}>
                              {event.deviation_pct > 0 ? "+" : ""}{fmtNum(event.deviation_pct, 1)}%
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>

                    {/* Status / Action */}
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex flex-col items-start gap-1.5">
                        <StatusBadge status={event.status} />
                        {event.status === "ACTIVE" && (
                          <button
                            onClick={() => ackMut.mutate({ id: event.id })}
                            disabled={ackMut.isPending}
                            className="px-2 py-0.5 text-[10px] bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded font-medium hover:bg-yellow-200 disabled:opacity-50 whitespace-nowrap"
                          >
                            Acknowledge
                          </button>
                        )}
                        {event.status === "ACKNOWLEDGED" && (
                          <button
                            onClick={() => setSelectedEvent(event)}
                            className="px-2 py-0.5 text-[10px] bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded font-medium hover:bg-green-200 whitespace-nowrap"
                          >
                            Resolve
                          </button>
                        )}
                        {event.status === "RESOLVED" && (
                          <span className="text-green-500 text-xs">✓</span>
                        )}
                        {event.status === "SUPPRESSED" && (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </div>
                    </td>

                    {/* Assigned To */}
                    <td className="px-4 py-3">
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        {event.assigned_to_name ?? <span className="italic text-gray-400">Unassigned</span>}
                      </p>
                    </td>

                    {/* Detail icon */}
                    <td className="px-4 py-3">
                      <button
                        onClick={e => { e.stopPropagation(); setSelectedEvent(event); }}
                        className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-base"
                        title="View details"
                      >
                        ⓘ
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Count & refresh info */}
      {!eventsQ.isLoading && (
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>{events.length} event{events.length !== 1 ? "s" : ""} shown</span>
          <span>Auto-refreshes every 30s</span>
        </div>
      )}

      {/* Event Detail Drawer */}
      {selectedEvent && (
        <EventDetailDrawer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onAck={notes => ackMut.mutate({ id: selectedEvent.id, notes })}
          onResolve={payload => resolveMut.mutate({ id: selectedEvent.id, payload })}
          onSuppress={() => suppressMut.mutate(selectedEvent.id)}
          onMaintenanceSuccess={msg => showToast(msg, "success")}
          ackSaving={ackMut.isPending}
          resolveSaving={resolveMut.isPending}
          suppressSaving={suppressMut.isPending}
        />
      )}

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
