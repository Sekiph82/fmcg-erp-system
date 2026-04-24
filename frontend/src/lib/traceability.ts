// Lot Traceability + Batch Recall Management — types, API client, label/color maps

const BASE = "/api/v1/traceability";

export type TraceEventType =
  | "receipt" | "issue" | "consumption" | "transformation" | "packaging"
  | "shipment" | "return_event" | "rework" | "scrap" | "transfer"
  | "quarantine" | "recall_action" | "adjustment";

export type TraceItemStage =
  | "supplier" | "grn" | "raw_stock" | "prepared" | "intermediate"
  | "bulk" | "finished_good" | "packaging" | "quarantine" | "rework"
  | "scrapped" | "shipped" | "returned";

export type GenealogyRelType =
  | "prepared_from" | "intermediate_from" | "bulk_from" | "packed_from"
  | "reworked_from" | "repacked_from" | "returned_from" | "received_from"
  | "split_from" | "merged_from";

export type RecallType = "internal" | "customer" | "market" | "regulatory" | "mock_recall";
export type RecallTrigger = "qc" | "complaint" | "supplier_notice" | "audit" | "regulatory" | "manual";
export type RecallSeverity = "low" | "medium" | "high" | "critical";
export type RecallStatus =
  | "draft" | "under_review" | "active" | "contained" | "in_progress"
  | "completed" | "closed" | "cancelled";
export type RecallActionType =
  | "quarantine" | "shipment_block" | "customer_notify" | "distributor_notify"
  | "internal_hold" | "return_request" | "destroy" | "rework"
  | "regulatory_report" | "followup_call" | "closeout_verification";
export type RecallActionStatus = "pending" | "in_progress" | "completed" | "cancelled" | "overdue";
export type RecallRiskStatus = "low" | "medium" | "high" | "critical";
export type TRRecAIAgentType = "scope_validator" | "risk_prioritizer" | "investigation_assistant";
export type TRRecAIRecStatus = "pending" | "accepted" | "rejected" | "applied";

// ── Domain objects ────────────────────────────────────────────────────────────

export interface TraceEventLine {
  id: string;
  event_id: string;
  product_id: string | null;
  material_id: string | null;
  source_lot_id: string | null;
  child_lot_id: string | null;
  quantity: string;
  uom: string | null;
  source_stage: TraceItemStage | null;
  dest_stage: TraceItemStage | null;
  quality_status: string | null;
  movement_reason: string | null;
  linked_customer_id: string | null;
  linked_shipment_id: string | null;
  linked_supplier_id: string | null;
  linked_grn_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface TraceEvent {
  id: string;
  trace_event_type: TraceEventType;
  event_datetime: string;
  reference_number: string | null;
  source_document_type: string | null;
  source_document_id: string | null;
  production_order_id: string | null;
  warehouse_id: string | null;
  performed_by_id: string | null;
  recall_id: string | null;
  notes: string | null;
  lines: TraceEventLine[];
  created_at: string;
}

export interface GenealogyLink {
  id: string;
  parent_lot_id: string;
  child_lot_id: string;
  relationship_type: GenealogyRelType;
  source_document_type: string | null;
  source_document_id: string | null;
  production_order_id: string | null;
  quantity_linked: string | null;
  uom: string | null;
  parent_stage: TraceItemStage | null;
  child_stage: TraceItemStage | null;
  notes: string | null;
  created_at: string;
}

export interface GenealogyNode {
  lot_id: string;
  lot_number: string;
  stage: TraceItemStage | null;
  quantity: number | null;
  rel_type: GenealogyRelType | null;
  children: GenealogyNode[];
  parents: GenealogyNode[];
}

export interface GenealogyEdge {
  source: string;
  target: string;
  rel_type: string;
  qty: number;
}

export interface GenealogyTree {
  root_lot_id: string;
  root_lot_number: string;
  direction: string;
  depth: number;
  nodes: GenealogyNode[];
  edges: GenealogyEdge[];
  lot_count: number;
  stage_summary: Record<string, number>;
}

export interface TraceabilitySearchResult {
  lot_id: string | null;
  lot_number: string | null;
  batch_number: string | null;
  item_name: string | null;
  stage: TraceItemStage | null;
  events: TraceEvent[];
  genealogy_link_count: number;
  has_recall: boolean;
}

export interface ForwardTraceResult {
  root_lot_id: string;
  affected_lots: Array<{ lot_id: string; rel_type: string; quantity: number; child_stage: string | null }>;
  affected_shipments: Array<{ event_id: string; shipment_ref: string | null; customer_id: string | null; lot_id: string; quantity: number; event_date: string | null }>;
  affected_customers: Array<{ customer_id: string }>;
  qty_in_stock: string;
  qty_shipped: string;
  qty_returned: string;
  qty_scrapped: string;
  qty_quarantined: string;
  qty_reworked: string;
  total_affected_qty: string;
}

export interface BackwardTraceResult {
  root_lot_id: string;
  source_lots: Array<{ lot_id: string; rel_type: string; quantity: number; parent_stage: string | null }>;
  production_orders: Array<{ id: string }>;
  suppliers: Array<{ id: string }>;
  grns: Array<{ grn_id: string; supplier_id: string | null; lot_id: string; quantity: number }>;
  qc_events: unknown[];
  genealogy_depth: number;
}

export interface RecallHeader {
  id: string;
  recall_no: string;
  recall_type: RecallType;
  recall_reason: string;
  trigger_source: RecallTrigger;
  severity_level: RecallSeverity;
  status: RecallStatus;
  initiation_datetime: string;
  initiated_by_id: string | null;
  approved_by_id: string | null;
  approved_at: string | null;
  source_lot_id: string | null;
  source_product_id: string | null;
  source_material_id: string | null;
  source_supplier_id: string | null;
  target_market: string | null;
  country_scope: string | null;
  product_scope_notes: string | null;
  scope_calculated_at: string | null;
  contained_at: string | null;
  completed_at: string | null;
  closed_at: string | null;
  total_affected_qty: string | null;
  total_affected_customers: number | null;
  recovery_pct: string | null;
  effectiveness_score: string | null;
  time_to_trace_hours: string | null;
  time_to_contain_hours: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecallScopeLine {
  id: string;
  recall_id: string;
  affected_item_id: string | null;
  affected_material_id: string | null;
  affected_lot_id: string | null;
  affected_warehouse_id: string | null;
  affected_qty_total: string;
  affected_qty_in_stock: string;
  affected_qty_in_transit: string;
  affected_qty_shipped: string;
  affected_qty_returned: string;
  affected_qty_quarantined: string;
  affected_qty_scrapped: string;
  affected_qty_reworked: string;
  affected_customer_count: number;
  risk_status: RecallRiskStatus;
  action_status: RecallActionStatus;
  hold_placed: boolean;
  hold_placed_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface RecallAction {
  id: string;
  recall_id: string;
  action_type: RecallActionType;
  status: RecallActionStatus;
  target_entity_type: string | null;
  target_entity_id: string | null;
  target_description: string | null;
  assigned_to_id: string | null;
  due_date: string | null;
  completed_at: string | null;
  completed_by_id: string | null;
  evidence_note: string | null;
  notes: string | null;
  created_at: string;
}

export interface RecallCustomerImpact {
  id: string;
  recall_id: string;
  customer_id: string | null;
  customer_name: string | null;
  contact_info: string | null;
  country_code: string | null;
  channel: string | null;
  affected_lot_id: string | null;
  shipment_reference: string | null;
  delivery_date: string | null;
  qty_delivered: string | null;
  qty_remaining_open: string | null;
  notification_sent: boolean;
  notification_sent_at: string | null;
  return_requested: boolean;
  return_confirmed: boolean;
  qty_returned: string | null;
  priority_rank: number | null;
  risk_level: RecallRiskStatus | null;
  notes: string | null;
  created_at: string;
}

export interface RecallReturn {
  id: string;
  recall_id: string;
  customer_id: string | null;
  lot_id: string | null;
  qty_requested: string | null;
  qty_confirmed: string | null;
  qty_received: string | null;
  qty_destroyed_at_customer: string | null;
  qty_quarantined_on_return: string | null;
  qty_reworked: string | null;
  qty_written_off: string | null;
  return_date: string | null;
  return_ref: string | null;
  discrepancy: string | null;
  return_refused: boolean;
  follow_up_required: boolean;
  evidence_notes: string | null;
  created_at: string;
}

export interface TRRecAIRecommendation {
  id: string;
  agent_type: TRRecAIAgentType;
  status: TRRecAIRecStatus;
  recall_id: string | null;
  lot_id: string | null;
  customer_id: string | null;
  warehouse_id: string | null;
  title: string;
  explanation: string;
  recommendation: string;
  confidence_score: string | null;
  priority_score: number | null;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface RecallDetail extends RecallHeader {
  scope_lines: RecallScopeLine[];
  actions: RecallAction[];
  customer_impacts: RecallCustomerImpact[];
  returns: RecallReturn[];
  ai_recs: TRRecAIRecommendation[];
}

export interface RecallDashboard {
  total_recalls: number;
  active_recalls: number;
  critical_recalls: number;
  completed_recalls: number;
  avg_time_to_trace_h: string | null;
  avg_recovery_pct: string | null;
  recent_recalls: RecallHeader[];
  pending_actions: number;
  open_scope_lines: number;
}

export interface RecallRegulatoryReport {
  recall_no: string;
  recall_type: RecallType;
  severity_level: RecallSeverity;
  trigger_source: RecallTrigger;
  initiation_datetime: string;
  recall_reason: string;
  source_lot_number: string | null;
  total_affected_qty: string | null;
  total_affected_customers: number | null;
  affected_lots: string[];
  affected_markets: string;
  actions_taken: string[];
  recovery_pct: string | null;
  time_to_trace_hours: string | null;
  time_to_contain_hours: string | null;
  status: RecallStatus;
  summary_narrative: string;
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

export const traceApi = {
  // Trace events
  createEvent: (d: Partial<TraceEvent>) =>
    req<TraceEvent>(`${BASE}/events`, { method: "POST", body: JSON.stringify(d) }),
  listEvents: (lotId?: string, eventType?: TraceEventType, limit = 200) => {
    const p = new URLSearchParams({ limit: String(limit) });
    if (lotId) p.set("lot_id", lotId);
    if (eventType) p.set("event_type", eventType);
    return req<TraceEvent[]>(`${BASE}/events?${p}`);
  },

  // Genealogy
  createLink: (d: Partial<GenealogyLink>) =>
    req<GenealogyLink>(`${BASE}/genealogy/links`, { method: "POST", body: JSON.stringify(d) }),
  listLinks: (lotId: string, direction = "both") =>
    req<GenealogyLink[]>(`${BASE}/genealogy/links/${lotId}?direction=${direction}`),
  getGenealogyTree: (lotId: string, direction = "both", maxDepth = 6) =>
    req<GenealogyTree>(`${BASE}/genealogy/${lotId}?direction=${direction}&max_depth=${maxDepth}`),

  // Search
  search: (d: Record<string, unknown>) =>
    req<TraceabilitySearchResult[]>(`${BASE}/search`, { method: "POST", body: JSON.stringify(d) }),

  // Forward / Backward
  forwardTrace: (lotId: string, maxDepth = 8) =>
    req<ForwardTraceResult>(`${BASE}/forward/${lotId}?max_depth=${maxDepth}`),
  backwardTrace: (lotId: string, maxDepth = 8) =>
    req<BackwardTraceResult>(`${BASE}/backward/${lotId}?max_depth=${maxDepth}`),

  // Recall dashboard
  getRecallDashboard: () => req<RecallDashboard>(`${BASE}/recalls/dashboard`),

  // Recall CRUD
  initiateRecall: (d: Record<string, unknown>) =>
    req<RecallHeader>(`${BASE}/recalls`, { method: "POST", body: JSON.stringify(d) }),
  listRecalls: (status?: RecallStatus) => {
    const p = new URLSearchParams();
    if (status) p.set("status", status);
    return req<RecallHeader[]>(`${BASE}/recalls?${p}`);
  },
  getRecallDetail: (id: string) => req<RecallDetail>(`${BASE}/recalls/${id}`),
  updateRecallStatus: (id: string, d: Record<string, unknown>) =>
    req<RecallHeader>(`${BASE}/recalls/${id}/status`, { method: "PATCH", body: JSON.stringify(d) }),

  // Scope
  calculateScope: (id: string) =>
    req<RecallScopeLine[]>(`${BASE}/recalls/${id}/scope-calculate`, { method: "POST" }),

  // Containment
  containRecall: (id: string) =>
    req<{ holds_placed: number }>(`${BASE}/recalls/${id}/contain`, { method: "POST" }),

  // Actions
  createAction: (id: string, d: Record<string, unknown>) =>
    req<RecallAction>(`${BASE}/recalls/${id}/actions`, { method: "POST", body: JSON.stringify(d) }),
  completeAction: (actionId: string, d: Record<string, unknown>) =>
    req<RecallAction>(`${BASE}/recalls/actions/${actionId}/complete`, { method: "POST", body: JSON.stringify(d) }),
  listActions: (id: string) => req<RecallAction[]>(`${BASE}/recalls/${id}/actions`),

  // Customer impact
  buildCustomerImpact: (id: string) =>
    req<RecallCustomerImpact[]>(`${BASE}/recalls/${id}/customer-impact/build`, { method: "POST" }),
  getCustomerImpact: (id: string) => req<RecallCustomerImpact[]>(`${BASE}/recalls/${id}/customer-impact`),
  notifyCustomer: (impactId: string, method = "email") =>
    req<RecallCustomerImpact>(`${BASE}/recalls/customer-impact/${impactId}/notify?method=${method}`, { method: "POST" }),

  // Returns
  recordReturn: (id: string, d: Record<string, unknown>) =>
    req<RecallReturn>(`${BASE}/recalls/${id}/returns`, { method: "POST", body: JSON.stringify(d) }),
  listReturns: (id: string) => req<RecallReturn[]>(`${BASE}/recalls/${id}/returns`),

  // Close
  closeRecall: (id: string, score?: number) => {
    const p = new URLSearchParams();
    if (score !== undefined) p.set("effectiveness_score", String(score));
    return req<RecallHeader>(`${BASE}/recalls/${id}/close?${p}`, { method: "POST" });
  },

  // Regulatory report
  getRegulatoryReport: (id: string) => req<RecallRegulatoryReport>(`${BASE}/recalls/${id}/regulatory-report`),

  // AI
  runAIAgents: (id: string) =>
    req<{ generated: number }>(`${BASE}/recalls/${id}/run-ai-agents`, { method: "POST" }),
  listAIRecs: (id: string) => req<TRRecAIRecommendation[]>(`${BASE}/recalls/${id}/ai-recommendations`),
  reviewAIRec: (recId: string, d: Record<string, unknown>) =>
    req<TRRecAIRecommendation>(`${BASE}/recalls/ai-recommendations/${recId}/review`, {
      method: "POST", body: JSON.stringify(d),
    }),
};

// ── Label & Color Maps ────────────────────────────────────────────────────────

export const RECALL_STATUS_BG: Record<RecallStatus, string> = {
  draft:        "bg-gray-100 text-gray-700",
  under_review: "bg-yellow-100 text-yellow-700",
  active:       "bg-blue-100 text-blue-700",
  contained:    "bg-purple-100 text-purple-700",
  in_progress:  "bg-indigo-100 text-indigo-700",
  completed:    "bg-teal-100 text-teal-700",
  closed:       "bg-green-100 text-green-700",
  cancelled:    "bg-gray-100 text-gray-400",
};

export const SEVERITY_BG: Record<RecallSeverity, string> = {
  low:      "bg-green-100 text-green-700",
  medium:   "bg-yellow-100 text-yellow-700",
  high:     "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export const RISK_BG: Record<RecallRiskStatus, string> = {
  low:      "bg-green-100 text-green-700",
  medium:   "bg-yellow-100 text-yellow-700",
  high:     "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export const ACTION_STATUS_BG: Record<RecallActionStatus, string> = {
  pending:    "bg-gray-100 text-gray-700",
  in_progress:"bg-blue-100 text-blue-700",
  completed:  "bg-green-100 text-green-700",
  cancelled:  "bg-gray-100 text-gray-400",
  overdue:    "bg-red-100 text-red-700",
};

export const STAGE_COLOR: Record<TraceItemStage, string> = {
  supplier:     "border-purple-300 bg-purple-50",
  grn:          "border-blue-300 bg-blue-50",
  raw_stock:    "border-green-300 bg-green-50",
  prepared:     "border-yellow-300 bg-yellow-50",
  intermediate: "border-orange-300 bg-orange-50",
  bulk:         "border-amber-300 bg-amber-50",
  finished_good:"border-teal-300 bg-teal-50",
  packaging:    "border-cyan-300 bg-cyan-50",
  quarantine:   "border-red-300 bg-red-50",
  rework:       "border-pink-300 bg-pink-50",
  scrapped:     "border-gray-300 bg-gray-100",
  shipped:      "border-indigo-300 bg-indigo-50",
  returned:     "border-violet-300 bg-violet-50",
};

export const RECALL_ACTION_LABEL: Record<RecallActionType, string> = {
  quarantine:            "Quarantine Stock",
  shipment_block:        "Block Shipments",
  customer_notify:       "Notify Customer",
  distributor_notify:    "Notify Distributor",
  internal_hold:         "Internal Hold",
  return_request:        "Request Return",
  destroy:               "Destroy Product",
  rework:                "Initiate Rework",
  regulatory_report:     "Submit Regulatory Report",
  followup_call:         "Follow-up Call",
  closeout_verification: "Closeout Verification",
};

export const AI_AGENT_LABEL: Record<TRRecAIAgentType, string> = {
  scope_validator:         "Scope Validator",
  risk_prioritizer:        "Risk Prioritizer",
  investigation_assistant: "Investigation Assistant",
};

export const TRACE_EVENT_LABEL: Record<TraceEventType, string> = {
  receipt:       "Receipt",
  issue:         "Issue",
  consumption:   "Consumption",
  transformation:"Transformation",
  packaging:     "Packaging",
  shipment:      "Shipment",
  return_event:  "Return",
  rework:        "Rework",
  scrap:         "Scrap",
  transfer:      "Transfer",
  quarantine:    "Quarantine",
  recall_action: "Recall Action",
  adjustment:    "Adjustment",
};
