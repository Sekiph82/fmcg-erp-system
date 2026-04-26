const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/dunning`;

async function r<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type DunningActionType = "EMAIL" | "SMS" | "WHATSAPP" | "TASK" | "CALL_REMINDER" | "CREDIT_HOLD" | "MANAGER_ESCALATION" | "FINAL_NOTICE" | "LEGAL_REVIEW_FLAG" | "PORTAL_NOTIFICATION";
export type DunningCaseStatus = "OPEN" | "ON_HOLD" | "DISPUTED" | "PROMISE_TO_PAY" | "RESOLVED" | "CLOSED" | "ESCALATED";
export type DunningActionOutcome = "SENT" | "DELIVERED" | "FAILED" | "ACKNOWLEDGED" | "MANUAL_LOGGED" | "SKIPPED";
export type PTPStatus = "OPEN" | "PARTIALLY_MET" | "MET" | "BROKEN" | "CANCELLED";
export type DunningExceptionType = "HOLD_SKIP" | "CREDIT_HOLD_OVERRIDE" | "DISPUTED_INVOICE_EXCLUSION" | "COLLECTOR_OVERRIDE" | "CUSTOMER_SPECIAL_TERMS";
export type DunningAIAgentType = "COLLECTION_PRIORITIZATION" | "PAYMENT_RISK_MONITOR" | "EFFECTIVENESS_ASSISTANT";
export type DunningAIRecStatus = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

export interface DunningPolicy {
  id: string;
  policy_code: string;
  policy_name: string;
  active_flag: boolean;
  default_flag: boolean;
  applies_to_channel?: string;
  applies_to_region?: string;
  applies_to_segment?: string;
  auto_credit_hold_days?: number;
  auto_credit_hold_amount?: number;
  notes?: string;
  created_at?: string;
}

export interface DunningLevel {
  id: string;
  policy_id: string;
  level_no: number;
  level_name: string;
  days_overdue_from: number;
  days_overdue_to?: number;
  action_type: DunningActionType;
  template_code?: string;
  auto_send_flag: boolean;
  requires_approval_flag: boolean;
  apply_credit_hold_flag: boolean;
  escalate_to_role?: string;
  active_flag: boolean;
}

export interface DunningTemplate {
  id: string;
  template_code: string;
  language: string;
  subject: string;
  body_text: string;
  channel: DunningActionType;
  active_flag: boolean;
  notes?: string;
}

export interface DunningCase {
  id: string;
  case_no: string;
  customer_id: string;
  policy_id?: string;
  current_level_no: number;
  case_status: DunningCaseStatus;
  total_overdue_amount: number;
  oldest_due_date?: string;
  latest_action_date?: string;
  next_action_date?: string;
  assigned_collector_id?: string;
  credit_hold_flag: boolean;
  credit_hold_reason?: string;
  credit_hold_date?: string;
  priority_score: number;
  collector_notes?: string;
  notes?: string;
  created_at?: string;
}

export interface DunningCaseInvoice {
  id: string;
  case_id: string;
  invoice_id: string;
  invoice_number: string;
  invoice_due_date: string;
  invoice_balance_amount: number;
  days_overdue: number;
  dispute_flag: boolean;
  dispute_reason?: string;
  promise_to_pay_date?: string;
  excluded_from_dunning: boolean;
}

export interface DunningActionLog {
  id: string;
  case_id: string;
  level_no: number;
  action_type: DunningActionType;
  action_datetime: string;
  sent_by_system_flag: boolean;
  outcome_status: DunningActionOutcome;
  rendered_subject?: string;
  rendered_body?: string;
  notes?: string;
}

export interface DunningPTP {
  id: string;
  case_id: string;
  customer_id: string;
  promised_amount: number;
  promised_date: string;
  recorded_by: string;
  recorded_at: string;
  status: PTPStatus;
  notes?: string;
}

export interface DunningException {
  id: string;
  case_id: string;
  exception_type: DunningExceptionType;
  approved_by: string;
  start_date: string;
  end_date?: string;
  reason: string;
}

export interface DunningAIRec {
  id: string;
  case_id?: string;
  customer_id?: string;
  agent_type: DunningAIAgentType;
  status: DunningAIRecStatus;
  title: string;
  body: string;
  severity: string;
  reference_type?: string;
  reference_id?: string;
  actioned_by?: string;
  created_at?: string;
}

export interface AgingRow {
  customer_id: string;
  customer_name: string;
  customer_code: string;
  currency: string;
  current: number;
  overdue_1_7: number;
  overdue_8_14: number;
  overdue_15_30: number;
  overdue_31_60: number;
  overdue_61_90: number;
  overdue_90_plus: number;
  total_overdue: number;
  credit_hold: boolean;
  case_id?: string;
  priority_score: number;
}

export interface DunningDashboard {
  open_cases: number;
  total_overdue_amount: number;
  credit_hold_count: number;
  disputed_cases: number;
  open_ptps: number;
  broken_ptps: number;
}

// ── Color Maps ────────────────────────────────────────────────────────────────

export const CASE_STATUS_COLORS: Record<DunningCaseStatus, string> = {
  OPEN: "bg-blue-100 text-blue-800",
  ON_HOLD: "bg-yellow-100 text-yellow-800",
  DISPUTED: "bg-orange-100 text-orange-800",
  PROMISE_TO_PAY: "bg-purple-100 text-purple-800",
  RESOLVED: "bg-green-100 text-green-800",
  CLOSED: "bg-gray-100 text-gray-600",
  ESCALATED: "bg-red-100 text-red-800",
};

export const PTP_STATUS_COLORS: Record<PTPStatus, string> = {
  OPEN: "bg-blue-100 text-blue-800",
  PARTIALLY_MET: "bg-yellow-100 text-yellow-800",
  MET: "bg-green-100 text-green-800",
  BROKEN: "bg-red-100 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-600",
};

export const OUTCOME_COLORS: Record<DunningActionOutcome, string> = {
  SENT: "bg-blue-100 text-blue-800",
  DELIVERED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
  ACKNOWLEDGED: "bg-teal-100 text-teal-800",
  MANUAL_LOGGED: "bg-gray-100 text-gray-700",
  SKIPPED: "bg-gray-100 text-gray-500",
};

export const SEVERITY_COLORS: Record<string, string> = {
  INFO: "bg-blue-100 text-blue-800",
  WARNING: "bg-yellow-100 text-yellow-800",
  CRITICAL: "bg-red-100 text-red-800",
};

// ── API Client ────────────────────────────────────────────────────────────────

const j = { "Content-Type": "application/json" };
const post = (url: string, body: any) => fetch(url, { method: "POST", headers: j, body: JSON.stringify(body) });
const patch = (url: string, body: any) => fetch(url, { method: "PATCH", headers: j, body: JSON.stringify(body) });
const put = (url: string, body: any) => fetch(url, { method: "PUT", headers: j, body: JSON.stringify(body) });

export const dunningApi = {
  // Policies
  listPolicies: (activeOnly = false) => fetch(`${BASE}/policies?active_only=${activeOnly}`).then(r<DunningPolicy[]>),
  createPolicy: (body: Partial<DunningPolicy>) => post(`${BASE}/policies`, body).then(r<DunningPolicy>),
  updatePolicy: (id: string, body: Partial<DunningPolicy>) => put(`${BASE}/policies/${id}`, body).then(r<DunningPolicy>),
  listLevels: (policyId: string) => fetch(`${BASE}/policies/${policyId}/levels`).then(r<DunningLevel[]>),
  addLevel: (policyId: string, body: Partial<DunningLevel>) => post(`${BASE}/policies/${policyId}/levels`, body).then(r<DunningLevel>),

  // Templates
  listTemplates: () => fetch(`${BASE}/templates`).then(r<DunningTemplate[]>),
  createTemplate: (body: Partial<DunningTemplate>) => post(`${BASE}/templates`, body).then(r<DunningTemplate>),

  // Detection
  runDetection: () => post(`${BASE}/run-overdue-detection`, {}).then(r<any>),
  checkBrokenPTPs: () => post(`${BASE}/check-broken-ptps`, {}).then(r<any>),

  // Cases
  listCases: (params?: { status?: string; credit_hold?: boolean; limit?: number }) => {
    const p = new URLSearchParams();
    if (params?.status) p.set("status", params.status);
    if (params?.credit_hold !== undefined) p.set("credit_hold", String(params.credit_hold));
    if (params?.limit) p.set("limit", String(params.limit));
    return fetch(`${BASE}/cases?${p}`).then(r<DunningCase[]>);
  },
  getCase: (id: string) => fetch(`${BASE}/cases/${id}`).then(r<DunningCase>),
  updateNotes: (id: string, collector_notes: string) => patch(`${BASE}/cases/${id}/notes`, { collector_notes }).then(r<DunningCase>),
  assignCase: (id: string, collector_id: string) => post(`${BASE}/cases/${id}/assign`, { assigned_collector_id: collector_id }).then(r<DunningCase>),
  closeCase: (id: string) => post(`${BASE}/cases/${id}/close`, {}).then(r<DunningCase>),

  // Case Invoices
  getCaseInvoices: (caseId: string) => fetch(`${BASE}/cases/${caseId}/invoices`).then(r<DunningCaseInvoice[]>),
  setDispute: (caseId: string, body: { invoice_id: string; dispute_flag: boolean; dispute_reason?: string }) =>
    post(`${BASE}/cases/${caseId}/dispute`, body).then(r<DunningCaseInvoice>),

  // Actions
  sendReminder: (caseId: string, channel: DunningActionType, note?: string) =>
    post(`${BASE}/cases/${caseId}/send-reminder`, { channel, manual_note: note }).then(r<DunningActionLog>),
  addNote: (caseId: string, notes: string) =>
    post(`${BASE}/cases/${caseId}/add-note`, { notes }).then(r<DunningActionLog>),
  listActions: (caseId: string) => fetch(`${BASE}/cases/${caseId}/actions`).then(r<DunningActionLog[]>),

  // PTPs
  listPTPs: (caseId: string) => fetch(`${BASE}/cases/${caseId}/ptps`).then(r<DunningPTP[]>),
  createPTP: (caseId: string, body: { promised_amount: number; promised_date: string; recorded_by: string; notes?: string }) =>
    post(`${BASE}/cases/${caseId}/set-promise-to-pay`, body).then(r<DunningPTP>),
  updatePTP: (ptpId: string, status: PTPStatus, notes?: string) =>
    patch(`${BASE}/ptps/${ptpId}`, { status, notes }).then(r<DunningPTP>),

  // Exceptions
  listExceptions: (caseId: string) => fetch(`${BASE}/cases/${caseId}/exceptions`).then(r<DunningException[]>),
  createException: (caseId: string, body: Partial<DunningException>) =>
    post(`${BASE}/cases/${caseId}/exceptions`, body).then(r<DunningException>),

  // Credit Hold
  applyCreditHold: (caseId: string, reason: string, applied_by: string) =>
    post(`${BASE}/cases/${caseId}/apply-credit-hold`, { reason, applied_by }).then(r<DunningCase>),
  releaseCreditHold: (caseId: string, released_by: string, notes?: string) =>
    post(`${BASE}/cases/${caseId}/release-credit-hold`, { released_by, notes }).then(r<DunningCase>),

  // AI
  runAI: () => post(`${BASE}/ai/run`, {}).then(r<{ generated: number }>),
  listAIRecs: (caseId?: string) =>
    fetch(`${BASE}/ai/recommendations${caseId ? `?case_id=${caseId}` : ""}`).then(r<DunningAIRec[]>),
  ackAIRec: (recId: string, status: DunningAIRecStatus, actioned_by: string) =>
    post(`${BASE}/ai/recommendations/${recId}/ack`, { status, actioned_by }).then(r<DunningAIRec>),

  // Reports
  getDashboard: () => fetch(`${BASE}/reports/dashboard`).then(r<DunningDashboard>),
  getAging: () => fetch(`${BASE}/reports/aging`).then(r<AgingRow[]>),
  getEffectiveness: () => fetch(`${BASE}/reports/effectiveness`).then(r<any[]>),
  getWorkqueue: (collectorId?: string) =>
    fetch(`${BASE}/reports/workqueue${collectorId ? `?collector_id=${collectorId}` : ""}`).then(r<any[]>),
  getPTPFulfillment: () => fetch(`${BASE}/reports/ptp-fulfillment`).then(r<any>),
};
