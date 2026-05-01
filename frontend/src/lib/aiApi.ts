import { apiClient } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AIStatus {
  provider: string;
  configured: boolean;
  model: string;
  mode: "live" | "mock";
}

export interface AIChatResponse {
  answer: string;
  provider: string;
  model: string;
  mode: "live" | "mock";
  erp_context_used: string[];
  tokens: { prompt: number; completion: number };
  latency_ms: number;
}

export interface AIForecastBaseline {
  baseline_forecast_kes: number;
  moving_average_kes: number;
  trend_pct: number;
  method: string;
  data_quality: string;
  confidence: number;
  monthly_history_kes: number[];
  note: string;
}

export interface AIDashboard {
  stats: {
    active_predictions: number;
    pending_recommendations: number;
    saved_formulations: number;
    scenario_simulations: number;
  };
  provider: AIStatus;
  recent_predictions: AIPrediction[];
  critical_recommendations: AIRecommendation[];
}

export interface AIPrediction {
  id: string;
  prediction_type: string;
  subject_name?: string;
  period?: string;
  forecast_value?: number;
  confidence_score?: number;
  risk_level?: "low" | "medium" | "high" | "critical";
  trend?: "up" | "down" | "stable";
  summary?: string;
  details?: Record<string, any>;
  is_archived: boolean;
  created_at: string;
}

export interface AIRecommendation {
  id: string;
  category: string;
  title: string;
  reason?: string;
  expected_impact?: string;
  confidence_level?: "low" | "medium" | "high";
  priority?: "low" | "medium" | "high" | "critical";
  action_data?: Record<string, any>;
  is_actioned: boolean;
  is_dismissed: boolean;
  created_at: string;
}

export interface AIScenario {
  id: string;
  title: string;
  scenario_type: string;
  input_parameters?: Record<string, any>;
  expected_impact?: string;
  risks?: string[];
  opportunities?: string[];
  simulation_data: Record<string, any>;
  created_at: string;
}

export interface FormulationIngredient {
  ingredient_name: string;
  inci_name?: string;
  cas_number?: string;
  percentage: number;
  function: string;
  supplier_examples?: string[];
  approx_cost_per_kg_usd?: number;
}

export interface FormulationData {
  name: string;
  product_category: string;
  version: string;
  description?: string;
  ingredients: FormulationIngredient[];
  process_instructions: string[];
  processing_temperature?: string;
  mixing_speed?: string;
  estimated_ph?: string;
  estimated_viscosity_cP?: string;
  cost_breakdown?: {
    raw_materials_per_kg_usd: number;
    packaging_estimate_per_unit_usd: number;
    labor_overhead_per_kg_usd: number;
    total_cogs_per_kg_usd: number;
  };
  performance_profile?: {
    cleaning_efficiency?: string;
    foam_level?: string;
    rinse_ability?: string;
    stability?: string;
    biodegradability?: string;
    skin_mildness?: string;
    antibacterial?: string;
  };
  alternatives?: {
    low_cost?: { name: string; key_changes: string; trade_offs: string };
    premium?: { name: string; key_changes: string; trade_offs: string };
    eco?: { name: string; key_changes: string; trade_offs: string };
  };
  safety_notes?: string[];
  regulatory_notes?: string;
  shelf_life?: string;
}

export interface AIFormulation {
  id: string;
  name: string;
  product_category: string;
  version: string;
  target_properties?: Record<string, any>;
  cost_target?: number;
  performance_priority?: string;
  formulation_data: FormulationData;
  estimated_cost_per_kg?: number;
  is_approved: boolean;
  is_favorite: boolean;
  notes?: string;
  created_at: string;
}

export interface AILog {
  id: string;
  request_type: string;
  provider: string;
  model?: string;
  status: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  latency_ms?: number;
  error_message?: string;
  created_at: string;
}

// ── API client ────────────────────────────────────────────────────────────────

export const aiApi = {
  status: (): Promise<AIStatus> =>
    apiClient.get<AIStatus>("/api/v1/ai/status/").then((r) => r.data),

  dashboard: (): Promise<AIDashboard> =>
    apiClient.get<AIDashboard>("/api/v1/ai/dashboard/").then((r) => r.data),

  // Predictions
  generatePredictions: (types?: string[]): Promise<{ count: number; predictions: AIPrediction[] }> =>
    apiClient.post("/api/v1/ai/predictions/generate/", { prediction_types: types ?? null }).then((r) => r.data),

  listPredictions: (params?: { prediction_type?: string; risk_level?: string; limit?: number }): Promise<AIPrediction[]> =>
    apiClient.get<AIPrediction[]>("/api/v1/ai/predictions/", { params }).then((r) => r.data),

  archivePrediction: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/ai/predictions/${id}/archive/`).then(() => undefined),

  // Recommendations
  generateRecommendations: (focusArea?: string): Promise<{ count: number; recommendations: AIRecommendation[] }> =>
    apiClient.post("/api/v1/ai/recommendations/generate/", { focus_area: focusArea ?? null }).then((r) => r.data),

  listRecommendations: (params?: { category?: string; priority?: string; include_actioned?: boolean }): Promise<AIRecommendation[]> =>
    apiClient.get<AIRecommendation[]>("/api/v1/ai/recommendations/", { params }).then((r) => r.data),

  actionRecommendation: (id: string): Promise<void> =>
    apiClient.post(`/api/v1/ai/recommendations/${id}/action/`).then(() => undefined),

  dismissRecommendation: (id: string): Promise<void> =>
    apiClient.post(`/api/v1/ai/recommendations/${id}/dismiss/`).then(() => undefined),

  // Scenarios
  simulateScenario: (body: { scenario_type: string; parameters: Record<string, any>; title?: string }): Promise<AIScenario> =>
    apiClient.post<AIScenario>("/api/v1/ai/scenarios/simulate/", body).then((r) => r.data),

  listScenarios: (params?: { scenario_type?: string }): Promise<AIScenario[]> =>
    apiClient.get<AIScenario[]>("/api/v1/ai/scenarios/", { params }).then((r) => r.data),

  getScenario: (id: string): Promise<AIScenario> =>
    apiClient.get<AIScenario>(`/api/v1/ai/scenarios/${id}/`).then((r) => r.data),

  // Formulations
  generateFormulation: (body: {
    product_category: string;
    target_properties: Record<string, any>;
    cost_target?: number;
    performance_priority?: string;
  }): Promise<AIFormulation> =>
    apiClient.post<AIFormulation>("/api/v1/ai/formulations/generate/", body).then((r) => r.data),

  listFormulations: (params?: { product_category?: string; is_approved?: boolean }): Promise<AIFormulation[]> =>
    apiClient.get<AIFormulation[]>("/api/v1/ai/formulations/", { params }).then((r) => r.data),

  getFormulation: (id: string): Promise<AIFormulation> =>
    apiClient.get<AIFormulation>(`/api/v1/ai/formulations/${id}/`).then((r) => r.data),

  approveFormulation: (id: string): Promise<void> =>
    apiClient.post(`/api/v1/ai/formulations/${id}/approve/`).then(() => undefined),

  toggleFavorite: (id: string): Promise<{ is_favorite: boolean }> =>
    apiClient.post<{ is_favorite: boolean }>(`/api/v1/ai/formulations/${id}/favorite/`).then((r) => r.data),

  // Logs
  listLogs: (limit?: number): Promise<AILog[]> =>
    apiClient.get<AILog[]>("/api/v1/ai/logs/", { params: { limit } }).then((r) => r.data),

  // ERP Copilot Chat
  chat: (message: string, conversation_history?: Array<{ role: string; content: string }>): Promise<AIChatResponse> =>
    apiClient.post<AIChatResponse>("/api/v1/ai/chat/", { message, conversation_history }).then((r) => r.data),

  // Deterministic forecast baseline
  forecastBaseline: (): Promise<AIForecastBaseline> =>
    apiClient.get<AIForecastBaseline>("/api/v1/ai/forecast-baseline/").then((r) => r.data),

  // AI Health
  health: (): Promise<{ status: string; provider: string; mode: string }> =>
    apiClient.get("/api/v1/ai/health/").then((r) => r.data),
};
