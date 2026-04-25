import { apiClient } from "@/lib/api";

// ── Enums / Types ─────────────────────────────────────────────────────────────

export type MatchLineStatus =
  | "FULLY_MATCHED" | "MATCHED_WITHIN_TOLERANCE"
  | "QUANTITY_MISMATCH" | "PRICE_MISMATCH" | "TAX_MISMATCH"
  | "MISSING_PO" | "MISSING_GRN" | "PARTIAL_MATCH" | "OVERBILLED"
  | "BLOCKED" | "APPROVED_EXCEPTION" | "REJECTED";

export type MatchOverallStatus =
  | "FULLY_MATCHED" | "MATCHED_WITHIN_TOLERANCE" | "PARTIAL_MATCH"
  | "QUANTITY_MISMATCH" | "PRICE_MISMATCH" | "MISSING_PO" | "MISSING_GRN"
  | "DUPLICATE_SUSPECTED" | "BLOCKED" | "APPROVED_EXCEPTION"
  | "REJECTED" | "PENDING_REVIEW";

export type IMAIAgentType = "ANOMALY_DETECTOR" | "EXCEPTION_PRIORITIZER" | "TOLERANCE_TUNER";
export type IMAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED";
export type DuplicateRisk = "EXACT" | "SUSPECTED" | "LOW";

// ── Interfaces ────────────────────────────────────────────────────────────────

export interface ToleranceRule {
  id: string;
  rule_name: string;
  supplier_id: string | null;
  item_category: string | null;
  quantity_tolerance_pct: number;
  quantity_tolerance_abs: number | null;
  price_tolerance_pct: number;
  price_tolerance_abs: number | null;
  tax_tolerance_pct: number;
  auto_approve_within_tolerance: boolean;
  block_payment_beyond_tolerance: boolean;
  approval_role_required: string | null;
  is_active: boolean;
  priority: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MatchGRNLink {
  id: string;
  grn_id: string | null;
  grn_line_id: string | null;
  grn_no: string | null;
  received_qty: number | null;
  accepted_qty: number | null;
  rejected_qty: number | null;
  received_date: string | null;
}

export interface MatchLine {
  id: string;
  header_id: string;
  invoice_line_id: string | null;
  po_line_id: string | null;
  material_id: string | null;
  material_name: string | null;
  description: string | null;
  ordered_qty: number | null;
  ordered_unit_price: number | null;
  ordered_tax_rate: number | null;
  total_received_qty: number | null;
  total_accepted_qty: number | null;
  prev_invoiced_qty: number;
  billable_qty: number | null;
  invoiced_qty: number | null;
  invoiced_unit_price: number | null;
  invoiced_tax_rate: number | null;
  invoiced_line_total: number | null;
  qty_variance: number | null;
  price_variance: number | null;
  tax_variance: number | null;
  qty_variance_pct: number | null;
  price_variance_pct: number | null;
  match_status: MatchLineStatus;
  tolerance_rule_id: string | null;
  action_required: boolean;
  notes: string | null;
  grn_links: MatchGRNLink[];
}

export interface MatchReview {
  id: string;
  header_id: string;
  action: string;
  reviewer_name: string;
  reviewer_role: string | null;
  previous_status: string | null;
  new_status: string | null;
  justification: string | null;
  created_at: string;
}

export interface MatchHeaderSummary {
  id: string;
  match_no: string;
  invoice_id: string;
  po_id: string | null;
  supplier_id: string | null;
  invoice_no: string | null;
  invoice_date: string | null;
  currency: string;
  invoice_total: number;
  overall_status: MatchOverallStatus;
  duplicate_flag: boolean;
  review_required: boolean;
  is_payable: boolean;
  payment_hold_reason: string | null;
  run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MatchHeaderOut extends MatchHeaderSummary {
  reviewed_by: string | null;
  reviewed_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  notes: string | null;
  match_lines: MatchLine[];
  reviews: MatchReview[];
}

export interface DuplicateLog {
  id: string;
  invoice_id: string;
  matched_invoice_id: string | null;
  invoice_no: string | null;
  matched_invoice_no: string | null;
  duplicate_risk: DuplicateRisk;
  match_reasons: string[] | null;
  similarity_score: number | null;
  is_resolved: boolean;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
}

export interface IMAIRec {
  id: string;
  header_id: string | null;
  agent_type: IMAIAgentType;
  status: IMAIRecStatus;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  suggested_action: string | null;
  priority: string;
  confidence_score: number | null;
  actioned_at: string | null;
  created_at: string;
}

export interface IMDashboard {
  total_matches: number;
  fully_matched: number;
  within_tolerance: number;
  mismatched: number;
  blocked: number;
  pending_review: number;
  duplicate_suspected: number;
  payable_count: number;
  on_hold_count: number;
  pending_ai_recs: number;
  mismatch_by_type: { type: string; count: number }[];
  recent_matches: MatchHeaderSummary[];
}

// ── Color / Label maps ────────────────────────────────────────────────────────

export const MATCH_STATUS_COLOR: Record<MatchOverallStatus, string> = {
  FULLY_MATCHED:            "bg-green-100 text-green-700",
  MATCHED_WITHIN_TOLERANCE: "bg-teal-100 text-teal-700",
  PARTIAL_MATCH:            "bg-yellow-100 text-yellow-700",
  QUANTITY_MISMATCH:        "bg-orange-100 text-orange-700",
  PRICE_MISMATCH:           "bg-red-100 text-red-700",
  MISSING_PO:               "bg-red-200 text-red-800",
  MISSING_GRN:              "bg-red-200 text-red-800",
  DUPLICATE_SUSPECTED:      "bg-purple-100 text-purple-700",
  BLOCKED:                  "bg-red-600 text-white",
  APPROVED_EXCEPTION:       "bg-blue-100 text-blue-700",
  REJECTED:                 "bg-gray-300 text-gray-700",
  PENDING_REVIEW:           "bg-yellow-200 text-yellow-800",
};

export const LINE_STATUS_COLOR: Record<MatchLineStatus, string> = {
  FULLY_MATCHED:            "bg-green-100 text-green-700",
  MATCHED_WITHIN_TOLERANCE: "bg-teal-100 text-teal-700",
  QUANTITY_MISMATCH:        "bg-orange-100 text-orange-700",
  PRICE_MISMATCH:           "bg-red-100 text-red-700",
  TAX_MISMATCH:             "bg-amber-100 text-amber-700",
  MISSING_PO:               "bg-red-200 text-red-800",
  MISSING_GRN:              "bg-rose-100 text-rose-700",
  PARTIAL_MATCH:            "bg-yellow-100 text-yellow-700",
  OVERBILLED:               "bg-red-600 text-white",
  BLOCKED:                  "bg-red-600 text-white",
  APPROVED_EXCEPTION:       "bg-blue-100 text-blue-700",
  REJECTED:                 "bg-gray-300 text-gray-700",
};

export const AI_PRIORITY_COLOR: Record<string, string> = {
  LOW:      "bg-gray-100 text-gray-600",
  MEDIUM:   "bg-yellow-100 text-yellow-700",
  HIGH:     "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

export const AI_AGENT_LABEL: Record<IMAIAgentType, string> = {
  ANOMALY_DETECTOR:      "Anomaly Detector",
  EXCEPTION_PRIORITIZER: "Exception Prioritizer",
  TOLERANCE_TUNER:       "Tolerance Tuner",
};

export function varColor(pct: number | null): string {
  if (pct === null) return "text-gray-400";
  const abs = Math.abs(pct);
  if (abs === 0) return "text-green-600";
  if (abs <= 2) return "text-yellow-600";
  if (abs <= 5) return "text-orange-600";
  return "text-red-600";
}

export function fmtVar(v: number | null, suffix = ""): string {
  if (v === null || v === undefined) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}${suffix}`;
}

// ── API ───────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/invoice-match";

export const imApi = {
  getDashboard: () => apiClient.get<IMDashboard>(`${BASE}/dashboard`),

  // Matching
  runMatch: (invoice_id: string, force_rerun = false) =>
    apiClient.post<MatchHeaderOut>(`${BASE}/run`, { invoice_id, force_rerun }),

  // List / Get
  list: (params?: { status?: string; review_required?: boolean; duplicate_flag?: boolean }) => {
    const qs = new URLSearchParams(
      Object.entries(params || {})
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return apiClient.get<MatchHeaderSummary[]>(`${BASE}${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiClient.get<MatchHeaderOut>(`${BASE}/${id}`),
  getBlockedInvoices: () => apiClient.get<MatchHeaderSummary[]>(`${BASE}/blocked-invoices`),
  getDuplicateSuspicions: () => apiClient.get<DuplicateLog[]>(`${BASE}/duplicate-suspicions`),

  // Review
  review: (id: string, body: Record<string, unknown>) =>
    apiClient.post<MatchHeaderOut>(`${BASE}/${id}/review`, body),
  approveException: (id: string, reviewer_name: string, justification: string) =>
    apiClient.post<MatchHeaderOut>(`${BASE}/${id}/approve-exception`, { reviewer_name, justification }),
  reject: (id: string, reviewer_name: string, justification: string) =>
    apiClient.post<MatchHeaderOut>(`${BASE}/${id}/reject`, { reviewer_name, justification }),

  // Duplicates
  resolveDuplicate: (dupId: string, resolved_by: string, resolution_notes: string) =>
    apiClient.post<DuplicateLog>(`${BASE}/duplicate-suspicions/${dupId}/resolve`, { resolved_by, resolution_notes }),

  // Tolerance rules
  listToleranceRules: (active_only = false) =>
    apiClient.get<ToleranceRule[]>(`${BASE}/tolerance-rules${active_only ? "?active_only=true" : ""}`),
  createToleranceRule: (body: Record<string, unknown>) =>
    apiClient.post<ToleranceRule>(`${BASE}/tolerance-rules`, body),
  updateToleranceRule: (id: string, body: Record<string, unknown>) =>
    apiClient.patch<ToleranceRule>(`${BASE}/tolerance-rules/${id}`, body),

  // Reports
  reportMismatchSummary: () =>
    apiClient.get<Record<string, unknown>[]>(`${BASE}/reports/mismatch-summary`),
  reportSupplierAccuracy: () =>
    apiClient.get<Record<string, unknown>[]>(`${BASE}/reports/supplier-accuracy`),

  // AI
  runAI: () => apiClient.post<{ recommendations_created: number }>(`${BASE}/ai/run`, {}),
  runAIForMatch: (id: string) => apiClient.post<{ recommendations_created: number }>(`${BASE}/${id}/ai/run`, {}),
  listAIRecs: (params?: { status?: string }) => {
    const qs = params?.status ? `?status=${params.status}` : "";
    return apiClient.get<IMAIRec[]>(`${BASE}/ai/recs${qs}`);
  },
  actionAIRec: (recId: string, status: "ACCEPTED" | "REJECTED") =>
    apiClient.post<IMAIRec>(`${BASE}/ai/recs/${recId}/action`, { status }),
};
