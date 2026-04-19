import { apiClient } from "./api";

// ── Enums ──────────────────────────────────────────────────────────────────────

export type ProdExecStatus =
  | "DRAFT" | "PLANNED" | "RELEASED" | "IN_PROGRESS"
  | "PAUSED" | "COMPLETED" | "CLOSED" | "CANCELLED";

export type WOExecStatus =
  | "PENDING" | "READY" | "IN_PROGRESS" | "PAUSED" | "COMPLETED" | "CANCELLED";

export type ExecSourceType =
  | "MRP" | "MPS" | "MANUAL" | "SALES" | "SUBCONTRACT_RETURN";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ExecWorkOrderOut {
  id: string;
  production_order_id: string;
  operation_code: string | null;
  step_sequence: number;
  step_name: string;
  work_center_id: string | null;
  section_id: string | null;
  line_id: string | null;
  machine_id: string | null;
  assigned_operator_id: string | null;
  planned_qty: number;
  completed_qty: number;
  scrap_qty: number;
  rework_qty: number;
  setup_time_planned: number;
  run_time_planned: number;
  cleanup_time_planned: number;
  setup_time_actual: number | null;
  run_time_actual: number | null;
  cleanup_time_actual: number | null;
  dependency_work_order_id: string | null;
  qc_required_flag: boolean;
  qc_passed: boolean | null;
  scrap_category: string | null;
  scrap_reason: string | null;
  status: WOExecStatus;
  started_at: string | null;
  completed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecOrderMaterialOut {
  id: string;
  production_order_id: string;
  work_order_id: string | null;
  item_type: string;
  item_id: string | null;
  item_name: string | null;
  item_code: string | null;
  required_qty: number;
  reserved_qty: number;
  issued_qty: number;
  consumed_qty: number;
  returned_qty: number;
  scrapped_qty: number;
  uom: string;
  status: string;
  lot_numbers: string[] | null;
  unit_cost: number | null;
  extended_cost: number | null;
}

export interface BatchGenealogyOut {
  id: string;
  production_order_id: string;
  input_lot_no: string | null;
  input_item_name: string | null;
  input_qty: number | null;
  input_uom: string | null;
  input_supplier: string | null;
  output_lot_no: string | null;
  output_item_name: string | null;
  output_qty: number | null;
  output_uom: string | null;
  link_type: string;
  created_at: string;
}

export interface ProdExecOrderSummary {
  id: string;
  order_no: string;
  product_id: string | null;
  product_name: string | null;
  bom_id: string | null;
  bom_code: string | null;
  planned_qty: number;
  completed_qty: number;
  scrap_qty: number;
  uom: string;
  batch_no: string | null;
  source_type: string;
  priority: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  status: ProdExecStatus;
  is_rework: boolean;
  is_split: boolean;
  parent_order_id: string | null;
  total_actual_cost: number;
  cost_per_uom: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProdExecOrderOut extends ProdExecOrderSummary {
  routing_id: string | null;
  plant_id: string | null;
  section_id: string | null;
  line_id: string | null;
  preferred_machine_id: string | null;
  planned_material_cost: number;
  actual_material_cost: number;
  planned_labor_cost: number;
  actual_labor_cost: number;
  overhead_cost: number;
  rework_qty: number;
  rework_reason: string | null;
  remarks: string | null;
  approved_by: string | null;
  work_orders: ExecWorkOrderOut[];
  materials: ExecOrderMaterialOut[];
}

export interface ExecAIRecOut {
  id: string;
  production_order_id: string;
  agent_type: string;
  status: string;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  confidence_score: number | null;
  actioned_at: string | null;
  created_at: string;
}

export interface ExecDashboard {
  total_orders: number;
  draft_orders: number;
  released_orders: number;
  in_progress_orders: number;
  completed_today: number;
  delayed_orders: number;
  total_work_orders: number;
  pending_work_orders: number;
  active_work_orders: number;
  total_scrap_qty: number;
  pending_ai_recs: number;
  by_status: Record<string, number>;
  recent_orders: ProdExecOrderSummary[];
}

// ── Color maps ─────────────────────────────────────────────────────────────────

export const STATUS_COLOR: Record<ProdExecStatus, string> = {
  DRAFT:       "bg-gray-100 text-gray-600",
  PLANNED:     "bg-blue-100 text-blue-700",
  RELEASED:    "bg-indigo-100 text-indigo-700",
  IN_PROGRESS: "bg-yellow-100 text-yellow-700",
  PAUSED:      "bg-orange-100 text-orange-700",
  COMPLETED:   "bg-green-100 text-green-700",
  CLOSED:      "bg-teal-100 text-teal-700",
  CANCELLED:   "bg-red-100 text-red-700",
};

export const WO_STATUS_COLOR: Record<WOExecStatus, string> = {
  PENDING:     "bg-gray-100 text-gray-500",
  READY:       "bg-blue-100 text-blue-700",
  IN_PROGRESS: "bg-yellow-100 text-yellow-700",
  PAUSED:      "bg-orange-100 text-orange-700",
  COMPLETED:   "bg-green-100 text-green-700",
  CANCELLED:   "bg-red-100 text-red-700",
};

export const LIFECYCLE_NEXT: Partial<Record<ProdExecStatus, string>> = {
  DRAFT:       "Mark Planned",
  PLANNED:     "Release",
  RELEASED:    "Start",
  IN_PROGRESS: "Complete",
  COMPLETED:   "Close",
};

export function fmtKES(v: number): string {
  return `KES ${v.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtMins(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

// ── API client ─────────────────────────────────────────────────────────────────

const BASE = "/production-execution";

export const execApi = {
  dashboard: () => apiClient.get<ExecDashboard>(`${BASE}/dashboard`),

  // Orders
  list:    (params?: { status?: string; product_id?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).filter(([, v]) => v) as [string, string][]
    ).toString();
    return apiClient.get<ProdExecOrderSummary[]>(`${BASE}${qs ? `?${qs}` : ""}`);
  },
  create:  (body: Partial<ProdExecOrderOut>) => apiClient.post<ProdExecOrderOut>(BASE, body),
  get:     (id: string) => apiClient.get<ProdExecOrderOut>(`${BASE}/${id}`),
  update:  (id: string, body: Partial<ProdExecOrderOut>) => apiClient.patch<ProdExecOrderOut>(`${BASE}/${id}`, body),

  // Lifecycle
  advance:  (id: string) => apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/advance`, {}),
  release:  (id: string) => apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/release`, {}),
  start:    (id: string) => apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/start`, {}),
  pause:    (id: string) => apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/pause`, {}),
  complete: (id: string, body: { completed_qty: number; scrap_qty?: number; remarks?: string }) =>
    apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/complete`, body),
  close:    (id: string) => apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/close`, {}),
  cancel:   (id: string) => apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/cancel`, {}),

  // Split / Merge / Rework
  split:  (id: string, split_qtys: number[], reason?: string) =>
    apiClient.post<ProdExecOrderOut[]>(`${BASE}/${id}/split`, { split_qtys, reason }),
  merge:  (order_ids: string[], reason?: string) =>
    apiClient.post<ProdExecOrderOut>(`${BASE}/merge`, { order_ids, reason }),
  rework: (id: string, qty: number, reason: string) =>
    apiClient.post<ProdExecOrderOut>(`${BASE}/${id}/rework`, { qty, reason }),

  // Genealogy
  genealogy: (id: string) => apiClient.get<any>(`${BASE}/${id}/genealogy`),
  addGenealogyLink: (id: string, body: Partial<BatchGenealogyOut>) =>
    apiClient.post<BatchGenealogyOut>(`${BASE}/${id}/genealogy`, body),

  // Batch record
  batchRecord: (id: string) => apiClient.get<any>(`${BASE}/${id}/batch-record`),

  // Work Orders
  listWorkOrders:    (params?: { status?: string }) => {
    const qs = params?.status ? `?status=${params.status}` : "";
    return apiClient.get<ExecWorkOrderOut[]>(`${BASE}/work-orders${qs}`);
  },
  addWorkOrder:     (orderId: string, body: Partial<ExecWorkOrderOut>) =>
    apiClient.post<ExecWorkOrderOut>(`${BASE}/${orderId}/work-orders`, body),
  startWorkOrder:   (woId: string) =>
    apiClient.post<ExecWorkOrderOut>(`${BASE}/work-orders/${woId}/start`, {}),
  completeWorkOrder:(woId: string, body: Record<string, unknown>) =>
    apiClient.post<ExecWorkOrderOut>(`${BASE}/work-orders/${woId}/complete`, body),
  updateWorkOrder:  (woId: string, body: Partial<ExecWorkOrderOut>) =>
    apiClient.patch<ExecWorkOrderOut>(`${BASE}/work-orders/${woId}`, body),

  // Materials
  addMaterial:    (orderId: string, body: Partial<ExecOrderMaterialOut>) =>
    apiClient.post<ExecOrderMaterialOut>(`${BASE}/${orderId}/materials`, body),
  issueMaterial:  (orderId: string, body: { material_id: string; qty: number; lot_no?: string; action: string }) =>
    apiClient.post<ExecOrderMaterialOut>(`${BASE}/${orderId}/materials/issue`, body),
  returnMaterial: (orderId: string, body: { material_id: string; qty: number; action: string }) =>
    apiClient.post<ExecOrderMaterialOut>(`${BASE}/${orderId}/materials/return`, body),

  // AI
  runAI:    (id: string) => apiClient.post<{ total: number }>(`${BASE}/${id}/run-ai`, {}),
  listAI:   (id: string) => apiClient.get<ExecAIRecOut[]>(`${BASE}/${id}/ai-recs`),
  actionAI: (recId: string, status: string) =>
    apiClient.post<ExecAIRecOut>(`${BASE}/ai-recs/${recId}/action`, { status }),
};
