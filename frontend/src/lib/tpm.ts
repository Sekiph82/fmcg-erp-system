import axios from "axios";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";
const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);
const ax = axios.create({ baseURL: API });

// ── Enums & Types ──────────────────────────────────────────────────────────────

export type TPMPeriodType    = "ANNUAL" | "QUARTERLY" | "MONTHLY" | "EVENT_BASED";
export type TPMPlanStatus    = "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "ACTIVE" | "CLOSED" | "ARCHIVED";
export type TPMPromotionType = "DISCOUNT" | "FREE_GOODS" | "VISIBILITY" | "DISPLAY" | "REBATE" | "OFF_INVOICE" | "BILL_BACK" | "LISTING_FEE" | "BUNDLE" | "EVENT" | "CUSTOM";
export type TPMObjectiveType = "VOLUME" | "MARKET_SHARE" | "DISTRIBUTION_GAIN" | "STOCK_CLEARANCE" | "LAUNCH_SUPPORT" | "RETENTION" | "SEASONAL_PUSH" | "CHANNEL_ACTIVATION";
export type TPMPromotionStatus = "DRAFT" | "PROPOSED" | "APPROVED" | "ACTIVE" | "COMPLETED" | "CANCELLED" | "SETTLED" | "ARCHIVED";
export type TPMBudgetType    = "DISCOUNT_BUDGET" | "FREE_GOODS_BUDGET" | "DISPLAY_BUDGET" | "REBATE_BUDGET" | "LISTING_FEE_BUDGET" | "MIXED";
export type TPMBaselineMethod = "PRIOR_PERIOD" | "SAME_PERIOD_LAST_YEAR" | "ROLLING_AVERAGE" | "MANUAL";
export type TPMClaimantType  = "CUSTOMER" | "DISTRIBUTOR" | "INTERNAL";
export type TPMClaimType     = "REBATE" | "DEDUCTION" | "BILL_BACK" | "DISPLAY_FEE" | "LISTING_FEE" | "FREE_GOODS_ADJUSTMENT" | "OFF_INVOICE_RECONCILIATION" | "CUSTOM";
export type TPMClaimStatus   = "DRAFT" | "SUBMITTED" | "UNDER_REVIEW" | "APPROVED" | "PARTIALLY_SETTLED" | "SETTLED" | "REJECTED" | "CANCELLED";
export type TPMAIAgentType   = "ROI_ANALYST" | "BUDGET_RISK_MONITOR" | "PLANNER_ASSISTANT";
export type TPMAIRecStatus   = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

// ── Interfaces ─────────────────────────────────────────────────────────────────

export interface TPMBudgetLine {
  id: string;
  tpm_promotion_id: string;
  budget_type: TPMBudgetType;
  planned_spend_amount: number;
  approved_spend_amount: number;
  actual_spend_amount: number;
  accrued_spend_amount: number;
  settled_spend_amount: number;
  remaining_budget_amount: number;
  cost_center_id?: string;
  notes?: string;
}

export interface TPMExpectedPerf {
  id: string;
  tpm_promotion_id: string;
  baseline_volume: number;
  target_volume: number;
  expected_uplift_qty: number;
  expected_uplift_pct: number;
  expected_revenue: number;
  expected_margin_impact: number;
  expected_roi_pct: number;
  baseline_method: TPMBaselineMethod;
  assumptions?: string;
  notes?: string;
}

export interface TPMActualPerf {
  id: string;
  tpm_promotion_id: string;
  actual_volume: number;
  actual_uplift_qty: number;
  actual_uplift_pct: number;
  actual_revenue: number;
  actual_margin_impact: number;
  actual_spend: number;
  actual_roi_pct: number;
  post_event_notes?: string;
}

export interface TPMPromotion {
  id: string;
  promotion_code: string;
  promotion_name: string;
  tpm_plan_id?: string;
  linked_scheme_id?: string;
  promotion_type: TPMPromotionType;
  objective_type: TPMObjectiveType;
  status: TPMPromotionStatus;
  valid_from: string;
  valid_to: string;
  brand_id?: string;
  category_id?: string;
  channel_id?: string;
  region_id?: string;
  customer_id?: string;
  distributor_group_id?: string;
  notes?: string;
  created_at: string;
  budget_lines: TPMBudgetLine[];
  expected_perf?: TPMExpectedPerf;
  actual_perf?: TPMActualPerf;
  claims?: TPMClaim[];
}

export interface TPMPlan {
  id: string;
  plan_code: string;
  plan_name: string;
  fiscal_year: number;
  period_type: TPMPeriodType;
  plan_start_date: string;
  plan_end_date: string;
  status: TPMPlanStatus;
  total_planned_budget: number;
  total_approved_budget: number;
  total_actual_spend: number;
  notes?: string;
  created_at: string;
  promotion_count: number;
}

export interface TPMClaimLine {
  id: string;
  tpm_claim_id: string;
  source_order_id?: string;
  source_scheme_id?: string;
  item_id?: string;
  quantity_basis?: number;
  rate_basis?: number;
  claimed_amount: number;
  approved_amount: number;
  supporting_doc_ref?: string;
  notes?: string;
}

export interface TPMClaim {
  id: string;
  claim_no: string;
  tpm_promotion_id: string;
  claimant_type: TPMClaimantType;
  claimant_id?: string;
  claim_date: string;
  claim_type: TPMClaimType;
  claimed_amount: number;
  approved_amount: number;
  rejected_amount: number;
  settled_amount: number;
  status: TPMClaimStatus;
  reference_document_no?: string;
  reviewer_notes?: string;
  notes?: string;
  created_at: string;
  claim_lines: TPMClaimLine[];
}

export interface TPMAIRec {
  id: string;
  agent_type: TPMAIAgentType;
  tpm_promotion_id?: string;
  tpm_claim_id?: string;
  title: string;
  detail?: string;
  severity?: string;
  status: TPMAIRecStatus;
  actioned_notes?: string;
  created_at: string;
}

export interface TPMDashboard {
  active_plans: number;
  active_promotions: number;
  total_planned_budget: number;
  total_actual_spend: number;
  open_claims: number;
  open_claims_amount: number;
  pending_approvals: number;
  promotions_by_status: Record<string, number>;
  top_promotions: Array<{
    id: string;
    promotion_code: string;
    promotion_name: string;
    status: string;
    valid_from: string;
    valid_to: string;
  }>;
}

// ── Labels ─────────────────────────────────────────────────────────────────────

export const PERIOD_TYPE_LABEL: Record<TPMPeriodType, string> = {
  ANNUAL:      "Annual",
  QUARTERLY:   "Quarterly",
  MONTHLY:     "Monthly",
  EVENT_BASED: "Event-Based",
};

export const PLAN_STATUS_BADGE: Record<TPMPlanStatus, string> = {
  DRAFT:        "bg-gray-100 text-gray-600",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-700",
  APPROVED:     "bg-blue-100 text-blue-700",
  ACTIVE:       "bg-green-100 text-green-700",
  CLOSED:       "bg-red-100 text-red-600",
  ARCHIVED:     "bg-gray-100 text-gray-500",
};

export const PROMOTION_TYPE_LABEL: Record<TPMPromotionType, string> = {
  DISCOUNT:    "Discount",
  FREE_GOODS:  "Free Goods",
  VISIBILITY:  "Visibility",
  DISPLAY:     "Display",
  REBATE:      "Rebate",
  OFF_INVOICE: "Off-Invoice",
  BILL_BACK:   "Bill-Back",
  LISTING_FEE: "Listing Fee",
  BUNDLE:      "Bundle",
  EVENT:       "Event",
  CUSTOM:      "Custom",
};

export const OBJECTIVE_TYPE_LABEL: Record<TPMObjectiveType, string> = {
  VOLUME:             "Volume Growth",
  MARKET_SHARE:       "Market Share",
  DISTRIBUTION_GAIN:  "Distribution Gain",
  STOCK_CLEARANCE:    "Stock Clearance",
  LAUNCH_SUPPORT:     "Launch Support",
  RETENTION:          "Retention",
  SEASONAL_PUSH:      "Seasonal Push",
  CHANNEL_ACTIVATION: "Channel Activation",
};

export const PROMOTION_STATUS_BADGE: Record<TPMPromotionStatus, string> = {
  DRAFT:     "bg-gray-100 text-gray-600",
  PROPOSED:  "bg-yellow-100 text-yellow-700",
  APPROVED:  "bg-blue-100 text-blue-700",
  ACTIVE:    "bg-green-100 text-green-700",
  COMPLETED: "bg-indigo-100 text-indigo-700",
  CANCELLED: "bg-red-100 text-red-600",
  SETTLED:   "bg-teal-100 text-teal-700",
  ARCHIVED:  "bg-gray-100 text-gray-500",
};

export const CLAIM_STATUS_BADGE: Record<TPMClaimStatus, string> = {
  DRAFT:             "bg-gray-100 text-gray-600",
  SUBMITTED:         "bg-blue-100 text-blue-700",
  UNDER_REVIEW:      "bg-yellow-100 text-yellow-700",
  APPROVED:          "bg-green-100 text-green-700",
  PARTIALLY_SETTLED: "bg-orange-100 text-orange-700",
  SETTLED:           "bg-teal-100 text-teal-700",
  REJECTED:          "bg-red-100 text-red-600",
  CANCELLED:         "bg-gray-100 text-gray-500",
};

export const AGENT_LABEL: Record<TPMAIAgentType, string> = {
  ROI_ANALYST:         "ROI Analyst",
  BUDGET_RISK_MONITOR: "Budget Risk Monitor",
  PLANNER_ASSISTANT:   "Planner Assistant",
};

export const SEVERITY_BADGE: Record<string, string> = {
  info:     "bg-blue-100 text-blue-700",
  warning:  "bg-yellow-100 text-yellow-700",
  critical: "bg-red-100 text-red-700",
};

export const fmtCurrency = (n: number) =>
  `KES ${Number(n).toLocaleString("en-KE", { minimumFractionDigits: 2 })}`;

// ── API Client ─────────────────────────────────────────────────────────────────

export const tpmApi = {
  // Dashboard
  getDashboard: () => r<TPMDashboard>(ax.get("/tpm/dashboard")),

  // Plans
  getPlans: (status?: TPMPlanStatus, fiscal_year?: number) =>
    r<TPMPlan[]>(ax.get("/tpm/plans", { params: { status, fiscal_year } })),
  createPlan: (data: object) => r<TPMPlan>(ax.post("/tpm/plans", data)),
  getPlan: (id: string) => r<TPMPlan>(ax.get(`/tpm/plans/${id}`)),
  approvePlan: (id: string) => r<TPMPlan>(ax.post(`/tpm/plans/${id}/approve`)),
  updatePlanStatus: (id: string, status: TPMPlanStatus) =>
    r<TPMPlan>(ax.patch(`/tpm/plans/${id}/status`, null, { params: { status } })),

  // Promotions
  getPromotions: (params?: { status?: string; plan_id?: string; promotion_type?: string; channel_id?: string; brand_id?: string }) =>
    r<TPMPromotion[]>(ax.get("/tpm/promotions", { params })),
  createPromotion: (data: object) => r<TPMPromotion>(ax.post("/tpm/promotions", data)),
  getPromotion: (id: string) => r<TPMPromotion>(ax.get(`/tpm/promotions/${id}`)),
  approvePromotion: (id: string) => r<TPMPromotion>(ax.post(`/tpm/promotions/${id}/approve`)),
  updatePromotionStatus: (id: string, status: TPMPromotionStatus) =>
    r<TPMPromotion>(ax.patch(`/tpm/promotions/${id}/status`, null, { params: { status } })),
  linkScheme: (id: string, scheme_id: string) =>
    r<TPMPromotion>(ax.post(`/tpm/promotions/${id}/link-scheme`, null, { params: { scheme_id } })),

  // Budget Lines
  addBudgetLine: (promo_id: string, data: object) =>
    r<TPMBudgetLine[]>(ax.post(`/tpm/promotions/${promo_id}/budget-lines`, data)),

  // Performance
  setExpectedPerf: (promo_id: string, data: object) =>
    r<TPMExpectedPerf>(ax.put(`/tpm/promotions/${promo_id}/expected-perf`, data)),
  setActualPerf: (promo_id: string, data: object) =>
    r<TPMActualPerf>(ax.put(`/tpm/promotions/${promo_id}/actual-perf`, data)),
  getPerformance: (promo_id: string) =>
    r<{ expected?: TPMExpectedPerf; actual?: TPMActualPerf }>(ax.get(`/tpm/promotions/${promo_id}/performance`)),

  // Claims
  getClaims: (params?: { status?: string; promotion_id?: string }) =>
    r<TPMClaim[]>(ax.get("/tpm/claims", { params })),
  createClaim: (data: object) => r<TPMClaim>(ax.post("/tpm/claims", data)),
  getClaim: (id: string) => r<TPMClaim>(ax.get(`/tpm/claims/${id}`)),
  reviewClaim: (id: string, data: object) => r<TPMClaim>(ax.post(`/tpm/claims/${id}/review`, data)),
  settleClaim: (id: string, data: object) => r<TPMClaim>(ax.post(`/tpm/claims/${id}/settle`, data)),

  // Reports
  getROIReport: () => r<any[]>(ax.get("/tpm/reports/roi")),
  getBudgetVsActual: (fiscal_year?: number) =>
    r<any[]>(ax.get("/tpm/reports/budget-vs-actual", { params: { fiscal_year } })),
  getClaimAging: () => r<any[]>(ax.get("/tpm/reports/claim-aging")),

  // AI
  runAgents: () => r<{ generated: number }>(ax.post("/tpm/ai/run-agents")),
  getAIRecs: (status?: TPMAIRecStatus) =>
    r<TPMAIRec[]>(ax.get("/tpm/ai/recommendations", { params: { status } })),
  ackAIRec: (id: string, data: object) =>
    r<TPMAIRec>(ax.patch(`/tpm/ai/recommendations/${id}`, data)),
};
