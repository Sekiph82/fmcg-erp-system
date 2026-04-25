import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);
const ax = axios.create({ baseURL: API });

// ── Enums & Types ──────────────────────────────────────────────────────────────

export type SchemeStatus = "DRAFT" | "APPROVED" | "ACTIVE" | "EXPIRED" | "SUSPENDED" | "ARCHIVED";
export type SchemeType =
  | "BUY_X_GET_Y" | "PERCENT_DISCOUNT" | "FIXED_DISCOUNT" | "TIERED_DISCOUNT"
  | "QTY_BREAK_PRICE" | "SPEND_BASED" | "MIX_AND_MATCH" | "BUNDLE"
  | "FREE_GOODS_DIFF_SKU" | "CHANNEL_DEAL";
export type TriggerBasis = "SKU" | "CATEGORY" | "BRAND" | "ORDER_TOTAL" | "QUANTITY" | "VALUE" | "MIX_SET";
export type RewardType = "FREE_GOODS" | "PERCENT_DISCOUNT" | "FIXED_DISCOUNT" | "SPECIAL_PRICE" | "BUNDLE_PRICE";
export type PromoApplicationType = "AUTO" | "MANUAL_APPROVED" | "MANUAL_OVERRIDE" | "REJECTED";
export type PromoImpactType = "DISCOUNT" | "FREE_GOODS" | "SPECIAL_PRICE" | "ORDER_DISCOUNT" | "BUNDLE_ADJUSTMENT";
export type OverrideStatus = "PENDING" | "APPROVED" | "REJECTED";
export type PromoAIAgentType = "CONFLICT_ADVISOR" | "COST_MONITOR" | "UPSELL_ASSISTANT";
export type PromoAIRecStatus = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

// ── Interfaces ─────────────────────────────────────────────────────────────────

export interface PromoTierLine {
  id: string;
  min_qty?: number;
  max_qty?: number;
  min_value?: number;
  max_value?: number;
  reward_percent?: number;
  reward_amount?: number;
  unit_price?: number;
  sort_order: number;
}

export interface PromoRuleLine {
  id: string;
  scheme_id: string;
  trigger_basis: TriggerBasis;
  trigger_item_id?: string;
  trigger_item_name?: string;
  trigger_category?: string;
  trigger_brand?: string;
  min_trigger_qty: number;
  min_trigger_value: number;
  max_trigger_qty?: number;
  reward_type: RewardType;
  reward_item_id?: string;
  reward_item_name?: string;
  reward_qty?: number;
  reward_percent?: number;
  reward_amount?: number;
  reward_special_unit_price?: number;
  max_reward_qty?: number;
  repeatable: boolean;
  sort_order: number;
  notes?: string;
}

export interface PromoEligibility {
  id: string;
  scheme_id: string;
  applies_to_customer_id?: string;
  applies_to_customer_group?: string;
  applies_to_distributor_group?: string;
  applies_to_region?: string;
  applies_to_channel?: string;
  applies_to_item_category?: string;
  applies_to_brand?: string;
  min_order_qty?: number;
  min_order_value?: number;
  active: boolean;
}

export interface PromoScheme {
  id: string;
  scheme_code: string;
  scheme_name: string;
  scheme_type: SchemeType;
  status: SchemeStatus;
  valid_from: string;
  valid_to: string;
  priority_rank: number;
  stackable: boolean;
  exclusive: boolean;
  requires_approval_override: boolean;
  notes?: string;
  eligibility_scopes: PromoEligibility[];
  rule_lines: PromoRuleLine[];
  usage_count: number;
  total_cost: number;
}

export interface PromoLineImpact {
  id: string;
  impact_type: PromoImpactType;
  impacted_qty?: number;
  impacted_amount?: number;
  reward_item_id?: string;
  reward_item_name?: string;
  reward_qty?: number;
  notes?: string;
}

export interface SalesOrderPromo {
  id: string;
  sales_order_id: string;
  scheme_id: string;
  scheme_name?: string;
  scheme_code?: string;
  application_type: PromoApplicationType;
  calculated_benefit_amount: number;
  promo_cost_estimate: number;
  stack_sequence: number;
  line_impacts: PromoLineImpact[];
}

export interface PromoApplicationResult {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  application_type: PromoApplicationType;
  calculated_benefit: number;
  promo_cost_estimate: number;
  stack_sequence: number;
  line_impacts: Array<{
    impact_type: PromoImpactType;
    reward_item_name?: string;
    reward_qty?: number;
    discount_amount?: number;
    discount_pct?: number;
    notes?: string;
  }>;
  next_threshold_hint?: string;
}

export interface EvaluateOrderResult {
  sales_order_id: string;
  applied_promos: PromoApplicationResult[];
  skipped_promos: Array<{ scheme_id: string; scheme_code?: string; reason: string; next_threshold_hint?: string }>;
  total_discount: number;
  total_free_goods_value: number;
  total_promo_cost: number;
}

export interface OverrideRequest {
  id: string;
  sales_order_id: string;
  scheme_id?: string;
  status: OverrideStatus;
  requested_discount_pct?: number;
  requested_free_qty?: number;
  reason: string;
  approver_notes?: string;
  created_at?: string;
}

export interface PromoAIRec {
  id: string;
  agent_type: PromoAIAgentType;
  title: string;
  detail?: string;
  severity: string;
  status: PromoAIRecStatus;
  scheme_id?: string;
}

export interface PromoDashboard {
  active_schemes: number;
  expiring_soon: number;
  total_applications_month: number;
  total_discount_month: number;
  total_free_value_month: number;
  pending_override_requests: number;
  pending_ai_recs: number;
}

// ── Labels ─────────────────────────────────────────────────────────────────────

export const SCHEME_TYPE_LABEL: Record<SchemeType, string> = {
  BUY_X_GET_Y:         "Buy X Get Y Free",
  PERCENT_DISCOUNT:    "% Discount",
  FIXED_DISCOUNT:      "Fixed Discount",
  TIERED_DISCOUNT:     "Tiered Discount",
  QTY_BREAK_PRICE:     "Qty Break Price",
  SPEND_BASED:         "Spend-Based",
  MIX_AND_MATCH:       "Mix & Match",
  BUNDLE:              "Bundle Deal",
  FREE_GOODS_DIFF_SKU: "Free Goods (Different SKU)",
  CHANNEL_DEAL:        "Channel Deal",
};

export const REWARD_TYPE_LABEL: Record<RewardType, string> = {
  FREE_GOODS:       "Free Goods",
  PERCENT_DISCOUNT: "% Discount",
  FIXED_DISCOUNT:   "Fixed Amount Off",
  SPECIAL_PRICE:    "Special Unit Price",
  BUNDLE_PRICE:     "Bundle Price",
};

export const TRIGGER_BASIS_LABEL: Record<TriggerBasis, string> = {
  SKU:         "Specific SKU",
  CATEGORY:    "Item Category",
  BRAND:       "Brand",
  ORDER_TOTAL: "Order Total (spend-based)",
  QUANTITY:    "Any Quantity",
  VALUE:       "Line Value",
  MIX_SET:     "Mix & Match Set",
};

export const STATUS_BADGE: Record<SchemeStatus, string> = {
  DRAFT:     "bg-gray-100 text-gray-600",
  APPROVED:  "bg-blue-100 text-blue-700",
  ACTIVE:    "bg-green-100 text-green-700",
  EXPIRED:   "bg-red-100 text-red-600",
  SUSPENDED: "bg-yellow-100 text-yellow-700",
  ARCHIVED:  "bg-gray-100 text-gray-500",
};

export const AGENT_LABEL: Record<PromoAIAgentType, string> = {
  CONFLICT_ADVISOR: "Conflict Advisor",
  COST_MONITOR:     "Cost Monitor",
  UPSELL_ASSISTANT: "Upsell Assistant",
};

export const SEVERITY_BADGE: Record<string, string> = {
  info:     "bg-blue-100 text-blue-700",
  warning:  "bg-yellow-100 text-yellow-700",
  critical: "bg-red-100 text-red-700",
};

export const fmtCurrency = (n: number) =>
  `KES ${Number(n).toLocaleString("en-KE", { minimumFractionDigits: 2 })}`;

// ── API Client ─────────────────────────────────────────────────────────────────

export const promoApi = {
  // Dashboard
  getDashboard: () => r<PromoDashboard>(ax.get("/promotions/dashboard")),

  // Schemes
  getSchemes: (status?: SchemeStatus, activeOnly?: boolean) =>
    r<PromoScheme[]>(ax.get("/promotions/schemes", { params: { status, active_only: activeOnly } })),
  getScheme: (id: string) => r<PromoScheme>(ax.get(`/promotions/schemes/${id}`)),
  createScheme: (data: object) => r<PromoScheme>(ax.post("/promotions/schemes", data)),
  activateScheme: (id: string) => r<PromoScheme>(ax.post(`/promotions/schemes/${id}/activate`)),
  updateSchemeStatus: (id: string, status: SchemeStatus) =>
    r<PromoScheme>(ax.patch(`/promotions/schemes/${id}/status`, null, { params: { status } })),

  // Evaluation
  evaluateOrder: (data: object) => r<EvaluateOrderResult>(ax.post("/promotions/evaluate-order", data)),
  getOrderPromos: (orderId: string) =>
    r<SalesOrderPromo[]>(ax.get(`/promotions/sales-orders/${orderId}/promotions`)),
  recalculateOrder: (orderId: string, data: object) =>
    r<EvaluateOrderResult>(ax.post(`/promotions/sales-orders/${orderId}/promotions/recalculate`, data)),

  // Override Requests
  getOverrideRequests: (status?: OverrideStatus) =>
    r<OverrideRequest[]>(ax.get("/promotions/override-requests", { params: { status } })),
  createOverrideRequest: (data: object) =>
    r<OverrideRequest>(ax.post("/promotions/override-requests", data)),
  approveOverride: (id: string, data: { approved: boolean; approver_notes?: string }) =>
    r<OverrideRequest>(ax.post(`/promotions/override-requests/${id}/approve`, data)),

  // Reports
  getUsageReport: () => r<any[]>(ax.get("/promotions/reports/usage")),

  // AI
  runAgents: () => r<{ generated: number }>(ax.post("/promotions/ai/run-agents")),
  getAIRecs: (status?: PromoAIRecStatus) =>
    r<PromoAIRec[]>(ax.get("/promotions/ai/recommendations", { params: { status } })),
  ackAIRec: (id: string, data: { status: PromoAIRecStatus }) =>
    r<PromoAIRec>(ax.patch(`/promotions/ai/recommendations/${id}`, data)),
};
