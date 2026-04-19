import { apiClient } from "./api";

// ── Enums ──────────────────────────────────────────────────────────────────────

export type BOMType = "FORMULA" | "INTERMEDIATE" | "PACKAGING" | "MULTILEVEL" | "PHANTOM" | "REWORK" | "COPRODUCT";
export type BOMLifecycle = "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "RELEASED" | "SUPERSEDED" | "ARCHIVED";
export type ComponentType = "RAW" | "INTERMEDIATE" | "PACKAGING" | "SERVICE" | "CO_PRODUCT" | "BY_PRODUCT" | "UTILITY" | "REWORK";
export type BasisType = "PER_BATCH" | "PER_UNIT" | "PER_100KG" | "PER_1000L" | "PERCENTAGE" | "FIXED";
export type SubstitutionPolicy = "NO_SUB" | "PLANNER_APPROVAL" | "QA_APPROVAL" | "BOTH_REQUIRED" | "SHORTAGE_ONLY" | "EMERGENCY_ONLY";
export type ItemLinkType = "PRODUCT" | "MATERIAL";
export type LossCategory = "PROCESS_LOSS" | "EVAPORATION" | "TRANSFER" | "STARTUP" | "SHUTDOWN" | "FILLING" | "PACKAGING_REJECT" | "QC_REJECTION" | "LINE_PURGE";
export type BOMAgentType = "FORMULA_ANALYZER" | "PACKAGING_OPTIMIZER" | "COMPLIANCE_CHECKER";
export type BOMRecStatus = "PENDING" | "ACCEPTED" | "REJECTED";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface BOMSummary {
  id: string;
  bom_code: string;
  bom_name: string;
  bom_type: BOMType;
  product_id: string | null;
  product_name: string | null;
  base_qty: number;
  base_uom: string;
  version_no: string;
  lifecycle: BOMLifecycle;
  is_default: boolean;
  effective_from: string | null;
  effective_to: string | null;
  standard_batch_cost: number | null;
  standard_cost_per_uom: number | null;
  created_at: string;
}

export interface BOMLineOut {
  id: string;
  bom_id: string;
  line_no: number;
  component_type: ComponentType;
  item_type: ItemLinkType;
  item_id: string | null;
  item_name: string | null;
  item_code: string | null;
  child_bom_id: string | null;
  required_qty: number;
  required_uom: string;
  basis_type: BasisType;
  concentration_pct: number | null;
  wastage_pct: number;
  process_loss_pct: number;
  fixed_consumption: boolean;
  is_optional: boolean;
  qc_required: boolean;
  allergen_flag: boolean;
  critical_component: boolean;
  substitute_group_id: string | null;
  substitution_policy: SubstitutionPolicy;
  consumption_stage: string | null;
  allergen_types: string[] | null;
  unit_cost: number | null;
  extended_cost: number | null;
  notes: string | null;
}

export interface BOMOut extends BOMSummary {
  revision_no: string;
  linked_routing_id: string | null;
  linked_quality_spec_id: string | null;
  allergen_flags: Record<string, boolean> | null;
  nutrition_per_100g: Record<string, number> | null;
  notes: string | null;
  lines: BOMLineOut[];
  yield_configs: YieldConfigOut[];
}

export interface YieldConfigOut {
  id: string;
  bom_id: string;
  loss_category: LossCategory;
  description: string | null;
  standard_pct: number;
  max_allowable_pct: number | null;
  cost_impact_flag: boolean;
}

export interface SubstituteOut {
  id: string;
  group_id: string;
  item_type: ItemLinkType;
  item_name: string | null;
  item_code: string | null;
  priority: number;
  qty_ratio: number;
  cost_impact_pct: number | null;
  quality_impact: string | null;
  allergen_impact: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface SubstGroupOut {
  id: string;
  group_code: string;
  group_name: string;
  policy: SubstitutionPolicy;
  notes: string | null;
  is_active: boolean;
  substitutes: SubstituteOut[];
}

export interface ConversionProfileOut {
  id: string;
  profile_code: string;
  profile_name: string;
  source_product_name: string | null;
  target_product_name: string | null;
  theoretical_conversion_ratio: number;
  standard_fill_volume: number | null;
  fill_volume_uom: string | null;
  startup_loss_pct: number;
  shutdown_loss_pct: number;
  packaging_reject_pct: number;
  residual_bulk_pct: number;
  line_purge_loss_pct: number;
  standard_expected_units: number | null;
  realistic_expected_units: number | null;
  is_active: boolean;
}

export interface ConversionCalcResult {
  source_qty: number;
  source_uom: string;
  theoretical_units: number;
  startup_loss_units: number;
  shutdown_loss_units: number;
  reject_units: number;
  residual_units: number;
  expected_good_units: number;
  total_loss_pct: number;
  fill_volume_per_unit: number | null;
  notes: string;
}

export interface ExplosionNode {
  level: number;
  line_id: string;
  bom_id: string;
  bom_code: string;
  parent_item_name: string;
  item_name: string;
  item_code: string | null;
  component_type: string;
  required_qty: number;
  adjusted_qty: number;
  required_uom: string;
  wastage_pct: number;
  process_loss_pct: number;
  allergen_flag: boolean;
  critical_component: boolean;
  substitutes: string[];
  children: ExplosionNode[];
}

export interface ExplosionResult {
  bom_id: string;
  bom_code: string;
  bom_name: string;
  target_qty: number;
  target_uom: string;
  total_levels: number;
  nodes: ExplosionNode[];
  flat_requirements: {
    item_name: string;
    item_code: string | null;
    component_type: string;
    required_uom: string;
    total_qty: number;
    total_adjusted_qty: number;
    allergen_flag: boolean;
    critical_component: boolean;
  }[];
}

export interface ScaledLine {
  line_no: number;
  item_name: string | null;
  item_code: string | null;
  component_type: string;
  basis_type: string;
  original_qty: number;
  scaled_qty: number;
  adjusted_qty: number;
  required_uom: string;
  fixed_consumption: boolean;
  warning: string | null;
}

export interface ScalingResult {
  bom_id: string;
  bom_code: string;
  original_base_qty: number;
  target_qty: number;
  scale_factor: number;
  lines: ScaledLine[];
}

export interface CostingLine {
  line_no: number;
  item_name: string | null;
  component_type: string;
  qty: number;
  uom: string;
  unit_cost: number | null;
  extended_cost: number;
  is_by_product_credit: boolean;
}

export interface CostingResult {
  bom_id: string;
  bom_code: string;
  bom_name: string;
  base_qty: number;
  base_uom: string;
  raw_material_cost: number;
  intermediate_cost: number;
  packaging_cost: number;
  utility_cost: number;
  by_product_credit: number;
  total_batch_cost: number;
  cost_per_uom: number;
  lines: CostingLine[];
}

export interface ComplianceSummary {
  bom_id: string;
  bom_code: string;
  allergen_flags: Record<string, boolean>;
  cross_contact_risks: string[];
  critical_components: string[];
  nutrition_per_100g: Record<string, number> | null;
  warnings: string[];
}

export interface BOMAIRecOut {
  id: string;
  bom_id: string;
  agent_type: BOMAgentType;
  status: BOMRecStatus;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  confidence_score: number | null;
  actioned_at: string | null;
}

export interface BOMDashboard {
  total_boms: number;
  released_boms: number;
  draft_boms: number;
  pending_review: number;
  boms_with_allergens: number;
  pending_ai_recs: number;
  recent_boms: BOMSummary[];
  by_type: Record<string, number>;
  by_lifecycle: Record<string, number>;
}

// ── Color / label maps ─────────────────────────────────────────────────────────

export const LIFECYCLE_COLOR: Record<BOMLifecycle, string> = {
  DRAFT:        "bg-gray-100 text-gray-600",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-700",
  APPROVED:     "bg-blue-100 text-blue-700",
  RELEASED:     "bg-green-100 text-green-700",
  SUPERSEDED:   "bg-orange-100 text-orange-600",
  ARCHIVED:     "bg-gray-200 text-gray-500",
};

export const BOM_TYPE_COLOR: Record<BOMType, string> = {
  FORMULA:      "bg-indigo-100 text-indigo-700",
  INTERMEDIATE: "bg-purple-100 text-purple-700",
  PACKAGING:    "bg-teal-100 text-teal-700",
  MULTILEVEL:   "bg-blue-100 text-blue-700",
  PHANTOM:      "bg-gray-100 text-gray-600",
  REWORK:       "bg-orange-100 text-orange-700",
  COPRODUCT:    "bg-green-100 text-green-700",
};

export const COMPONENT_COLOR: Record<ComponentType, string> = {
  RAW:          "bg-gray-100 text-gray-600",
  INTERMEDIATE: "bg-purple-100 text-purple-700",
  PACKAGING:    "bg-teal-100 text-teal-700",
  SERVICE:      "bg-blue-100 text-blue-700",
  CO_PRODUCT:   "bg-green-100 text-green-700",
  BY_PRODUCT:   "bg-yellow-100 text-yellow-700",
  UTILITY:      "bg-orange-100 text-orange-600",
  REWORK:       "bg-red-100 text-red-700",
};

export const AGENT_LABEL: Record<BOMAgentType, string> = {
  FORMULA_ANALYZER:    "Formula Analyzer",
  PACKAGING_OPTIMIZER: "Packaging Optimizer",
  COMPLIANCE_CHECKER:  "Compliance Checker",
};

export const AGENT_COLOR: Record<BOMAgentType, string> = {
  FORMULA_ANALYZER:    "bg-indigo-100 text-indigo-700",
  PACKAGING_OPTIMIZER: "bg-teal-100 text-teal-700",
  COMPLIANCE_CHECKER:  "bg-red-100 text-red-700",
};

export const LIFECYCLE_NEXT: Partial<Record<BOMLifecycle, string>> = {
  DRAFT: "Submit for Review",
  UNDER_REVIEW: "Approve",
  APPROVED: "Release",
};

export function fmtKES(v: number): string {
  return `KES ${v.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ── API client ─────────────────────────────────────────────────────────────────

export const bomApi = {
  dashboard: () => apiClient.get<BOMDashboard>("/bom/dashboard"),

  // BOM CRUD
  create:  (body: Partial<BOMSummary>) => apiClient.post<BOMSummary>("/bom", body),
  list:    (params?: { bom_type?: string; lifecycle?: string; product_id?: string }) => {
    const qs = new URLSearchParams(Object.entries(params || {}).filter(([, v]) => v) as [string, string][]).toString();
    return apiClient.get<BOMSummary[]>(`/bom${qs ? `?${qs}` : ""}`);
  },
  get:     (id: string) => apiClient.get<BOMOut>(`/bom/${id}`),
  update:  (id: string, body: Partial<BOMSummary>) => apiClient.patch<BOMSummary>(`/bom/${id}`, body),
  clone:   (id: string, newVersion: string) => apiClient.post<BOMSummary>(`/bom/${id}/clone?new_version=${newVersion}`, {}),
  advance: (id: string) => apiClient.post<BOMSummary>(`/bom/${id}/advance`, {}),
  archive: (id: string) => apiClient.post<BOMSummary>(`/bom/${id}/archive`, {}),

  // Lines
  addLine:    (bomId: string, body: Partial<BOMLineOut>) => apiClient.post<BOMLineOut>(`/bom/${bomId}/lines`, body),
  listLines:  (bomId: string) => apiClient.get<BOMLineOut[]>(`/bom/${bomId}/lines`),
  updateLine: (lineId: string, body: Partial<BOMLineOut>) => apiClient.patch<BOMLineOut>(`/bom/lines/${lineId}`, body),
  deleteLine: (lineId: string) => apiClient.delete(`/bom/lines/${lineId}`),

  // Explosion
  explode: (id: string, targetQty?: number) =>
    apiClient.get<ExplosionResult>(`/bom/${id}/explode${targetQty ? `?target_qty=${targetQty}` : ""}`),

  // Scaling
  scale: (id: string, targetQty: number) =>
    apiClient.post<ScalingResult>(`/bom/${id}/scale`, { target_qty: targetQty }),

  // Costing
  costing: (id: string) => apiClient.get<CostingResult>(`/bom/${id}/costing`),

  // Compliance
  compliance: (id: string) => apiClient.get<ComplianceSummary>(`/bom/${id}/compliance-summary`),

  // Compare
  compare: (id: string, otherId: string) => apiClient.get<Record<string, unknown>>(`/bom/${id}/compare/${otherId}`),

  // AI
  runAI:    (id: string) => apiClient.post<{ total: number }>(`/bom/${id}/run-ai`, {}),
  listAI:   (id: string) => apiClient.get<BOMAIRecOut[]>(`/bom/${id}/ai-recommendations`),
  actionAI: (recId: string, status: BOMRecStatus) =>
    apiClient.post<BOMAIRecOut>(`/bom/ai-recommendations/${recId}/action`, { status }),

  // Yield configs
  addYield:    (id: string, body: Partial<YieldConfigOut>) => apiClient.post<YieldConfigOut>(`/bom/${id}/yield-configs`, body),
  listYield:   (id: string) => apiClient.get<YieldConfigOut[]>(`/bom/${id}/yield-configs`),

  // Substitute groups
  createGroup:  (body: { group_name: string; policy: string; notes?: string }) =>
    apiClient.post<SubstGroupOut>("/bom/substitute-groups", body),
  listGroups:   () => apiClient.get<SubstGroupOut[]>("/bom/substitute-groups"),
  addSubstitute:(body: Partial<SubstituteOut & { group_id: string }>) =>
    apiClient.post<SubstituteOut>("/bom/substitutes", body),

  // Conversion profiles
  createConversion: (body: Partial<ConversionProfileOut>) =>
    apiClient.post<ConversionProfileOut>("/bom/conversion-profiles", body),
  listConversions:  () => apiClient.get<ConversionProfileOut[]>("/bom/conversion-profiles"),
  calcConversion:   (profileId: string, sourceQty: number, sourceUom?: string) =>
    apiClient.post<ConversionCalcResult>(
      `/bom/conversion-profiles/${profileId}/calculate?source_qty=${sourceQty}${sourceUom ? `&source_uom=${sourceUom}` : ""}`,
      {}
    ),
};
