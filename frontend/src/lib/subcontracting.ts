import { apiClient } from "@/lib/api";

// ── Enums ─────────────────────────────────────────────────────────────────────
export type SCOrderStatus = "DRAFT"|"APPROVED"|"ISSUED"|"IN_PROGRESS"|"PARTIALLY_RECEIVED"|"COMPLETED"|"CLOSED"|"CANCELLED";
export type SCIssueStatus = "DRAFT"|"ISSUED"|"PARTIALLY_RETURNED"|"RETURNED";
export type SCReceiptStatus = "DRAFT"|"POSTED"|"QC_HOLD"|"REJECTED";
export type SCYieldStatus = "NORMAL"|"LOW_YIELD"|"HIGH_SCRAP"|"ABNORMAL";
export type SCAIAgentType = "PERFORMANCE_ANALYZER"|"COST_OPTIMIZER"|"RISK_DETECTOR";

// ── Types ─────────────────────────────────────────────────────────────────────
export interface SCDashboard {
  total_orders: number; draft_orders: number; active_orders: number;
  completed_orders: number; overdue_orders: number;
  total_material_issued_value: number; avg_yield_pct: number|null;
  total_scrap_cost: number; ai_recs_count: number;
  supplier_count: number; locations_count: number;
}
export interface SubcontractorLocationOut {
  id: string; supplier_id: string; warehouse_id: string;
  is_active: boolean; notes: string|null; created_at: string|null;
  supplier_name: string|null; warehouse_name: string|null; warehouse_code: string|null;
}
export interface SCOrderLineOut {
  id: string; order_id: string; line_no: number;
  product_id: string|null; material_id: string|null;
  description: string|null; quantity_ordered: number; quantity_received: number;
  uom: string; bom_id: string|null; service_unit_cost: number|null;
  estimated_yield_pct: number|null; notes: string|null;
  product_name: string|null; material_name: string|null;
}
export interface SCOrderOut {
  id: string; order_no: string; supplier_id: string; order_date: string;
  expected_completion_date: string|null; actual_completion_date: string|null;
  status: SCOrderStatus; linked_po_id: string|null; warehouse_id: string|null;
  subcontractor_location_id: string|null;
  total_material_cost: number|null; total_service_cost: number|null;
  total_wastage_cost: number|null; currency: string;
  approved_by_id: string|null; approved_at: string|null;
  created_by_id: string|null; remarks: string|null; created_at: string|null;
  supplier_name: string|null; warehouse_name: string|null;
  lines: SCOrderLineOut[];
}
export interface SCIssueLineOut {
  id: string; issue_id: string; line_no: number; material_id: string;
  lot_id: string|null; quantity_issued: number; quantity_returned: number;
  quantity_consumed: number; quantity_scrapped: number; uom: string;
  unit_cost: number|null; stock_movement_id: string|null; notes: string|null;
  material_name: string|null; material_code: string|null; lot_number: string|null;
}
export interface SCIssueOut {
  id: string; issue_no: string; order_id: string; issue_date: string;
  status: SCIssueStatus; issued_by_id: string|null; notes: string|null;
  created_at: string|null; lines: SCIssueLineOut[];
}
export interface SCReceiptLineOut {
  id: string; receipt_id: string; order_line_id: string|null; line_no: number;
  product_id: string|null; material_id: string|null;
  quantity_received: number; quantity_accepted: number; quantity_rejected: number;
  uom: string; lot_number: string|null; expiry_date: string|null;
  unit_service_cost: number|null; stock_movement_id: string|null; notes: string|null;
  product_name: string|null; material_name: string|null;
}
export interface SCReceiptOut {
  id: string; receipt_no: string; order_id: string; receipt_date: string;
  status: SCReceiptStatus; received_by_id: string|null;
  qc_inspection_id: string|null; notes: string|null; created_at: string|null;
  lines: SCReceiptLineOut[];
}
export interface SCYieldOut {
  id: string; order_id: string; order_line_id: string;
  total_material_issued: number; expected_material_input: number|null;
  quantity_ordered: number; quantity_received: number;
  expected_yield_pct: number|null; actual_yield_pct: number|null;
  yield_variance_pct: number|null; yield_status: SCYieldStatus;
  total_scrapped: number; scrap_reason: string|null; scrap_cost: number|null;
  material_variance_qty: number|null; material_variance_cost: number|null;
  is_abnormal: boolean; notes: string|null;
}
export interface SCPerformanceOut {
  id: string; order_id: string; supplier_id: string;
  planned_completion: string|null; actual_completion: string|null;
  delay_days: number|null; on_time: boolean|null;
  total_qty_ordered: number; total_qty_received: number; total_qty_rejected: number;
  rejection_rate_pct: number|null; avg_yield_pct: number|null;
  budgeted_cost: number|null; actual_cost: number|null;
  cost_variance_pct: number|null; performance_score: number|null;
  notes: string|null; supplier_name: string|null; order_no: string|null;
}
export interface SCAIRecOut {
  id: string; order_id: string|null; supplier_id: string|null;
  agent_type: SCAIAgentType; title: string; recommendation: string;
  rationale: string|null; risk_level: string|null; potential_saving: number|null;
  priority: number; is_actioned: boolean; action_notes: string|null;
  created_at: string|null; supplier_name: string|null; order_no: string|null;
}
export interface SubcontractorStockRow {
  supplier_id: string; supplier_name: string;
  material_id: string; material_code: string; material_name: string; uom: string|null;
  qty_issued: number; qty_returned: number; qty_consumed: number;
  qty_scrapped: number; qty_balance: number;
  unit_cost: number|null; total_value: number|null;
}

// ── Color helpers ─────────────────────────────────────────────────────────────
export const orderStatusBadge = (s: SCOrderStatus) => ({
  DRAFT:"bg-gray-100 text-gray-600", APPROVED:"bg-blue-100 text-blue-700",
  ISSUED:"bg-indigo-100 text-indigo-700", IN_PROGRESS:"bg-yellow-100 text-yellow-700",
  PARTIALLY_RECEIVED:"bg-orange-100 text-orange-700", COMPLETED:"bg-green-100 text-green-700",
  CLOSED:"bg-purple-100 text-purple-700", CANCELLED:"bg-red-100 text-red-700",
}[s] ?? "bg-gray-100 text-gray-600");

export const yieldBadge = (s: SCYieldStatus) => ({
  NORMAL:"bg-green-100 text-green-700", LOW_YIELD:"bg-orange-100 text-orange-700",
  HIGH_SCRAP:"bg-red-100 text-red-700", ABNORMAL:"bg-red-200 text-red-800",
}[s] ?? "bg-gray-100 text-gray-600");

export const riskBadge = (r: string|null) => ({
  LOW:"bg-green-100 text-green-700", MEDIUM:"bg-yellow-100 text-yellow-700",
  HIGH:"bg-orange-100 text-orange-700", CRITICAL:"bg-red-100 text-red-700",
}[r ?? ""] ?? "bg-gray-100 text-gray-600");

export const agentLabel = (a: SCAIAgentType) => ({
  PERFORMANCE_ANALYZER:"Performance Analyzer",
  COST_OPTIMIZER:"Cost Optimizer",
  RISK_DETECTOR:"Risk Detector",
}[a] ?? a);

export const fmt = (n: number|null|undefined, dp = 2) =>
  n == null ? "—" : Number(n).toLocaleString("en-KE", {minimumFractionDigits: dp, maximumFractionDigits: dp});

// ── API client ────────────────────────────────────────────────────────────────
const B = "/api/v1/subcontracting";

export const scApi = {
  getDashboard: () => apiClient.get<SCDashboard>(`${B}/dashboard`).then((r) => r.data),

  listLocations: () => apiClient.get<SubcontractorLocationOut[]>(`${B}/locations`).then((r) => r.data),
  createLocation: (p: {supplier_id: string; warehouse_id: string; notes?: string}) =>
    apiClient.post<SubcontractorLocationOut>(`${B}/locations`, p).then((r) => r.data),

  listOrders: (params?: {status?: string; supplier_id?: string; skip?: number; limit?: number}) => {
    const qs = new URLSearchParams();
    if (params?.status)      qs.set("status", params.status);
    if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
    if (params?.skip)        qs.set("skip", String(params.skip));
    if (params?.limit)       qs.set("limit", String(params.limit));
    return apiClient.get<SCOrderOut[]>(`${B}/orders?${qs}`).then((r) => r.data);
  },
  createOrder: (p: Partial<SCOrderOut> & {lines?: Partial<SCOrderLineOut>[]}) =>
    apiClient.post<SCOrderOut>(`${B}/orders`, p).then((r) => r.data),
  getOrder: (id: string) => apiClient.get<SCOrderOut>(`${B}/orders/${id}`).then((r) => r.data),
  approveOrder: (id: string) => apiClient.post<SCOrderOut>(`${B}/orders/${id}/approve`, {}).then((r) => r.data),
  completeOrder: (id: string) => apiClient.post<SCOrderOut>(`${B}/orders/${id}/complete`, {}).then((r) => r.data),

  issueMaterial: (orderId: string, p: Partial<SCIssueOut> & {lines?: Partial<SCIssueLineOut>[]}) =>
    apiClient.post<SCIssueOut>(`${B}/orders/${orderId}/issue-material`, p).then((r) => r.data),
  listIssues: (orderId: string) => apiClient.get<SCIssueOut[]>(`${B}/orders/${orderId}/issues`).then((r) => r.data),

  receiveGoods: (orderId: string, p: Partial<SCReceiptOut> & {lines?: Partial<SCReceiptLineOut>[]}) =>
    apiClient.post<SCReceiptOut>(`${B}/orders/${orderId}/receive`, p).then((r) => r.data),
  listReceipts: (orderId: string) => apiClient.get<SCReceiptOut[]>(`${B}/orders/${orderId}/receipts`).then((r) => r.data),

  getYield: (orderId: string) => apiClient.get<SCYieldOut[]>(`${B}/orders/${orderId}/yield`).then((r) => r.data),
  yieldReport: (abnormalOnly = false) =>
    apiClient.get<SCYieldOut[]>(`${B}/yield/report?abnormal_only=${abnormalOnly}`).then((r) => r.data),

  getStock: (supplierId?: string) => {
    const qs = supplierId ? `?supplier_id=${supplierId}` : "";
    return apiClient.get<SubcontractorStockRow[]>(`${B}/stock${qs}`).then((r) => r.data);
  },

  getPerformance: (supplierId?: string) => {
    const qs = supplierId ? `?supplier_id=${supplierId}` : "";
    return apiClient.get<SCPerformanceOut[]>(`${B}/performance${qs}`).then((r) => r.data);
  },

  runAI: (orderId?: string) => orderId
    ? apiClient.post<{generated: number; by_agent: Record<string, number>}>(`${B}/orders/${orderId}/ai/run`, {}).then((r) => r.data)
    : apiClient.post<{generated: number; by_agent: Record<string, number>}>(`${B}/ai/run`, {}).then((r) => r.data),
  listAIRecs: (params?: {order_id?: string; supplier_id?: string}) => {
    const qs = new URLSearchParams();
    if (params?.order_id)    qs.set("order_id", params.order_id);
    if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
    return apiClient.get<SCAIRecOut[]>(`${B}/ai/recommendations?${qs}`).then((r) => r.data);
  },
  actionAIRec: (id: string, notes?: string) =>
    apiClient.post<SCAIRecOut>(`${B}/ai/recommendations/${id}/action?notes=${encodeURIComponent(notes ?? "")}`, {}).then((r) => r.data),
};
