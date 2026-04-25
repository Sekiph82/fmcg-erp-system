const BASE = "/api/v1/shop-floor";

// ── Types ──────────────────────────────────────────────────────────────────────

export type SFSessionStatus = "ACTIVE" | "IDLE" | "LOGGED_OUT" | "EXPIRED";

export type WOEventType =
  | "START" | "PAUSE" | "RESUME" | "FINISH"
  | "QTY_UPDATE" | "SCRAP" | "DOWNTIME_START" | "DOWNTIME_STOP"
  | "QC_TRIGGER" | "HELP_REQUEST" | "HANDOVER" | "NOTE" | "SUPERVISOR_OVERRIDE";

export type SFLiveStatus =
  | "WAITING" | "READY" | "ASSIGNED" | "RUNNING"
  | "PAUSED" | "BLOCKED" | "QC_HOLD" | "SUPERVISOR_REVIEW"
  | "COMPLETED" | "CANCELLED";

export type SFDowntimeCat =
  | "MACHINE_BREAKDOWN" | "MATERIAL_SHORTAGE" | "PACKAGING_SHORTAGE"
  | "QC_WAITING" | "CHANGEOVER" | "CLEANING" | "POWER_ISSUE"
  | "LABOR_SHORTAGE" | "SUPERVISOR_HOLD" | "MAINTENANCE_STOP"
  | "LABEL_MISMATCH" | "IT_ISSUE" | "OTHER";

export type SFImpactLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface SFSession {
  id: string;
  session_code: string;
  operator_id: string | null;
  operator_name: string;
  team_id: string | null;
  machine_id: string | null;
  line_id: string | null;
  work_center_id: string | null;
  shift_id: string | null;
  login_time: string;
  logout_time: string | null;
  current_work_order_id: string | null;
  status: SFSessionStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WOActivityLog {
  id: string;
  work_order_id: string;
  production_order_id: string | null;
  session_id: string | null;
  operator_name: string | null;
  line_id: string | null;
  event_type: WOEventType;
  timestamp_start: string;
  timestamp_end: string | null;
  duration_minutes: number | null;
  qty_good: number | null;
  qty_scrap: number | null;
  qty_rework: number | null;
  reason_code: string | null;
  remarks: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string;
}

export interface SFDowntimeLog {
  id: string;
  work_order_id: string | null;
  production_order_id: string | null;
  machine_id: string | null;
  machine_name: string | null;
  line_id: string | null;
  operator_name: string | null;
  start_time: string;
  end_time: string | null;
  duration_minutes: number | null;
  is_closed: boolean;
  downtime_category: SFDowntimeCat;
  root_reason: string | null;
  impact_level: SFImpactLevel;
  comments: string | null;
  created_at: string;
}

export interface ShiftHandover {
  id: string;
  line_id: string | null;
  work_center_id: string | null;
  shift_from_name: string | null;
  shift_to_name: string | null;
  outgoing_supervisor: string | null;
  incoming_supervisor: string | null;
  outgoing_operators: string[] | null;
  incoming_operators: string[] | null;
  open_work_orders: Record<string, unknown>[] | null;
  qty_completed: number | null;
  qty_remaining: number | null;
  issues_open: string[] | null;
  qc_pending_items: string[] | null;
  material_shortages: string[] | null;
  notes: string | null;
  handover_time: string;
  is_approved: boolean;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface SupervisorOverride {
  id: string;
  work_order_id: string | null;
  production_order_id: string | null;
  supervisor_name: string;
  override_type: string;
  reason: string | null;
  target_operator_name: string | null;
  approved_at: string;
  notes: string | null;
  created_at: string;
}

export interface LiveWOItem {
  id: string;
  work_order_id: string;
  production_order_id: string | null;
  order_no: string | null;
  step_sequence: number;
  step_name: string;
  work_center_id: string | null;
  line_id: string | null;
  planned_qty: number;
  completed_qty: number;
  scrap_qty: number;
  status: string;
  live_status: SFLiveStatus;
  started_at: string | null;
  planned_start: string | null;
  planned_end: string | null;
  product_name: string | null;
  batch_no: string | null;
  qc_required_flag: boolean;
  has_active_downtime: boolean;
  last_event: string | null;
  last_event_time: string | null;
  operator_name: string | null;
}

export interface LiveStatusResponse {
  total_work_orders: number;
  running: number;
  paused: number;
  waiting: number;
  qc_hold: number;
  active_sessions: number;
  active_downtime: number;
  alerts: Record<string, unknown>[];
  by_line: Record<string, unknown>;
  timestamp: string;
}

export interface SFDashboard {
  active_sessions: number;
  running_work_orders: number;
  paused_work_orders: number;
  qc_hold_count: number;
  active_downtime_count: number;
  help_requests_open: number;
  total_scrap_today: number;
  total_good_qty_today: number;
  pending_ai_recs: number;
  recent_handovers: ShiftHandover[];
  active_downtimes: SFDowntimeLog[];
  supervisor_overrides_today: number;
}

export interface SFAIRec {
  id: string;
  work_order_id: string | null;
  production_order_id: string | null;
  agent_type: string;
  status: string;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  confidence_score: number | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Color maps ─────────────────────────────────────────────────────────────────

export const LIVE_STATUS_COLOR: Record<SFLiveStatus, string> = {
  WAITING:           "bg-gray-100 text-gray-500",
  READY:             "bg-blue-100 text-blue-700",
  ASSIGNED:          "bg-indigo-100 text-indigo-700",
  RUNNING:           "bg-green-100 text-green-700",
  PAUSED:            "bg-yellow-100 text-yellow-700",
  BLOCKED:           "bg-red-100 text-red-700",
  QC_HOLD:           "bg-purple-100 text-purple-700",
  SUPERVISOR_REVIEW: "bg-orange-100 text-orange-700",
  COMPLETED:         "bg-teal-100 text-teal-700",
  CANCELLED:         "bg-gray-200 text-gray-400",
};

export const DOWNTIME_CAT_LABEL: Record<SFDowntimeCat, string> = {
  MACHINE_BREAKDOWN:  "Machine Breakdown",
  MATERIAL_SHORTAGE:  "Material Shortage",
  PACKAGING_SHORTAGE: "Packaging Shortage",
  QC_WAITING:         "QC Waiting",
  CHANGEOVER:         "Changeover",
  CLEANING:           "Cleaning",
  POWER_ISSUE:        "Power Issue",
  LABOR_SHORTAGE:     "Labor Shortage",
  SUPERVISOR_HOLD:    "Supervisor Hold",
  MAINTENANCE_STOP:   "Maintenance Stop",
  LABEL_MISMATCH:     "Label Mismatch",
  IT_ISSUE:           "IT Issue",
  OTHER:              "Other",
};

export const IMPACT_COLOR: Record<SFImpactLevel, string> = {
  LOW:      "bg-green-100 text-green-700",
  MEDIUM:   "bg-yellow-100 text-yellow-700",
  HIGH:     "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

// ── API client ─────────────────────────────────────────────────────────────────

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const sfApi = {
  // Dashboard & status
  getDashboard: () => req<SFDashboard>("/dashboard"),
  getLiveStatus: () => req<LiveStatusResponse>("/live-status"),
  getLiveQueue: (params?: { line_id?: string }) => {
    const qs = params?.line_id ? `?line_id=${params.line_id}` : "";
    return req<LiveWOItem[]>(`/live-queue${qs}`);
  },
  getAlerts: () => req<Record<string, unknown>[]>("/alerts"),

  // Sessions
  createSession: (body: Partial<SFSession> & { operator_name: string }) =>
    req<SFSession>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  listSessions: (status?: string) => {
    const qs = status ? `?status=${status}` : "";
    return req<SFSession[]>(`/sessions${qs}`);
  },
  getActiveSessions: () => req<SFSession[]>("/sessions/active"),
  logoutSession: (id: string) =>
    req<SFSession>(`/sessions/${id}/logout`, { method: "POST", body: "{}" }),

  // WO execution
  startWO: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/start`, { method: "POST", body: JSON.stringify(body) }),
  pauseWO: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/pause`, { method: "POST", body: JSON.stringify(body) }),
  resumeWO: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/resume`, { method: "POST", body: JSON.stringify(body) }),
  updateQty: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/update-qty`, { method: "POST", body: JSON.stringify(body) }),
  recordScrap: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/scrap`, { method: "POST", body: JSON.stringify(body) }),
  finishWO: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/finish`, { method: "POST", body: JSON.stringify(body) }),
  requestHelp: (woId: string, remarks: string, operatorName?: string) =>
    req<WOActivityLog>(`/work-orders/${woId}/help`, { method: "POST", body: JSON.stringify({ remarks, operator_name: operatorName }) }),
  triggerQC: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/qc-trigger`, { method: "POST", body: JSON.stringify(body) }),
  addNote: (woId: string, remarks: string, operatorName?: string) =>
    req<WOActivityLog>(`/work-orders/${woId}/note`, { method: "POST", body: JSON.stringify({ remarks, operator_name: operatorName }) }),
  getActivityLog: (woId: string) =>
    req<WOActivityLog[]>(`/work-orders/${woId}/activity`),

  // Downtime
  startDowntime: (body: Record<string, unknown>) =>
    req<SFDowntimeLog>("/downtime", { method: "POST", body: JSON.stringify(body) }),
  listDowntime: (params?: { is_closed?: boolean; line_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.is_closed !== undefined) qs.set("is_closed", String(params.is_closed));
    if (params?.line_id) qs.set("line_id", params.line_id);
    return req<SFDowntimeLog[]>(`/downtime${qs.toString() ? "?" + qs : ""}`);
  },
  stopDowntime: (id: string, comments?: string) =>
    req<SFDowntimeLog>(`/downtime/${id}/stop`, { method: "POST", body: JSON.stringify({ comments }) }),

  // Handovers
  createHandover: (body: Record<string, unknown>) =>
    req<ShiftHandover>("/handovers", { method: "POST", body: JSON.stringify(body) }),
  listHandovers: (lineId?: string) => {
    const qs = lineId ? `?line_id=${lineId}` : "";
    return req<ShiftHandover[]>(`/handovers${qs}`);
  },
  approveHandover: (id: string, approvedBy: string) =>
    req<ShiftHandover>(`/handovers/${id}/approve`, { method: "POST", body: JSON.stringify({ approved_by: approvedBy }) }),

  // Overrides
  createOverride: (body: Record<string, unknown>) =>
    req<SupervisorOverride>("/overrides", { method: "POST", body: JSON.stringify(body) }),
  listOverrides: () => req<SupervisorOverride[]>("/overrides"),

  // AI
  runAI: () => req<Record<string, number>>("/ai/run", { method: "POST", body: "{}" }),
  listAIRecs: (params?: { status?: string; agent_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.agent_type) qs.set("agent_type", params.agent_type);
    return req<SFAIRec[]>(`/ai/recs${qs.toString() ? "?" + qs : ""}`);
  },
  actionAIRec: (id: string, status: "ACCEPTED" | "REJECTED") =>
    req<SFAIRec>(`/ai/recs/${id}/action`, { method: "POST", body: JSON.stringify({ status }) }),
};
