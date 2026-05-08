// Quality Management System (QMS) + HACCP — types & API client

const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/qms`;

// ── Enums / Types ─────────────────────────────────────────────────────────────

export type QCType = "INCOMING" | "IN_PROCESS" | "FINISHED_GOODS" | "RETEST";
export type QCStatus = "PENDING" | "IN_PROGRESS" | "PASSED" | "FAILED" | "CONDITIONAL_RELEASE" | "CANCELLED";
export type QCDecision = "ACCEPT" | "REJECT" | "CONDITIONAL_RELEASE" | "REWORK";
export type ParameterType = "NUMERIC" | "TEXT" | "BOOLEAN" | "PASS_FAIL";
export type SamplingMethod = "FIXED" | "PERCENTAGE" | "FREQUENCY" | "TIME_BASED" | "CCP_TRIGGERED";
export type HazardType = "BIOLOGICAL" | "CHEMICAL" | "PHYSICAL" | "ALLERGEN" | "RADIOLOGICAL";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type DeviationStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED";
export type CorrectiveActionStatus = "OPEN" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED" | "OVERDUE";
export type ReleaseStatus = "UNRELEASED" | "QUARANTINED" | "ON_HOLD" | "RELEASED" | "REJECTED" | "REWORK" | "SCRAPPED";
export type QMSAIAgentType = "QUALITY_RISK_PREDICTOR" | "DEVIATION_ANALYZER" | "HACCP_ASSISTANT";
export type QMSAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "APPLIED";

// ── Domain Objects ────────────────────────────────────────────────────────────

export interface QCTemplateParameter {
  id: string;
  template_id: string;
  parameter_id: string | null;
  parameter_name: string;
  parameter_type: ParameterType;
  unit: string | null;
  target_value: string | null;
  min_value: string | null;
  max_value: string | null;
  is_critical: boolean;
  is_ccp_parameter: boolean;
  display_order: number;
  created_at: string;
}

export interface QCTemplate {
  id: string;
  name: string;
  description: string | null;
  qc_type: QCType;
  qc_sub_type: string | null;
  product_id: string | null;
  material_id: string | null;
  product_category: string | null;
  sampling_method: SamplingMethod;
  sample_size: string | null;
  sample_percentage: string | null;
  is_ccp_template: boolean;
  is_mandatory: boolean;
  blocks_progression: boolean;
  release_required: boolean;
  is_active: boolean;
  created_at: string;
  parameters: QCTemplateParameter[];
  product_name: string | null;
  material_name: string | null;
}

export interface HazardAnalysis {
  id: string;
  hazard_no: string;
  process_step: string;
  hazard_type: HazardType;
  hazard_description: string;
  risk_level: RiskLevel;
  likelihood_score: number | null;
  severity_score: number | null;
  risk_score: number | null;
  control_measure: string;
  is_ccp: boolean;
  ccp_id: string | null;
  product_id: string | null;
  material_id: string | null;
  is_active: boolean;
  created_at: string;
  product_name: string | null;
  material_name: string | null;
}

export interface CriticalControlPoint {
  id: string;
  ccp_no: string;
  ccp_name: string;
  process_step: string;
  hazard_type: HazardType;
  parameter_name: string;
  parameter_unit: string | null;
  critical_limit_min: string | null;
  critical_limit_max: string | null;
  critical_limit_description: string | null;
  monitoring_method: string;
  monitoring_frequency: string;
  corrective_action_description: string;
  responsible_role: string | null;
  is_active: boolean;
  allergen_related: boolean;
  cleaning_required: boolean;
  created_at: string;
  product_name: string | null;
  recent_violations: number;
  last_monitored_at: string | null;
}

export interface CCPMonitoringLog {
  id: string;
  ccp_id: string;
  production_order_id: string | null;
  lot_id: string | null;
  monitoring_datetime: string;
  recorded_value: string | null;
  recorded_text: string | null;
  is_within_limits: boolean;
  is_violation: boolean;
  deviation_amount: string | null;
  recorded_by_id: string | null;
  corrective_action_taken: string | null;
  corrective_action_id: string | null;
  process_blocked: boolean;
  notes: string | null;
  created_at: string;
  ccp_name: string | null;
  recorded_by_name: string | null;
}

export interface CorrectiveActionStep {
  id: string;
  corrective_action_id: string;
  step_no: number;
  step_description: string;
  assigned_to_id: string | null;
  due_date: string | null;
  is_completed: boolean;
  completed_at: string | null;
  completion_notes: string | null;
  created_at: string;
}

export interface CorrectiveAction {
  id: string;
  ca_no: string;
  title: string;
  description: string;
  status: CorrectiveActionStatus;
  severity: RiskLevel;
  trigger_type: string | null;
  production_order_id: string | null;
  lot_id: string | null;
  product_id: string | null;
  assigned_to_id: string | null;
  due_date: string | null;
  completed_at: string | null;
  verified_at: string | null;
  root_cause_analysis: string | null;
  effectiveness_check: string | null;
  preventive_measures: string | null;
  notes: string | null;
  steps: CorrectiveActionStep[];
  created_at: string;
  assigned_to_name: string | null;
  product_name: string | null;
  steps_total: number;
  steps_completed: number;
}

export interface QCDeviation {
  id: string;
  deviation_no: string;
  inspection_id: string | null;
  production_order_id: string | null;
  lot_id: string | null;
  product_id: string | null;
  material_id: string | null;
  deviation_type: string;
  severity: RiskLevel;
  status: DeviationStatus;
  description: string;
  root_cause: string | null;
  immediate_action: string | null;
  affected_quantity: string | null;
  affected_uom: string | null;
  assigned_to_id: string | null;
  due_date: string | null;
  corrective_action_id: string | null;
  reported_by_id: string | null;
  resolved_at: string | null;
  notes: string | null;
  created_at: string;
  product_name: string | null;
  material_name: string | null;
  assigned_to_name: string | null;
}

export interface LotQualityStatus {
  id: string;
  lot_id: string;
  qc_status: string;
  release_status: ReleaseStatus;
  hold_flag: boolean;
  quarantine_flag: boolean;
  quarantine_location: string | null;
  hold_reason: string | null;
  last_inspection_id: string | null;
  released_by_id: string | null;
  released_at: string | null;
  release_notes: string | null;
  fefo_eligible: boolean;
  shipment_eligible: boolean;
  allergen_cleared: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AllergenValidationRecord {
  id: string;
  validation_no: string;
  production_order_id: string | null;
  previous_product_id: string | null;
  current_product_id: string | null;
  allergens_present: string | null;
  cleaning_method: string | null;
  cleaning_completed_at: string | null;
  validation_passed: boolean | null;
  swab_test_result: string | null;
  evidence_notes: string | null;
  notes: string | null;
  validated_by_id: string | null;
  created_at: string;
  previous_product_name: string | null;
  current_product_name: string | null;
}

export interface QMSAIRecommendation {
  id: string;
  agent_type: QMSAIAgentType;
  status: QMSAIRecStatus;
  lot_id: string | null;
  production_order_id: string | null;
  ccp_id: string | null;
  deviation_id: string | null;
  title: string;
  explanation: string;
  recommendation: string;
  risk_level: RiskLevel | null;
  confidence_score: string | null;
  priority_score: number | null;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface QMSDashboard {
  total_inspections: number;
  pending_inspections: number;
  passed_today: number;
  failed_today: number;
  conditional_today: number;
  pass_rate_7d: number;
  open_deviations: number;
  critical_deviations: number;
  open_corrective_actions: number;
  overdue_corrective_actions: number;
  active_ccps: number;
  ccp_violations_7d: number;
  lots_on_hold: number;
  lots_quarantined: number;
  lots_pending_release: number;
  allergen_validations_pending: number;
  ai_recommendations_pending: number;
}

export interface QCGateCheck {
  lot_id: string;
  stage: string | null;
  blocked: boolean;
  reason: string | null;
  inspection_id: string | null;
  inspection_no: string | null;
  inspection_status: string | null;
}

// ── Color Maps ────────────────────────────────────────────────────────────────

export const RISK_BG: Record<RiskLevel, string> = {
  LOW: "bg-green-100 text-green-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800",
};

export const STATUS_BG: Record<string, string> = {
  OPEN: "bg-red-100 text-red-800",
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  VERIFIED: "bg-teal-100 text-teal-800",
  OVERDUE: "bg-red-200 text-red-900",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
  RESOLVED: "bg-green-100 text-green-800",
  CLOSED: "bg-gray-100 text-gray-600",
  PASSED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
  PENDING: "bg-yellow-100 text-yellow-800",
  CONDITIONAL_RELEASE: "bg-orange-100 text-orange-800",
  CANCELLED: "bg-gray-100 text-gray-600",
};

export const RELEASE_BG: Record<ReleaseStatus, string> = {
  UNRELEASED: "bg-gray-100 text-gray-600",
  QUARANTINED: "bg-red-100 text-red-800",
  ON_HOLD: "bg-orange-100 text-orange-800",
  RELEASED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-200 text-red-900",
  REWORK: "bg-purple-100 text-purple-800",
  SCRAPPED: "bg-gray-200 text-gray-700",
};

// ── API Client ────────────────────────────────────────────────────────────────

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...authHeader() },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface CalibrationRecord {
  id: string;
  instrument_id: string;
  instrument_name: string;
  instrument_type: string;
  location?: string;
  serial_no?: string;
  last_calibration_date?: string;
  next_calibration_due?: string;
  calibration_interval_days: number;
  calibration_authority?: string;
  certificate_ref?: string;
  status: string;
  days_until_due?: number;
  is_overdue: boolean;
  is_active: boolean;
  notes?: string;
}

export interface AQLPlan {
  id: string;
  plan_code: string;
  plan_name: string;
  product_name?: string;
  lot_size_min: number;
  lot_size_max?: number;
  sample_size: number;
  aql_level: string;
  aql_value: number;
  acceptance_number: number;
  rejection_number: number;
  inspection_level: string;
  applies_to_type: string;
  is_active: boolean;
  notes?: string;
}

export interface CoARecord {
  id: string;
  coa_no: string;
  lot_id: string;
  lot_number?: string;
  batch_no?: string;
  product_name?: string;
  issue_date: string;
  valid_until?: string;
  manufacture_date?: string;
  expiry_date?: string;
  overall_result?: string;
  status: string;
  notes?: string;
}

export const qmsApi = {
  // Dashboard
  getDashboard: () => apiFetch<QMSDashboard>(`${BASE}/dashboard`),

  // Gate check
  gateCheck: (lot_id: string, stage?: string) =>
    apiFetch<QCGateCheck>(`${BASE}/gate-check?lot_id=${lot_id}${stage ? `&stage=${stage}` : ""}`),

  // Templates
  listTemplates: (params?: { qc_type?: QCType; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.qc_type) q.set("qc_type", params.qc_type);
    if (params?.active_only !== undefined) q.set("active_only", String(params.active_only));
    return apiFetch<QCTemplate[]>(`${BASE}/templates?${q}`);
  },
  createTemplate: (body: Record<string, unknown>) =>
    apiFetch<QCTemplate>(`${BASE}/templates`, { method: "POST", body: JSON.stringify(body) }),
  getTemplate: (id: string) => apiFetch<QCTemplate>(`${BASE}/templates/${id}`),
  updateTemplate: (id: string, body: Record<string, unknown>) =>
    apiFetch<QCTemplate>(`${BASE}/templates/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTemplate: (id: string) => apiFetch<void>(`${BASE}/templates/${id}`, { method: "DELETE" }),

  // Hazard Analysis
  listHazards: (params?: { product_id?: string; is_ccp?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.product_id) q.set("product_id", params.product_id);
    if (params?.is_ccp !== undefined) q.set("is_ccp", String(params.is_ccp));
    return apiFetch<HazardAnalysis[]>(`${BASE}/haccp/hazards?${q}`);
  },
  createHazard: (body: Record<string, unknown>) =>
    apiFetch<HazardAnalysis>(`${BASE}/haccp/hazards`, { method: "POST", body: JSON.stringify(body) }),
  updateHazard: (id: string, body: Record<string, unknown>) =>
    apiFetch<HazardAnalysis>(`${BASE}/haccp/hazards/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  // CCPs
  listCCPs: (params?: { product_id?: string; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.product_id) q.set("product_id", params.product_id);
    if (params?.active_only !== undefined) q.set("active_only", String(params.active_only));
    return apiFetch<CriticalControlPoint[]>(`${BASE}/haccp/ccp?${q}`);
  },
  createCCP: (body: Record<string, unknown>) =>
    apiFetch<CriticalControlPoint>(`${BASE}/haccp/ccp`, { method: "POST", body: JSON.stringify(body) }),
  getCCP: (id: string) => apiFetch<CriticalControlPoint>(`${BASE}/haccp/ccp/${id}`),
  updateCCP: (id: string, body: Record<string, unknown>) =>
    apiFetch<CriticalControlPoint>(`${BASE}/haccp/ccp/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  // CCP Monitoring
  getCCPLogs: (ccp_id: string, limit = 50) =>
    apiFetch<CCPMonitoringLog[]>(`${BASE}/haccp/ccp/${ccp_id}/logs?limit=${limit}`),
  recordMonitoring: (body: Record<string, unknown>) =>
    apiFetch<CCPMonitoringLog>(`${BASE}/haccp/monitoring`, { method: "POST", body: JSON.stringify(body) }),
  listViolations: (limit = 50) =>
    apiFetch<CCPMonitoringLog[]>(`${BASE}/haccp/violations?limit=${limit}`),

  // Deviations
  listDeviations: (params?: { status?: DeviationStatus; severity?: RiskLevel; product_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.severity) q.set("severity", params.severity);
    if (params?.product_id) q.set("product_id", params.product_id);
    return apiFetch<QCDeviation[]>(`${BASE}/deviations?${q}`);
  },
  createDeviation: (body: Record<string, unknown>) =>
    apiFetch<QCDeviation>(`${BASE}/deviations`, { method: "POST", body: JSON.stringify(body) }),
  getDeviation: (id: string) => apiFetch<QCDeviation>(`${BASE}/deviations/${id}`),
  updateDeviation: (id: string, body: Record<string, unknown>) =>
    apiFetch<QCDeviation>(`${BASE}/deviations/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  // Corrective Actions
  listCAs: (params?: { status?: CorrectiveActionStatus; severity?: RiskLevel }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.severity) q.set("severity", params.severity);
    return apiFetch<CorrectiveAction[]>(`${BASE}/corrective-actions?${q}`);
  },
  createCA: (body: Record<string, unknown>) =>
    apiFetch<CorrectiveAction>(`${BASE}/corrective-actions`, { method: "POST", body: JSON.stringify(body) }),
  getCA: (id: string) => apiFetch<CorrectiveAction>(`${BASE}/corrective-actions/${id}`),
  updateCA: (id: string, body: Record<string, unknown>) =>
    apiFetch<CorrectiveAction>(`${BASE}/corrective-actions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  completeStep: (ca_id: string, step_id: string, notes?: string) =>
    apiFetch<CorrectiveAction>(
      `${BASE}/corrective-actions/${ca_id}/steps/${step_id}/complete${notes ? `?completion_notes=${encodeURIComponent(notes)}` : ""}`,
      { method: "POST" }
    ),
  verifyCA: (ca_id: string, effectiveness_check: string) =>
    apiFetch<CorrectiveAction>(
      `${BASE}/corrective-actions/${ca_id}/verify?effectiveness_check=${encodeURIComponent(effectiveness_check)}`,
      { method: "POST" }
    ),

  // Lot Quality Status
  getLotStatus: (lot_id: string) => apiFetch<LotQualityStatus>(`${BASE}/lot-status/${lot_id}`),
  listLotStatuses: (params?: { release_status?: ReleaseStatus; hold_flag?: boolean; quarantine_flag?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.release_status) q.set("release_status", params.release_status);
    if (params?.hold_flag !== undefined) q.set("hold_flag", String(params.hold_flag));
    if (params?.quarantine_flag !== undefined) q.set("quarantine_flag", String(params.quarantine_flag));
    return apiFetch<LotQualityStatus[]>(`${BASE}/lot-status?${q}`);
  },
  releaseLot: (lot_id: string, notes?: string) =>
    apiFetch<LotQualityStatus>(`${BASE}/lot-status/release`, {
      method: "POST",
      body: JSON.stringify({ lot_id, release_notes: notes }),
    }),
  holdLot: (body: { lot_id: string; hold_reason: string; quarantine?: boolean; quarantine_location?: string }) =>
    apiFetch<LotQualityStatus>(`${BASE}/lot-status/hold`, { method: "POST", body: JSON.stringify(body) }),

  // Allergen Validations
  listAllergenValidations: (production_order_id?: string) => {
    const q = production_order_id ? `?production_order_id=${production_order_id}` : "";
    return apiFetch<AllergenValidationRecord[]>(`${BASE}/allergen-validations${q}`);
  },
  createAllergenValidation: (body: Record<string, unknown>) =>
    apiFetch<AllergenValidationRecord>(`${BASE}/allergen-validations`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // AI
  listAIRecs: (params?: { agent_type?: QMSAIAgentType; status?: QMSAIRecStatus }) => {
    const q = new URLSearchParams();
    if (params?.agent_type) q.set("agent_type", params.agent_type);
    if (params?.status) q.set("status", params.status);
    return apiFetch<QMSAIRecommendation[]>(`${BASE}/ai/recommendations?${q}`);
  },
  runQualityRisk: (production_order_id?: string, lot_id?: string) => {
    const q = new URLSearchParams();
    if (production_order_id) q.set("production_order_id", production_order_id);
    if (lot_id) q.set("lot_id", lot_id);
    return apiFetch<QMSAIRecommendation[]>(`${BASE}/ai/run/quality-risk?${q}`, { method: "POST" });
  },
  runDeviationAnalyzer: (product_id?: string) =>
    apiFetch<QMSAIRecommendation[]>(
      `${BASE}/ai/run/deviation-analyzer${product_id ? `?product_id=${product_id}` : ""}`,
      { method: "POST" }
    ),
  runHACCPAssistant: (product_id?: string) =>
    apiFetch<QMSAIRecommendation[]>(
      `${BASE}/ai/run/haccp-assistant${product_id ? `?product_id=${product_id}` : ""}`,
      { method: "POST" }
    ),
  reviewAIRec: (id: string, status: QMSAIRecStatus, review_note?: string) =>
    apiFetch<QMSAIRecommendation>(`${BASE}/ai/recommendations/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ status, review_note }),
    }),

  // Reports
  getQCSummaryReport: (params?: { from_date?: string; to_date?: string; qc_type?: QCType }) => {
    const q = new URLSearchParams();
    if (params?.from_date) q.set("from_date", params.from_date);
    if (params?.to_date) q.set("to_date", params.to_date);
    if (params?.qc_type) q.set("qc_type", params.qc_type);
    return apiFetch<Record<string, unknown>>(`${BASE}/reports/qc-summary?${q}`);
  },
  getCCPViolationReport: (from_date?: string, to_date?: string) => {
    const q = new URLSearchParams();
    if (from_date) q.set("from_date", from_date);
    if (to_date) q.set("to_date", to_date);
    return apiFetch<Record<string, unknown>>(`${BASE}/reports/ccp-violations?${q}`);
  },
  getDeviationReport: (from_date?: string, to_date?: string) => {
    const q = new URLSearchParams();
    if (from_date) q.set("from_date", from_date);
    if (to_date) q.set("to_date", to_date);
    return apiFetch<Record<string, unknown>>(`${BASE}/reports/deviations?${q}`);
  },
  getLotQualityReport: () => apiFetch<Record<string, unknown>>(`${BASE}/reports/lot-quality`),

  // Instrument Calibration
  listCalibrations: (status?: string) => {
    const q = status ? `?status=${status}` : "";
    return apiFetch<CalibrationRecord[]>(`${BASE}/calibration${q}`);
  },
  createCalibration: (body: Record<string, unknown>) =>
    apiFetch<{ id: string; instrument_id: string; status: string }>(`${BASE}/calibration`, {
      method: "POST", body: JSON.stringify(body),
    }),
  updateCalibration: (id: string, body: Record<string, unknown>) =>
    apiFetch<{ id: string; status: string }>(`${BASE}/calibration/${id}`, {
      method: "PATCH", body: JSON.stringify(body),
    }),

  // AQL Sampling Plans
  listAQLPlans: (active_only = true) =>
    apiFetch<AQLPlan[]>(`${BASE}/aql-plans?active_only=${active_only}`),
  createAQLPlan: (body: Record<string, unknown>) =>
    apiFetch<{ id: string; plan_code: string }>(`${BASE}/aql-plans`, {
      method: "POST", body: JSON.stringify(body),
    }),
  updateAQLPlan: (id: string, body: Record<string, unknown>) =>
    apiFetch<{ id: string; plan_code: string }>(`${BASE}/aql-plans/${id}`, {
      method: "PATCH", body: JSON.stringify(body),
    }),

  // Certificate of Analysis
  listCoA: (params?: { lot_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.lot_id) q.set("lot_id", params.lot_id);
    if (params?.status) q.set("status", params.status);
    return apiFetch<CoARecord[]>(`${BASE}/coa?${q}`);
  },
  createCoA: (body: Record<string, unknown>) =>
    apiFetch<{ id: string; coa_no: string; status: string }>(`${BASE}/coa`, {
      method: "POST", body: JSON.stringify(body),
    }),
  issueCoA: (id: string) =>
    apiFetch<{ id: string; coa_no: string; status: string }>(`${BASE}/coa/${id}/issue`, {
      method: "POST",
    }),
};
