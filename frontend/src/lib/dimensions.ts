import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);
const ax = axios.create({ baseURL: API });

// ── Enums & Types ──────────────────────────────────────────────────────────────

export type DimensionScope = "FINANCIAL" | "OPERATIONAL" | "BOTH";
export type CostCenterType =
  | "PRODUCTION" | "WAREHOUSE" | "ADMIN" | "SALES"
  | "UTILITIES" | "MAINTENANCE" | "CORPORATE" | "PROJECT" | "OTHER";
export type DimSourceType = "MANUAL" | "DEFAULT" | "INHERITED" | "RULE_BASED" | "SYSTEM_GENERATED";
export type AllocationBasis =
  | "FIXED_PCT" | "HEADCOUNT" | "FLOOR_AREA" | "MACHINE_HOURS"
  | "LABOR_HOURS" | "REVENUE" | "QTY" | "MANUAL" | "CUSTOM_FORMULA";
export type AllocationFrequency = "MONTHLY" | "QUARTERLY" | "MANUAL";
export type AllocationRunStatus = "DRAFT" | "PREVIEWED" | "POSTED" | "REVERSED";
export type ValidationSeverity = "WARN" | "BLOCK";
export type DimAIAgentType = "COMPLETENESS_MONITOR" | "ALLOCATION_OPTIMIZER" | "PROFITABILITY_LENS";
export type DimAIRecStatus = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

// ── Dimension Type ─────────────────────────────────────────────────────────────

export interface DimType {
  id: string;
  type_code: string;
  type_name: string;
  dimension_scope: DimensionScope;
  hierarchy_enabled: boolean;
  is_mandatory: boolean;
  active: boolean;
  notes?: string;
  value_count: number;
}

// ── Dimension Value ────────────────────────────────────────────────────────────

export interface DimValue {
  id: string;
  dim_type_id: string;
  dim_code: string;
  dim_name: string;
  parent_id?: string;
  level_no: number;
  active: boolean;
  start_date?: string;
  end_date?: string;
  notes?: string;
  dim_type_name?: string;
  parent_name?: string;
  children_count: number;
}

// ── Cost Center ────────────────────────────────────────────────────────────────

export interface CostCenter {
  id: string;
  cost_center_code: string;
  cost_center_name: string;
  parent_id?: string;
  cost_center_type: CostCenterType;
  department?: string;
  active: boolean;
  start_date?: string;
  end_date?: string;
  notes?: string;
  parent_name?: string;
  children_count: number;
}

// ── Transaction Dimension Tag ──────────────────────────────────────────────────

export interface TransactionDimTag {
  id: string;
  transaction_type: string;
  transaction_id: string;
  line_id?: string;
  dim_type_id: string;
  dim_value_id: string;
  source_type: DimSourceType;
  locked: boolean;
  dim_type_name?: string;
  dim_value_name?: string;
}

// ── Validation Rule ────────────────────────────────────────────────────────────

export interface DimValidationRule {
  id: string;
  rule_name: string;
  transaction_type?: string;
  gl_account_pattern?: string;
  module?: string;
  dim_type_id: string;
  severity: ValidationSeverity;
  active: boolean;
  dim_type_name?: string;
}

// ── Default Rule ───────────────────────────────────────────────────────────────

export interface DimDefaultRule {
  id: string;
  rule_name: string;
  transaction_type: string;
  source_field?: string;
  source_field_value?: string;
  dim_type_id: string;
  dim_value_id: string;
  priority: number;
  active: boolean;
  dim_type_name?: string;
  dim_value_name?: string;
}

// ── Allocation Rule ────────────────────────────────────────────────────────────

export interface AllocationRuleLine {
  id: string;
  target_dim_value_id: string;
  target_dim_value_name?: string;
  fixed_pct?: number;
  weight_value?: number;
  active: boolean;
}

export interface AllocationRule {
  id: string;
  rule_code: string;
  rule_name: string;
  source_dim_type_id: string;
  source_dim_value_id: string;
  target_dim_type_id: string;
  allocation_basis: AllocationBasis;
  frequency: AllocationFrequency;
  gl_account_cost_pool?: string;
  active: boolean;
  source_dim_value_name?: string;
  target_dim_type_name?: string;
  lines: AllocationRuleLine[];
}

// ── Allocation Run ─────────────────────────────────────────────────────────────

export interface AllocationRunLine {
  id: string;
  target_dim_value_id: string;
  target_dim_value_name?: string;
  pct_applied?: number;
  allocated_amount?: number;
  journal_entry_id?: string;
}

export interface AllocationRun {
  id: string;
  rule_id: string;
  rule_name?: string;
  period_start: string;
  period_end: string;
  dry_run: boolean;
  status: AllocationRunStatus;
  source_pool_amount: number;
  total_allocated: number;
  run_notes?: string;
  lines: AllocationRunLine[];
}

// ── Reclassification ───────────────────────────────────────────────────────────

export interface Reclassification {
  id: string;
  transaction_type: string;
  transaction_id: string;
  dim_type_id: string;
  dim_type_name?: string;
  old_dim_value_id?: string;
  old_dim_value_name?: string;
  new_dim_value_id: string;
  new_dim_value_name?: string;
  reason: string;
  journal_entry_ref?: string;
  created_at?: string;
}

// ── AI Recommendations ─────────────────────────────────────────────────────────

export interface DimAIRec {
  id: string;
  agent_type: DimAIAgentType;
  title: string;
  detail?: string;
  severity: string;
  status: DimAIRecStatus;
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export interface DimDashboard {
  total_dim_types: number;
  total_dim_values: number;
  total_cost_centers: number;
  active_allocation_rules: number;
  untagged_transactions_today: number;
  pending_ai_recs: number;
}

// ── Labels ─────────────────────────────────────────────────────────────────────

export const CC_TYPE_LABEL: Record<CostCenterType, string> = {
  PRODUCTION:  "Production",
  WAREHOUSE:   "Warehouse",
  ADMIN:       "Administration",
  SALES:       "Sales",
  UTILITIES:   "Utilities",
  MAINTENANCE: "Maintenance",
  CORPORATE:   "Corporate",
  PROJECT:     "Project",
  OTHER:       "Other",
};

export const ALLOC_BASIS_LABEL: Record<AllocationBasis, string> = {
  FIXED_PCT:      "Fixed %",
  HEADCOUNT:      "Headcount",
  FLOOR_AREA:     "Floor Area",
  MACHINE_HOURS:  "Machine Hours",
  LABOR_HOURS:    "Labor Hours",
  REVENUE:        "Revenue",
  QTY:            "Quantity",
  MANUAL:         "Manual",
  CUSTOM_FORMULA: "Custom Formula",
};

export const AGENT_LABEL: Record<DimAIAgentType, string> = {
  COMPLETENESS_MONITOR: "Completeness Monitor",
  ALLOCATION_OPTIMIZER: "Allocation Optimizer",
  PROFITABILITY_LENS:   "Profitability Lens",
};

export const SEVERITY_BADGE: Record<string, string> = {
  info:     "bg-blue-100 text-blue-700",
  warning:  "bg-yellow-100 text-yellow-700",
  critical: "bg-red-100 text-red-700",
};

// ── API Client ─────────────────────────────────────────────────────────────────

export const dimApi = {
  // Dashboard
  getDashboard: () => r<DimDashboard>(ax.get("/dimensions/dashboard")),

  // Dimension Types
  getTypes: (activeOnly?: boolean) =>
    r<DimType[]>(ax.get("/dimensions/types", { params: { active_only: activeOnly } })),
  createType: (data: Partial<DimType>) =>
    r<DimType>(ax.post("/dimensions/types", data)),
  updateType: (id: string, data: Partial<DimType>) =>
    r<DimType>(ax.patch(`/dimensions/types/${id}`, data)),

  // Dimension Values
  getValues: (dimTypeId?: string, activeOnly?: boolean) =>
    r<DimValue[]>(ax.get("/dimensions/values", { params: { dim_type_id: dimTypeId, active_only: activeOnly } })),
  createValue: (data: Partial<DimValue>) =>
    r<DimValue>(ax.post("/dimensions/values", data)),

  // Cost Centers
  getCostCenters: (activeOnly?: boolean) =>
    r<CostCenter[]>(ax.get("/dimensions/cost-centers", { params: { active_only: activeOnly } })),
  createCostCenter: (data: Partial<CostCenter>) =>
    r<CostCenter>(ax.post("/dimensions/cost-centers", data)),
  updateCostCenter: (id: string, data: Partial<CostCenter>) =>
    r<CostCenter>(ax.patch(`/dimensions/cost-centers/${id}`, data)),

  // Tags
  getTags: (transactionType: string, transactionId: string) =>
    r<TransactionDimTag[]>(ax.get("/dimensions/tags", { params: { transaction_type: transactionType, transaction_id: transactionId } })),
  tagTransaction: (data: Partial<TransactionDimTag>) =>
    r<TransactionDimTag>(ax.post("/dimensions/tags", data)),

  // Validation Rules
  getValidationRules: () => r<DimValidationRule[]>(ax.get("/dimensions/validation-rules")),
  createValidationRule: (data: Partial<DimValidationRule>) =>
    r<DimValidationRule>(ax.post("/dimensions/validation-rules", data)),

  // Default Rules
  getDefaultRules: () => r<DimDefaultRule[]>(ax.get("/dimensions/default-rules")),
  createDefaultRule: (data: Partial<DimDefaultRule>) =>
    r<DimDefaultRule>(ax.post("/dimensions/default-rules", data)),

  // Allocation Rules
  getAllocationRules: () => r<AllocationRule[]>(ax.get("/dimensions/allocation-rules")),
  createAllocationRule: (data: Partial<AllocationRule>) =>
    r<AllocationRule>(ax.post("/dimensions/allocation-rules", data)),

  // Allocation Runs
  getAllocationRuns: (ruleId?: string) =>
    r<AllocationRun[]>(ax.get("/dimensions/allocation-runs", { params: { rule_id: ruleId } })),
  previewAllocation: (data: object) =>
    r<AllocationRun>(ax.post("/dimensions/allocation-runs/preview", data)),
  postAllocation: (data: object) =>
    r<AllocationRun>(ax.post("/dimensions/allocation-runs/post", data)),

  // Reclassification
  getReclassifications: (transactionType?: string) =>
    r<Reclassification[]>(ax.get("/dimensions/reclassifications", { params: { transaction_type: transactionType } })),
  reclassify: (data: object) =>
    r<Reclassification>(ax.post("/dimensions/reclassify", data)),

  // Reports
  getTaggingCompleteness: () =>
    r<any[]>(ax.get("/dimensions/reports/tagging-completeness")),

  // AI
  runAgents: () => r<{ generated: number }>(ax.post("/dimensions/ai/run-agents")),
  getAIRecs: (status?: DimAIRecStatus) =>
    r<DimAIRec[]>(ax.get("/dimensions/ai/recommendations", { params: { status } })),
  ackAIRec: (id: string, data: { status: DimAIRecStatus }) =>
    r<DimAIRec>(ax.patch(`/dimensions/ai/recommendations/${id}`, data)),
};
