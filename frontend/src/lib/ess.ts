const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/ess`;

export type ESSAccountStatus = "active" | "inactive" | "suspended";
export type EmploymentStatus = "active" | "on_leave" | "resigned" | "terminated" | "probation";
export type LeaveStatus = "draft" | "submitted" | "approved" | "rejected" | "cancelled";
export type AttendanceStatus = "present" | "absent" | "late" | "half_day" | "on_leave" | "holiday" | "work_from_home";
export type ESSRequestType = "leave" | "expense" | "profile_update" | "document" | "certificate" | "payslip" | "other";
export type ESSRequestStatus = "draft" | "submitted" | "in_review" | "approved" | "rejected" | "closed";
export type NotificationType = "leave_approved" | "leave_rejected" | "request_update" | "hr_announcement" | "reminder" | "system" | "payslip_ready";
export type ESSDocumentType = "payslip" | "contract" | "offer_letter" | "experience_cert" | "salary_cert" | "hr_letter" | "appraisal" | "other";
export type ESSAIAgentType = "employee_assistant" | "hr_support_assistant";
export type ESSAIRecStatus = "pending" | "acknowledged" | "dismissed" | "actioned";

export interface ESSAccount {
  ess_account_id: string;
  employee_id: string;
  email: string;
  status: ESSAccountStatus;
  last_login?: string;
  created_at: string;
}

export interface ESSProfile {
  profile_id: string;
  employee_id: string;
  full_name: string;
  email: string;
  personal_email?: string;
  phone?: string;
  address?: string;
  department_name?: string;
  manager_name?: string;
  job_title?: string;
  joining_date?: string;
  employment_status: EmploymentStatus;
  grade?: string;
  profile_photo?: string;
  national_id?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  created_at: string;
  updated_at: string;
}

export interface ESSLeaveType {
  leave_type_id: string;
  type_code: string;
  type_name: string;
  annual_entitlement_days: number;
  carry_forward_max: number;
  requires_approval: boolean;
  requires_document: boolean;
  paid_leave: boolean;
  active_flag: boolean;
  created_at: string;
}

export interface ESSLeaveBalance {
  balance_id: string;
  employee_id: string;
  leave_type_id: string;
  year: number;
  entitled_days: number;
  taken_days: number;
  pending_days: number;
  carried_forward: number;
  adjusted_days: number;
  available_days: number;
}

export interface ESSLeaveRequest {
  leave_request_id: string;
  leave_request_no: string;
  employee_id: string;
  leave_type_id: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  reason?: string;
  attachment_ref?: string;
  status: LeaveStatus;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface ESSAttendanceRecord {
  attendance_id: string;
  employee_id: string;
  attendance_date: string;
  check_in?: string;
  check_out?: string;
  status: AttendanceStatus;
  hours_worked?: number;
  overtime_hours: number;
  late_minutes: number;
  notes?: string;
  created_at: string;
}

export interface ESSRequest {
  request_id: string;
  request_no: string;
  employee_id: string;
  request_type: ESSRequestType;
  request_date: string;
  subject: string;
  description?: string;
  attachment_ref?: string;
  status: ESSRequestStatus;
  approved_by?: string;
  approved_at?: string;
  hr_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ESSNotification {
  notification_id: string;
  employee_id: string;
  notification_type: NotificationType;
  title: string;
  body: string;
  reference_id?: string;
  read_flag: boolean;
  read_at?: string;
  created_at: string;
}

export interface ESSDocument {
  document_id: string;
  employee_id: string;
  document_type: ESSDocumentType;
  document_name: string;
  document_ref?: string;
  period?: string;
  visible_to_employee: boolean;
  created_at: string;
}

export interface ESSDashboard {
  employee_name: string;
  job_title?: string;
  department_name?: string;
  days_since_joining: number;
  pending_leave_requests: number;
  unread_notifications: number;
  pending_requests: number;
  annual_leave_available: number;
  attendance_this_month: number;
  documents_count: number;
}

export interface ESSAIRecommendation {
  rec_id: string;
  agent_type: ESSAIAgentType;
  subject: string;
  body: string;
  ref_employee_id?: string;
  status: ESSAIRecStatus;
  created_at: string;
}

// ── Color / label maps ────────────────────────────────────────────────────────

export const LEAVE_STATUS_COLOR: Record<LeaveStatus, string> = {
  draft: "bg-slate-500/20 text-slate-400",
  submitted: "bg-blue-500/20 text-blue-300",
  approved: "bg-emerald-500/20 text-emerald-300",
  rejected: "bg-red-500/20 text-red-300",
  cancelled: "bg-slate-700/20 text-slate-500",
};

export const ATTENDANCE_STATUS_COLOR: Record<AttendanceStatus, string> = {
  present: "bg-emerald-500/20 text-emerald-300",
  absent: "bg-red-500/20 text-red-300",
  late: "bg-amber-500/20 text-amber-300",
  half_day: "bg-orange-500/20 text-orange-300",
  on_leave: "bg-blue-500/20 text-blue-300",
  holiday: "bg-purple-500/20 text-purple-300",
  work_from_home: "bg-teal-500/20 text-teal-300",
};

export const REQUEST_STATUS_COLOR: Record<ESSRequestStatus, string> = {
  draft: "bg-slate-500/20 text-slate-400",
  submitted: "bg-blue-500/20 text-blue-300",
  in_review: "bg-amber-500/20 text-amber-300",
  approved: "bg-emerald-500/20 text-emerald-300",
  rejected: "bg-red-500/20 text-red-300",
  closed: "bg-slate-700/20 text-slate-500",
};

export const NOTIF_TYPE_ICON: Record<NotificationType, string> = {
  leave_approved: "✅",
  leave_rejected: "❌",
  request_update: "📋",
  hr_announcement: "📢",
  reminder: "🔔",
  system: "⚙️",
  payslip_ready: "💰",
};

export const AI_AGENT_LABEL: Record<ESSAIAgentType, string> = {
  employee_assistant: "Employee Assistant",
  hr_support_assistant: "HR Support Assistant",
};

// ── API client ────────────────────────────────────────────────────────────────

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const essApi = {
  // Auth
  login: (email: string, password: string) =>
    api<{ ess_account_id: string; employee_id: string; email: string; token: string }>("/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  createAccount: (d: object) => api<ESSAccount>("/accounts", { method: "POST", body: JSON.stringify(d) }),
  listAccounts: () => api<ESSAccount[]>("/accounts"),

  // Profile
  upsertProfile: (d: object) => api<ESSProfile>("/profiles", { method: "POST", body: JSON.stringify(d) }),
  getProfile: (employeeId: string) => api<ESSProfile>(`/profiles/${employeeId}`),
  updateProfile: (employeeId: string, d: object) =>
    api<ESSProfile>(`/profiles/${employeeId}`, { method: "PATCH", body: JSON.stringify(d) }),

  // Leave types
  listLeaveTypes: () => api<ESSLeaveType[]>("/leave-types"),
  seedLeaveTypes: () => api<ESSLeaveType[]>("/leave-types/seed", { method: "POST" }),

  // Leave balances
  getLeaveBalances: (employeeId: string, year?: number) =>
    api<ESSLeaveBalance[]>(`/leave-balances/${employeeId}${year ? `?year=${year}` : ""}`),
  upsertLeaveBalance: (d: object) => api<ESSLeaveBalance>("/leave-balances", { method: "POST", body: JSON.stringify(d) }),

  // Leave requests
  listLeaveRequests: (p?: { employee_id?: string; status?: LeaveStatus }) => {
    const q = new URLSearchParams();
    if (p?.employee_id) q.set("employee_id", p.employee_id);
    if (p?.status) q.set("status", p.status);
    return api<ESSLeaveRequest[]>(`/leave-requests?${q}`);
  },
  createLeaveRequest: (d: object) => api<ESSLeaveRequest>("/leave-requests", { method: "POST", body: JSON.stringify(d) }),
  submitLeaveRequest: (id: string) =>
    api<ESSLeaveRequest>(`/leave-requests/${id}/submit`, { method: "POST" }),
  approveLeave: (id: string, d: object) =>
    api<ESSLeaveRequest>(`/leave-requests/${id}/approve`, { method: "POST", body: JSON.stringify(d) }),
  rejectLeave: (id: string, d: object) =>
    api<ESSLeaveRequest>(`/leave-requests/${id}/reject`, { method: "POST", body: JSON.stringify(d) }),
  cancelLeave: (id: string, employeeId: string) =>
    api<ESSLeaveRequest>(`/leave-requests/${id}/cancel?employee_id=${employeeId}`, { method: "POST" }),

  // Attendance
  listAttendance: (employeeId: string, month?: number, year?: number) => {
    const q = new URLSearchParams();
    if (month) q.set("month", String(month));
    if (year) q.set("year", String(year));
    return api<ESSAttendanceRecord[]>(`/attendance/${employeeId}?${q}`);
  },
  upsertAttendance: (d: object) => api<ESSAttendanceRecord>("/attendance", { method: "POST", body: JSON.stringify(d) }),
  attendanceSummary: (employeeId: string, month: number, year: number) =>
    api<object>(`/attendance/${employeeId}/summary?month=${month}&year=${year}`),

  // Requests
  listRequests: (p?: { employee_id?: string; status?: ESSRequestStatus }) => {
    const q = new URLSearchParams();
    if (p?.employee_id) q.set("employee_id", p.employee_id);
    if (p?.status) q.set("status", p.status);
    return api<ESSRequest[]>(`/requests?${q}`);
  },
  createRequest: (d: object) => api<ESSRequest>("/requests", { method: "POST", body: JSON.stringify(d) }),
  submitRequest: (id: string) => api<ESSRequest>(`/requests/${id}/submit`, { method: "POST" }),
  reviewRequest: (id: string, d: object) =>
    api<ESSRequest>(`/requests/${id}/review`, { method: "PATCH", body: JSON.stringify(d) }),

  // Documents
  listDocuments: (employeeId: string, docType?: string) =>
    api<ESSDocument[]>(`/documents/${employeeId}${docType ? `?doc_type=${docType}` : ""}`),
  uploadDocument: (d: object) => api<ESSDocument>("/documents", { method: "POST", body: JSON.stringify(d) }),

  // Notifications
  listNotifications: (employeeId: string, unreadOnly = false) =>
    api<ESSNotification[]>(`/notifications/${employeeId}${unreadOnly ? "?unread_only=true" : ""}`),
  markRead: (notifId: string, employeeId: string) =>
    api<ESSNotification>(`/notifications/${notifId}/read?employee_id=${employeeId}`, { method: "POST" }),
  markAllRead: (employeeId: string) =>
    api<{ marked_read: number }>(`/notifications/${employeeId}/mark-all-read`, { method: "POST" }),

  // Dashboard
  getDashboard: (employeeId: string) => api<ESSDashboard>(`/dashboard/${employeeId}`),

  // Activity
  getActivity: (employeeId: string) => api<object[]>(`/activity/${employeeId}`),

  // AI
  runEmployeeAssistant: () => api<{ generated: number }>("/ai/run-employee-assistant", { method: "POST" }),
  runHRSupportAssistant: () => api<{ generated: number }>("/ai/run-hr-support-assistant", { method: "POST" }),
  listRecs: (status?: ESSAIRecStatus) =>
    api<ESSAIRecommendation[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackRec: (id: string, d: { status: ESSAIRecStatus; notes?: string }) =>
    api<ESSAIRecommendation>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
