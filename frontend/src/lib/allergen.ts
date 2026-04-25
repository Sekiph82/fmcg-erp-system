// Allergen + Nutrition Management — types & API client

const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/allergen`;

// ── Types ─────────────────────────────────────────────────────────────────────

export type AllergenCategory = "MAJOR" | "MINOR" | "CUSTOM";
export type PresenceType = "CONTAINS" | "MAY_CONTAIN" | "PRODUCED_IN_SAME_FACILITY" | "FREE_FROM" | "UNKNOWN";
export type CrossContactRisk = "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type NutrientBasis = "PER_100G" | "PER_100ML" | "PER_SERVING" | "PER_UNIT";
export type NutrientSource = "SUPPLIER" | "LAB" | "MANUAL" | "CALCULATED";
export type LabelBasisType = "PER_100G" | "PER_100ML" | "PER_SERVING" | "BOTH";
export type ANAIAgentType = "ALLERGEN_RISK_MONITOR" | "NUTRITION_CHANGE_ANALYZER" | "LABEL_COMPLIANCE_ASSISTANT";
export type ANAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "APPLIED";

export interface AllergenMaster {
  id: string;
  allergen_code: string;
  allergen_name: string;
  regulatory_name: string | null;
  category: AllergenCategory;
  is_active: boolean;
  sort_order: number;
  notes: string | null;
  created_at: string;
}

export interface MaterialAllergenLine {
  id: string;
  allergen_id: string;
  presence_type: PresenceType;
  concentration_note: string | null;
  declaration_required: boolean;
  critical_flag: boolean;
  notes: string | null;
  allergen_code: string | null;
  allergen_name: string | null;
  created_at: string;
}

export interface MaterialAllergenProfile {
  id: string;
  material_id: string;
  allergen_present_flag: boolean;
  allergen_may_contain_flag: boolean;
  cross_contact_risk_level: CrossContactRisk;
  supplier_allergen_statement_ref: string | null;
  allergen_review_date: string | null;
  approved_by: string | null;
  is_active: boolean;
  notes: string | null;
  lines: MaterialAllergenLine[];
  material_name: string | null;
  created_at: string;
}

export interface NutritionLine {
  id: string;
  nutrient_code: string;
  nutrient_name: string;
  unit: string;
  value: string;
  source_type: NutrientSource;
  approved_flag: boolean;
  review_date: string | null;
  notes: string | null;
  created_at: string;
}

export interface NutritionProfile {
  id: string;
  material_id: string | null;
  product_id: string | null;
  basis_type: NutrientBasis;
  density_factor: string | null;
  moisture_factor: string | null;
  is_active: boolean;
  notes: string | null;
  lines: NutritionLine[];
  entity_name: string | null;
  created_at: string;
}

export interface AllergenRollupLine {
  allergen_code: string;
  allergen_name: string;
  presence_type: PresenceType;
  declaration_required: boolean;
  critical_flag: boolean;
  source_materials: string[];
}

export interface AllergenRollupResult {
  product_id: string | null;
  bom_id: string | null;
  bom_version: string | null;
  contains: AllergenRollupLine[];
  may_contain: AllergenRollupLine[];
  free_from: string[];
  declaration_required: AllergenRollupLine[];
  cross_contact_risk: CrossContactRisk;
  label_statement: string;
  may_contain_statement: string;
  ingredient_allergen_map: Record<string, string[]>;
}

export interface NutritionRollupLine {
  nutrient_code: string;
  nutrient_name: string;
  unit: string;
  value_per_100g: string;
  value_per_serving: string | null;
}

export interface NutritionRollupResult {
  product_id: string | null;
  bom_id: string | null;
  bom_version: string | null;
  serving_size_g: string | null;
  nutrients: NutritionRollupLine[];
  per_100g: Record<string, { value: number; unit: string; name: string }>;
  per_serving: Record<string, { value: number; unit: string; name: string }>;
  completeness_pct: string;
  missing_profiles: string[];
}

export interface ProductAllergenSummary {
  id: string;
  product_id: string;
  bom_id: string | null;
  bom_version: string | null;
  contains_allergens: string[] | null;
  may_contain_allergens: string[] | null;
  declaration_required: Array<{ code: string; name: string }> | null;
  cross_contact_risk: CrossContactRisk | null;
  label_statement: string | null;
  may_contain_statement: string | null;
  last_calculated_at: string | null;
  is_stale: boolean;
  product_name: string | null;
  created_at: string;
}

export interface ProductNutritionSummary {
  id: string;
  product_id: string;
  bom_id: string | null;
  bom_version: string | null;
  serving_size_value: string | null;
  serving_size_uom: string | null;
  servings_per_pack: string | null;
  label_basis_type: LabelBasisType;
  nutrition_per_100g: Record<string, { value: number; unit: string; name: string }> | null;
  nutrition_per_serving: Record<string, { value: number; unit: string; name: string }> | null;
  last_calculated_at: string | null;
  is_stale: boolean;
  product_name: string | null;
  created_at: string;
}

export interface AllergenChangeLog {
  id: string;
  product_id: string | null;
  bom_id: string | null;
  bom_version_from: string | null;
  bom_version_to: string | null;
  change_type: string;
  old_value: string | null;
  new_value: string | null;
  detected_at: string | null;
  requires_label_review: boolean;
  requires_qc_review: boolean;
  label_review_done: boolean;
  qc_review_done: boolean;
  allergen_name: string | null;
  product_name: string | null;
  created_at: string;
}

export interface LabelReadiness {
  product_id: string;
  product_name: string;
  allergen_summary_complete: boolean;
  allergen_summary_stale: boolean;
  nutrition_summary_complete: boolean;
  nutrition_summary_stale: boolean;
  serving_config_present: boolean;
  open_change_logs: number;
  pending_label_reviews: number;
  pending_qc_reviews: number;
  readiness_score: number;
  warnings: string[];
  last_checked: string;
}

export interface ANAIRecommendation {
  id: string;
  agent_type: ANAIAgentType;
  title: string;
  description: string;
  affected_entity_type: string | null;
  recommendation: string;
  severity: string;
  status: ANAIRecStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  agent_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ANDashboard {
  total_allergens: number;
  materials_with_allergen_profiles: number;
  materials_missing_profiles: number;
  products_with_allergen_summaries: number;
  products_with_nutrition_summaries: number;
  stale_allergen_summaries: number;
  stale_nutrition_summaries: number;
  open_change_logs: number;
  pending_label_reviews: number;
  ai_pending: number;
  high_risk_cross_contact: number;
}

// ── API Client ────────────────────────────────────────────────────────────────

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const allergenApi = {
  // Dashboard
  getDashboard: () => req<ANDashboard>("GET", "/dashboard"),

  // Allergen master
  listAllergens: (active_only = true) => req<AllergenMaster[]>("GET", `/allergens?active_only=${active_only}`),
  getAllergen: (id: string) => req<AllergenMaster>("GET", `/allergens/${id}`),
  createAllergen: (d: Partial<AllergenMaster>) => req<AllergenMaster>("POST", "/allergens", d),
  updateAllergen: (id: string, d: Partial<AllergenMaster>) => req<AllergenMaster>("PATCH", `/allergens/${id}`, d),
  seedDefaults: () => req<{ added: number }>("POST", "/allergens/seed-defaults"),

  // Material allergen profiles
  listAllergenProfiles: (has_allergens?: boolean) => {
    const q = has_allergens !== undefined ? `?has_allergens=${has_allergens}` : "";
    return req<MaterialAllergenProfile[]>("GET", `/materials/allergen-profiles${q}`);
  },
  getMaterialAllergenProfile: (materialId: string) =>
    req<MaterialAllergenProfile>("GET", `/materials/${materialId}/allergen-profile`),
  upsertAllergenProfile: (materialId: string, d: Partial<MaterialAllergenProfile>) =>
    req<MaterialAllergenProfile>("POST", `/materials/${materialId}/allergen-profile`, d),

  // Nutrition profiles
  listNutritionProfiles: (entity_type = "material") =>
    req<NutritionProfile[]>("GET", `/nutrition-profiles?entity_type=${entity_type}`),
  getMaterialNutrition: (materialId: string) =>
    req<NutritionProfile>("GET", `/materials/${materialId}/nutrition-profile`),
  createMaterialNutrition: (materialId: string, d: Partial<NutritionProfile>) =>
    req<NutritionProfile>("POST", `/materials/${materialId}/nutrition-profile`, d),
  createProductNutrition: (productId: string, d: Partial<NutritionProfile>) =>
    req<NutritionProfile>("POST", `/products/${productId}/nutrition-profile`, d),
  addNutritionLine: (profileId: string, d: Partial<NutritionLine>) =>
    req<NutritionLine>("POST", `/nutrition-profiles/${profileId}/lines`, d),
  updateNutritionLine: (lineId: string, d: Partial<NutritionLine>) =>
    req<NutritionLine>("PATCH", `/nutrition-profiles/lines/${lineId}`, d),

  // Roll-up
  bomAllergenRollup: (bomId: string) => req<AllergenRollupResult>("GET", `/bom/${bomId}/allergen-rollup`),
  bomNutritionRollup: (bomId: string, serving_size_g?: number) => {
    const q = serving_size_g ? `?serving_size_g=${serving_size_g}` : "";
    return req<NutritionRollupResult>("GET", `/bom/${bomId}/nutrition-rollup${q}`);
  },
  recipeAllergenRollup: (recipeId: string) => req<AllergenRollupResult>("GET", `/recipe/${recipeId}/allergen-rollup`),
  recipeNutritionRollup: (recipeId: string, serving_size_g?: number) => {
    const q = serving_size_g ? `?serving_size_g=${serving_size_g}` : "";
    return req<NutritionRollupResult>("GET", `/recipe/${recipeId}/nutrition-rollup${q}`);
  },

  // Product summaries
  listAllergenSummaries: () => req<ProductAllergenSummary[]>("GET", "/products/allergen-summaries"),
  getAllergenSummary: (productId: string) => req<ProductAllergenSummary>("GET", `/products/${productId}/allergen-summary`),
  calculateAllergenSummary: (productId: string, params: { bom_id?: string; recipe_id?: string }) => {
    const q = new URLSearchParams();
    if (params.bom_id) q.set("bom_id", params.bom_id);
    if (params.recipe_id) q.set("recipe_id", params.recipe_id);
    return req("POST", `/products/${productId}/allergen-summary/calculate?${q}`);
  },
  listNutritionSummaries: () => req<ProductNutritionSummary[]>("GET", "/products/nutrition-summaries"),
  getNutritionSummary: (productId: string) => req<ProductNutritionSummary>("GET", `/products/${productId}/nutrition-summary`),
  calculateNutritionSummary: (productId: string, params: { bom_id?: string; recipe_id?: string; serving_size_g?: number }) => {
    const q = new URLSearchParams();
    if (params.bom_id) q.set("bom_id", params.bom_id);
    if (params.recipe_id) q.set("recipe_id", params.recipe_id);
    if (params.serving_size_g) q.set("serving_size_g", String(params.serving_size_g));
    return req("POST", `/products/${productId}/nutrition-summary/calculate?${q}`);
  },

  // Serving config
  getServingConfig: (productId: string) => req("GET", `/products/${productId}/serving-config`),
  upsertServingConfig: (productId: string, d: object) => req("POST", `/products/${productId}/serving-config`, d),

  // Label readiness
  getLabelReadiness: (productId: string) => req<LabelReadiness>("GET", `/products/${productId}/label-readiness`),

  // BOM comparison
  compareBOMAllergens: (bomIdA: string, bomIdB: string) => req("GET", `/bom/compare/${bomIdA}/${bomIdB}/allergens`),
  compareBOMNutrition: (bomIdA: string, bomIdB: string) => req("GET", `/bom/compare/${bomIdA}/${bomIdB}/nutrition`),

  // Change logs
  listChangeLogs: (params?: { product_id?: string; review_pending?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.product_id) q.set("product_id", params.product_id);
    if (params?.review_pending !== undefined) q.set("review_pending", String(params.review_pending));
    return req<AllergenChangeLog[]>("GET", `/change-logs?${q}`);
  },
  markReviewed: (logId: string, review_type: "label" | "qc") =>
    req("PATCH", `/change-logs/${logId}/mark-reviewed?review_type=${review_type}`),

  // AI
  runAllergenMonitor: () => req<{ generated: number }>("POST", "/ai/run-allergen-risk-monitor"),
  runNutritionAnalyzer: () => req<{ generated: number }>("POST", "/ai/run-nutrition-change-analyzer"),
  runLabelAssistant: () => req<{ generated: number }>("POST", "/ai/run-label-compliance-assistant"),
  listRecommendations: (agent_type?: string, status?: string) => {
    const q = new URLSearchParams();
    if (agent_type) q.set("agent_type", agent_type);
    if (status) q.set("status", status);
    return req<ANAIRecommendation[]>("GET", `/ai/recommendations?${q}`);
  },
  reviewRecommendation: (id: string, status: string, reviewed_by?: string) =>
    req<ANAIRecommendation>("PATCH", `/ai/recommendations/${id}`, { status, reviewed_by }),

  // Reports
  reportRMAllergens: () => req<unknown[]>("GET", "/reports/raw-material-allergens"),
  reportFGAllergens: () => req<unknown[]>("GET", "/reports/finished-product-allergens"),
  reportNutritionCompleteness: () => req<unknown[]>("GET", "/reports/nutrition-completeness"),
  reportMissingStatements: () => req<unknown[]>("GET", "/reports/missing-supplier-statements"),
};

// ── Color Maps ────────────────────────────────────────────────────────────────

export const presenceColor: Record<PresenceType, string> = {
  CONTAINS:                  "bg-red-100 text-red-800",
  MAY_CONTAIN:               "bg-orange-100 text-orange-800",
  PRODUCED_IN_SAME_FACILITY: "bg-yellow-100 text-yellow-800",
  FREE_FROM:                 "bg-green-100 text-green-800",
  UNKNOWN:                   "bg-gray-100 text-gray-600",
};

export const riskColor: Record<CrossContactRisk, string> = {
  NONE:     "bg-green-100 text-green-700",
  LOW:      "bg-blue-100 text-blue-700",
  MEDIUM:   "bg-yellow-100 text-yellow-700",
  HIGH:     "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

export const severityColor: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-yellow-100 text-yellow-800",
  LOW:      "bg-green-100 text-green-800",
};

export const DEFAULT_NUTRIENTS = [
  { code: "energy_kcal", name: "Energy", unit: "kcal" },
  { code: "energy_kj",   name: "Energy", unit: "kJ" },
  { code: "protein",     name: "Protein", unit: "g" },
  { code: "total_fat",   name: "Total Fat", unit: "g" },
  { code: "saturated_fat", name: "Saturated Fat", unit: "g" },
  { code: "carbohydrates", name: "Carbohydrates", unit: "g" },
  { code: "sugars",      name: "of which Sugars", unit: "g" },
  { code: "fiber",       name: "Dietary Fiber", unit: "g" },
  { code: "sodium",      name: "Sodium", unit: "mg" },
  { code: "salt",        name: "Salt", unit: "g" },
];
