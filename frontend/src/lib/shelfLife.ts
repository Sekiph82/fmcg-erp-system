// FEFO + Shelf-Life Control — types, API client, label/color maps

const BASE = "/api/v1/shelf-life";

export type ShelfLifeStatus =
  | "not_applicable" | "active" | "near_expiry" | "expired"
  | "blocked" | "qc_hold" | "quarantine" | "pending_retest"
  | "retested_released" | "customer_restricted";

export type PickingStrategy = "fefo" | "fifo" | "lifo" | "manual" | "hybrid";
export type ExpiryBlockPolicy = "block" | "warn" | "allow_with_approval";
export type NearExpiryPolicy = "allow" | "warn" | "require_approval" | "block_external";
export type ShelfLifeCategory = "raw" | "intermediate" | "bulk" | "finished_goods" | "packaging" | "other";
export type RetestStatus = "pending" | "requested" | "in_progress" | "passed" | "failed" | "cancelled";
export type DispositionAction = "use_urgently" | "prioritize_shipment" | "clearance_channel" | "retest" | "quarantine" | "rework" | "scrap";
export type DispositionStatus = "suggested" | "approved" | "executed" | "cancelled";
export type AlertType = "near_expiry" | "expired" | "bulk_age_limit" | "order_blocked" | "production_blocked" | "retest_overdue" | "high_risk_value" | "poor_compliance" | "unretested_lot";
export type AlertSeverity = "info" | "warning" | "critical";
export type SLAIAgentType = "expiry_risk_predictor" | "allocation_optimizer" | "compliance_monitor";
export type SLAIRecStatus = "pending" | "accepted" | "rejected" | "applied";
export type FEFOContext = "production_issue" | "warehouse_pick" | "sales_shipment" | "internal_transfer" | "line_side_issue";
export type StrategyScope = "item_warehouse_location" | "item_warehouse" | "item_default" | "warehouse_default" | "system_fallback";
export type CustomerRuleType = "fixed_days" | "percentage";

// ── Domain objects ────────────────────────────────────────────────────────────

export interface LotShelfLifeProfile {
  id: string;
  lot_id: string;
  manufacturing_date: string | null;
  expiry_date: string | null;
  best_before_date: string | null;
  retest_date: string | null;
  qc_release_date: string | null;
  remaining_shelf_life_days: number | null;
  age_since_production_days: number | null;
  age_since_release_days: number | null;
  original_shelf_life_days: number | null;
  pct_remaining: string | null;
  shelf_life_status: ShelfLifeStatus;
  near_expiry_flag: boolean;
  expired_flag: boolean;
  blocked_for_issue_flag: boolean;
  blocked_for_shipment_flag: boolean;
  blocked_for_consumption_flag: boolean;
  hold_reason: string | null;
  last_recalc_at: string | null;
  created_at: string;
}

export interface ItemShelfLifeConfig {
  id: string;
  product_id: string | null;
  material_id: string | null;
  shelf_life_control_enabled: boolean;
  shelf_life_category: ShelfLifeCategory;
  shelf_life_days: number | null;
  min_remaining_days_issue: number | null;
  min_remaining_days_ship: number | null;
  near_expiry_threshold_days: number;
  picking_strategy_default: PickingStrategy;
  expiry_block_policy: ExpiryBlockPolicy;
  near_expiry_issue_policy: NearExpiryPolicy;
  near_expiry_ship_policy: NearExpiryPolicy;
  manufacturing_date_required: boolean;
  expiry_date_required: boolean;
  retest_date_required: boolean;
  best_before_date_required: boolean;
  allowed_retest: boolean;
  auto_expiry_calculation: boolean;
  max_hold_hours: string | null;
  notes: string | null;
  created_at: string;
}

export interface PickingStrategyConfig {
  id: string;
  scope: StrategyScope;
  strategy: PickingStrategy;
  is_active: boolean;
  product_id: string | null;
  material_id: string | null;
  warehouse_id: string | null;
  location_id: string | null;
  effective_from: string | null;
  notes: string | null;
  created_at: string;
}

export interface CustomerShelfLifeRule {
  id: string;
  customer_id: string | null;
  customer_group: string | null;
  country_code: string | null;
  channel: string | null;
  product_id: string | null;
  material_id: string | null;
  rule_type: CustomerRuleType;
  min_remaining_days: number | null;
  min_pct_remaining: string | null;
  block_policy: ExpiryBlockPolicy;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export interface FEFOLotCandidate {
  lot_id: string;
  lot_number: string;
  expiry_date: string | null;
  remaining_days: number | null;
  pct_remaining: string | null;
  quantity_available: string;
  shelf_life_status: ShelfLifeStatus;
  rank: number;
  is_recommended: boolean;
  exclusion_reason: string | null;
}

export interface FEFORankResponse {
  candidates: FEFOLotCandidate[];
  recommended_lot_id: string | null;
  strategy_used: PickingStrategy;
  policy_violations: string[];
}

export interface FEFOValidateIssueResponse {
  allowed: boolean;
  requires_approval: boolean;
  warnings: string[];
  errors: string[];
  lot_status: ShelfLifeStatus | null;
  remaining_days: number | null;
}

export interface FEFOValidateShipmentResponse {
  allowed: boolean;
  requires_approval: boolean;
  warnings: string[];
  errors: string[];
  remaining_days: number | null;
  pct_remaining: string | null;
  customer_min_days: number | null;
}

export interface FEFOAuditLog {
  id: string;
  context: FEFOContext;
  reference_doc: string | null;
  reference_doc_type: string | null;
  product_id: string | null;
  material_id: string | null;
  warehouse_id: string | null;
  customer_id: string | null;
  recommended_lot_id: string | null;
  actual_lot_id: string | null;
  recommended_expiry: string | null;
  actual_expiry: string | null;
  is_fefo_compliant: boolean;
  override_reason: string | null;
  quantity: string | null;
  created_at: string;
}

export interface RetestRequest {
  id: string;
  lot_id: string;
  request_number: string;
  status: RetestStatus;
  reason: string;
  requested_by_id: string | null;
  requested_at: string | null;
  assigned_to_id: string | null;
  scheduled_date: string | null;
  result_passed: boolean | null;
  result_notes: string | null;
  result_by_id: string | null;
  result_at: string | null;
  new_expiry_date: string | null;
  new_retest_date: string | null;
  new_release_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface BulkHoldRecord {
  id: string;
  lot_id: string | null;
  material_id: string | null;
  warehouse_id: string | null;
  location_ref: string | null;
  creation_time: string;
  max_hold_hours: string;
  expiry_time: string;
  hours_used: string | null;
  pct_hold_used: string | null;
  is_expired: boolean;
  is_near_limit: boolean;
  is_blocked: boolean;
  qc_reassessment_triggered: boolean;
  disposition_action: DispositionAction | null;
  notes: string | null;
  created_at: string;
}

export interface ShelfLifeAlert {
  id: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  is_resolved: boolean;
  resolved_at: string | null;
  lot_id: string | null;
  product_id: string | null;
  material_id: string | null;
  warehouse_id: string | null;
  customer_id: string | null;
  title: string;
  message: string;
  days_remaining: number | null;
  stock_value_at_risk: string | null;
  quantity_affected: string | null;
  created_at: string;
}

export interface DispositionSuggestion {
  id: string;
  lot_id: string;
  product_id: string | null;
  material_id: string | null;
  warehouse_id: string | null;
  action: DispositionAction;
  status: DispositionStatus;
  reason: string;
  urgency_score: number | null;
  quantity_affected: string | null;
  financial_exposure: string | null;
  days_until_expiry: number | null;
  approved_by_id: string | null;
  approved_at: string | null;
  execution_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SLAIRecommendation {
  id: string;
  agent_type: SLAIAgentType;
  status: SLAIRecStatus;
  lot_id: string | null;
  product_id: string | null;
  material_id: string | null;
  warehouse_id: string | null;
  title: string;
  explanation: string;
  recommendation: string;
  confidence_score: string | null;
  impact_value_kes: string | null;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface ShelfLifeKPIs {
  total_lots_tracked: number;
  active_lots: number;
  near_expiry_lots: number;
  expired_lots: number;
  blocked_lots: number;
  pending_retest_lots: number;
  near_expiry_value_kes: string;
  expired_value_kes: string;
  fefo_compliance_pct: string | null;
  open_alerts: number;
  pending_dispositions: number;
}

export interface ShelfLifeDashboard {
  kpis: ShelfLifeKPIs;
  critical_alerts: ShelfLifeAlert[];
  near_expiry_lots: LotShelfLifeProfile[];
  expired_lots: LotShelfLifeProfile[];
  pending_dispositions: DispositionSuggestion[];
  pending_ai_recs: SLAIRecommendation[];
  retest_overdue: number;
  bulk_hold_at_risk: number;
}

export interface FEFOComplianceRow {
  warehouse_id: string | null;
  warehouse_name: string | null;
  total_picks: number;
  compliant_picks: number;
  non_compliant_picks: number;
  compliance_pct: string;
  override_count: number;
}

export interface FEFOComplianceReport {
  period_from: string | null;
  period_to: string | null;
  overall_compliance_pct: string;
  rows: FEFOComplianceRow[];
  top_overriders: Record<string, unknown>[];
}

// ── API Client ────────────────────────────────────────────────────────────────

const _BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const r = await fetch(`${_BACKEND}${url}`, {
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...opts,
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const shelfLifeApi = {
  // Dashboard
  getDashboard: () => req<ShelfLifeDashboard>(`${BASE}/dashboard`),

  // Item configs
  listItemConfigs: () => req<ItemShelfLifeConfig[]>(`${BASE}/config/item`),
  createItemConfig: (d: Partial<ItemShelfLifeConfig>) =>
    req<ItemShelfLifeConfig>(`${BASE}/config/item`, { method: "POST", body: JSON.stringify(d) }),
  updateItemConfig: (id: string, d: Partial<ItemShelfLifeConfig>) =>
    req<ItemShelfLifeConfig>(`${BASE}/config/item/${id}`, { method: "PUT", body: JSON.stringify(d) }),

  // Picking strategy
  listPickingStrategies: () => req<PickingStrategyConfig[]>(`${BASE}/config/picking-strategy`),
  createPickingStrategy: (d: Partial<PickingStrategyConfig>) =>
    req<PickingStrategyConfig>(`${BASE}/config/picking-strategy`, { method: "POST", body: JSON.stringify(d) }),

  // Customer rules
  listCustomerRules: () => req<CustomerShelfLifeRule[]>(`${BASE}/config/customer-rules`),
  createCustomerRule: (d: Partial<CustomerShelfLifeRule>) =>
    req<CustomerShelfLifeRule>(`${BASE}/config/customer-rule`, { method: "POST", body: JSON.stringify(d) }),

  // Lot profiles
  getLotProfile: (lotId: string) => req<LotShelfLifeProfile>(`${BASE}/lots/${lotId}/shelf-life`),
  updateLotProfile: (lotId: string, d: Partial<LotShelfLifeProfile>) =>
    req<LotShelfLifeProfile>(`${BASE}/lots/${lotId}/shelf-life`, { method: "PUT", body: JSON.stringify(d) }),
  recalculateLot: (lotId: string, days = 30) =>
    req<LotShelfLifeProfile>(`${BASE}/lots/${lotId}/recalculate?near_expiry_days=${days}`, { method: "POST" }),
  batchRecalculate: () =>
    req<{ updated: number }>(`${BASE}/lots/batch-recalculate`, { method: "POST" }),
  listLots: (status?: ShelfLifeStatus, limit = 200) => {
    const p = new URLSearchParams({ limit: String(limit) });
    if (status) p.set("status", status);
    return req<LotShelfLifeProfile[]>(`${BASE}/lots?${p}`);
  },

  // Near-expiry & expired
  getNearExpiry: (days = 30) => req<LotShelfLifeProfile[]>(`${BASE}/near-expiry?days=${days}`),
  getExpired: () => req<LotShelfLifeProfile[]>(`${BASE}/expired`),

  // FEFO
  rankFEFO: (d: Record<string, unknown>) =>
    req<FEFORankResponse>(`${BASE}/fefo/rank`, { method: "POST", body: JSON.stringify(d) }),
  validateIssue: (d: Record<string, unknown>) =>
    req<FEFOValidateIssueResponse>(`${BASE}/fefo/validate-issue`, { method: "POST", body: JSON.stringify(d) }),
  validateShipment: (d: Record<string, unknown>) =>
    req<FEFOValidateShipmentResponse>(`${BASE}/fefo/validate-shipment`, { method: "POST", body: JSON.stringify(d) }),
  logAudit: (d: Partial<FEFOAuditLog>) =>
    req<FEFOAuditLog>(`${BASE}/fefo/audit-log`, { method: "POST", body: JSON.stringify(d) }),
  listAuditLog: (limit = 200) => req<FEFOAuditLog[]>(`${BASE}/fefo/audit-log?limit=${limit}`),
  getComplianceReport: (from?: string, to?: string) => {
    const p = new URLSearchParams();
    if (from) p.set("date_from", from);
    if (to) p.set("date_to", to);
    return req<FEFOComplianceReport>(`${BASE}/compliance?${p}`);
  },

  // Retest
  createRetestRequest: (d: { lot_id: string; reason: string; scheduled_date?: string }) =>
    req<RetestRequest>(`${BASE}/retest-request`, { method: "POST", body: JSON.stringify(d) }),
  recordRetestResult: (id: string, d: { result_passed: boolean; result_notes?: string; new_expiry_date?: string }) =>
    req<RetestRequest>(`${BASE}/retest-request/${id}/result`, { method: "POST", body: JSON.stringify(d) }),
  listRetestQueue: () => req<RetestRequest[]>(`${BASE}/retest-queue`),

  // Bulk hold
  createBulkHold: (d: Partial<BulkHoldRecord>) =>
    req<BulkHoldRecord>(`${BASE}/bulk-hold`, { method: "POST", body: JSON.stringify(d) }),
  listBulkHolds: (activeOnly = true) =>
    req<BulkHoldRecord[]>(`${BASE}/bulk-hold?active_only=${activeOnly}`),
  refreshBulkHolds: () =>
    req<{ updated: number }>(`${BASE}/bulk-hold/refresh`, { method: "POST" }),

  // Alerts
  generateAlerts: () => req<{ created: number }>(`${BASE}/alerts/generate`, { method: "POST" }),
  listAlerts: (resolved = false, severity?: AlertSeverity) => {
    const p = new URLSearchParams({ resolved: String(resolved) });
    if (severity) p.set("severity", severity);
    return req<ShelfLifeAlert[]>(`${BASE}/alerts?${p}`);
  },
  resolveAlert: (id: string) =>
    req<ShelfLifeAlert>(`${BASE}/alerts/${id}/resolve`, { method: "POST" }),

  // Disposition
  generateDispositions: () =>
    req<{ created: number }>(`${BASE}/disposition-suggestions/generate`, { method: "POST" }),
  listDispositions: (status?: DispositionStatus) => {
    const p = new URLSearchParams();
    if (status) p.set("status", status);
    return req<DispositionSuggestion[]>(`${BASE}/disposition-suggestions?${p}`);
  },
  approveDisposition: (id: string, d: { approved_by_id: string; execution_notes?: string }) =>
    req<DispositionSuggestion>(`${BASE}/disposition-suggestions/${id}/approve`, {
      method: "POST", body: JSON.stringify(d),
    }),

  // AI
  runAIAgents: () => req<{ generated: number }>(`${BASE}/run-ai-agents`, { method: "POST" }),
  listAIRecs: (status?: SLAIRecStatus, agentType?: SLAIAgentType) => {
    const p = new URLSearchParams();
    if (status) p.set("status", status);
    if (agentType) p.set("agent_type", agentType);
    return req<SLAIRecommendation[]>(`${BASE}/ai-recommendations?${p}`);
  },
  reviewAIRec: (id: string, d: { status: SLAIRecStatus; reviewed_by_id: string; review_note?: string }) =>
    req<SLAIRecommendation>(`${BASE}/ai-recommendations/${id}/review`, {
      method: "POST", body: JSON.stringify(d),
    }),
};

// ── Label & Color Maps ────────────────────────────────────────────────────────

export const SL_STATUS_LABEL: Record<ShelfLifeStatus, string> = {
  not_applicable:     "N/A",
  active:             "Active",
  near_expiry:        "Near Expiry",
  expired:            "Expired",
  blocked:            "Blocked",
  qc_hold:            "QC Hold",
  quarantine:         "Quarantine",
  pending_retest:     "Pending Retest",
  retested_released:  "Retested & Released",
  customer_restricted:"Customer Restricted",
};

export const SL_STATUS_COLOR: Record<ShelfLifeStatus, string> = {
  not_applicable:     "text-gray-400",
  active:             "text-green-600",
  near_expiry:        "text-amber-600",
  expired:            "text-red-700",
  blocked:            "text-red-600",
  qc_hold:            "text-orange-600",
  quarantine:         "text-purple-600",
  pending_retest:     "text-blue-600",
  retested_released:  "text-teal-600",
  customer_restricted:"text-indigo-600",
};

export const SL_STATUS_BG: Record<ShelfLifeStatus, string> = {
  not_applicable:     "bg-gray-100 text-gray-700",
  active:             "bg-green-100 text-green-700",
  near_expiry:        "bg-amber-100 text-amber-700",
  expired:            "bg-red-100 text-red-700",
  blocked:            "bg-red-100 text-red-700",
  qc_hold:            "bg-orange-100 text-orange-700",
  quarantine:         "bg-purple-100 text-purple-700",
  pending_retest:     "bg-blue-100 text-blue-700",
  retested_released:  "bg-teal-100 text-teal-700",
  customer_restricted:"bg-indigo-100 text-indigo-700",
};

export const ALERT_SEV_BG: Record<AlertSeverity, string> = {
  info:    "bg-blue-100 text-blue-700",
  warning: "bg-amber-100 text-amber-700",
  critical:"bg-red-100 text-red-700",
};

export const DISPOSITION_ACTION_LABEL: Record<DispositionAction, string> = {
  use_urgently:        "Use Urgently",
  prioritize_shipment: "Prioritize Shipment",
  clearance_channel:   "Clearance Channel",
  retest:              "Send for Retest",
  quarantine:          "Move to Quarantine",
  rework:              "Send for Rework",
  scrap:               "Scrap / Write-off",
};

export const STRATEGY_LABEL: Record<PickingStrategy, string> = {
  fefo:   "FEFO (First Expired, First Out)",
  fifo:   "FIFO (First In, First Out)",
  lifo:   "LIFO (Last In, First Out)",
  manual: "Manual Selection",
  hybrid: "Hybrid (FEFO then FIFO)",
};

export const AI_AGENT_LABEL: Record<SLAIAgentType, string> = {
  expiry_risk_predictor: "Expiry Risk Predictor",
  allocation_optimizer:  "Shelf-Life Allocation Optimizer",
  compliance_monitor:    "FEFO Compliance Monitor",
};

export function fmtDays(days: number | null): string {
  if (days === null || days === undefined) return "—";
  if (days < 0) return `${Math.abs(days)}d expired`;
  return `${days}d`;
}

export function expiryColor(days: number | null): string {
  if (days === null) return "text-gray-400";
  if (days < 0) return "text-red-700 font-semibold";
  if (days <= 7) return "text-red-600 font-semibold";
  if (days <= 30) return "text-amber-600 font-semibold";
  return "text-green-700";
}

export function expiryBgColor(days: number | null): string {
  if (days === null) return "bg-gray-50";
  if (days < 0) return "bg-red-50";
  if (days <= 7) return "bg-red-50";
  if (days <= 30) return "bg-amber-50";
  return "bg-green-50";
}
