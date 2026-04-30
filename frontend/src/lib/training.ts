const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/training`;

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

export type SkillCategory = "technical" | "soft" | "safety" | "compliance" | "management";
export type SkillLevel = "basic" | "intermediate" | "advanced" | "expert";
export type TrainingType = "internal" | "external" | "online" | "classroom" | "on_job";
export type SessionStatus = "planned" | "in_progress" | "completed" | "cancelled";
export type AssignmentStatus = "assigned" | "in_progress" | "completed" | "overdue" | "waived";
export type CertificationStatus = "valid" | "expiring" | "expired" | "revoked";
export type TRAIAgentType = "skill_gap_advisor" | "effectiveness_analyzer" | "compliance_risk";
export type TRAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface Skill {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  category: SkillCategory;
  description: string | null;
  active_flag: boolean;
  created_at: string;
}

export interface EmployeeSkillRow {
  employee_skill_id: string;
  employee_id: string;
  employee_name: string | null;
  department_id: string | null;
  skill_id: string;
  skill_name: string;
  skill_category: SkillCategory;
  current_level: SkillLevel | null;
  required_level: SkillLevel | null;
  has_gap: boolean;
  last_assessed_date: string | null;
  notes: string | null;
  created_at: string;
}

export interface TrainingProgram {
  training_id: string;
  training_code: string;
  training_name: string;
  training_type: TrainingType;
  category: SkillCategory;
  duration_hours: number | null;
  provider: string | null;
  cost: number | null;
  mandatory_flag: boolean;
  validity_period_days: number | null;
  active_flag: boolean;
  notes: string | null;
  created_at: string;
}

export interface TrainingSession {
  session_id: string;
  training_id: string;
  training_name: string | null;
  session_date: string;
  end_date: string | null;
  location: string | null;
  trainer_id: string | null;
  trainer_name: string | null;
  capacity: number | null;
  enrolled_count: number;
  status: SessionStatus;
  notes: string | null;
  created_at: string;
}

export interface TrainingAssignment {
  assignment_id: string;
  employee_id: string;
  employee_name: string | null;
  department_id: string | null;
  training_id: string;
  training_name: string | null;
  session_id: string | null;
  assigned_by: string | null;
  due_date: string | null;
  completion_date: string | null;
  status: AssignmentStatus;
  score: number | null;
  notes: string | null;
  created_at: string;
}

export interface CertificationRecord {
  certification_id: string;
  employee_id: string;
  employee_name: string | null;
  training_id: string | null;
  certificate_name: string;
  certificate_no: string | null;
  issuer: string | null;
  issue_date: string;
  expiry_date: string | null;
  status: CertificationStatus;
  days_to_expiry: number | null;
  document_url: string | null;
  notes: string | null;
  created_at: string;
}

export interface TrainingFeedback {
  feedback_id: string;
  employee_id: string;
  employee_name: string | null;
  training_id: string;
  session_id: string | null;
  rating: number;
  content_rating: number | null;
  trainer_rating: number | null;
  relevance_rating: number | null;
  comments: string | null;
  created_at: string;
}

export interface TrainingDashboard {
  total_programs: number;
  active_programs: number;
  total_sessions: number;
  upcoming_sessions: number;
  total_assignments: number;
  completed_assignments: number;
  overdue_assignments: number;
  total_certifications: number;
  expiring_soon: number;
  expired_certifications: number;
  total_skill_profiles: number;
  skill_gaps: number;
  avg_feedback_rating: number | null;
}

export interface TRAIRec {
  rec_id: string;
  agent_type: TRAIAgentType;
  status: TRAIRecStatus;
  title: string;
  body: string;
  employee_id: string | null;
  department_id: string | null;
  training_id: string | null;
  certification_id: string | null;
  score: number | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Color/Label Maps ──────────────────────────────────────────────────────────

export const CATEGORY_COLOR: Record<SkillCategory, string> = {
  technical: "bg-blue-100 text-blue-700",
  soft: "bg-purple-100 text-purple-700",
  safety: "bg-red-100 text-red-700",
  compliance: "bg-orange-100 text-orange-700",
  management: "bg-indigo-100 text-indigo-700",
};

export const LEVEL_COLOR: Record<SkillLevel, string> = {
  basic: "bg-gray-100 text-gray-600",
  intermediate: "bg-yellow-100 text-yellow-700",
  advanced: "bg-blue-100 text-blue-700",
  expert: "bg-green-100 text-green-700",
};

export const LEVEL_ORDER: Record<SkillLevel, number> = {
  basic: 1, intermediate: 2, advanced: 3, expert: 4,
};

export const SESSION_STATUS_COLOR: Record<SessionStatus, string> = {
  planned: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};

export const ASSIGNMENT_STATUS_COLOR: Record<AssignmentStatus, string> = {
  assigned: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  waived: "bg-gray-100 text-gray-500",
};

export const CERT_STATUS_COLOR: Record<CertificationStatus, string> = {
  valid: "bg-green-100 text-green-700",
  expiring: "bg-yellow-100 text-yellow-800",
  expired: "bg-red-100 text-red-700",
  revoked: "bg-gray-100 text-gray-500",
};

export const TRAINING_TYPE_LABEL: Record<TrainingType, string> = {
  internal: "Internal",
  external: "External",
  online: "Online",
  classroom: "Classroom",
  on_job: "On-the-Job",
};

// ── API Client ────────────────────────────────────────────────────────────────

export const trainingApi = {
  getDashboard: () => req<TrainingDashboard>("/dashboard"),

  // Skills
  createSkill: (d: object) => req<Skill>("/skills", { method: "POST", body: JSON.stringify(d) }),
  listSkills: (category?: string, active?: boolean) => {
    const q = new URLSearchParams();
    if (category) q.set("category", category);
    if (active) q.set("active_only", "true");
    return req<Skill[]>(`/skills?${q}`);
  },
  getSkill: (id: string) => req<Skill>(`/skills/${id}`),
  updateSkill: (id: string, d: object) => req<Skill>(`/skills/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  seedSkills: () => req<{ created: number }>("/skills/seed-defaults", { method: "POST" }),

  // Skill Profiles
  upsertSkillProfile: (d: object) => req<EmployeeSkillRow>("/skill-profiles", { method: "POST", body: JSON.stringify(d) }),
  updateSkillProfile: (id: string, d: object) =>
    req<EmployeeSkillRow>(`/skill-profiles/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  getSkillMatrix: (employee_id?: string, department_id?: string) => {
    const q = new URLSearchParams();
    if (employee_id) q.set("employee_id", employee_id);
    if (department_id) q.set("department_id", department_id);
    return req<EmployeeSkillRow[]>(`/skill-matrix?${q}`);
  },
  getSkillGapReport: (department_id?: string) =>
    req<EmployeeSkillRow[]>(`/skill-gap-report${department_id ? `?department_id=${department_id}` : ""}`),

  // Programs
  createProgram: (d: object) => req<TrainingProgram>("/programs", { method: "POST", body: JSON.stringify(d) }),
  listPrograms: (params?: { category?: string; mandatory_only?: boolean; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.category) q.set("category", params.category);
    if (params?.mandatory_only) q.set("mandatory_only", "true");
    if (params?.active_only) q.set("active_only", "true");
    return req<TrainingProgram[]>(`/programs?${q}`);
  },
  getProgram: (id: string) => req<TrainingProgram>(`/programs/${id}`),
  updateProgram: (id: string, d: object) =>
    req<TrainingProgram>(`/programs/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  getProgramEffectiveness: (id: string) => req<object>(`/programs/${id}/effectiveness`),

  // Sessions
  createSession: (d: object) => req<TrainingSession>("/sessions", { method: "POST", body: JSON.stringify(d) }),
  listSessions: (params?: { training_id?: string; status?: string; upcoming_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.training_id) q.set("training_id", params.training_id);
    if (params?.status) q.set("status", params.status);
    if (params?.upcoming_only) q.set("upcoming_only", "true");
    return req<TrainingSession[]>(`/sessions?${q}`);
  },
  getSession: (id: string) => req<TrainingSession>(`/sessions/${id}`),
  updateSession: (id: string, d: object) =>
    req<TrainingSession>(`/sessions/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  completeSession: (id: string) =>
    req<TrainingSession>(`/sessions/${id}/complete`, { method: "POST" }),

  // Assignments
  createAssignment: (d: object) =>
    req<TrainingAssignment>("/assignments", { method: "POST", body: JSON.stringify(d) }),
  listAssignments: (params?: { employee_id?: string; training_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.training_id) q.set("training_id", params.training_id);
    if (params?.status) q.set("status", params.status);
    return req<TrainingAssignment[]>(`/assignments?${q}`);
  },
  completeAssignment: (id: string, d: object) =>
    req<TrainingAssignment>(`/assignments/${id}/complete`, { method: "POST", body: JSON.stringify(d) }),
  markOverdue: () => req<{ marked_overdue: number }>("/assignments/mark-overdue", { method: "POST" }),

  // Certifications
  createCertification: (d: object) =>
    req<CertificationRecord>("/certifications", { method: "POST", body: JSON.stringify(d) }),
  listCertifications: (params?: { employee_id?: string; status?: string; expiring_days?: number }) => {
    const q = new URLSearchParams();
    if (params?.employee_id) q.set("employee_id", params.employee_id);
    if (params?.status) q.set("status", params.status);
    if (params?.expiring_days != null) q.set("expiring_days", String(params.expiring_days));
    return req<CertificationRecord[]>(`/certifications?${q}`);
  },
  getCertification: (id: string) => req<CertificationRecord>(`/certifications/${id}`),
  updateCertification: (id: string, d: object) =>
    req<CertificationRecord>(`/certifications/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  refreshCertStatuses: () => req<{ updated: number }>("/certifications/refresh-statuses", { method: "POST" }),

  // Feedback
  submitFeedback: (d: object) => req<TrainingFeedback>("/feedback", { method: "POST", body: JSON.stringify(d) }),
  listFeedback: (training_id?: string) =>
    req<TrainingFeedback[]>(`/feedback${training_id ? `?training_id=${training_id}` : ""}`),

  // Reports
  reportCompletion: (training_id?: string) =>
    req<object>(`/reports/completion${training_id ? `?training_id=${training_id}` : ""}`),
  reportCertExpiry: (days?: number) =>
    req<object[]>(`/reports/certification-expiry${days ? `?days=${days}` : ""}`),
  reportTrainingCost: () => req<object[]>("/reports/training-cost"),
  reportSkillGaps: (department_id?: string) =>
    req<EmployeeSkillRow[]>(`/reports/skill-gaps${department_id ? `?department_id=${department_id}` : ""}`),

  // AI
  runSkillGapAdvisor: () => req<TRAIRec[]>("/ai/run-skill-gap-advisor", { method: "POST" }),
  runEffectivenessAnalyzer: () => req<TRAIRec[]>("/ai/run-effectiveness-analyzer", { method: "POST" }),
  runComplianceRisk: () => req<TRAIRec[]>("/ai/run-compliance-risk", { method: "POST" }),
  listAIRecs: (status?: string) =>
    req<TRAIRec[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackAIRec: (id: string, d: object) =>
    req<TRAIRec>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
