import { apiClient } from "@/lib/api";

export type AssetStatus = "ACTIVE" | "IDLE" | "UNDER_MAINTENANCE" | "DECOMMISSIONED";
export type PMFrequency = "DAILY" | "WEEKLY" | "MONTHLY" | "QUARTERLY" | "BIANNUAL" | "ANNUAL";
export type PMStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "OVERDUE" | "SKIPPED";
export type BreakdownSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type BreakdownStatus = "OPEN" | "IN_REPAIR" | "RESOLVED";
export type MaintenancePredictionStatus = "OPEN" | "REVIEWED" | "WORK_ORDER_CREATED" | "DISMISSED";
export type MaintenancePredictionRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Asset {
  id: string;
  asset_no: string;
  name: string;
  description?: string;
  asset_type?: string;
  line?: string;
  serial_no?: string;
  manufacturer?: string;
  model?: string;
  install_date?: string;
  warranty_expiry?: string;
  location?: string;
  status: AssetStatus;
  notes?: string;
  created_at: string;
}

export interface PMPlan {
  id: string;
  asset_id: string;
  asset_name?: string;
  asset_no?: string;
  name: string;
  description?: string;
  frequency: PMFrequency;
  interval_days?: number;
  estimated_duration_minutes?: number;
  is_active: boolean;
  checklist?: string;
  assigned_to?: string;
  last_completed_date?: string;
  next_due_date?: string;
  created_at: string;
}

export interface PMWorkOrder {
  id: string;
  wo_no: string;
  plan_id: string;
  plan_name?: string;
  asset_id?: string;
  asset_name?: string;
  scheduled_date: string;
  status: PMStatus;
  started_at?: string;
  completed_at?: string;
  actual_duration_minutes?: number;
  technician?: string;
  checklist_notes?: string;
  created_at: string;
}

export interface BreakdownRecord {
  id: string;
  breakdown_no: string;
  asset_id: string;
  asset_name?: string;
  asset_no?: string;
  production_order_id?: string;
  start_time: string;
  end_time?: string;
  downtime_minutes?: number;
  reason: string;
  root_cause?: string;
  severity: BreakdownSeverity;
  status: BreakdownStatus;
  corrective_action?: string;
  created_at: string;
}

export interface SparePart {
  id: string;
  part_no: string;
  name: string;
  description?: string;
  unit: string;
  material_id?: string;
  current_stock: number;
  reorder_level?: number;
  unit_cost?: number;
  supplier?: string;
  lead_time_days?: number;
  is_active: boolean;
  created_at: string;
}

export interface SparePartUsage {
  id: string;
  spare_part_id: string;
  spare_part_name?: string;
  asset_id: string;
  asset_name?: string;
  breakdown_id?: string;
  pm_work_order_id?: string;
  quantity_used: number;
  unit_cost?: number;
  notes?: string;
  created_at: string;
}

export interface MtbfMttrRow {
  asset_id: string;
  asset_no: string;
  asset_name: string;
  line?: string;
  breakdown_count: number;
  total_downtime_minutes: number;
  avg_downtime_minutes: number;
  mtbf_days?: number;
}

export interface DowntimeByMachineRow {
  asset_id: string;
  asset_no: string;
  asset_name: string;
  line?: string;
  breakdown_count: number;
  total_downtime_minutes: number;
  open_breakdowns: number;
}

export interface OverduePMRow {
  plan_id: string;
  asset_id: string;
  asset_no: string;
  asset_name: string;
  plan_name: string;
  frequency: PMFrequency;
  next_due_date?: string;
  days_overdue: number;
}

export interface MaintenancePrediction {
  id: string;
  asset_id?: string | null;
  asset_no?: string | null;
  asset_name?: string | null;
  machine_id: string;
  machine_name?: string | null;
  predicted_failure_date: string;
  confidence: number;
  risk_level: MaintenancePredictionRisk;
  failure_mode: string;
  recommended_action: string;
  evidence_summary?: string | null;
  source_metrics?: Record<string, any> | null;
  status: MaintenancePredictionStatus;
  generated_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_notes?: string | null;
  created_at: string;
}

export const maintenanceApi = {
  // Assets
  async listAssets(params?: { status?: AssetStatus; line?: string }): Promise<Asset[]> {
    const res = await apiClient.get<Asset[]>("/api/v1/maintenance/assets/", { params });
    return res.data;
  },
  async createAsset(data: object): Promise<Asset> {
    const res = await apiClient.post<Asset>("/api/v1/maintenance/assets/", data);
    return res.data;
  },
  async updateAsset(id: string, data: object): Promise<Asset> {
    const res = await apiClient.patch<Asset>(`/api/v1/maintenance/assets/${id}`, data);
    return res.data;
  },

  // PM Plans
  async listPMPlans(params?: { asset_id?: string; active_only?: boolean }): Promise<PMPlan[]> {
    const res = await apiClient.get<PMPlan[]>("/api/v1/maintenance/pm-plans/", { params });
    return res.data;
  },
  async createPMPlan(data: object): Promise<PMPlan> {
    const res = await apiClient.post<PMPlan>("/api/v1/maintenance/pm-plans/", data);
    return res.data;
  },
  async updatePMPlan(id: string, data: object): Promise<PMPlan> {
    const res = await apiClient.patch<PMPlan>(`/api/v1/maintenance/pm-plans/${id}`, data);
    return res.data;
  },

  // Work Orders
  async listWorkOrders(params?: { plan_id?: string; status?: PMStatus }): Promise<PMWorkOrder[]> {
    const res = await apiClient.get<PMWorkOrder[]>("/api/v1/maintenance/work-orders/", { params });
    return res.data;
  },
  async createWorkOrder(data: object): Promise<PMWorkOrder> {
    const res = await apiClient.post<PMWorkOrder>("/api/v1/maintenance/work-orders/", data);
    return res.data;
  },
  async completeWorkOrder(id: string, data: object): Promise<PMWorkOrder> {
    const res = await apiClient.post<PMWorkOrder>(`/api/v1/maintenance/work-orders/${id}/complete`, data);
    return res.data;
  },

  // Breakdowns
  async listBreakdowns(params?: { asset_id?: string; status?: BreakdownStatus }): Promise<BreakdownRecord[]> {
    const res = await apiClient.get<BreakdownRecord[]>("/api/v1/maintenance/breakdowns/", { params });
    return res.data;
  },
  async createBreakdown(data: object): Promise<BreakdownRecord> {
    const res = await apiClient.post<BreakdownRecord>("/api/v1/maintenance/breakdowns/", data);
    return res.data;
  },
  async resolveBreakdown(id: string, data: object): Promise<BreakdownRecord> {
    const res = await apiClient.patch<BreakdownRecord>(`/api/v1/maintenance/breakdowns/${id}/resolve`, data);
    return res.data;
  },
  async listBreakdownSpares(bdId: string): Promise<SparePartUsage[]> {
    const res = await apiClient.get<SparePartUsage[]>(`/api/v1/maintenance/breakdowns/${bdId}/spare-usages`);
    return res.data;
  },

  // Spare Parts
  async listSpareParts(activeOnly = true): Promise<SparePart[]> {
    const res = await apiClient.get<SparePart[]>("/api/v1/maintenance/spare-parts/", { params: { active_only: activeOnly } });
    return res.data;
  },
  async createSparePart(data: object): Promise<SparePart> {
    const res = await apiClient.post<SparePart>("/api/v1/maintenance/spare-parts/", data);
    return res.data;
  },
  async updateSparePart(id: string, data: object): Promise<SparePart> {
    const res = await apiClient.patch<SparePart>(`/api/v1/maintenance/spare-parts/${id}`, data);
    return res.data;
  },
  async recordSpareUsage(data: object): Promise<SparePartUsage> {
    const res = await apiClient.post<SparePartUsage>("/api/v1/maintenance/spare-parts/usage", data);
    return res.data;
  },

  // Reports
  async reportMtbfMttr(): Promise<MtbfMttrRow[]> {
    const res = await apiClient.get<MtbfMttrRow[]>("/api/v1/maintenance/reports/mtbf-mttr");
    return res.data;
  },
  async reportDowntimeByMachine(): Promise<DowntimeByMachineRow[]> {
    const res = await apiClient.get<DowntimeByMachineRow[]>("/api/v1/maintenance/reports/downtime-by-machine");
    return res.data;
  },
  async reportOverduePM(): Promise<OverduePMRow[]> {
    const res = await apiClient.get<OverduePMRow[]>("/api/v1/maintenance/reports/overdue-pm");
    return res.data;
  },

  // Predictive maintenance
  async generatePredictions(horizonDays = 30): Promise<MaintenancePrediction[]> {
    const res = await apiClient.post<MaintenancePrediction[]>("/api/v1/maintenance/predictions/generate", null, {
      params: { horizon_days: horizonDays },
    });
    return res.data;
  },
  async listPredictions(params?: {
    status?: MaintenancePredictionStatus;
    risk_level?: MaintenancePredictionRisk;
    machine_id?: string;
    limit?: number;
  }): Promise<MaintenancePrediction[]> {
    const res = await apiClient.get<MaintenancePrediction[]>("/api/v1/maintenance/predictions", { params });
    return res.data;
  },
  async reviewPrediction(id: string, data: { status: MaintenancePredictionStatus; reviewed_by: string; review_notes?: string }): Promise<MaintenancePrediction> {
    const res = await apiClient.patch<MaintenancePrediction>(`/api/v1/maintenance/predictions/${id}/review`, data);
    return res.data;
  },
};
