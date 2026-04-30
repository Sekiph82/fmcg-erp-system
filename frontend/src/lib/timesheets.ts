const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/timesheets`;

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type TimesheetStatus = "draft" | "submitted" | "manager_approved" | "rejected" | "finalized";
export type ActivityType = "regular" | "overtime" | "training" | "leave" | "meeting" | "admin" | "project" | "support" | "other";
export type ApprovalAction = "submitted" | "approved" | "rejected" | "finalized" | "resubmitted";
export type TSAIAgentType = "utilization_analyzer" | "anomaly_detector";
export type TSAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface TimesheetLine {
  timesheet_line_id: string;
  timesheet_id: string;
  work_date: string;
  project_id: string | null;
  project_name: string | null;
  task_id: string | null;
  task_name: string | null;
  activity_type: ActivityType;
  cost_center_id: string | null;
  cost_center_name: string | null;
  hours_worked: number;
  overtime_flag: boolean;
  billable_flag: boolean;
  notes: string | null;
  created_at: string;
}

export interface ApprovalLog {
  approval_id: string;
  timesheet_id: string;
  approver_id: string | null;
  approver_name: string | null;
  action: ApprovalAction;
  action_date: string;
  comments: string | null;
}

export interface TimesheetHeader {
  timesheet_id: string;
  employee_id: string;
  employee_name: string | null;
  department_id: string | null;
  department_name: string | null;
  manager_id: string | null;
  manager_name: string | null;
  period_start: string;
  period_end: string;
  status: TimesheetStatus;
  total_hours: number;
  overtime_hours: number;
  regular_hours: number;
  submitted_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  finalized_at: string | null;
  rejection_count: number;
  notes: string | null;
  created_at: string;
  lines: TimesheetLine[];
  approval_logs: ApprovalLog[];
}

export interface TimesheetDashboard {
  total_timesheets: number;
  draft: number;
  submitted: number;
  manager_approved: number;
  rejected: number;
  finalized: number;
  total_hours_this_period: number;
  overtime_hours_this_period: number;
  avg_hours_per_employee: number;
  pending_approval: number;
  employees_with_timesheets: number;
  project_hours: { project: string; hours: number }[];
}

export interface TSAIRec {
  rec_id: string;
  agent_type: TSAIAgentType;
  status: TSAIRecStatus;
  title: string;
  body: string;
  employee_id: string | null;
  department_id: string | null;
  timesheet_id: string | null;
  score: number | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Maps ──────────────────────────────────────────────────────────────────────

export const STATUS_COLOR: Record<TimesheetStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  manager_approved: "bg-purple-100 text-purple-700",
  rejected: "bg-red-100 text-red-700",
  finalized: "bg-green-100 text-green-700",
};

export const STATUS_LABEL: Record<TimesheetStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  manager_approved: "Manager Approved",
  rejected: "Rejected",
  finalized: "Finalized",
};

export const ACTIVITY_COLOR: Record<ActivityType, string> = {
  regular: "bg-blue-100 text-blue-700",
  overtime: "bg-orange-100 text-orange-700",
  training: "bg-purple-100 text-purple-700",
  leave: "bg-yellow-100 text-yellow-700",
  meeting: "bg-cyan-100 text-cyan-700",
  admin: "bg-gray-100 text-gray-600",
  project: "bg-green-100 text-green-700",
  support: "bg-teal-100 text-teal-700",
  other: "bg-gray-100 text-gray-500",
};

export const ACTIVITY_TYPES: ActivityType[] = [
  "regular","overtime","training","leave","meeting","admin","project","support","other"
];

export const ACTION_COLOR: Record<ApprovalAction, string> = {
  submitted: "text-blue-600",
  approved: "text-green-600",
  rejected: "text-red-600",
  finalized: "text-purple-600",
  resubmitted: "text-yellow-600",
};

// ── API ───────────────────────────────────────────────────────────────────────

export const timesheetsApi = {
  getDashboard: () => req<TimesheetDashboard>("/dashboard"),

  create: (d: object) => req<TimesheetHeader>("/", { method: "POST", body: JSON.stringify(d) }),
  list: (params?: { employee_id?: string; status?: string; period_start?: string; department_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.status) q.set("status", params.status);
    if (params?.period_start) q.set("period_start", params.period_start);
    if (params?.department_id) q.set("department_id", params.department_id);
    return req<TimesheetHeader[]>(`/?${q}`);
  },
  get: (id: string) => req<TimesheetHeader>(`/${id}`),
  submit: (id: string, d: object) => req<TimesheetHeader>(`/${id}/submit`, { method: "POST", body: JSON.stringify(d) }),
  approve: (id: string, d: object) => req<TimesheetHeader>(`/${id}/approve`, { method: "POST", body: JSON.stringify(d) }),
  reject: (id: string, d: object) => req<TimesheetHeader>(`/${id}/reject`, { method: "POST", body: JSON.stringify(d) }),
  finalize: (id: string, d: object) => req<TimesheetHeader>(`/${id}/finalize`, { method: "POST", body: JSON.stringify(d) }),

  addLine: (id: string, d: object) => req<TimesheetLine>(`/${id}/lines`, { method: "POST", body: JSON.stringify(d) }),
  updateLine: (lineId: string, d: object) => req<TimesheetLine>(`/lines/${lineId}`, { method: "PATCH", body: JSON.stringify(d) }),
  deleteLine: (lineId: string) => req<void>(`/lines/${lineId}`, { method: "DELETE" }),
  autoFill: (id: string, attendance: object[]) =>
    req<{ lines_added: number }>(`/${id}/auto-fill`, { method: "POST", body: JSON.stringify(attendance) }),

  approvalQueue: (department_id?: string) =>
    req<TimesheetHeader[]>(`/approval-queue/pending${department_id ? `?department_id=${department_id}` : ""}`),

  reportSummary: (period_start?: string) =>
    req<object>(`/reports/summary${period_start ? `?period_start=${period_start}` : ""}`),
  reportUtilization: (period_start?: string) =>
    req<object[]>(`/reports/utilization${period_start ? `?period_start=${period_start}` : ""}`),
  reportOvertime: (period_start?: string) =>
    req<object[]>(`/reports/overtime${period_start ? `?period_start=${period_start}` : ""}`),
  reportProjectTime: (project_id?: string) =>
    req<object[]>(`/reports/project-time${project_id ? `?project_id=${project_id}` : ""}`),
  reportActivitySummary: (period_start?: string) =>
    req<object[]>(`/reports/activity-summary${period_start ? `?period_start=${period_start}` : ""}`),
  payrollInput: (period_start: string, period_end: string) =>
    req<object[]>(`/payroll-input?period_start=${period_start}&period_end=${period_end}`),

  runUtilizationAnalyzer: () => req<TSAIRec[]>("/ai/run-utilization-analyzer", { method: "POST" }),
  runAnomalyDetector: () => req<TSAIRec[]>("/ai/run-anomaly-detector", { method: "POST" }),
  listAIRecs: (status?: string) => req<TSAIRec[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackAIRec: (id: string, d: object) => req<TSAIRec>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
