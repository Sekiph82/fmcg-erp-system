import { apiFetch } from "@/lib/api";
const BASE = "/api/v1/shop-floor";

// ── Types ──────────────────────────────────────────────────────────────────────

export type SFSessionStatus = "ACTIVE" | "IDLE" | "LOGGED_OUT" | "EXPIRED";

export type WOEventType =
  | "START" | "PAUSE" | "RESUME" | "FINISH"
  | "QTY_UPDATE" | "SCRAP" | "DOWNTIME_START" | "DOWNTIME_STOP"
  | "QC_TRIGGER" | "QC_CHECKPOINT" | "MATERIAL_CONSUMPTION"
  | "HELP_REQUEST" | "HANDOVER" | "NOTE" | "SUPERVISOR_OVERRIDE";

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
  actor_user_id?: string | null;
  operator_id?: string | null;
  operator_name: string | null;
  team_id?: string | null;
  machine_id?: string | null;
  shift_id?: string | null;
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

export interface SFOperationMaterial {
  id: string;
  production_order_id: string;
  work_order_id: string;
  item_type: string;
  item_id: string | null;
  item_name: string | null;
  item_code: string | null;
  required_qty: number;
  reserved_qty: number;
  issued_qty: number;
  consumed_qty: number;
  returned_qty: number;
  scrapped_qty: number;
  uom: string;
  status: string;
  lot_numbers: string[] | null;
}

export interface SFDowntimeLog {
  id: string;
  work_order_id: string | null;
  production_order_id: string | null;
  session_id?: string | null;
  machine_id: string | null;
  machine_name: string | null;
  line_id: string | null;
  operator_name: string | null;
  operator_id?: string | null;
  team_id?: string | null;
  shift_id?: string | null;
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
  qc_passed: boolean | null;
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

const inMemoryIdempotencyKeys = new Map<string, string>();

export class ShopFloorRequestError extends Error {
  constructor(
    public readonly status: number | null,
    public readonly hasIdempotencyKey = false,
  ) {
    super(status === null ? "The Shop Floor server could not be reached." : `Shop Floor request failed (${status}).`);
    this.name = "ShopFloorRequestError";
  }
}

export function describeShopFloorError(error: unknown): { message: string; requiresRefresh: boolean } {
  const status = error instanceof ShopFloorRequestError ? error.status : null;
  if (status === 401) return { message: "Your sign-in has expired. Sign in again before continuing.", requiresRefresh: false };
  if (status === 403) return { message: "You do not have permission for this action. Contact a supervisor if you need access.", requiresRefresh: false };
  if (status === 409) return { message: "The server reports a conflict. Refresh the latest Shop Floor state and resolve it before retrying.", requiresRefresh: true };
  if (status !== null && status < 500) return { message: `The server rejected this request (${status}). Check the current record and your entries before trying again.`, requiresRefresh: false };
  const retryGuidance = error instanceof ShopFloorRequestError && error.hasIdempotencyKey
    ? "An unchanged retry reuses its request key."
    : "Confirm the latest session or record state before resubmitting."
  return {
    message: `The result is not confirmed. The server may have saved this action. Refresh Shop Floor state before deciding what to do. ${retryGuidance} Offline changes are not stored on this device.`,
    requiresRefresh: true,
  };
}

async function pendingExecutionIdempotencyKey(path: string, body: string): Promise<{ storageKey: string; key: string }> {
  const source = `${path}\n${body}`;
  const bytes = new TextEncoder().encode(source);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  const fingerprint = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join("");
  const storageKey = `shop-floor:idempotency:${fingerprint}`;
  let key: string | null = null;
  try {
    key = globalThis.sessionStorage.getItem(storageKey);
  } catch {
    key = inMemoryIdempotencyKeys.get(storageKey) || null;
  }
  if (!key) {
    key = globalThis.crypto.randomUUID();
    try {
      globalThis.sessionStorage.setItem(storageKey, key);
    } catch {
      inMemoryIdempotencyKeys.set(storageKey, key);
    }
  }
  return { storageKey, key };
}

function clearPendingExecutionIdempotencyKey(storageKey: string): void {
  inMemoryIdempotencyKeys.delete(storageKey);
  try {
    globalThis.sessionStorage.removeItem(storageKey);
  } catch {
    // The in-memory entry is still cleared when session storage is unavailable.
  }
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const method = (opts?.method || "GET").toUpperCase();
  const requestBody = typeof opts?.body === "string" ? opts.body : "";
  const idempotency = method === "POST" && (
    path.startsWith("/work-orders/") || path === "/downtime" || path.startsWith("/downtime/")
  )
    ? await pendingExecutionIdempotencyKey(path, requestBody)
    : null;
  const headers = new Headers(opts?.headers);
  headers.set("Content-Type", "application/json");
  if (idempotency) headers.set("Idempotency-Key", idempotency.key);
  let res: Response;
  try {
    res = await apiFetch(`${BASE}${path}`, {
      ...opts,
      headers,
    });
  } catch {
    throw new ShopFloorRequestError(null, idempotency !== null);
  }
  if (!res.ok) throw new ShopFloorRequestError(res.status, idempotency !== null);
  const result = await res.json();
  if (idempotency) clearPendingExecutionIdempotencyKey(idempotency.storageKey);
  return result;
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
  getSession: (id: string) => req<SFSession>(`/sessions/${id}`),
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
  requestHelp: (woId: string, remarks: string, operatorName?: string, sessionId?: string) =>
    req<WOActivityLog>(`/work-orders/${woId}/help`, { method: "POST", body: JSON.stringify({ remarks, operator_name: operatorName, session_id: sessionId }) }),
  triggerQC: (woId: string, body: Record<string, unknown>) =>
    req<WOActivityLog>(`/work-orders/${woId}/qc-trigger`, { method: "POST", body: JSON.stringify(body) }),
  addNote: (woId: string, remarks: string, operatorName?: string, sessionId?: string) =>
    req<WOActivityLog>(`/work-orders/${woId}/note`, { method: "POST", body: JSON.stringify({ remarks, operator_name: operatorName, session_id: sessionId }) }),
  getActivityLog: (woId: string) =>
    req<WOActivityLog[]>(`/work-orders/${woId}/activity`),
  getWorkOrderMaterials: (woId: string, sessionId: string) =>
    req<SFOperationMaterial[]>(`/work-orders/${woId}/materials?session_id=${encodeURIComponent(sessionId)}`),
  consumeWorkOrderMaterial: (
    woId: string,
    materialId: string,
    body: { qty: number; session_id: string; lot_no?: string },
  ) => req<SFOperationMaterial>(
    `/work-orders/${woId}/materials/${materialId}/consume`,
    { method: "POST", body: JSON.stringify(body) },
  ),
  getWorkOrderQCCheckpoints: (woId: string, sessionId: string) =>
    req<WOActivityLog[]>(`/work-orders/${woId}/qc-checkpoints?session_id=${encodeURIComponent(sessionId)}`),
  recordWorkOrderQCCheckpoint: (
    woId: string,
    body: {
      session_id: string;
      checkpoint_name: string;
      result: "PASS" | "FAIL";
      measured_value?: string;
      unit?: string;
      notes?: string;
    },
  ) => req<WOActivityLog>(`/work-orders/${woId}/qc-checkpoints`, {
    method: "POST",
    body: JSON.stringify(body),
  }),

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
