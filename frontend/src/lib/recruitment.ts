const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/recruitment`;

export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";
export type RequisitionStatus = "draft" | "approved" | "open" | "closed" | "cancelled";
export type PostingChannel = "internal" | "website" | "job_portal" | "agency" | "referral";
export type PostingStatus = "draft" | "active" | "expired" | "closed";
export type CandidateSource = "portal" | "referral" | "agency" | "manual" | "linkedin" | "job_portal";
export type PipelineStatus = "active" | "moved" | "rejected" | "hired" | "on_hold" | "withdrawn";
export type InterviewType = "online" | "onsite" | "phone" | "panel";
export type InterviewDecision = "pass" | "fail" | "hold" | "pending";
export type OfferStatus = "draft" | "sent" | "accepted" | "rejected" | "negotiating" | "expired";
export type StageType = "active" | "final_hire" | "final_reject";
export type RTAIAgentType = "candidate_matcher" | "hiring_risk_detector" | "pipeline_optimizer";
export type RTAIRecStatus = "pending" | "acknowledged" | "dismissed" | "actioned";

export interface RecruitmentStage {
  stage_id: string;
  stage_code: string;
  stage_name: string;
  sequence: number;
  stage_type: StageType;
  active_flag: boolean;
  created_at: string;
}

export interface JobRequisition {
  requisition_id: string;
  requisition_code: string;
  job_title: string;
  department_id?: string;
  location?: string;
  employment_type: EmploymentType;
  headcount: number;
  filled_count: number;
  requested_by?: string;
  approved_by?: string;
  approved_at?: string;
  status: RequisitionStatus;
  opening_date?: string;
  closing_date?: string;
  job_description?: string;
  requirements?: string;
  salary_min?: number;
  salary_max?: number;
  currency: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface JobPosting {
  posting_id: string;
  requisition_id: string;
  posting_channel: PostingChannel;
  posting_url?: string;
  publish_date?: string;
  expiry_date?: string;
  status: PostingStatus;
  views_count: number;
  applications_count: number;
  notes?: string;
  created_at: string;
}

export interface Candidate {
  candidate_id: string;
  candidate_code: string;
  full_name: string;
  email: string;
  phone?: string;
  location?: string;
  cv_attachment?: string;
  source: CandidateSource;
  current_employer?: string;
  current_title?: string;
  years_experience?: number;
  education_level?: string;
  skills_tags?: string;
  notes?: string;
  blacklisted: boolean;
  created_at: string;
  updated_at: string;
}

export interface CandidatePipeline {
  pipeline_id: string;
  candidate_id: string;
  requisition_id: string;
  stage_id: string;
  assigned_recruiter?: string;
  status: PipelineStatus;
  application_date?: string;
  last_update: string;
  screening_score?: number;
  overall_score?: number;
  notes?: string;
  created_at: string;
}

export interface Interview {
  interview_id: string;
  candidate_id: string;
  requisition_id: string;
  stage_id?: string;
  interviewer_id?: string;
  interview_date: string;
  interview_type: InterviewType;
  location_or_link?: string;
  feedback?: string;
  score?: number;
  technical_score?: number;
  cultural_score?: number;
  decision: InterviewDecision;
  completed_at?: string;
  notes?: string;
  created_at: string;
}

export interface Offer {
  offer_id: string;
  offer_code: string;
  candidate_id: string;
  requisition_id: string;
  offer_date: string;
  expiry_date?: string;
  salary_offer: number;
  currency: string;
  joining_date?: string;
  employment_type: EmploymentType;
  status: OfferStatus;
  sent_at?: string;
  responded_at?: string;
  rejection_reason?: string;
  negotiation_notes?: string;
  employee_id_created?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface RecruitmentDashboard {
  open_requisitions: number;
  total_candidates: number;
  active_pipelines: number;
  interviews_this_week: number;
  pending_offers: number;
  hires_this_month: number;
  avg_time_to_hire_days: number;
  ai_alerts: number;
}

export interface RTAIRecommendation {
  rec_id: string;
  agent_type: RTAIAgentType;
  subject: string;
  body: string;
  ref_requisition_id?: string;
  ref_candidate_id?: string;
  status: RTAIRecStatus;
  created_at: string;
}

// ── Label / color maps ────────────────────────────────────────────────────────

export const REQ_STATUS_LABEL: Record<RequisitionStatus, string> = {
  draft: "Draft", approved: "Approved", open: "Open",
  closed: "Closed", cancelled: "Cancelled",
};
export const REQ_STATUS_COLOR: Record<RequisitionStatus, string> = {
  draft: "bg-slate-500/20 text-slate-400",
  approved: "bg-blue-500/20 text-blue-300",
  open: "bg-emerald-500/20 text-emerald-300",
  closed: "bg-slate-700/20 text-slate-500",
  cancelled: "bg-red-500/20 text-red-300",
};
export const PIPELINE_STATUS_COLOR: Record<PipelineStatus, string> = {
  active: "bg-blue-500/20 text-blue-300",
  moved: "bg-indigo-500/20 text-indigo-300",
  rejected: "bg-red-500/20 text-red-300",
  hired: "bg-emerald-500/20 text-emerald-300",
  on_hold: "bg-amber-500/20 text-amber-300",
  withdrawn: "bg-slate-700/20 text-slate-500",
};
export const OFFER_STATUS_COLOR: Record<OfferStatus, string> = {
  draft: "bg-slate-500/20 text-slate-400",
  sent: "bg-blue-500/20 text-blue-300",
  accepted: "bg-emerald-500/20 text-emerald-300",
  rejected: "bg-red-500/20 text-red-300",
  negotiating: "bg-amber-500/20 text-amber-300",
  expired: "bg-slate-700/20 text-slate-500",
};
export const INTERVIEW_DECISION_COLOR: Record<InterviewDecision, string> = {
  pass: "bg-emerald-500/20 text-emerald-300",
  fail: "bg-red-500/20 text-red-300",
  hold: "bg-amber-500/20 text-amber-300",
  pending: "bg-slate-500/20 text-slate-400",
};
export const AI_AGENT_LABEL: Record<RTAIAgentType, string> = {
  candidate_matcher: "Candidate Matcher",
  hiring_risk_detector: "Hiring Risk Detector",
  pipeline_optimizer: "Pipeline Optimizer",
};

export function fmtCurrency(v: number | string, cur = "KES") {
  return `${cur} ${Number(v).toLocaleString("en-KE", { minimumFractionDigits: 0 })}`;
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

export const recruitmentApi = {
  dashboard: () => api<RecruitmentDashboard>("/dashboard"),

  // Stages
  listStages: () => api<RecruitmentStage[]>("/stages"),
  createStage: (d: object) => api<RecruitmentStage>("/stages", { method: "POST", body: JSON.stringify(d) }),
  seedStages: () => api<RecruitmentStage[]>("/stages/seed-defaults", { method: "POST" }),

  // Requisitions
  listRequisitions: (p?: { status?: RequisitionStatus }) => {
    const q = new URLSearchParams();
    if (p?.status) q.set("status", p.status);
    return api<JobRequisition[]>(`/requisitions?${q}`);
  },
  createRequisition: (d: object) => api<JobRequisition>("/requisitions", { method: "POST", body: JSON.stringify(d) }),
  getRequisition: (id: string) => api<JobRequisition>(`/requisitions/${id}`),
  approveRequisition: (id: string, d: object) =>
    api<JobRequisition>(`/requisitions/${id}/approve`, { method: "POST", body: JSON.stringify(d) }),
  openRequisition: (id: string) => api<JobRequisition>(`/requisitions/${id}/open`, { method: "POST" }),
  closeRequisition: (id: string) => api<JobRequisition>(`/requisitions/${id}/close`, { method: "POST" }),

  // Postings
  listPostings: (requisitionId?: string) =>
    api<JobPosting[]>(`/postings${requisitionId ? `?requisition_id=${requisitionId}` : ""}`),
  createPosting: (d: object) => api<JobPosting>("/postings", { method: "POST", body: JSON.stringify(d) }),
  publishPosting: (id: string) => api<JobPosting>(`/postings/${id}/publish`, { method: "POST" }),

  // Candidates
  listCandidates: (p?: { search?: string; source?: string }) => {
    const q = new URLSearchParams();
    if (p?.search) q.set("search", p.search);
    if (p?.source) q.set("source", p.source);
    return api<Candidate[]>(`/candidates?${q}`);
  },
  createCandidate: (d: object) => api<Candidate>("/candidates", { method: "POST", body: JSON.stringify(d) }),
  getCandidate: (id: string) => api<Candidate>(`/candidates/${id}`),
  updateCandidate: (id: string, d: object) =>
    api<Candidate>(`/candidates/${id}`, { method: "PATCH", body: JSON.stringify(d) }),

  // Pipeline
  listPipeline: (p?: { requisition_id?: string; stage_id?: string; status?: PipelineStatus }) => {
    const q = new URLSearchParams();
    if (p?.requisition_id) q.set("requisition_id", p.requisition_id);
    if (p?.stage_id) q.set("stage_id", p.stage_id);
    if (p?.status) q.set("status", p.status);
    return api<CandidatePipeline[]>(`/pipeline?${q}`);
  },
  addToPipeline: (d: object) => api<CandidatePipeline>("/pipeline", { method: "POST", body: JSON.stringify(d) }),
  moveStage: (id: string, d: object) =>
    api<CandidatePipeline>(`/pipeline/${id}/move`, { method: "POST", body: JSON.stringify(d) }),
  rejectCandidate: (id: string, notes = "") =>
    api<CandidatePipeline>(`/pipeline/${id}/reject?notes=${encodeURIComponent(notes)}`, { method: "POST" }),

  // Interviews
  listInterviews: (p?: { candidate_id?: string; requisition_id?: string }) => {
    const q = new URLSearchParams();
    if (p?.candidate_id) q.set("candidate_id", p.candidate_id);
    if (p?.requisition_id) q.set("requisition_id", p.requisition_id);
    return api<Interview[]>(`/interviews?${q}`);
  },
  scheduleInterview: (d: object) => api<Interview>("/interviews", { method: "POST", body: JSON.stringify(d) }),
  recordFeedback: (id: string, d: object) =>
    api<Interview>(`/interviews/${id}/feedback`, { method: "POST", body: JSON.stringify(d) }),

  // Offers
  listOffers: (p?: { requisition_id?: string; status?: OfferStatus }) => {
    const q = new URLSearchParams();
    if (p?.requisition_id) q.set("requisition_id", p.requisition_id);
    if (p?.status) q.set("status", p.status);
    return api<Offer[]>(`/offers?${q}`);
  },
  createOffer: (d: object) => api<Offer>("/offers", { method: "POST", body: JSON.stringify(d) }),
  sendOffer: (id: string) => api<Offer>(`/offers/${id}/send`, { method: "POST" }),
  respondToOffer: (id: string, d: object) =>
    api<Offer>(`/offers/${id}/respond`, { method: "POST", body: JSON.stringify(d) }),

  // Reports
  reportPipelineByStage: () => api<object[]>("/reports/pipeline-by-stage"),
  reportSourceEffectiveness: () => api<object[]>("/reports/source-effectiveness"),
  reportOfferAcceptance: () => api<object>("/reports/offer-acceptance"),

  // AI
  runCandidateMatcher: () => api<{ generated: number }>("/ai/run-candidate-matcher", { method: "POST" }),
  runHiringRiskDetector: () => api<{ generated: number }>("/ai/run-hiring-risk-detector", { method: "POST" }),
  runPipelineOptimizer: () => api<{ generated: number }>("/ai/run-pipeline-optimizer", { method: "POST" }),
  listRecs: (status?: RTAIRecStatus) =>
    api<RTAIRecommendation[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackRec: (id: string, d: { status: RTAIRecStatus; notes?: string }) =>
    api<RTAIRecommendation>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
