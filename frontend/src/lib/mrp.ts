/**
 * MRP + Demand Forecasting — TypeScript API client
 * Mirrors backend/app/schemas/mrp.py and endpoints/mrp.py
 */
import { apiClient } from "./api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ForecastLine {
  id: string;
  period_date: string;
  forecast_qty: number;
  adjusted_qty?: number | null;
  actual_qty?: number | null;
  error_pct?: number | null;
  is_spike: boolean;
  is_outlier: boolean;
  notes?: string | null;
}

export interface Forecast {
  id: string;
  product_id: string;
  product_sku?: string | null;
  product_name?: string | null;
  warehouse_id?: string | null;
  forecast_model: string;
  period_type: string;
  start_date: string;
  end_date: string;
  status: string;
  is_approved: boolean;
  mape?: number | null;
  notes?: string | null;
  created_at?: string | null;
  lines: ForecastLine[];
}

export interface ForecastSummary {
  id: string;
  product_id: string;
  product_sku?: string | null;
  product_name?: string | null;
  forecast_model: string;
  period_type: string;
  start_date: string;
  end_date: string;
  status: string;
  mape?: number | null;
  created_at?: string | null;
}

export interface ForecastAccuracyRow {
  product_id: string;
  product_sku?: string | null;
  product_name?: string | null;
  periods: number;
  avg_mape?: number | null;
  min_mape?: number | null;
  max_mape?: number | null;
}

export interface MRPRun {
  id: string;
  run_no: string;
  run_date: string;
  planning_horizon_days: number;
  frozen_horizon_days: number;
  status: string;
  trigger: string;
  include_forecast: boolean;
  include_safety_stock: boolean;
  warehouse_id?: string | null;
  error_message?: string | null;
  product_count?: number | null;
  shortage_count?: number | null;
  suggestion_count?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  notes?: string | null;
  created_at?: string | null;
}

export interface MRPException {
  id: string;
  run_id: string;
  exception_type: "SHORTAGE" | "EXCESS_STOCK" | "LATE_ORDER" | "DEMAND_SPIKE" | "FROZEN_DEMAND";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  product_id?: string | null;
  product_sku?: string | null;
  product_name?: string | null;
  material_id?: string | null;
  material_name?: string | null;
  message: string;
  action_required?: string | null;
  qty?: number | null;
  due_date?: string | null;
  is_acknowledged: boolean;
  created_at?: string | null;
}

export interface MRPResult {
  id: string;
  run_id: string;
  product_id: string;
  product_sku?: string | null;
  product_name?: string | null;
  so_demand_qty: number;
  forecast_demand_qty: number;
  safety_stock_qty: number;
  gross_demand_qty: number;
  stock_on_hand_qty: number;
  incoming_po_qty: number;
  incoming_prod_qty: number;
  total_supply_qty: number;
  net_requirement_qty: number;
  shortage_flag: boolean;
  suggested_production_qty?: number | null;
  suggested_procurement_qty?: number | null;
}

export interface MRPSuggestion {
  id: string;
  run_id: string;
  suggestion_type: string;
  status: string;
  product_id?: string | null;
  product_sku?: string | null;
  product_name?: string | null;
  material_id?: string | null;
  material_code?: string | null;
  material_name?: string | null;
  suggested_qty: number;
  uom?: string | null;
  required_date: string;
  planned_start_date?: string | null;
  driver_product_id?: string | null;
  net_requirement_qty?: number | null;
  moq?: number | null;
  preferred_supplier_id?: string | null;
  preferred_supplier_name?: string | null;
  estimated_cost?: number | null;
  rejection_reason?: string | null;
  notes?: string | null;
  created_at?: string | null;
}

export interface MRPDashboard {
  last_run?: MRPRun | null;
  total_runs: number;
  open_suggestions: number;
  shortage_products: number;
  pending_approval: number;
  active_forecasts: number;
  recent_runs: MRPRun[];
}

export interface ShortageAlert {
  product_id: string;
  product_sku?: string | null;
  product_name?: string | null;
  net_requirement: number;
  suggested_qty?: number | null;
  required_date?: string | null;
  run_no: string;
}

export interface SuggestionConvertResult {
  suggestion_id: string;
  converted_to: string;
  reference_no: string;
  reference_id: string;
}

// ── Request bodies ────────────────────────────────────────────────────────────

export interface ForecastGenerateRequest {
  product_id: string;
  warehouse_id?: string;
  forecast_model?: string;
  period_type?: string;
  periods_ahead?: number;
  history_periods?: number;
  model_params?: Record<string, unknown>;
}

export interface MRPRunCreate {
  planning_horizon_days?: number;
  frozen_horizon_days?: number;
  include_forecast?: boolean;
  include_safety_stock?: boolean;
  warehouse_id?: string;
  notes?: string;
}

// ── API client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/mrp";

export const mrpApi = {
  // ── Forecasting ────────────────────────────────────────────────────────────
  async generateForecast(body: ForecastGenerateRequest): Promise<Forecast> {
    const r = await apiClient.post<Forecast>(`${BASE}/forecast/generate`, body);
    return r.data;
  },

  async listForecasts(params?: { product_id?: string; status?: string; skip?: number; limit?: number }): Promise<ForecastSummary[]> {
    const r = await apiClient.get<ForecastSummary[]>(`${BASE}/forecasts`, { params });
    return r.data;
  },

  async getForecast(id: string): Promise<Forecast> {
    const r = await apiClient.get<Forecast>(`${BASE}/forecasts/${id}`);
    return r.data;
  },

  async approveForecast(id: string): Promise<Forecast> {
    const r = await apiClient.patch<Forecast>(`${BASE}/forecasts/${id}/approve`);
    return r.data;
  },

  async overrideLine(forecastId: string, lineId: string, body: { adjusted_qty?: number; notes?: string }): Promise<ForecastLine> {
    const r = await apiClient.patch<ForecastLine>(`${BASE}/forecasts/${forecastId}/lines/${lineId}`, body);
    return r.data;
  },

  async backfillActuals(forecastId: string): Promise<{ updated_lines: number }> {
    const r = await apiClient.post<{ updated_lines: number }>(`${BASE}/forecasts/${forecastId}/backfill`);
    return r.data;
  },

  async forecastAccuracy(): Promise<ForecastAccuracyRow[]> {
    const r = await apiClient.get<ForecastAccuracyRow[]>(`${BASE}/forecasts/accuracy`);
    return r.data;
  },

  // ── MRP Runs ───────────────────────────────────────────────────────────────
  async triggerRun(body: MRPRunCreate): Promise<MRPRun> {
    const r = await apiClient.post<MRPRun>(`${BASE}/runs`, body);
    return r.data;
  },

  async listRuns(params?: { skip?: number; limit?: number }): Promise<MRPRun[]> {
    const r = await apiClient.get<MRPRun[]>(`${BASE}/runs`, { params });
    return r.data;
  },

  async getRun(id: string): Promise<MRPRun> {
    const r = await apiClient.get<MRPRun>(`${BASE}/runs/${id}`);
    return r.data;
  },

  async getRunResults(runId: string, shortageOnly?: boolean): Promise<MRPResult[]> {
    const r = await apiClient.get<MRPResult[]>(`${BASE}/runs/${runId}/results`, {
      params: { shortage_only: shortageOnly },
    });
    return r.data;
  },

  // ── Suggestions ────────────────────────────────────────────────────────────
  async listSuggestions(params?: {
    run_id?: string; suggestion_type?: string; status?: string; skip?: number; limit?: number;
  }): Promise<MRPSuggestion[]> {
    const r = await apiClient.get<MRPSuggestion[]>(`${BASE}/suggestions`, { params });
    return r.data;
  },

  async approveSuggestion(id: string, notes?: string): Promise<MRPSuggestion> {
    const r = await apiClient.patch<MRPSuggestion>(`${BASE}/suggestions/${id}/approve`, { notes });
    return r.data;
  },

  async rejectSuggestion(id: string, rejection_reason: string): Promise<MRPSuggestion> {
    const r = await apiClient.patch<MRPSuggestion>(`${BASE}/suggestions/${id}/reject`, { rejection_reason });
    return r.data;
  },

  async convertSuggestion(id: string): Promise<SuggestionConvertResult> {
    const r = await apiClient.post<SuggestionConvertResult>(`${BASE}/suggestions/${id}/convert`);
    return r.data;
  },

  // ── Dashboard ──────────────────────────────────────────────────────────────
  async getDashboard(): Promise<MRPDashboard> {
    const r = await apiClient.get<MRPDashboard>(`${BASE}/dashboard`);
    return r.data;
  },

  async getShortageAlerts(run_id?: string): Promise<ShortageAlert[]> {
    const r = await apiClient.get<ShortageAlert[]>(`${BASE}/shortage-alerts`, {
      params: run_id ? { run_id } : undefined,
    });
    return r.data;
  },

  async getExceptions(run_id?: string, unacknowledged_only?: boolean): Promise<MRPException[]> {
    const r = await apiClient.get<MRPException[]>(`${BASE}/exceptions`, {
      params: { run_id, unacknowledged_only },
    });
    return r.data;
  },

  async acknowledgeException(id: string): Promise<MRPException> {
    const r = await apiClient.patch<MRPException>(`${BASE}/exceptions/${id}/acknowledge`);
    return r.data;
  },
};

// ── Formatting helpers ────────────────────────────────────────────────────────

export const STATUS_COLOR: Record<string, string> = {
  DRAFT:     "bg-gray-100 text-gray-700",
  APPROVED:  "bg-green-100 text-green-700",
  REJECTED:  "bg-red-100 text-red-700",
  CONVERTED: "bg-blue-100 text-blue-700",
  QUEUED:    "bg-yellow-100 text-yellow-700",
  RUNNING:   "bg-blue-100 text-blue-700 animate-pulse",
  COMPLETED: "bg-green-100 text-green-700",
  FAILED:    "bg-red-100 text-red-700",
  LOCKED:    "bg-purple-100 text-purple-700",
};

export const SUGGESTION_TYPE_COLOR: Record<string, string> = {
  PRODUCTION:  "bg-orange-100 text-orange-700",
  PROCUREMENT: "bg-teal-100 text-teal-700",
};

export function fmtQty(n?: number | null, dp = 1): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

export function fmtMape(n?: number | null): string {
  if (n == null) return "—";
  const color = n < 10 ? "text-green-600" : n < 20 ? "text-yellow-600" : "text-red-600";
  return n.toFixed(1) + "%";
}
