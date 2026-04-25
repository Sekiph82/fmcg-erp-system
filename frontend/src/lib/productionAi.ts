/**
 * Production AI Intelligence Layer — TypeScript types and API client.
 *
 * Six agents:
 *  1. PREDICTION   – completion time, output qty, delay risk
 *  2. ANOMALY      – material overuse, efficiency drop, downtime, waste spikes
 *  3. OPTIMIZATION – batch size, resource allocation
 *  4. RECIPE       – QC instability, high-cost ingredients
 *  5. COST         – cost per unit trend analysis
 *  6. MAINTENANCE  – MTBF-based failure prediction
 */
import { apiClient } from "./api";

// ── Enums / label maps ────────────────────────────────────────────────────────

export type AgentType = "PREDICTION" | "ANOMALY" | "OPTIMIZATION" | "RECIPE" | "COST" | "MAINTENANCE";
export type SeverityType = "low" | "medium" | "high" | "critical";
export type RiskLevel = "GREEN" | "YELLOW" | "RED";
export type SuggestionStatus = "pending" | "accepted" | "rejected" | "applied" | "expired";

export const AGENT_LABELS: Record<AgentType, string> = {
  PREDICTION:   "Production Prediction",
  ANOMALY:      "Anomaly Detection",
  OPTIMIZATION: "Optimization",
  RECIPE:       "Recipe Intelligence",
  COST:         "Cost Optimization",
  MAINTENANCE:  "Predictive Maintenance",
};

export const AGENT_COLORS: Record<AgentType, string> = {
  PREDICTION:   "text-indigo-400",
  ANOMALY:      "text-red-400",
  OPTIMIZATION: "text-cyan-400",
  RECIPE:       "text-violet-400",
  COST:         "text-amber-400",
  MAINTENANCE:  "text-orange-400",
};

export const AGENT_BG: Record<AgentType, string> = {
  PREDICTION:   "bg-indigo-500/10 border-indigo-500/20",
  ANOMALY:      "bg-red-500/10 border-red-500/20",
  OPTIMIZATION: "bg-cyan-500/10 border-cyan-500/20",
  RECIPE:       "bg-violet-500/10 border-violet-500/20",
  COST:         "bg-amber-500/10 border-amber-500/20",
  MAINTENANCE:  "bg-orange-500/10 border-orange-500/20",
};

export const SEVERITY_COLORS: Record<SeverityType, string> = {
  low:      "text-slate-400",
  medium:   "text-amber-400",
  high:     "text-orange-400",
  critical: "text-red-400",
};

export const SEVERITY_BG: Record<SeverityType, string> = {
  low:      "bg-slate-500/10 border-slate-500/20",
  medium:   "bg-amber-500/10 border-amber-500/20",
  high:     "bg-orange-500/10 border-orange-500/20",
  critical: "bg-red-500/10 border-red-500/20",
};

export const RISK_COLORS: Record<RiskLevel, string> = {
  GREEN:  "text-emerald-400",
  YELLOW: "text-amber-400",
  RED:    "text-red-400",
};

export const RISK_BG: Record<RiskLevel, string> = {
  GREEN:  "bg-emerald-500/10 border-emerald-500/20",
  YELLOW: "bg-amber-500/10 border-amber-500/20",
  RED:    "bg-red-500/10 border-red-500/20",
};

// ── Types ──────────────────────────────────────────────────────────────────────

export interface PredictionOutput {
  prediction_id?:           string | null;
  predicted_completion_at?: string | null;
  predicted_output_qty?:    number | null;
  predicted_output_uom?:    string | null;
  delay_risk_pct:           number;
  efficiency_forecast_pct?: number | null;
  historical_sample_size:   number;
  confidence_score:         number;
  explanation:              string;
  risk_level:               RiskLevel;
}

export interface AnomalyOutput {
  anomaly_type:        string;
  severity:            SeverityType;
  affected_area:       string | null;
  affected_material:   string | null;
  deviation_pct:       number | null;
  actual_value:        number | null;
  expected_value:      number | null;
  baseline_source:     string | null;
  confidence_score:    number;
  explanation:         string;
  production_order_id?: string | null;
  work_center_id?:     string | null;
}

export interface AnomalyRead extends AnomalyOutput {
  id:          string;
  anomaly_no:  string;
  is_resolved: boolean;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at:  string | null;
}

export interface SuggestionOutput {
  agent_type:                    AgentType;
  suggestion_type:               string;
  issue_detected:                string;
  suggested_change:              string;
  current_value?:                number | null;
  recommended_value?:            number | null;
  value_unit?:                   string | null;
  expected_efficiency_gain_pct?: number | null;
  expected_cost_reduction_pct?:  number | null;
  expected_quality_improvement?: string | null;
  estimated_kes_saving?:         number | null;
  confidence_score:              number;
  explanation:                   string;
  product_id?:                   string | null;
  recipe_id?:                    string | null;
  work_center_id?:               string | null;
  // Maintenance extras
  predicted_next_failure?:       string | null;
  hours_to_failure?:             number | null;
  mtbf_hours?:                   number | null;
  pct_of_mtbf?:                  number | null;
}

export interface SuggestionRead extends SuggestionOutput {
  id:               string;
  suggestion_no:    string;
  status:           SuggestionStatus;
  actioned_by:      string | null;
  actioned_at:      string | null;
  rejection_reason: string | null;
  created_at:       string | null;
}

export interface PredictionRead extends PredictionOutput {
  id:                     string;
  prediction_no:          string;
  production_order_id:    string;
  actual_completion_at:   string | null;
  actual_output_qty:      number | null;
  was_delayed:            boolean | null;
  prediction_error_pct:   number | null;
  created_at:             string | null;
}

export interface AIDashboard {
  anomalies_7d: {
    critical: number;
    high:     number;
    medium:   number;
    low:      number;
    total:    number;
  };
  suggestions: {
    pending:  number;
    accepted: number;
    rejected: number;
  };
  predictions_7d: {
    green:  number;
    yellow: number;
    red:    number;
  };
}

export interface RunAllOutput {
  prediction?:  PredictionOutput | null;
  anomalies:    AnomalyOutput[];
  suggestions:  SuggestionOutput[];
  summary: {
    anomaly_count:      number;
    suggestion_count:   number;
    critical_anomalies: number;
  };
}

// ── API client ─────────────────────────────────────────────────────────────────

export const productionAiApi = {
  async dashboard(): Promise<AIDashboard> {
    const r = await apiClient.get<AIDashboard>("/api/v1/production-ai/dashboard").then((r) => r.data);
    return r.data;
  },

  async runAll(orderId?: string): Promise<RunAllOutput> {
    const params = orderId ? { order_id: orderId } : undefined;
    const r = await apiClient.post<RunAllOutput>("/api/v1/production-ai/run-all", null, { params }).then((r) => r.data);
    return r.data;
  },

  async predict(orderId: string): Promise<PredictionOutput> {
    const r = await apiClient.post<PredictionOutput>(`/api/v1/production-ai/predict/${orderId}`).then((r) => r.data);
    return r.data;
  },

  async detectAnomalies(params?: { order_id?: string; look_back_days?: number }): Promise<AnomalyOutput[]> {
    const r = await apiClient.post<AnomalyOutput[]>("/api/v1/production-ai/detect-anomalies", null, { params }).then((r) => r.data);
    return r.data;
  },

  async optimize(productId?: string): Promise<SuggestionOutput[]> {
    const r = await apiClient.post<SuggestionOutput[]>("/api/v1/production-ai/optimize", null, {
      params: productId ? { product_id: productId } : undefined,
    });
    return r.data;
  },

  async recipeInsights(recipeId?: string): Promise<SuggestionOutput[]> {
    const r = await apiClient.post<SuggestionOutput[]>("/api/v1/production-ai/recipe-insights", null, {
      params: recipeId ? { recipe_id: recipeId } : undefined,
    });
    return r.data;
  },

  async costIntelligence(lookBackDays = 60): Promise<SuggestionOutput[]> {
    const r = await apiClient.post<SuggestionOutput[]>("/api/v1/production-ai/cost-intelligence", null, {
      params: { look_back_days: lookBackDays },
    });
    return r.data;
  },

  async maintenancePredict(): Promise<SuggestionOutput[]> {
    const r = await apiClient.post<SuggestionOutput[]>("/api/v1/production-ai/maintenance-predict").then((r) => r.data);
    return r.data;
  },

  async listAnomalies(params?: { is_resolved?: boolean; severity?: string; limit?: number }): Promise<AnomalyRead[]> {
    const r = await apiClient.get<AnomalyRead[]>("/api/v1/production-ai/anomalies", { params }).then((r) => r.data);
    return r.data;
  },

  async resolveAnomaly(id: string, resolved_by: string, notes?: string): Promise<AnomalyRead> {
    const r = await apiClient.post<AnomalyRead>(`/api/v1/production-ai/anomalies/${id}/resolve`, {
      resolved_by, notes,
    });
    return r.data;
  },

  async listSuggestions(params?: {
    status?: string; agent_type?: string; product_id?: string; limit?: number;
  }): Promise<SuggestionRead[]> {
    const r = await apiClient.get<SuggestionRead[]>("/api/v1/production-ai/suggestions", { params }).then((r) => r.data);
    return r.data;
  },

  async actionSuggestion(
    id: string,
    status: "accepted" | "rejected" | "applied",
    actioned_by?: string,
    rejection_reason?: string,
  ): Promise<SuggestionRead> {
    const r = await apiClient.post<SuggestionRead>(`/api/v1/production-ai/suggestions/${id}/action`, {
      status, actioned_by, rejection_reason,
    });
    return r.data;
  },

  async listPredictions(params?: {
    order_id?: string; risk_level?: string; limit?: number;
  }): Promise<PredictionRead[]> {
    const r = await apiClient.get<PredictionRead[]>("/api/v1/production-ai/predictions", { params }).then((r) => r.data);
    return r.data;
  },
};

// ── Formatting helpers ──────────────────────────────────────────────────────────

export function fmtConfidence(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

export function confidenceColor(v: number): string {
  return v >= 0.8 ? "text-emerald-400" : v >= 0.6 ? "text-amber-400" : "text-slate-400";
}
