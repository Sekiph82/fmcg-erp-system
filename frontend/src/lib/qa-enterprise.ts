import { apiClient } from "@/lib/api";

const BASE = "/api/v1/quality-enterprise";

export type QCType = "INCOMING" | "IN_PROCESS" | "FINISHED_GOODS" | "RETEST";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ChangeType = "SPECIFICATION" | "QC_PLAN" | "TEST_METHOD" | "PROCESS" | "OTHER";
export type ChangeStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED" | "IMPLEMENTED" | "CLOSED" | "CANCELLED";
export type CostCategory = "PREVENTION" | "APPRAISAL" | "INTERNAL_FAILURE" | "EXTERNAL_FAILURE";

export interface TestMethod {
  id: string;
  method_code: string;
  version: number;
  name: string;
  standard_reference: string | null;
  instrument_type: string | null;
  requires_instrument: boolean;
  required_skill_id: string | null;
  is_active: boolean;
}

export interface ChangeRequest {
  id: string;
  cr_no: string;
  title: string;
  change_type: ChangeType;
  target_reference: string | null;
  status: ChangeStatus;
  requested_by_id: string;
  decided_by_id: string | null;
  decided_at: string | null;
  implemented_at: string | null;
  closed_at: string | null;
}

export interface Specification {
  id: string;
  spec_code: string;
  version: number;
  name: string;
  scope_type: "PRODUCT" | "MATERIAL" | "PROCESS";
  product_id: string | null;
  material_id: string | null;
  process_stage: string | null;
  template_id: string;
  status: "DRAFT" | "APPROVED" | "SUPERSEDED" | "RETIRED";
  effective_from: string;
  effective_to: string | null;
  change_request_id: string | null;
  created_by_id: string;
  approved_by_id: string | null;
  approved_at: string | null;
}

export interface PlanStep {
  sequence: number;
  qc_type: QCType;
  qc_sub_type?: string | null;
  spec_code?: string | null;
  is_mandatory: boolean;
}

export interface QCPlan {
  id: string;
  plan_code: string;
  version: number;
  name: string;
  product_id: string | null;
  material_id: string | null;
  status: "DRAFT" | "ACTIVE" | "RETIRED";
  created_by_id: string;
  approved_by_id: string | null;
  steps: PlanStep[];
}

export interface PlanCoverage {
  complete: boolean;
  missing_steps: number[];
  failed_steps: number[];
  steps: Array<PlanStep & { state: "SATISFIED" | "FAILED" | "IN_PROGRESS" | "NOT_STARTED" }>;
}

export interface AQLResult {
  plan_id: string;
  plan_code: string;
  sample_size: number;
  decision: "ACCEPT" | "REJECT" | "SECOND_SAMPLE" | "INCOMPLETE";
  reason?: string;
  acceptance_number?: number;
  rejection_number?: number;
  defects_found?: number;
}

export interface SPCViolation {
  index: number;
  rule: string;
  test_result_id: string;
  value: number;
}

export interface SPCAnalysis {
  n: number;
  limits: { center: number; sigma: number; ucl: number; lcl: number; mr_bar: number; mr_ucl: number };
  capability: { pp: number | null; ppk: number | null; mean?: number; stdev?: number };
  lsl: number | null;
  usl: number | null;
  violations: SPCViolation[];
  points?: Array<{ test_result_id: string; value: number; recorded_at: string | null }>;
}

export interface SPCEvaluation {
  analysis: SPCAnalysis;
  new_signals: number;
  deviation_id: string | null;
}

export interface Concession {
  id: string;
  concession_no: string;
  deviation_id: string;
  lot_id: string;
  quantity_limit: string | null;
  uom: string | null;
  conditions: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "REVOKED";
  valid_until: string | null;
  requested_by_id: string;
  decided_by_id: string | null;
  decided_at: string | null;
}

export interface QualityCostSummary {
  by_category: Record<CostCategory, string>;
  by_risk_level: Record<string, string>;
  cost_of_good_quality: string;
  cost_of_poor_quality: string;
  total: string;
  copq_share_pct: string | null;
  currencies: string[];
  mixed_currency: boolean;
}

export interface RetainSample {
  id: string;
  sample_no: string;
  lot_id: string;
  quantity: string;
  quantity_remaining: string;
  uom: string;
  storage_location: string;
  collected_on: string;
  retain_until: string;
  status: "STORED" | "DEPLETED" | "DISPOSED";
}

export interface CapaLink {
  id: string;
  ca_no: string;
  title: string;
  status: string;
  severity: string;
  due_date: string | null;
}

const get = async <T,>(path: string, params?: Record<string, unknown>) =>
  (await apiClient.get<T>(`${BASE}${path}`, { params })).data;
const post = async <T,>(path: string, body?: unknown, params?: Record<string, unknown>) =>
  (await apiClient.post<T>(`${BASE}${path}`, body, { params })).data;

export const qaEnterpriseApi = {
  listTestMethods: () => get<TestMethod[]>("/test-methods"),
  createTestMethod: (body: Partial<TestMethod>) => post<TestMethod>("/test-methods", body),
  linkParameterMethod: async (parameterId: string, testMethodId: string | null) =>
    (await apiClient.put(`${BASE}/template-parameters/${parameterId}/test-method`, null, {
      params: testMethodId ? { test_method_id: testMethodId } : {},
    })).data,

  listChangeRequests: () => get<ChangeRequest[]>("/change-requests"),
  createChangeRequest: (body: Record<string, unknown>) => post<ChangeRequest>("/change-requests", body),
  transitionChangeRequest: (id: string, status: ChangeStatus, notes?: string) =>
    post<ChangeRequest>(`/change-requests/${id}/transition`, { status, notes }),

  listSpecifications: () => get<Specification[]>("/specifications"),
  createSpecification: (body: Record<string, unknown>) => post<Specification>("/specifications", body),
  approveSpecification: (id: string) => post<Specification>(`/specifications/${id}/approve`),

  listPlans: () => get<QCPlan[]>("/qc-plans"),
  createPlan: (body: Record<string, unknown>) => post<QCPlan>("/qc-plans", body),
  activatePlan: (id: string) => post<QCPlan>(`/qc-plans/${id}/activate`),
  planCoverage: (id: string, params: { production_order_id?: string; lot_id?: string }) =>
    get<PlanCoverage>(`/qc-plans/${id}/coverage`, params),

  evaluateAql: (body: Record<string, unknown>) => post<AQLResult>("/aql/evaluate", body),
  spcChart: (params: { product_id: string; parameter_name: string; qc_type?: QCType; limit?: number }) =>
    get<SPCAnalysis>("/spc/chart", params),
  spcEvaluate: (params: { product_id: string; parameter_name: string; qc_type?: QCType }) =>
    post<SPCEvaluation>("/spc/evaluate", undefined, params),

  listConcessions: (lotId?: string) => get<Concession[]>("/concessions", lotId ? { lot_id: lotId } : undefined),
  requestConcession: (body: Record<string, unknown>) => post<Concession>("/concessions", body),
  decideConcession: (id: string, body: { approve: boolean; conditions?: string; valid_until?: string; notes?: string }) =>
    post<Concession>(`/concessions/${id}/decide`, body),
  revokeConcession: (id: string, notes: string) => post<Concession>(`/concessions/${id}/revoke`, undefined, { notes }),

  recordQualityCost: (body: Record<string, unknown>) => post("/quality-costs", body),
  qualityCostSummary: (params: { date_from?: string; date_to?: string }) =>
    get<QualityCostSummary>("/quality-costs/summary", params),

  listRetainSamples: (dueOnly: boolean) => get<RetainSample[]>("/retain-samples", { due_only: dueOnly }),
  registerRetainSample: (body: Record<string, unknown>) => post<RetainSample>("/retain-samples", body),
  withdrawRetainSample: (id: string, quantity: string, reason: string) =>
    post<RetainSample>(`/retain-samples/${id}/withdraw`, { quantity, reason }),
  disposeRetainSample: (id: string, reason: string) => post<RetainSample>(`/retain-samples/${id}/dispose`, { reason }),

  capaFromComplaint: (id: string) => post<{ corrective_action_id: string; ca_no: string; created: boolean }>(`/complaints/${id}/capa`),
  capaFromRecall: (id: string) => post<{ corrective_action_id: string; ca_no: string; created: boolean }>(`/recalls/${id}/capa`),
  capaLinks: (triggerType: string, triggerId: string) =>
    get<CapaLink[]>("/capa-links", { trigger_type: triggerType, trigger_id: triggerId }),
};

export function apiErrorMessage(error: unknown): string {
  const candidate = error as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = candidate.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d))).join("; ");
  }
  if (detail && typeof detail === "object" && "detail" in detail && typeof detail.detail === "string") return detail.detail;
  return candidate.message || "The request could not be completed.";
}
