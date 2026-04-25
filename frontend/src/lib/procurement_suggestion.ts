import { apiClient } from "@/lib/api";

// ── Enums ─────────────────────────────────────────────────────────────────────

export type PSRunStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type PSSuggestionStatus = "DRAFT" | "REVIEWED" | "APPROVED" | "CONVERTED" | "REJECTED";
export type PSUrgencyLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type PSGroupStatus = "DRAFT" | "SENT" | "CONVERTED";
export type PSAIAgentType = "SUPPLIER_OPTIMIZER" | "DEMAND_RISK_PREDICTOR" | "COST_OPTIMIZER";
export type SupplierItemPriority = "PRIMARY" | "SECONDARY" | "TERTIARY" | "FALLBACK";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PSDashboard {
  total_runs: number;
  latest_run_no: string | null;
  latest_run_status: string | null;
  open_suggestions: number;
  critical_suggestions: number;
  high_suggestions: number;
  risk_flagged: number;
  total_estimated_cost: number;
  approved_count: number;
  converted_count: number;
  supplier_count: number;
  supplier_items_count: number;
  ai_recs_count: number;
}

export interface PSRunOut {
  id: string;
  run_no: string;
  suggestion_date: string;
  warehouse_id: string | null;
  warehouse_name: string | null;
  mrp_run_id: string | null;
  mrp_run_no: string | null;
  status: PSRunStatus;
  planning_horizon_days: number;
  include_safety_stock: boolean;
  include_reorder_point: boolean;
  suggestion_count: number | null;
  total_estimated_cost: number | null;
  currency: string;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface PSLineOut {
  id: string;
  run_id: string;
  material_id: string;
  material_name: string | null;
  material_code: string | null;
  uom: string | null;
  required_qty: number;
  available_qty: number;
  shortage_qty: number;
  safety_stock_qty: number;
  reorder_point_qty: number;
  incoming_po_qty: number;
  supplier_id: string | null;
  supplier_name: string | null;
  alternative_supplier_ids: string[] | null;
  supplier_price: number | null;
  currency: string;
  moq: number | null;
  pack_size: number | null;
  adjusted_order_qty: number;
  estimated_total_cost: number | null;
  lead_time_days: number | null;
  buffer_days: number;
  required_date: string | null;
  suggested_order_date: string | null;
  urgency_level: PSUrgencyLevel;
  risk_flag: boolean;
  risk_notes: string | null;
  recommendation_score: number | null;
  status: PSSuggestionStatus;
  group_id: string | null;
  converted_pr_id: string | null;
  notes: string | null;
}

export interface PSGroupOut {
  id: string;
  run_id: string;
  supplier_id: string;
  supplier_name: string | null;
  group_no: string | null;
  target_delivery_date: string | null;
  line_count: number;
  total_estimated_cost: number | null;
  currency: string;
  status: PSGroupStatus;
  converted_pr_id: string | null;
  notes: string | null;
  lines: PSLineOut[];
}

export interface PSAIRecOut {
  id: string;
  run_id: string;
  agent_type: PSAIAgentType;
  material_id: string | null;
  material_name: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  title: string;
  recommendation: string;
  rationale: string | null;
  potential_saving: number | null;
  priority: number;
  is_actioned: boolean;
  action_notes: string | null;
  created_at: string | null;
}

export interface SupplierCompareRow {
  supplier_id: string;
  supplier_name: string;
  supplier_code: string;
  priority: string;
  unit_price: number;
  currency: string;
  moq: number;
  lead_time_days: number;
  total_lead_days: number;
  reliability_score: number | null;
  contract_no: string | null;
  performance_score: number | null;
  is_preferred: boolean;
  score: number;
}

export interface SupplierCompareResult {
  material_id: string;
  material_name: string;
  material_code: string;
  suppliers: SupplierCompareRow[];
  recommended_supplier_id: string | null;
}

export interface SupplierItemPriceOut {
  id: string;
  supplier_id: string;
  supplier_name: string | null;
  material_id: string;
  material_name: string | null;
  material_code: string | null;
  unit_price: number;
  currency: string;
  moq: number;
  pack_size: number | null;
  lead_time_days: number;
  buffer_days: number;
  customs_days: number;
  priority: SupplierItemPriority;
  reliability_score: number | null;
  contract_no: string | null;
  is_active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface ShortageReportRow {
  material_id: string;
  material_code: string;
  material_name: string;
  uom: string | null;
  available_qty: number;
  required_qty: number;
  shortage_qty: number;
  safety_stock_qty: number;
  reorder_point_qty: number;
  urgency_level: string;
  risk_flag: boolean;
  suggested_order_date: string | null;
  required_date: string | null;
  supplier_name: string | null;
  estimated_cost: number | null;
}

// ── Color helpers ─────────────────────────────────────────────────────────────

export const urgencyColor = (u: PSUrgencyLevel) =>
  ({ CRITICAL: "red", HIGH: "orange", MEDIUM: "yellow", LOW: "green" }[u] ?? "gray");

export const urgencyBadge = (u: PSUrgencyLevel) => ({
  CRITICAL: "bg-red-100 text-red-700 border-red-300",
  HIGH:     "bg-orange-100 text-orange-700 border-orange-300",
  MEDIUM:   "bg-yellow-100 text-yellow-700 border-yellow-300",
  LOW:      "bg-green-100 text-green-700 border-green-300",
}[u] ?? "bg-gray-100 text-gray-600");

export const statusBadge = (s: PSSuggestionStatus) => ({
  DRAFT:     "bg-gray-100 text-gray-600",
  REVIEWED:  "bg-blue-100 text-blue-700",
  APPROVED:  "bg-green-100 text-green-700",
  CONVERTED: "bg-purple-100 text-purple-700",
  REJECTED:  "bg-red-100 text-red-700",
}[s] ?? "bg-gray-100 text-gray-600");

export const runStatusBadge = (s: PSRunStatus) => ({
  QUEUED:    "bg-gray-100 text-gray-600",
  RUNNING:   "bg-blue-100 text-blue-700",
  COMPLETED: "bg-green-100 text-green-700",
  FAILED:    "bg-red-100 text-red-700",
}[s] ?? "bg-gray-100 text-gray-600");

export const agentLabel = (a: PSAIAgentType) => ({
  SUPPLIER_OPTIMIZER:    "Supplier Optimizer",
  DEMAND_RISK_PREDICTOR: "Demand Risk Predictor",
  COST_OPTIMIZER:        "Cost Optimizer",
}[a] ?? a);

export const fmt = (n: number | null | undefined, dp = 2) =>
  n == null ? "—" : Number(n).toLocaleString("en-KE", { minimumFractionDigits: dp, maximumFractionDigits: dp });

// ── API client ─────────────────────────────────────────────────────────────────

const BASE = "/api/v1/procurement/suggestions";

export const psApi = {
  getDashboard: () =>
    apiClient.get<PSDashboard>(`${BASE}/dashboard`),

  listRuns: (skip = 0, limit = 50) =>
    apiClient.get<PSRunOut[]>(`${BASE}/runs?skip=${skip}&limit=${limit}`),

  createRun: (payload: {
    warehouse_id?: string;
    mrp_run_id?: string;
    planning_horizon_days?: number;
    include_safety_stock?: boolean;
    include_reorder_point?: boolean;
    currency?: string;
    notes?: string;
  }) => apiClient.post<PSRunOut>(`${BASE}/runs`, payload),

  getRun: (id: string) =>
    apiClient.get<PSRunOut>(`${BASE}/runs/${id}`),

  executeRun: (id: string) =>
    apiClient.post<PSRunOut>(`${BASE}/runs/${id}/execute`, {}),

  listSuggestions: (runId: string, params?: {
    urgency?: PSUrgencyLevel;
    risk_only?: boolean;
    status?: PSSuggestionStatus;
    skip?: number;
    limit?: number;
  }) => {
    const qs = new URLSearchParams({ run_id: runId });
    if (params?.urgency)   qs.set("urgency", params.urgency);
    if (params?.risk_only) qs.set("risk_only", "true");
    if (params?.status)    qs.set("status", params.status);
    if (params?.skip)      qs.set("skip", String(params.skip));
    if (params?.limit)     qs.set("limit", String(params.limit));
    return apiClient.get<PSLineOut[]>(`${BASE}/suggestions?${qs}`);
  },

  updateSuggestion: (id: string, payload: Partial<PSLineOut>) =>
    apiClient.patch<PSLineOut>(`${BASE}/suggestions/${id}`, payload),

  approveSuggestion: (id: string) =>
    apiClient.post<PSLineOut>(`${BASE}/suggestions/${id}/approve`, {}),

  rejectSuggestion: (id: string, reason?: string) =>
    apiClient.post<PSLineOut>(`${BASE}/suggestions/${id}/reject?reason=${encodeURIComponent(reason ?? "")}`, {}),

  listGroups: (runId: string) =>
    apiClient.get<PSGroupOut[]>(`${BASE}/groups?run_id=${runId}`),

  convertGroupToPR: (payload: { group_id: string; required_date: string; notes?: string }) =>
    apiClient.post<{ pr_id: string; pr_no: string; status: string }>(`${BASE}/groups/convert-to-pr`, payload),

  compareSuppliers: (materialId: string) =>
    apiClient.get<SupplierCompareResult>(`${BASE}/suppliers/${materialId}/compare`),

  listSupplierPrices: (params?: { material_id?: string; supplier_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.material_id) qs.set("material_id", params.material_id);
    if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
    return apiClient.get<SupplierItemPriceOut[]>(`${BASE}/supplier-prices?${qs}`);
  },

  createSupplierPrice: (payload: Partial<SupplierItemPriceOut>) =>
    apiClient.post<SupplierItemPriceOut>(`${BASE}/supplier-prices`, payload),

  updateSupplierPrice: (id: string, payload: Partial<SupplierItemPriceOut>) =>
    apiClient.patch<SupplierItemPriceOut>(`${BASE}/supplier-prices/${id}`, payload),

  deleteSupplierPrice: (id: string) =>
    apiClient.delete(`${BASE}/supplier-prices/${id}`),

  runAIAgents: (runId: string) =>
    apiClient.post<{ generated: number; by_agent: Record<string, number> }>(`${BASE}/runs/${runId}/ai/run`, {}),

  listAIRecs: (runId: string) =>
    apiClient.get<PSAIRecOut[]>(`${BASE}/runs/${runId}/ai/recommendations`),

  actionAIRec: (recId: string, notes?: string) =>
    apiClient.post<PSAIRecOut>(`${BASE}/ai/recommendations/${recId}/action?notes=${encodeURIComponent(notes ?? "")}`, {}),

  shortageReport: (runId: string) =>
    apiClient.get<ShortageReportRow[]>(`${BASE}/reports/shortages?run_id=${runId}`),
};
