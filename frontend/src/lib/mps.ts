import { apiClient } from "@/lib/api";

// ── Enums ─────────────────────────────────────────────────────────────────────

export type MPSPlanningMode = "MANUAL" | "ASSISTED" | "AUTO" | "AI";
export type MPSCapacityMode = "FINITE" | "INFINITE";
export type MPSStatus = "DRAFT" | "APPROVED" | "RELEASED" | "CLOSED";
export type MPSFeasibilityStatus =
  | "PENDING" | "FEASIBLE" | "OVERLOADED" | "MATERIAL_SHORT" | "INFEASIBLE" | "ON_HOLD";
export type MPSAgentType = "OPTIMIZER" | "RISK_PREDICTOR";
export type MPSRecType = "SEQUENCE" | "CAMPAIGN" | "BATCH_SIZE" | "RISK_ALERT" | "CAPACITY" | "SPLIT" | "MERGE";
export type MPSRecStatus = "PENDING" | "ACCEPTED" | "REJECTED";
export type WhatIfStatus = "DRAFT" | "COMPUTED";
export type MPSChangeType =
  | "DELAY" | "BATCH_SIZE" | "LINE_CHANGE" | "SPLIT" | "MERGE" | "SHIFT_ADD" | "QTY_ADJUST";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MPSPlanSummary {
  id: string;
  plan_no: string;
  plan_name: string;
  status: MPSStatus;
  planning_mode: MPSPlanningMode;
  capacity_mode: MPSCapacityMode;
  start_date: string;
  end_date: string;
  total_lines: number;
  overloaded_lines: number;
  feasible_lines: number;
  created_at: string;
}

export interface MPSPlan extends MPSPlanSummary {
  plant_code: string | null;
  planning_horizon_days: number;
  mrp_run_id: string | null;
  locked_lines: number;
  approved_at: string | null;
  released_at: string | null;
  created_by_id: string | null;
  approved_by_id: string | null;
  notes: string | null;
  updated_at: string;
}

export interface MPSLine {
  id: string;
  line_no: string;
  mps_id: string;
  product_id: string;
  product_name?: string;
  product_code?: string;
  mrp_result_id: string | null;
  period_label: string | null;
  period_start: string;
  period_end: string;
  confirmed_demand_qty: number;
  forecast_qty: number;
  safety_stock_qty: number;
  net_requirement_qty: number;
  planned_production_qty: number;
  batch_size_qty: number | null;
  num_batches: number | null;
  work_center_id: string | null;
  work_center_name?: string;
  planned_start_date: string | null;
  planned_end_date: string | null;
  required_hours: number | null;
  campaign_id: string | null;
  priority_score: number;
  feasibility_status: MPSFeasibilityStatus;
  overload_hours: number | null;
  is_locked: boolean;
  remarks: string | null;
  production_order_id: string | null;
}

export interface MPSCampaign {
  id: string;
  campaign_code: string;
  campaign_name: string;
  mps_id: string;
  work_center_id: string | null;
  campaign_start: string | null;
  campaign_end: string | null;
  total_production_hrs: number;
  total_changeover_hrs: number;
  sequence_order: number;
  sku_count: number;
  notes: string | null;
}

export interface CapacitySlot {
  id: string;
  work_center_id: string;
  slot_date: string;
  available_hours: number;
  allocated_hours: number;
  downtime_hours: number;
  overload_hours: number;
  utilization_pct: number;
  is_overloaded: boolean;
  work_center_name?: string;
}

export interface CapacityHeatmapRow {
  work_center_id: string;
  work_center_name: string;
  slots: CapacitySlot[];
  peak_utilization_pct: number;
  overloaded_days: number;
}

export interface CapacityHeatmap {
  mps_id: string;
  rows: CapacityHeatmapRow[];
  overload_alerts: Array<{
    work_center: string;
    date: string;
    overload_hours: number;
    utilization_pct: number;
  }>;
}

export interface WhatIfChange {
  line_id: string;
  change_type: MPSChangeType;
  new_value: unknown;
}

export interface MPSWhatIf {
  id: string;
  scenario_no: string;
  scenario_name: string;
  mps_id: string;
  description: string | null;
  changes: WhatIfChange[];
  impact_service_level_pct: number | null;
  impact_delay_count: number | null;
  impact_cost_delta: number | null;
  impact_summary: string | null;
  status: WhatIfStatus;
  created_by_id: string | null;
  created_at: string;
}

export interface MPSAIRec {
  id: string;
  mps_id: string;
  agent_type: MPSAgentType;
  rec_type: MPSRecType;
  affected_line_ids: string[];
  recommendation: string;
  impact_summary: string | null;
  confidence_score: number;
  status: MPSRecStatus;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface MPSDashboard {
  active_plans: number;
  total_lines: number;
  overloaded_lines: number;
  feasible_lines: number;
  pending_ai_recs: number;
  pending_approvals: number;
  overload_alerts: Array<{
    line_id: string;
    line_no: string;
    product_id: string;
    overload_hours: number;
    period_start: string;
  }>;
  recent_plans: MPSPlanSummary[];
}

// ── Color / Label maps ────────────────────────────────────────────────────────

export const FEASIBILITY_COLOR: Record<MPSFeasibilityStatus, string> = {
  PENDING:        "bg-gray-100 text-gray-600",
  FEASIBLE:       "bg-green-100 text-green-700",
  OVERLOADED:     "bg-red-100 text-red-700",
  MATERIAL_SHORT: "bg-orange-100 text-orange-700",
  INFEASIBLE:     "bg-red-200 text-red-800",
  ON_HOLD:        "bg-yellow-100 text-yellow-700",
};

export const STATUS_COLOR: Record<MPSStatus, string> = {
  DRAFT:    "bg-gray-100 text-gray-600",
  APPROVED: "bg-blue-100 text-blue-700",
  RELEASED: "bg-green-100 text-green-700",
  CLOSED:   "bg-slate-100 text-slate-600",
};

export const REC_STATUS_COLOR: Record<MPSRecStatus, string> = {
  PENDING:  "bg-yellow-100 text-yellow-700",
  ACCEPTED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
};

export const AGENT_LABEL: Record<MPSAgentType, string> = {
  OPTIMIZER:      "Optimizer",
  RISK_PREDICTOR: "Risk Predictor",
};

export const REC_TYPE_COLOR: Record<MPSRecType, string> = {
  SEQUENCE:   "bg-blue-100 text-blue-700",
  CAMPAIGN:   "bg-purple-100 text-purple-700",
  BATCH_SIZE: "bg-teal-100 text-teal-700",
  RISK_ALERT: "bg-red-100 text-red-700",
  CAPACITY:   "bg-orange-100 text-orange-700",
  SPLIT:      "bg-sky-100 text-sky-700",
  MERGE:      "bg-indigo-100 text-indigo-700",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

export function fmtHours(h: number | null): string {
  if (h == null) return "—";
  return `${h.toFixed(1)} hrs`;
}

export function utilizationColor(pct: number): string {
  if (pct >= 100) return "bg-red-500";
  if (pct >= 80) return "bg-orange-400";
  if (pct >= 60) return "bg-yellow-400";
  return "bg-green-400";
}

// ── API ───────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/mps";

export const mpsApi = {
  // Dashboard
  dashboard: () => apiClient.get<MPSDashboard>(`${BASE}/dashboard`),

  // Plans
  createPlan: (body: {
    plan_name: string;
    start_date: string;
    end_date: string;
    planning_horizon_days?: number;
    planning_mode?: MPSPlanningMode;
    capacity_mode?: MPSCapacityMode;
    mrp_run_id?: string;
    notes?: string;
  }) => apiClient.post<MPSPlan>(`${BASE}/plans`, body),

  listPlans: (limit = 50, offset = 0) =>
    apiClient.get<MPSPlanSummary[]>(`${BASE}/plans?limit=${limit}&offset=${offset}`),

  getPlan: (id: string) => apiClient.get<MPSPlan>(`${BASE}/plans/${id}`),

  generateFromMrp: (mpsId: string, body: {
    mrp_run_id: string;
    period_type?: string;
    respect_batch_sizes?: boolean;
    default_batch_qty?: number;
  }) => apiClient.post<{ lines_created: number }>(`${BASE}/plans/${mpsId}/generate-from-mrp`, body),

  runCapacity:  (id: string) => apiClient.post<Record<string, unknown>>(`${BASE}/plans/${id}/run-capacity`, {}),
  runCampaigns: (id: string) => apiClient.post<Record<string, unknown>>(`${BASE}/plans/${id}/run-campaigns`, {}),
  runAI:        (id: string) => apiClient.post<Record<string, unknown>>(`${BASE}/plans/${id}/run-ai`, {}),
  approvePlan:  (id: string) => apiClient.patch<MPSPlan>(`${BASE}/plans/${id}/approve`, {}),
  releasePlan:  (id: string, targetWarehouseId: string) =>
    apiClient.post<Record<string, unknown>>(`${BASE}/plans/${id}/release?target_warehouse_id=${targetWarehouseId}`, {}),

  // Lines
  listLines: (mpsId: string) => apiClient.get<MPSLine[]>(`${BASE}/plans/${mpsId}/lines`),
  updateLine: (mpsId: string, lineId: string, body: Partial<MPSLine>) =>
    apiClient.patch<MPSLine>(`${BASE}/plans/${mpsId}/lines/${lineId}`, body),

  // Capacity
  getCapacityHeatmap: (mpsId: string) => apiClient.get<CapacityHeatmap>(`${BASE}/plans/${mpsId}/capacity-heatmap`),
  getRescheduleSuggestion: (lineId: string) =>
    apiClient.get<Record<string, unknown>>(`${BASE}/lines/${lineId}/reschedule-suggestion`),

  // Campaigns
  getCampaigns: (mpsId: string) => apiClient.get<MPSCampaign[]>(`${BASE}/plans/${mpsId}/campaigns`),

  // What-If
  createWhatIf: (mpsId: string, body: { scenario_name: string; description?: string; changes: WhatIfChange[] }) =>
    apiClient.post<MPSWhatIf>(`${BASE}/plans/${mpsId}/whatif`, body),
  listWhatIf: (mpsId: string) => apiClient.get<MPSWhatIf[]>(`${BASE}/plans/${mpsId}/whatif`),
  getWhatIf: (id: string) => apiClient.get<MPSWhatIf>(`${BASE}/whatif/${id}`),

  // AI
  getAIRecs: (mpsId: string) => apiClient.get<MPSAIRec[]>(`${BASE}/plans/${mpsId}/ai-recommendations`),
  acceptRec: (recId: string) => apiClient.patch<MPSAIRec>(`${BASE}/ai-recommendations/${recId}/accept`, {}),
  rejectRec: (recId: string) => apiClient.patch<MPSAIRec>(`${BASE}/ai-recommendations/${recId}/reject`, {}),
};
