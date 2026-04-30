const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/appraisals`;

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? r.statusText);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type AppraisalPeriodType = "annual" | "semi_annual" | "quarterly" | "probation" | "project_based" | "custom";
export type AppraisalPeriodStatus = "draft" | "active" | "closed" | "archived";
export type AppraisalStatus = "draft" | "self_review" | "manager_review" | "hr_review" | "calibration" | "completed" | "rejected";
export type FinalRating = "excellent" | "good" | "meets_expectations" | "improvement_needed";
export type DevelopmentPlanStatus = "open" | "in_progress" | "completed" | "cancelled";
export type APAIAgentType = "performance_insight" | "calibration_risk" | "development_plan";
export type APAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface AppraisalPeriod {
  appraisal_period_id: string;
  period_code: string;
  period_name: string;
  period_type: AppraisalPeriodType;
  start_date: string;
  end_date: string;
  review_start_date: string | null;
  review_end_date: string | null;
  status: AppraisalPeriodStatus;
  notes: string | null;
  created_at: string;
}

export interface AppraisalTemplate {
  template_id: string;
  template_code: string;
  template_name: string;
  department_id: string | null;
  role_id: string | null;
  employee_grade_id: string | null;
  kpi_weight_pct: number;
  competency_weight_pct: number;
  active_flag: boolean;
  notes: string | null;
  created_at: string;
}

export interface KPILine {
  kpi_line_id: string;
  appraisal_id: string;
  kpi_name: string;
  kpi_description: string | null;
  target_value: number | null;
  actual_value: number | null;
  unit: string | null;
  weight_pct: number;
  self_score: number | null;
  manager_score: number | null;
  final_score: number | null;
  comments: string | null;
}

export interface CompetencyLine {
  competency_line_id: string;
  appraisal_id: string;
  competency_name: string;
  description: string | null;
  weight_pct: number;
  self_rating: number | null;
  manager_rating: number | null;
  final_rating: number | null;
  comments: string | null;
}

export interface DevelopmentPlan {
  development_plan_id: string;
  appraisal_id: string;
  employee_id: string;
  goal_title: string;
  action_plan: string | null;
  due_date: string | null;
  owner_id: string | null;
  owner_name: string | null;
  status: DevelopmentPlanStatus;
  notes: string | null;
  created_at: string;
}

export interface AppraisalRecord {
  appraisal_id: string;
  appraisal_period_id: string;
  employee_id: string;
  employee_name: string | null;
  manager_id: string | null;
  manager_name: string | null;
  department_id: string | null;
  department_name: string | null;
  template_id: string | null;
  status: AppraisalStatus;
  self_score: number | null;
  manager_score: number | null;
  final_score: number | null;
  final_rating: FinalRating | null;
  increment_recommendation: number | null;
  promotion_recommendation: boolean;
  self_submitted_at: string | null;
  manager_reviewed_at: string | null;
  hr_reviewed_at: string | null;
  finalized_at: string | null;
  hr_notes: string | null;
  calibration_notes: string | null;
  notes: string | null;
  created_at: string;
  kpi_lines: KPILine[];
  competency_lines: CompetencyLine[];
  development_plans: DevelopmentPlan[];
}

export interface AppraisalDashboard {
  total_records: number;
  self_review_pending: number;
  manager_review_pending: number;
  hr_review_pending: number;
  calibration_pending: number;
  completed: number;
  avg_final_score: number | null;
  rating_distribution: Record<string, number>;
  department_avg_scores: { department: string; avg_score: number }[];
  pending_development_plans: number;
  promotion_recommendations: number;
}

export interface APAIRec {
  rec_id: string;
  agent_type: APAIAgentType;
  status: APAIRecStatus;
  title: string;
  body: string;
  appraisal_id: string | null;
  employee_id: string | null;
  department_id: string | null;
  score: number | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Color / Label Maps ────────────────────────────────────────────────────────

export const PERIOD_STATUS_COLOR: Record<AppraisalPeriodStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  active: "bg-green-100 text-green-700",
  closed: "bg-blue-100 text-blue-700",
  archived: "bg-gray-200 text-gray-500",
};

export const APPRAISAL_STATUS_COLOR: Record<AppraisalStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  self_review: "bg-yellow-100 text-yellow-700",
  manager_review: "bg-orange-100 text-orange-700",
  hr_review: "bg-purple-100 text-purple-700",
  calibration: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
};

export const APPRAISAL_STATUS_LABEL: Record<AppraisalStatus, string> = {
  draft: "Draft",
  self_review: "Self Review",
  manager_review: "Manager Review",
  hr_review: "HR Review",
  calibration: "Calibration",
  completed: "Completed",
  rejected: "Rejected",
};

export const RATING_COLOR: Record<FinalRating, string> = {
  excellent: "bg-green-100 text-green-800",
  good: "bg-blue-100 text-blue-800",
  meets_expectations: "bg-yellow-100 text-yellow-800",
  improvement_needed: "bg-red-100 text-red-800",
};

export const RATING_LABEL: Record<FinalRating, string> = {
  excellent: "Excellent (90–100)",
  good: "Good (75–89)",
  meets_expectations: "Meets Expectations (60–74)",
  improvement_needed: "Needs Improvement (<60)",
};

export const PLAN_STATUS_COLOR: Record<DevelopmentPlanStatus, string> = {
  open: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};

export const PERIOD_TYPE_LABEL: Record<AppraisalPeriodType, string> = {
  annual: "Annual",
  semi_annual: "Semi-Annual",
  quarterly: "Quarterly",
  probation: "Probation",
  project_based: "Project-Based",
  custom: "Custom",
};

// ── API Client ────────────────────────────────────────────────────────────────

export const appraisalsApi = {
  // Dashboard
  getDashboard: (period_id?: string) =>
    req<AppraisalDashboard>(`/dashboard${period_id ? `?period_id=${period_id}` : ""}`),

  // Periods
  createPeriod: (d: object) => req<AppraisalPeriod>("/periods", { method: "POST", body: JSON.stringify(d) }),
  listPeriods: (status?: string) => req<AppraisalPeriod[]>(`/periods${status ? `?status=${status}` : ""}`),
  getPeriod: (id: string) => req<AppraisalPeriod>(`/periods/${id}`),
  updatePeriod: (id: string, d: object) => req<AppraisalPeriod>(`/periods/${id}`, { method: "PATCH", body: JSON.stringify(d) }),

  // Templates
  createTemplate: (d: object) => req<AppraisalTemplate>("/templates", { method: "POST", body: JSON.stringify(d) }),
  listTemplates: (active?: boolean) => req<AppraisalTemplate[]>(`/templates${active ? "?active_only=true" : ""}`),
  getTemplate: (id: string) => req<AppraisalTemplate>(`/templates/${id}`),

  // Records
  createRecord: (d: object) => req<AppraisalRecord>("/", { method: "POST", body: JSON.stringify(d) }),
  listRecords: (params?: { period_id?: string; employee_id?: string; department_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.period_id) q.set("period_id", params.period_id);
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.department_id) q.set("department_id", params.department_id);
    if (params?.status) q.set("status", params.status);
    return req<AppraisalRecord[]>(`/?${q.toString()}`);
  },
  getRecord: (id: string) => req<AppraisalRecord>(`/${id}`),
  selfSubmit: (id: string, d: object) => req<AppraisalRecord>(`/${id}/self-submit`, { method: "POST", body: JSON.stringify(d) }),
  managerReview: (id: string, d: object) => req<AppraisalRecord>(`/${id}/manager-review`, { method: "POST", body: JSON.stringify(d) }),
  hrReview: (id: string, d: object) => req<AppraisalRecord>(`/${id}/hr-review`, { method: "POST", body: JSON.stringify(d) }),
  finalize: (id: string, d: object) => req<AppraisalRecord>(`/${id}/finalize`, { method: "POST", body: JSON.stringify(d) }),
  reject: (id: string, notes?: string) =>
    req<AppraisalRecord>(`/${id}/reject${notes ? `?notes=${encodeURIComponent(notes)}` : ""}`, { method: "POST" }),
  calculateScores: (id: string) => req<AppraisalRecord>(`/${id}/calculate-scores`, { method: "POST" }),

  // KPI Lines
  addKPILine: (appraisalId: string, d: object) =>
    req<KPILine>(`/${appraisalId}/kpi-lines`, { method: "POST", body: JSON.stringify(d) }),
  updateKPILine: (id: string, d: object) =>
    req<KPILine>(`/kpi-lines/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  deleteKPILine: (id: string) => req<void>(`/kpi-lines/${id}`, { method: "DELETE" }),

  // Competency Lines
  addCompetencyLine: (appraisalId: string, d: object) =>
    req<CompetencyLine>(`/${appraisalId}/competency-lines`, { method: "POST", body: JSON.stringify(d) }),
  updateCompetencyLine: (id: string, d: object) =>
    req<CompetencyLine>(`/competency-lines/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  deleteCompetencyLine: (id: string) => req<void>(`/competency-lines/${id}`, { method: "DELETE" }),

  // Development Plans
  addDevelopmentPlan: (appraisalId: string, employeeId: string, d: object) =>
    req<DevelopmentPlan>(`/${appraisalId}/development-plans?employee_id=${employeeId}`, { method: "POST", body: JSON.stringify(d) }),
  updateDevelopmentPlan: (id: string, d: object) =>
    req<DevelopmentPlan>(`/development-plans/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  listDevelopmentPlans: (params?: { employee_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.status) q.set("status", params.status);
    return req<DevelopmentPlan[]>(`/development-plans/list?${q.toString()}`);
  },

  // Reports
  reportCompletion: (period_id: string) => req<object>(`/reports/completion?period_id=${period_id}`),
  reportRatingDist: (period_id?: string) =>
    req<object[]>(`/reports/rating-distribution${period_id ? `?period_id=${period_id}` : ""}`),
  reportPromotions: (period_id?: string) =>
    req<object[]>(`/reports/promotions${period_id ? `?period_id=${period_id}` : ""}`),

  // AI
  runPerformanceInsight: () => req<APAIRec[]>("/ai/run-performance-insight", { method: "POST" }),
  runCalibrationRisk: () => req<APAIRec[]>("/ai/run-calibration-risk", { method: "POST" }),
  runDevelopmentPlan: () => req<APAIRec[]>("/ai/run-development-plan", { method: "POST" }),
  listAIRecs: (status?: string) => req<APAIRec[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackAIRec: (id: string, d: object) =>
    req<APAIRec>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
