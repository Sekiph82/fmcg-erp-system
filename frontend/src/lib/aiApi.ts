import { apiClient } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AIStatus {
  provider: string;
  configured: boolean;
  model: string;
  mode: "live" | "mock";
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
  async status(): Promise<AIStatus> {
    const res = await apiClient.get<AIStatus>("/api/v1/ai/status/").then((r) => r.data);
    return res.data;
  },

  async dashboard(): Promise<AIDashboard> {
    const res = await apiClient.get<AIDashboard>("/api/v1/ai/dashboard/").then((r) => r.data);
    return res.data;
  },

  // Predictions
  async generatePredictions(types?: string[]): Promise<{ count: number; predictions: AIPrediction[] }> {
    const res = await apiClient.post("/api/v1/ai/predictions/generate/", { prediction_types: types ?? null }).then((r) => r.data);
    return res.data;
  },
  async listPredictions(params?: { prediction_type?: string; risk_level?: string; limit?: number }): Promise<AIPrediction[]> {
    const res = await apiClient.get<AIPrediction[]>("/api/v1/ai/predictions/", { params }).then((r) => r.data);
    return res.data;
  },
  async archivePrediction(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/ai/predictions/${id}/archive/`).then((r) => r.data);
  },

  // Recommendations
  async generateRecommendations(focusArea?: string): Promise<{ count: number; recommendations: AIRecommendation[] }> {
    const res = await apiClient.post("/api/v1/ai/recommendations/generate/", { focus_area: focusArea ?? null }).then((r) => r.data);
    return res.data;
  },
  async listRecommendations(params?: { category?: string; priority?: string; include_actioned?: boolean }): Promise<AIRecommendation[]> {
    const res = await apiClient.get<AIRecommendation[]>("/api/v1/ai/recommendations/", { params }).then((r) => r.data);
    return res.data;
  },
  async actionRecommendation(id: string): Promise<void> {
    await apiClient.post(`/api/v1/ai/recommendations/${id}/action/`).then((r) => r.data);
  },
  async dismissRecommendation(id: string): Promise<void> {
    await apiClient.post(`/api/v1/ai/recommendations/${id}/dismiss/`).then((r) => r.data);
  },

  // Scenarios
  async simulateScenario(body: {
    scenario_type: string; parameters: Record<string, any>; title?: string;
  }): Promise<AIScenario> {
    const res = await apiClient.post<AIScenario>("/api/v1/ai/scenarios/simulate/", body).then((r) => r.data);
    return res.data;
  },
  async listScenarios(params?: { scenario_type?: string }): Promise<AIScenario[]> {
    const res = await apiClient.get<AIScenario[]>("/api/v1/ai/scenarios/", { params }).then((r) => r.data);
    return res.data;
  },
  async getScenario(id: string): Promise<AIScenario> {
    const res = await apiClient.get<AIScenario>(`/api/v1/ai/scenarios/${id}/`).then((r) => r.data);
    return res.data;
  },

  // Formulations
  async generateFormulation(body: {
    product_category: string;
    target_properties: Record<string, any>;
    cost_target?: number;
    performance_priority?: string;
  }): Promise<AIFormulation> {
    const res = await apiClient.post<AIFormulation>("/api/v1/ai/formulations/generate/", body).then((r) => r.data);
    return res.data;
  },
  async listFormulations(params?: { product_category?: string; is_approved?: boolean }): Promise<AIFormulation[]> {
    const res = await apiClient.get<AIFormulation[]>("/api/v1/ai/formulations/", { params }).then((r) => r.data);
    return res.data;
  },
  async getFormulation(id: string): Promise<AIFormulation> {
    const res = await apiClient.get<AIFormulation>(`/api/v1/ai/formulations/${id}/`).then((r) => r.data);
    return res.data;
  },
  async approveFormulation(id: string): Promise<void> {
    await apiClient.post(`/api/v1/ai/formulations/${id}/approve/`).then((r) => r.data);
  },
  async toggleFavorite(id: string): Promise<{ is_favorite: boolean }> {
    const res = await apiClient.post<{ is_favorite: boolean }>(`/api/v1/ai/formulations/${id}/favorite/`).then((r) => r.data);
    return res.data;
  },

  // Logs
  async listLogs(limit?: number): Promise<AILog[]> {
    const res = await apiClient.get<AILog[]>("/api/v1/ai/logs/", { params: { limit } }).then((r) => r.data);
    return res.data;
  },
};
