import { apiClient } from "@/lib/api";

export type PlanStatus = "DRAFT" | "CONFIRMED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type OrderStatus = "PLANNED" | "RELEASED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type DowntimeReason =
  | "BREAKDOWN"
  | "MAINTENANCE"
  | "CHANGEOVER"
  | "MATERIAL_SHORTAGE"
  | "QUALITY_HOLD"
  | "OTHER";

export interface ProductionPlan {
  id: string;
  plan_no: string;
  name: string;
  description?: string;
  status: PlanStatus;
  planned_date: string;
  created_by?: string;
}

export interface PlanLine {
  id: string;
  plan_id: string;
  line_no: number;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  recipe_id: string;
  recipe_name?: string;
  recipe_version?: string;
  target_quantity: number;
  uom: string;
  target_warehouse_id: string;
  target_warehouse_name?: string;
  planned_date?: string;
  notes?: string;
}

export interface ProductionPlanDetail extends ProductionPlan {
  lines: PlanLine[];
}

export interface ProductionOrder {
  id: string;
  order_no: string;
  plan_line_id?: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  recipe_id: string;
  recipe_name?: string;
  planned_quantity: number;
  actual_quantity?: number;
  batch_no?: string;
  uom: string;
  status: OrderStatus;
  target_warehouse_id: string;
  target_warehouse_name?: string;
  source_warehouse_id?: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_start?: string;
  actual_end?: string;
  created_by?: string;
  notes?: string;
}

export interface MaterialConsumption {
  id: string;
  material_id: string;
  material_name?: string;
  material_code?: string;
  lot_id?: string;
  lot_number?: string;
  standard_quantity: number;
  actual_quantity: number;
  variance_quantity: number;
  unit: string;
  source_warehouse_id: string;
  source_warehouse_name?: string;
}

export interface FGReceipt {
  id: string;
  product_id: string;
  quantity: number;
  uom: string;
  lot_number?: string;
  batch_no?: string;
  warehouse_id: string;
  warehouse_name?: string;
}

export interface DowntimeLog {
  id: string;
  production_order_id: string;
  machine_id?: string;
  reason: DowntimeReason;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  notes?: string;
}

export interface OEEMetrics {
  order_id: string;
  order_no: string;
  scheduled_minutes: number;
  actual_minutes?: number;
  downtime_minutes: number;
  availability: number;
  performance: number;
  quality: number;
  oee: number;
}

export interface ProductionOrderDetail extends ProductionOrder {
  consumptions: MaterialConsumption[];
  fg_receipts: FGReceipt[];
  downtime_logs: DowntimeLog[];
  oee?: OEEMetrics;
}

export interface ProductionReportRow {
  date: string;
  order_no: string;
  product_name: string;
  product_sku: string;
  planned_quantity: number;
  actual_quantity?: number;
  variance?: number;
  variance_pct?: number;
  status: OrderStatus;
  batch_no?: string;
  downtime_minutes: number;
}

export interface DowntimeSummaryRow {
  reason: string;
  count: number;
  total_minutes: number;
  machine_id?: string;
}

export interface ProductionSummary {
  total_orders: number;
  completed_orders: number;
  in_progress_orders: number;
  planned_quantity_total: number;
  actual_quantity_total: number;
  overall_variance: number;
  total_downtime_minutes: number;
  avg_oee?: number;
  orders: ProductionReportRow[];
  downtime_summary: DowntimeSummaryRow[];
}

export interface PlanCreate {
  plan_no: string;
  name: string;
  description?: string;
  planned_date: string;
}

export interface PlanLineCreate {
  line_no: number;
  product_id: string;
  recipe_id: string;
  target_quantity: number;
  uom: string;
  target_warehouse_id: string;
  planned_date?: string;
  notes?: string;
}

export interface OrderCreate {
  order_no: string;
  plan_line_id?: string;
  product_id: string;
  recipe_id: string;
  planned_quantity: number;
  uom: string;
  batch_no?: string;
  target_warehouse_id: string;
  source_warehouse_id?: string;
  scheduled_start: string;
  scheduled_end: string;
  notes?: string;
}

export interface CompleteOrderRequest {
  actual_quantity: number;
  fg_lot_number?: string;
  fg_expiry_date?: string;
  source_warehouse_id?: string;
  consume_materials?: boolean;
  notes?: string;
}

export const productionApi = {
  // Plans
  async listPlans(params?: { status?: PlanStatus; skip?: number; limit?: number }): Promise<ProductionPlan[]> {
    const res = await apiClient.get<ProductionPlan[]>("/api/v1/production/plans/", { params }).then((r) => r.data);
    return res.data;
  },
  async getPlan(id: string): Promise<ProductionPlanDetail> {
    const res = await apiClient.get<ProductionPlanDetail>(`/api/v1/production/plans/${id}`).then((r) => r.data);
    return res.data;
  },
  async createPlan(data: PlanCreate): Promise<ProductionPlan> {
    const res = await apiClient.post<ProductionPlan>("/api/v1/production/plans/", data).then((r) => r.data);
    return res.data;
  },
  async confirmPlan(id: string): Promise<ProductionPlan> {
    const res = await apiClient.post<ProductionPlan>(`/api/v1/production/plans/${id}/confirm`).then((r) => r.data);
    return res.data;
  },
  async addPlanLine(planId: string, data: PlanLineCreate): Promise<PlanLine> {
    const res = await apiClient.post<PlanLine>(`/api/v1/production/plans/${planId}/lines`, data).then((r) => r.data);
    return res.data;
  },
  async deletePlanLine(planId: string, lineId: string): Promise<void> {
    await apiClient.delete(`/api/v1/production/plans/${planId}/lines/${lineId}`).then((r) => r.data);
  },

  // Orders
  async listOrders(params?: { status?: OrderStatus; product_id?: string; skip?: number; limit?: number }): Promise<ProductionOrder[]> {
    const res = await apiClient.get<ProductionOrder[]>("/api/v1/production/orders/", { params }).then((r) => r.data);
    return res.data;
  },
  async getOrder(id: string): Promise<ProductionOrderDetail> {
    const res = await apiClient.get<ProductionOrderDetail>(`/api/v1/production/orders/${id}`).then((r) => r.data);
    return res.data;
  },
  async createOrder(data: OrderCreate): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>("/api/v1/production/orders/", data).then((r) => r.data);
    return res.data;
  },

  // Execution
  async releaseOrder(id: string): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(`/api/v1/production/orders/${id}/release`).then((r) => r.data);
    return res.data;
  },
  async startOrder(id: string): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(`/api/v1/production/orders/${id}/start`).then((r) => r.data);
    return res.data;
  },
  async pauseOrder(id: string, data: { machine_id?: string; reason: DowntimeReason; notes?: string }): Promise<DowntimeLog> {
    const res = await apiClient.post<DowntimeLog>(`/api/v1/production/orders/${id}/pause`, data).then((r) => r.data);
    return res.data;
  },
  async resumeOrder(id: string, notes?: string): Promise<DowntimeLog> {
    const res = await apiClient.post<DowntimeLog>(`/api/v1/production/orders/${id}/resume`, { notes }).then((r) => r.data);
    return res.data;
  },
  async completeOrder(id: string, data: CompleteOrderRequest): Promise<ProductionOrderDetail> {
    const res = await apiClient.post<ProductionOrderDetail>(`/api/v1/production/orders/${id}/complete`, data).then((r) => r.data);
    return res.data;
  },
  async cancelOrder(id: string): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(`/api/v1/production/orders/${id}/cancel`).then((r) => r.data);
    return res.data;
  },
  async getOEE(id: string): Promise<OEEMetrics> {
    const res = await apiClient.get<OEEMetrics>(`/api/v1/production/orders/${id}/oee`).then((r) => r.data);
    return res.data;
  },

  // Reports
  async getReport(params: { date_from: string; date_to: string; product_id?: string }): Promise<ProductionSummary> {
    const res = await apiClient.get<ProductionSummary>("/api/v1/production/reports/summary", { params }).then((r) => r.data);
    return res.data;
  },
};
