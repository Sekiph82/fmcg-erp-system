const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/expenses`;

export type ExpenseStatus = "draft" | "submitted" | "manager_approved" | "finance_approved" | "rejected" | "paid" | "cancelled";
export type ReimbursementMethod = "payroll" | "ap" | "bank" | "cash" | "manual";
export type AdvanceSettlementStatus = "open" | "partially_settled" | "settled" | "overdue";
export type PolicyViolationSeverity = "warning" | "block";
export type ExpAIAgentType = "risk_monitor" | "policy_optimizer" | "reimbursement_assistant";
export type ExpAIRecStatus = "pending" | "acknowledged" | "dismissed" | "actioned";

export interface ExpenseCategory {
  expense_category_id: string;
  category_code: string;
  category_name: string;
  default_gl_account_id?: string;
  default_cost_center_id?: string;
  receipt_required_flag: boolean;
  approval_required_flag: boolean;
  taxable_flag: boolean;
  daily_limit_amount?: number;
  monthly_limit_amount?: number;
  active_flag: boolean;
  notes?: string;
  created_at: string;
}

export interface ExpensePolicy {
  expense_policy_id: string;
  policy_name: string;
  category_id: string;
  employee_grade_id?: string;
  department_id?: string;
  max_amount_per_line?: number;
  max_amount_per_day?: number;
  max_amount_per_month?: number;
  receipt_required_above_amount?: number;
  approval_level_required: number;
  active_flag: boolean;
  notes?: string;
  created_at: string;
}

export interface ExpenseClaimLine {
  expense_line_id: string;
  expense_claim_id: string;
  expense_category_id: string;
  expense_date: string;
  description: string;
  vendor_name?: string;
  receipt_no?: string;
  claimed_amount: number;
  approved_amount?: number;
  tax_amount: number;
  currency: string;
  payment_method_used?: string;
  cost_center_id?: string;
  project_id?: string;
  customer_id?: string;
  sales_route_id?: string;
  attachment_ref?: string;
  policy_violation_flag: boolean;
  policy_violation_note?: string;
  policy_violation_severity?: PolicyViolationSeverity;
  line_status: string;
  notes?: string;
  created_at: string;
}

export interface ExpenseClaim {
  expense_claim_id: string;
  claim_no: string;
  employee_id: string;
  department_id?: string;
  claim_date: string;
  period_start?: string;
  period_end?: string;
  currency: string;
  total_claimed_amount: number;
  total_approved_amount: number;
  total_rejected_amount: number;
  advance_deducted: number;
  reimbursement_method: ReimbursementMethod;
  status: ExpenseStatus;
  submitted_at?: string;
  approved_by_manager?: string;
  manager_approved_at?: string;
  approved_by_finance?: string;
  finance_approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  rejection_reason?: string;
  paid_at?: string;
  payment_reference?: string;
  advance_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  lines: ExpenseClaimLine[];
}

export interface ExpenseAdvance {
  advance_id: string;
  employee_id: string;
  advance_no: string;
  advance_date: string;
  advance_amount: number;
  settled_amount: number;
  currency: string;
  purpose?: string;
  settlement_status: AdvanceSettlementStatus;
  due_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ExpenseDashboard {
  total_claims: number;
  pending_approval: number;
  approved_unpaid: number;
  total_reimbursed_month: number;
  total_claimed_month: number;
  policy_violations_open: number;
  overdue_advances: number;
  ai_alerts: number;
}

export interface ExpAIRecommendation {
  rec_id: string;
  agent_type: ExpAIAgentType;
  subject: string;
  body: string;
  ref_expense_claim_id?: string;
  ref_employee_id?: string;
  status: ExpAIRecStatus;
  created_at: string;
}

// ── Label maps ────────────────────────────────────────────────────────────────

export const STATUS_LABEL: Record<ExpenseStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  manager_approved: "Manager Approved",
  finance_approved: "Finance Approved",
  rejected: "Rejected",
  paid: "Paid",
  cancelled: "Cancelled",
};

export const STATUS_COLOR: Record<ExpenseStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  manager_approved: "bg-indigo-100 text-indigo-700",
  finance_approved: "bg-purple-100 text-purple-700",
  rejected: "bg-red-100 text-red-700",
  paid: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};

export const ADVANCE_STATUS_COLOR: Record<AdvanceSettlementStatus, string> = {
  open: "bg-yellow-100 text-yellow-700",
  partially_settled: "bg-blue-100 text-blue-700",
  settled: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
};

export const AI_AGENT_LABEL: Record<ExpAIAgentType, string> = {
  risk_monitor: "Expense Risk Monitor",
  policy_optimizer: "Policy Optimizer",
  reimbursement_assistant: "Reimbursement Assistant",
};

export function fmtCurrency(v: number | string, currency = "KES") {
  return `${currency} ${Number(v).toLocaleString("en-KE", { minimumFractionDigits: 2 })}`;
}

// ── API client ────────────────────────────────────────────────────────────────

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const expensesApi = {
  dashboard: () => api<ExpenseDashboard>("/dashboard"),

  // Categories
  listCategories: () => api<ExpenseCategory[]>("/categories"),
  createCategory: (data: Partial<ExpenseCategory>) =>
    api<ExpenseCategory>("/categories", { method: "POST", body: JSON.stringify(data) }),
  updateCategory: (id: string, data: Partial<ExpenseCategory>) =>
    api<ExpenseCategory>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Policies
  listPolicies: () => api<ExpensePolicy[]>("/policies"),
  createPolicy: (data: Partial<ExpensePolicy>) =>
    api<ExpensePolicy>("/policies", { method: "POST", body: JSON.stringify(data) }),

  // Claims
  listClaims: (params?: { employee_id?: string; status?: ExpenseStatus; department_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.status) q.set("status", params.status);
    if (params?.department_id) q.set("department_id", params.department_id);
    return api<ExpenseClaim[]>(`/claims?${q}`);
  },
  createClaim: (data: object) =>
    api<ExpenseClaim>("/claims", { method: "POST", body: JSON.stringify(data) }),
  getClaim: (id: string) => api<ExpenseClaim>(`/claims/${id}`),
  addLine: (id: string, data: object) =>
    api<ExpenseClaim>(`/claims/${id}/lines`, { method: "POST", body: JSON.stringify(data) }),
  submitClaim: (id: string) =>
    api<ExpenseClaim>(`/claims/${id}/submit`, { method: "POST" }),
  managerApprove: (id: string, data: object) =>
    api<ExpenseClaim>(`/claims/${id}/manager-approve`, { method: "POST", body: JSON.stringify(data) }),
  financeApprove: (id: string, data: object) =>
    api<ExpenseClaim>(`/claims/${id}/finance-approve`, { method: "POST", body: JSON.stringify(data) }),
  rejectClaim: (id: string, data: object) =>
    api<ExpenseClaim>(`/claims/${id}/reject`, { method: "POST", body: JSON.stringify(data) }),
  returnForCorrection: (id: string, notes: string) =>
    api<ExpenseClaim>(`/claims/${id}/return?notes=${encodeURIComponent(notes)}`, { method: "POST" }),
  payClaim: (id: string, data: object) =>
    api<ExpenseClaim>(`/claims/${id}/pay`, { method: "POST", body: JSON.stringify(data) }),

  // Advances
  listAdvances: (params?: { employee_id?: string; status?: AdvanceSettlementStatus }) => {
    const q = new URLSearchParams();
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.status) q.set("status", params.status);
    return api<ExpenseAdvance[]>(`/advances?${q}`);
  },
  createAdvance: (data: object) =>
    api<ExpenseAdvance>("/advances", { method: "POST", body: JSON.stringify(data) }),
  getAdvance: (id: string) => api<ExpenseAdvance>(`/advances/${id}`),

  // Reports
  reportByEmployee: () => api<object[]>("/reports/by-employee"),
  reportByCategory: () => api<object[]>("/reports/by-category"),
  reportViolations: () => api<object[]>("/reports/policy-violations"),

  // AI
  runRiskMonitor: () => api<{ generated: number }>("/ai/run-risk-monitor", { method: "POST" }),
  runPolicyOptimizer: () => api<{ generated: number }>("/ai/run-policy-optimizer", { method: "POST" }),
  runReimbursementAssistant: () => api<{ generated: number }>("/ai/run-reimbursement-assistant", { method: "POST" }),
  listRecs: (status?: ExpAIRecStatus) =>
    api<ExpAIRecommendation[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackRec: (id: string, data: { status: ExpAIRecStatus; notes?: string }) =>
    api<ExpAIRecommendation>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
};
