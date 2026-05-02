import { apiClient } from "./api";

const BASE = "/api/v1/production-adv";

// ── Types ───────────────────────────────────────────────────────────────────

export interface WorkCenter {
  id: string; work_center_id: string; name: string; type: string;
  capacity?: number; capacity_uom?: string; location?: string;
  department?: string; setup_time_min?: number; status: string; notes?: string;
}

export interface Routing {
  id: string; routing_id: string; product_id: string;
  product_name?: string; product_sku?: string;
  version: number; name?: string; is_active: boolean;
  steps: RoutingStep[];
}
export interface RoutingStep {
  id: string; routing_id: string; step_number: number; operation: string;
  work_center_id: string; work_center_name?: string;
  standard_time_minutes: number; setup_time_minutes?: number; is_parallel: boolean;
}

export interface WorkOrder {
  id: string; work_order_id: string; production_order_id: string;
  order_no?: string; work_center_id: string; work_center_name?: string;
  operation: string; operator?: string; status: string;
  planned_quantity?: number; actual_quantity?: number;
  start_time?: string; end_time?: string;
  planned_start?: string; planned_end?: string; created_at: string;
}

export interface Shift {
  id: string; shift_code: string; name: string;
  start_time_str: string; end_time_str: string;
  duration_hours: number; is_active: boolean;
}

export interface ProductionSchedule {
  id: string; schedule_id: string; production_order_id: string;
  order_no?: string; work_center_id: string; work_center_name?: string;
  shift_id?: string; shift_name?: string;
  start_time: string; end_time: string;
  status: string; priority: string; conflict_flag: boolean;
}

export interface TimeTracking {
  id: string; log_id: string; work_order_id: string; work_order_code?: string;
  actual_start: string; actual_end?: string;
  duration_actual_min?: number; duration_planned_min?: number;
  downtime_minutes?: number; category: string; reason?: string; efficiency_pct?: number;
}

export interface DowntimeEvent {
  id: string; downtime_id: string; work_center_id: string; work_center_name?: string;
  machine_id?: string; work_order_id?: string;
  start_time: string; end_time?: string; duration_min?: number;
  reason: string; category: string; reported_by?: string;
}

export interface QCInspection {
  id: string; qc_id: string; production_order_id: string; order_no?: string;
  work_order_id?: string; inspection_type: string; status: string;
  checked_by?: string; inspected_at?: string; batch_ref?: string;
  results: QCResult[];
}
export interface QCResult {
  id: string; inspection_id: string; test_type: string;
  actual_value?: number; min_value?: number; max_value?: number;
  unit?: string; result: string;
}

export interface WasteRecord {
  id: string; waste_id: string; production_order_id: string; order_no?: string;
  material_code?: string; waste_type: string; waste_category: string;
  expected_qty: number; actual_qty: number; loss_qty: number;
  loss_pct?: number; uom?: string; reason?: string; is_anomaly: boolean;
}

export interface BatchLot {
  id: string; batch_id: string; production_order_id: string; order_no?: string;
  product_id: string; product_name?: string; product_sku?: string;
  quantity: number; uom: string;
  manufacture_date?: string; expiry_date?: string; status: string;
  traceability_code?: string; warehouse_id?: string;
}

export interface LaborLog {
  id: string; labor_id: string; work_order_id: string; work_order_code?: string;
  employee_id?: string; employee_code?: string; operator_name?: string;
  hours_worked?: number; role?: string; activity_type: string;
  pieces_produced?: number; created_at: string;
}

export interface OEERecord {
  id: string; oee_id: string; work_center_id: string; work_center_name?: string;
  machine_id?: string; shift_id?: string; shift_name?: string;
  record_date: string; planned_production_time_min: number;
  actual_production_time_min?: number; downtime_min?: number;
  total_units_produced?: number; good_units_produced?: number;
  availability?: number; performance?: number; quality?: number; oee_score?: number;
  is_low_oee: boolean; is_high_downtime: boolean;
}

export interface OEESummaryRow {
  work_center_id: string; work_center_name?: string;
  avg_availability?: number; avg_performance?: number;
  avg_quality?: number; avg_oee?: number;
  total_downtime_min: number; records_count: number;
}

export interface AIInsight {
  type: string; severity: string;
  machine?: string; date?: string;
  oee_score?: number; downtime_min?: number;
  loss_pct?: number; waste_id?: string;
  recommendation: string;
}

// ── API ─────────────────────────────────────────────────────────────────────

export const advProductionApi = {
  // Work Centers
  async listWorkCenters(p?: { status?: string }): Promise<WorkCenter[]> {
    const r = await apiClient.get(`${BASE}/work-centers`, { params: p });
    return r.data;
  },
  async createWorkCenter(d: Partial<WorkCenter>): Promise<WorkCenter> {
    const r = await apiClient.post(`${BASE}/work-centers`, d);
    return r.data;
  },
  async updateWorkCenter(id: string, d: Partial<WorkCenter>): Promise<WorkCenter> {
    const r = await apiClient.patch(`${BASE}/work-centers/${id}`, d);
    return r.data;
  },
  async deleteWorkCenter(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/work-centers/${id}`).then((r) => r.data);
  },

  // Routings
  async listRoutings(p?: { product_id?: string }): Promise<Routing[]> {
    const r = await apiClient.get(`${BASE}/routings`, { params: p });
    return r.data;
  },
  async createRouting(d: object): Promise<Routing> {
    const r = await apiClient.post(`${BASE}/routings`, d);
    return r.data;
  },
  async deleteRouting(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/routings/${id}`).then((r) => r.data);
  },
  async addRoutingStep(routingId: string, d: object): Promise<RoutingStep> {
    const r = await apiClient.post(`${BASE}/routings/${routingId}/steps`, d);
    return r.data;
  },

  // Work Orders
  async listWorkOrders(p?: { production_order_id?: string; status?: string }): Promise<WorkOrder[]> {
    const r = await apiClient.get(`${BASE}/work-orders`, { params: p });
    return r.data;
  },
  async createWorkOrder(d: object): Promise<WorkOrder> {
    const r = await apiClient.post(`${BASE}/work-orders`, d);
    return r.data;
  },
  async updateWorkOrder(id: string, d: object): Promise<WorkOrder> {
    const r = await apiClient.patch(`${BASE}/work-orders/${id}`, d);
    return r.data;
  },
  async startWorkOrder(id: string): Promise<WorkOrder> {
    const r = await apiClient.post(`${BASE}/work-orders/${id}/start`);
    return r.data;
  },
  async completeWorkOrder(id: string, qty?: number): Promise<WorkOrder> {
    const r = await apiClient.post(`${BASE}/work-orders/${id}/complete`, null, { params: { actual_quantity: qty } });
    return r.data;
  },
  async deleteWorkOrder(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/work-orders/${id}`).then((r) => r.data);
  },

  // Shifts
  async listShifts(): Promise<Shift[]> {
    const r = await apiClient.get(`${BASE}/shifts`);
    return r.data;
  },
  async createShift(d: object): Promise<Shift> {
    const r = await apiClient.post(`${BASE}/shifts`, d);
    return r.data;
  },
  async deleteShift(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/shifts/${id}`).then((r) => r.data);
  },

  // Schedules
  async listSchedules(p?: { work_center_id?: string; status?: string; date_from?: string; date_to?: string }): Promise<ProductionSchedule[]> {
    const r = await apiClient.get(`${BASE}/schedules`, { params: p });
    return r.data;
  },
  async createSchedule(d: object): Promise<ProductionSchedule> {
    const r = await apiClient.post(`${BASE}/schedules`, d);
    return r.data;
  },
  async getConflicts(): Promise<ProductionSchedule[]> {
    const r = await apiClient.get(`${BASE}/schedules/conflicts`);
    return r.data;
  },
  async deleteSchedule(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/schedules/${id}`).then((r) => r.data);
  },

  // Time Tracking
  async listTimeTracking(p?: { work_order_id?: string }): Promise<TimeTracking[]> {
    const r = await apiClient.get(`${BASE}/time-tracking`, { params: p });
    return r.data;
  },
  async createTimeTracking(d: object): Promise<TimeTracking> {
    const r = await apiClient.post(`${BASE}/time-tracking`, d);
    return r.data;
  },
  async deleteTimeTracking(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/time-tracking/${id}`).then((r) => r.data);
  },

  // Downtime
  async listDowntime(p?: { work_center_id?: string; category?: string }): Promise<DowntimeEvent[]> {
    const r = await apiClient.get(`${BASE}/downtime`, { params: p });
    return r.data;
  },
  async createDowntime(d: object): Promise<DowntimeEvent> {
    const r = await apiClient.post(`${BASE}/downtime`, d);
    return r.data;
  },
  async updateDowntime(id: string, d: object): Promise<DowntimeEvent> {
    const r = await apiClient.patch(`${BASE}/downtime/${id}`, d);
    return r.data;
  },
  async deleteDowntime(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/downtime/${id}`).then((r) => r.data);
  },

  // QC
  async listQC(p?: { production_order_id?: string; status?: string }): Promise<QCInspection[]> {
    const r = await apiClient.get(`${BASE}/qc`, { params: p });
    return r.data;
  },
  async createQC(d: object): Promise<QCInspection> {
    const r = await apiClient.post(`${BASE}/qc`, d);
    return r.data;
  },
  async updateQC(id: string, d: object): Promise<QCInspection> {
    const r = await apiClient.patch(`${BASE}/qc/${id}`, d);
    return r.data;
  },
  async deleteQC(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/qc/${id}`).then((r) => r.data);
  },

  // Waste
  async listWaste(p?: { production_order_id?: string; is_anomaly?: boolean }): Promise<WasteRecord[]> {
    const r = await apiClient.get(`${BASE}/waste`, { params: p });
    return r.data;
  },
  async createWaste(d: object): Promise<WasteRecord> {
    const r = await apiClient.post(`${BASE}/waste`, d);
    return r.data;
  },
  async deleteWaste(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/waste/${id}`).then((r) => r.data);
  },

  // Batch Lots
  async listBatchLots(p?: { production_order_id?: string; status?: string }): Promise<BatchLot[]> {
    const r = await apiClient.get(`${BASE}/batch-lots`, { params: p });
    return r.data;
  },
  async createBatchLot(d: object): Promise<BatchLot> {
    const r = await apiClient.post(`${BASE}/batch-lots`, d);
    return r.data;
  },
  async updateBatchLot(id: string, d: object): Promise<BatchLot> {
    const r = await apiClient.patch(`${BASE}/batch-lots/${id}`, d);
    return r.data;
  },
  async deleteBatchLot(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/batch-lots/${id}`).then((r) => r.data);
  },

  // Labor
  async listLabor(p?: { work_order_id?: string }): Promise<LaborLog[]> {
    const r = await apiClient.get(`${BASE}/labor`, { params: p });
    return r.data;
  },
  async createLabor(d: object): Promise<LaborLog> {
    const r = await apiClient.post(`${BASE}/labor`, d);
    return r.data;
  },
  async deleteLabor(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/labor/${id}`).then((r) => r.data);
  },

  // OEE
  async listOEE(p?: { work_center_id?: string; date_from?: string; date_to?: string }): Promise<OEERecord[]> {
    const r = await apiClient.get(`${BASE}/oee`, { params: p });
    return r.data;
  },
  async createOEE(d: object): Promise<OEERecord> {
    const r = await apiClient.post(`${BASE}/oee`, d);
    return r.data;
  },
  async updateOEE(id: string, d: object): Promise<OEERecord> {
    const r = await apiClient.patch(`${BASE}/oee/${id}`, d);
    return r.data;
  },
  async deleteOEE(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/oee/${id}`).then((r) => r.data);
  },
  async oeeeSummary(p?: { work_center_id?: string; date_from?: string; date_to?: string }): Promise<OEESummaryRow[]> {
    const r = await apiClient.get(`${BASE}/oee/summary`, { params: p });
    return r.data;
  },

  // AI Insights
  async aiInsights(p?: { work_center_id?: string }): Promise<{ total_insights: number; insights: AIInsight[] }> {
    const r = await apiClient.get(`${BASE}/ai-insights`, { params: p });
    return r.data;
  },
};
