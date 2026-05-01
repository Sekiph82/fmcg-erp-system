import { apiClient } from "@/lib/api";

export type PutawayRuleType = "FIXED" | "ZONE" | "CATEGORY" | "RANDOM" | "NEAREST";
export type PutawayTaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type LocationType = "RACK" | "BIN" | "FLOOR" | "COLD_STORAGE";

export interface PutawayRule {
  id: string;
  rule_code: string;
  warehouse_id: string;
  warehouse_name?: string;
  rule_type: PutawayRuleType;
  priority: number;
  product_id?: string;
  product_name?: string;
  category?: string;
  zone_id?: string;
  zone_name?: string;
  location_id?: string;
  location_code?: string;
  is_active: boolean;
  notes?: string;
}

export interface PutawayTask {
  id: string;
  task_no: string;
  warehouse_id: string;
  warehouse_name?: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  material_id?: string;
  material_name?: string;
  lot_number?: string;
  quantity: number;
  weight_kg?: number;
  volume_m3?: number;
  suggested_location_id?: string;
  suggested_location_code?: string;
  assigned_to?: string;
  assignee_name?: string;
  status: PutawayTaskStatus;
  receipt_ref?: string;
  override_reason?: string;
  notes?: string;
}

export interface PutawayExecution {
  id: string;
  task_id: string;
  actual_location_id: string;
  actual_location_code?: string;
  executed_by?: string;
  executed_at: string;
  is_variance: boolean;
  notes?: string;
}

export interface SuggestLocationResult {
  location_id?: string;
  location_code?: string;
  zone_name?: string;
  rule_applied?: string;
  confidence: string;
}

export const putawayApi = {
  // Rules
  async listRules(params?: { warehouse_id?: string; is_active?: boolean }): Promise<PutawayRule[]> {
    const res = await apiClient.get("/api/v1/wms/putaway/rules", { params });
    return res.data?.data ?? res.data;
  },
  async createRule(data: Omit<PutawayRule, "id" | "warehouse_name" | "zone_name" | "location_code" | "product_name">): Promise<PutawayRule> {
    const res = await apiClient.post("/api/v1/wms/putaway/rules", data);
    return res.data?.data ?? res.data;
  },
  async updateRule(id: string, data: Partial<PutawayRule>): Promise<PutawayRule> {
    const res = await apiClient.patch(`/api/v1/wms/putaway/rules/${id}`, data);
    return res.data?.data ?? res.data;
  },

  // Tasks
  async listTasks(params?: { warehouse_id?: string; status?: PutawayTaskStatus; skip?: number; limit?: number }): Promise<PutawayTask[]> {
    const res = await apiClient.get("/api/v1/wms/putaway/tasks", { params });
    return res.data?.data ?? res.data;
  },
  async getTask(id: string): Promise<PutawayTask> {
    const res = await apiClient.get(`/api/v1/wms/putaway/tasks/${id}`);
    return res.data?.data ?? res.data;
  },
  async createTask(data: {
    warehouse_id: string;
    product_id?: string;
    material_id?: string;
    lot_number?: string;
    quantity: number;
    weight_kg?: number;
    volume_m3?: number;
    receipt_ref?: string;
    notes?: string;
  }): Promise<PutawayTask> {
    const res = await apiClient.post("/api/v1/wms/putaway/tasks", data);
    return res.data?.data ?? res.data;
  },
  async executeTask(taskId: string, data: {
    actual_location_id: string;
    override_reason?: string;
    notes?: string;
  }): Promise<PutawayExecution> {
    const res = await apiClient.post(`/api/v1/wms/putaway/tasks/${taskId}/execute`, data);
    return res.data?.data ?? res.data;
  },

  // Suggest
  async suggestLocation(params: {
    warehouse_id: string;
    product_id?: string;
    material_id?: string;
    category?: string;
    weight_kg?: number;
    volume_m3?: number;
  }): Promise<SuggestLocationResult> {
    const res = await apiClient.get("/api/v1/wms/putaway/suggest", { params });
    return res.data?.data ?? res.data;
  },

  // AI
  async spaceOptimizer(warehouseId: string): Promise<any> {
    const res = await apiClient.get("/api/v1/wms/putaway/ai/space-optimizer", {
      params: { warehouse_id: warehouseId },
    });
    return res.data?.data ?? res.data;
  },
  async efficiencyAnalyzer(warehouseId: string): Promise<any> {
    const res = await apiClient.get("/api/v1/wms/putaway/ai/efficiency", {
      params: { warehouse_id: warehouseId },
    });
    return res.data?.data ?? res.data;
  },
};
