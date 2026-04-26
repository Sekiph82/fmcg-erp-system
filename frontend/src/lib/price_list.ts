const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/price-lists`;

async function r<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type PLType = "STANDARD" | "WHOLESALE" | "RETAIL" | "EXPORT" | "DISTRIBUTOR" | "MODERN_TRADE" | "CUSTOMER_SPECIFIC" | "PROMO" | "CUSTOM";
export type PLStatus = "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "ACTIVE" | "EXPIRED" | "ARCHIVED";
export type PLDiscountType = "PERCENTAGE" | "FIXED_AMOUNT" | "OVERRIDE_PRICE";
export type PLDiscountScope = "LINE" | "ORDER" | "CUSTOMER" | "VOLUME" | "CHANNEL" | "MANUAL" | "PROMOTIONAL";
export type PLApprovalAction = "SUBMITTED" | "APPROVED" | "REJECTED" | "WITHDRAWN";
export type PLAIAgentType = "PRICING_RISK_MONITOR" | "PRICE_OPTIMIZATION" | "DISCOUNT_ABUSE_DETECTOR";
export type PLAIRecStatus = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

export interface PLHeader {
  id: string;
  price_list_code: string;
  price_list_name: string;
  currency: string;
  pl_type: PLType;
  country?: string;
  region?: string;
  channel?: string;
  customer_id?: string;
  distributor_id?: string;
  valid_from: string;
  valid_to?: string;
  status: PLStatus;
  priority_rank: number;
  default_flag: boolean;
  minimum_margin_pct?: number;
  max_manual_discount?: number;
  created_by?: string;
  approved_by?: string;
  approved_at?: string;
  notes?: string;
  created_at?: string;
}

export interface PLLine {
  id: string;
  header_id: string;
  product_id: string;
  brand?: string;
  category?: string;
  uom: string;
  base_price: number;
  minimum_price?: number;
  recommended_price?: number;
  currency: string;
  tax_included_flag: boolean;
  valid_from?: string;
  valid_to?: string;
  active_flag: boolean;
  notes?: string;
}

export interface PLTier {
  id: string;
  line_id: string;
  min_qty: number;
  max_qty?: number;
  unit_price?: number;
  discount_pct?: number;
  fixed_discount_amount?: number;
  effective_margin_pct?: number;
  active_flag: boolean;
}

export interface PLAssignment {
  id: string;
  header_id: string;
  customer_id?: string;
  distributor_id?: string;
  channel?: string;
  region?: string;
  country?: string;
  segment?: string;
  valid_from: string;
  valid_to?: string;
  priority_rank: number;
  active_flag: boolean;
}

export interface PLDiscountRule {
  id: string;
  rule_code: string;
  rule_name: string;
  scope: PLDiscountScope;
  discount_type: PLDiscountType;
  discount_value: number;
  max_discount_pct?: number;
  requires_approval: boolean;
  min_margin_pct?: number;
  applies_to_pl_type?: string;
  applies_to_channel?: string;
  reason_required: boolean;
  valid_from?: string;
  valid_to?: string;
  active_flag: boolean;
}

export interface PLApproval {
  id: string;
  header_id: string;
  action: PLApprovalAction;
  submitted_by: string;
  reviewed_by?: string;
  reviewed_at?: string;
  notes?: string;
  created_at?: string;
}

export interface PLChangeHistory {
  id: string;
  header_id: string;
  line_id?: string;
  change_type: string;
  changed_by: string;
  changed_at: string;
  old_value_json?: Record<string, any>;
  new_value_json?: Record<string, any>;
  notes?: string;
}

export interface PLAIRec {
  id: string;
  header_id?: string;
  line_id?: string;
  agent_type: PLAIAgentType;
  status: PLAIRecStatus;
  title: string;
  body: string;
  severity: string;
  reference_type?: string;
  reference_id?: string;
  actioned_by?: string;
  actioned_at?: string;
  created_at?: string;
}

export interface PriceResolveResult {
  product_id: string;
  quantity: number;
  uom: string;
  unit_price: number;
  currency: string;
  source_price_list?: string;
  source_pl_id?: string;
  source_pl_type?: string;
  tier_applied: boolean;
  discount_applied?: number;
  effective_price: number;
  minimum_price?: number;
  margin_warning: boolean;
  margin_pct?: number;
  resolution_path: string[];
}

export interface MarginCheckResult {
  product_id: string;
  proposed_price: number;
  cost_price?: number;
  margin_pct?: number;
  margin_status: string;
  blocked: boolean;
  requires_approval: boolean;
  message: string;
}

// ── Color Maps ────────────────────────────────────────────────────────────────

export const PL_STATUS_COLORS: Record<PLStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
  APPROVED: "bg-blue-100 text-blue-800",
  ACTIVE: "bg-green-100 text-green-800",
  EXPIRED: "bg-red-100 text-red-700",
  ARCHIVED: "bg-gray-200 text-gray-500",
};

export const PL_TYPE_COLORS: Record<PLType, string> = {
  STANDARD: "bg-gray-100 text-gray-700",
  WHOLESALE: "bg-blue-100 text-blue-800",
  RETAIL: "bg-purple-100 text-purple-800",
  EXPORT: "bg-indigo-100 text-indigo-800",
  DISTRIBUTOR: "bg-orange-100 text-orange-800",
  MODERN_TRADE: "bg-teal-100 text-teal-800",
  CUSTOMER_SPECIFIC: "bg-pink-100 text-pink-800",
  PROMO: "bg-yellow-100 text-yellow-800",
  CUSTOM: "bg-red-100 text-red-700",
};

export const MARGIN_STATUS_COLORS: Record<string, string> = {
  OK: "text-green-700",
  WARNING: "text-yellow-700",
  BELOW_MINIMUM: "text-orange-700",
  BELOW_COST: "text-red-700",
  NO_COST_DATA: "text-gray-500",
};

// ── API Client ────────────────────────────────────────────────────────────────

const j = { "Content-Type": "application/json" };
const post = (url: string, body: any) => fetch(url, { method: "POST", headers: j, body: JSON.stringify(body) });
const put = (url: string, body: any) => fetch(url, { method: "PUT", headers: j, body: JSON.stringify(body) });

export const plApi = {
  // Headers
  listHeaders: (params?: { status?: string; pl_type?: string; active_only?: boolean }) => {
    const p = new URLSearchParams();
    if (params?.status) p.set("status", params.status);
    if (params?.pl_type) p.set("pl_type", params.pl_type);
    if (params?.active_only) p.set("active_only", "true");
    return fetch(`${BASE}/?${p}`).then(r<PLHeader[]>);
  },
  createHeader: (body: Partial<PLHeader>) => post(`${BASE}/`, body).then(r<PLHeader>),
  getHeader: (id: string) => fetch(`${BASE}/${id}`).then(r<PLHeader>),
  updateHeader: (id: string, body: Partial<PLHeader>, updatedBy = "admin") =>
    put(`${BASE}/${id}?updated_by=${encodeURIComponent(updatedBy)}`, body).then(r<PLHeader>),
  submitForApproval: (id: string, submitted_by: string) =>
    post(`${BASE}/${id}/submit`, { submitted_by }).then(r<PLHeader>),
  reviewApproval: (id: string, action: PLApprovalAction, reviewed_by: string, notes?: string) =>
    post(`${BASE}/${id}/approve`, { action, reviewed_by, notes }).then(r<PLHeader>),
  activate: (id: string, activatedBy = "admin") =>
    post(`${BASE}/${id}/activate?activated_by=${encodeURIComponent(activatedBy)}`, {}).then(r<PLHeader>),
  archive: (id: string, archivedBy = "admin") =>
    post(`${BASE}/${id}/archive?archived_by=${encodeURIComponent(archivedBy)}`, {}).then(r<PLHeader>),
  pendingApproval: () => fetch(`${BASE}/pending-approval`).then(r<PLHeader[]>),
  getHistory: (id: string) => fetch(`${BASE}/${id}/history`).then(r<PLChangeHistory[]>),
  getApprovals: (id: string) => fetch(`${BASE}/${id}/approvals`).then(r<PLApproval[]>),

  // Lines
  listLines: (headerId: string) => fetch(`${BASE}/${headerId}/lines`).then(r<PLLine[]>),
  addLine: (headerId: string, body: Partial<PLLine>, addedBy = "admin") =>
    post(`${BASE}/${headerId}/lines?added_by=${encodeURIComponent(addedBy)}`, body).then(r<PLLine>),
  updateLine: (lineId: string, body: Partial<PLLine>, updatedBy = "admin") =>
    put(`${BASE}/lines/${lineId}?updated_by=${encodeURIComponent(updatedBy)}`, body).then(r<PLLine>),

  // Tiers
  listTiers: (lineId: string) => fetch(`${BASE}/lines/${lineId}/tiers`).then(r<PLTier[]>),
  addTier: (lineId: string, body: Partial<PLTier>) =>
    post(`${BASE}/lines/${lineId}/tiers`, body).then(r<PLTier>),

  // Assignments
  listAssignments: (headerId: string) => fetch(`${BASE}/${headerId}/assignments`).then(r<PLAssignment[]>),
  addAssignment: (headerId: string, body: Partial<PLAssignment>) =>
    post(`${BASE}/${headerId}/assignments`, body).then(r<PLAssignment>),
  customerAssignments: (customerId: string) =>
    fetch(`${BASE}/customer/${customerId}/assignments`).then(r<PLAssignment[]>),

  // Discount Rules
  listDiscountRules: (activeOnly = true) =>
    fetch(`${BASE}/discount-rules?active_only=${activeOnly}`).then(r<PLDiscountRule[]>),
  createDiscountRule: (body: Partial<PLDiscountRule>) =>
    post(`${BASE}/discount-rules`, body).then(r<PLDiscountRule>),

  // Price Resolution
  resolvePrice: (body: {
    product_id: string; quantity: number; uom?: string;
    customer_id?: string; distributor_id?: string; channel?: string; region?: string;
  }) => post(`${BASE}/resolve-price`, body).then(r<PriceResolveResult>),

  // Margin Check
  checkMargin: (body: { product_id: string; proposed_price: number; quantity: number; currency?: string }) =>
    post(`${BASE}/check-margin`, body).then(r<MarginCheckResult>),

  // Bulk Import
  bulkImport: (body: { header_id: string; rows: any[]; imported_by: string }) =>
    post(`${BASE}/import`, body).then(r<{ imported: number; skipped: number; errors: string[] }>),
  downloadTemplate: () => `${BASE}/template`,

  // Reports
  getDashboard: () => fetch(`${BASE}/reports/dashboard`).then(r<any>),
  getExpiring: (days = 30) => fetch(`${BASE}/reports/expiring?days=${days}`).then(r<PLHeader[]>),
  getBelowMargin: () => fetch(`${BASE}/reports/below-margin`).then(r<any[]>),
  versionCompare: (idA: string, idB: string) =>
    fetch(`${BASE}/reports/version-compare?header_id_a=${idA}&header_id_b=${idB}`).then(r<any>),

  // AI
  runAI: () => post(`${BASE}/ai/run`, {}).then(r<{ generated: number }>),
  listAIRecs: (headerId?: string) =>
    fetch(`${BASE}/ai/recommendations${headerId ? `?header_id=${headerId}` : ""}`).then(r<PLAIRec[]>),
  ackAIRec: (recId: string, status: PLAIRecStatus, actioned_by: string) =>
    post(`${BASE}/ai/recommendations/${recId}/ack`, { status, actioned_by }).then(r<PLAIRec>),
};
