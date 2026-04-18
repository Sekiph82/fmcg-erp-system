/**
 * Utility Management — Cross-Module Integration API client & types.
 * Endpoints: /api/v1/utility-management/integration/
 */
import { apiClient } from "./api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UtilityTypeBreakdown {
  utility_type: string;
  quantity: number | null;
  unit: string | null;
  cost: number | null;
}

export interface ProductionUtilitySummary {
  production_order_id: string;
  order_no: string;
  total_utility_cost: number;
  by_type: UtilityTypeBreakdown[];
}

export interface PostBillToGLRequest {
  debit_account_id: string;
  credit_account_id: string;
}

export interface PostBillToGLResult {
  bill_id: string;
  journal_entry_id: string;
  entry_no: string;
  amount: number;
}

export interface PostAllocationsResult {
  bill_id: string;
  entries_created: number;
  total_cost_posted: number;
}

export interface ChemicalSyncRequest {
  warehouse_id: string;
}

export interface ChemicalSyncResult {
  record_id: string;
  movement_id: string;
  movement_reference: string;
  quantity_issued: number;
}

export interface MaintenanceActionRequest {
  action_type: "PM_WORK_ORDER" | "BREAKDOWN";
  description: string;
  scheduled_date?: string;
  plan_id?: string;
  assigned_to_id?: string;
}

export interface MaintenanceActionResult {
  type: string;
  alarm_event_id: string;
  work_order_id?: string;
  wo_no?: string;
  breakdown_id?: string;
  breakdown_no?: string;
}

export interface PMPlanSummary {
  id: string;
  name: string;
  next_due_date: string | null;
  status: string | null;
}

export interface BreakdownSummary {
  id: string;
  breakdown_no: string;
  severity: string;
  status: string;
}

export interface MaintenanceStatusResult {
  linked: boolean;
  utility_asset_id: string;
  maintenance_asset_id?: string;
  asset_name?: string;
  asset_status?: string;
  overdue_pm_count: number;
  open_breakdown_count: number;
  next_pm_due?: string;
  pm_plans: PMPlanSummary[];
  recent_breakdowns: BreakdownSummary[];
}

export interface QualityInspectionSummary {
  inspection_id: string;
  inspection_no: string;
  qc_type: string;
  status: string;
  decision: string | null;
  inspection_date: string | null;
  lot_number: string | null;
  batch_no: string | null;
}

// ── API client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/utility-management/integration";

export const integrationApi = {
  /** GET production utility cost summary for a production order */
  async getProductionUtilitySummary(orderId: string): Promise<ProductionUtilitySummary> {
    const r = await apiClient.get<ProductionUtilitySummary>(
      `${BASE}/production/${orderId}/utility-summary`
    );
    return r.data;
  },

  /** POST utility bill to the General Ledger as a journal entry */
  async postBillToGL(billId: string, body: PostBillToGLRequest): Promise<PostBillToGLResult> {
    const r = await apiClient.post<PostBillToGLResult>(
      `${BASE}/bills/${billId}/post-to-gl`,
      body
    );
    return r.data;
  },

  /** POST approved cost allocations for a bill to production costing */
  async postAllocationsToProductionCosts(billId: string): Promise<PostAllocationsResult> {
    const r = await apiClient.post<PostAllocationsResult>(
      `${BASE}/bills/${billId}/post-allocations`
    );
    return r.data;
  },

  /** POST sync a chemical dosing record as an inventory stock movement */
  async syncChemicalToInventory(
    recordId: string,
    body: ChemicalSyncRequest
  ): Promise<ChemicalSyncResult> {
    const r = await apiClient.post<ChemicalSyncResult>(
      `${BASE}/chemical/${recordId}/sync-inventory`,
      body
    );
    return r.data;
  },

  /** GET maintenance status for a utility asset */
  async getMaintenanceStatus(assetId: string): Promise<MaintenanceStatusResult> {
    const r = await apiClient.get<MaintenanceStatusResult>(
      `${BASE}/assets/${assetId}/maintenance-status`
    );
    return r.data;
  },

  /** POST create a maintenance work order or breakdown record from an alarm event */
  async createMaintenanceAction(
    eventId: string,
    body: MaintenanceActionRequest
  ): Promise<MaintenanceActionResult> {
    const r = await apiClient.post<MaintenanceActionResult>(
      `${BASE}/alarm-events/${eventId}/maintenance-action`,
      body
    );
    return r.data;
  },

  /** GET quality inspections linked to a utility asset */
  async getQualityInspections(
    assetId: string,
    params?: { date_from?: string; date_to?: string }
  ): Promise<QualityInspectionSummary[]> {
    const r = await apiClient.get<QualityInspectionSummary[]>(
      `${BASE}/assets/${assetId}/quality-inspections`,
      { params }
    );
    return r.data;
  },
};
