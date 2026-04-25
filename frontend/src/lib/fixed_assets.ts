import axios from "axios";

const API = "/api/v1/fixed-assets";

// ── Enums ──────────────────────────────────────────────────────────────────────

export type DepreciationMethod = "STRAIGHT_LINE" | "DECLINING_BALANCE" | "UNITS_OF_PRODUCTION" | "MANUAL";
export type DepreciationFrequency = "MONTHLY" | "QUARTERLY" | "YEARLY";
export type FAAssetStatus = "DRAFT" | "ACTIVE" | "SUSPENDED" | "IMPAIRED" | "DISPOSED" | "RETIRED" | "ARCHIVED";
export type ScheduleStatus = "PLANNED" | "POSTED" | "REVERSED" | "ADJUSTED";
export type AssetEventType =
  | "ACQUISITION" | "CAPITALIZATION" | "TRANSFER" | "REVALUATION" | "IMPAIRMENT"
  | "REPAIR_CAPITALIZATION" | "DEPRECIATION" | "DISPOSAL" | "WRITEOFF"
  | "RETIREMENT" | "SUSPENSION" | "REACTIVATION" | "LEGACY_IMPORT";
export type DisposalMethod = "SALE" | "RETIREMENT" | "SCRAP" | "WRITEOFF";
export type FAIAgentType = "RISK_MONITOR" | "DEPRECIATION_REVIEW" | "CAPITALIZATION_CHECKER";
export type FAIRecStatus = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

// ── Interfaces ─────────────────────────────────────────────────────────────────

export interface FAAssetCategory {
  id: string;
  category_code: string;
  category_name: string;
  default_depreciation_method: DepreciationMethod;
  default_useful_life_months: number | null;
  default_salvage_value_pct: number | null;
  capitalization_threshold: number | null;
  depreciation_start_rule: string;
  asset_account: string | null;
  accum_depreciation_account: string | null;
  depreciation_expense_account: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export interface FAFixedAsset {
  id: string;
  asset_code: string;
  asset_name: string;
  asset_category_id: string;
  category_name: string | null;
  asset_type: string | null;
  serial_no: string | null;
  asset_tag_no: string | null;
  acquisition_date: string | null;
  in_service_date: string | null;
  capitalization_date: string | null;
  depreciation_start_date: string | null;
  depreciation_end_date: string | null;
  original_cost: number;
  currency: string;
  local_currency_cost: number;
  salvage_value: number;
  depreciable_base: number;
  useful_life_months: number | null;
  depreciation_method: DepreciationMethod;
  depreciation_frequency: DepreciationFrequency;
  declining_balance_rate: number | null;
  accumulated_depreciation: number;
  net_book_value: number;
  last_depreciation_date: string | null;
  status: FAAssetStatus;
  location: string | null;
  plant: string | null;
  department: string | null;
  cost_center: string | null;
  condition_status: string | null;
  is_legacy_import: boolean;
  notes: string | null;
  created_at: string;
}

export interface FADepreciationScheduleRow {
  id: string;
  asset_id: string;
  period_start: string;
  period_end: string;
  scheduled_amount: number;
  posted_amount: number | null;
  posting_date: string | null;
  schedule_status: ScheduleStatus;
  opening_nbv: number;
  closing_nbv: number;
  actual_production_units: number | null;
}

export interface FAAssetEvent {
  id: string;
  asset_id: string;
  event_type: AssetEventType;
  event_date: string;
  amount: number | null;
  nbv_before: number | null;
  nbv_after: number | null;
  reason: string | null;
  notes: string | null;
  created_at: string;
}

export interface FAComponent {
  id: string;
  parent_asset_id: string;
  component_name: string;
  component_cost: number;
  salvage_value: number;
  useful_life_months: number | null;
  depreciation_method: DepreciationMethod;
  in_service_date: string | null;
  accumulated_depreciation: number;
  net_book_value: number;
  is_active: boolean;
}

export interface FADisposal {
  id: string;
  asset_id: string;
  disposal_method: DisposalMethod;
  disposal_date: string;
  sale_proceeds: number | null;
  nbv_at_disposal: number;
  cost_at_disposal: number;
  accum_depr_at_disposal: number;
  gain_loss: number;
  reason: string | null;
  created_at: string;
}

export interface FAAIRecommendation {
  id: string;
  asset_id: string | null;
  agent_type: FAIAgentType;
  status: FAIRecStatus;
  title: string;
  detail: string;
  severity: string | null;
  action_taken: string | null;
  created_at: string;
}

export interface FADashboardSummary {
  total_assets: number;
  active_assets: number;
  total_nbv: number;
  total_cost: number;
  total_accumulated_depreciation: number;
  pending_depreciation_lines: number;
  ai_pending_recommendations: number;
}

export interface FANBVReportRow {
  asset_id: string;
  asset_code: string;
  asset_name: string;
  category: string;
  cost_center: string | null;
  original_cost: number;
  accumulated_depreciation: number;
  net_book_value: number;
  status: string;
  as_of_date: string;
}

export interface FADeprPostResult {
  total_assets: number;
  total_posted: number;
  total_amount: number;
  failed: string[];
  dry_run: boolean;
}

// ── API Client ─────────────────────────────────────────────────────────────────

const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);

export const faApi = {
  // Dashboard
  getDashboard: () => r<FADashboardSummary>(axios.get(`${API}/dashboard/summary`)),

  // Categories
  getCategories: (activeOnly = true) =>
    r<FAAssetCategory[]>(axios.get(`${API}/categories`, { params: { active_only: activeOnly } })),
  createCategory: (data: Partial<FAAssetCategory>) =>
    r<FAAssetCategory>(axios.post(`${API}/categories`, data)),
  updateCategory: (id: string, data: Partial<FAAssetCategory>) =>
    r<FAAssetCategory>(axios.patch(`${API}/categories/${id}`, data)),

  // Assets
  listAssets: (params?: {
    status?: FAAssetStatus; category_id?: string; cost_center?: string; search?: string;
  }) => r<FAFixedAsset[]>(axios.get(API, { params })),
  getAsset: (id: string) => r<FAFixedAsset>(axios.get(`${API}/${id}`)),
  createAsset: (data: Partial<FAFixedAsset>) => r<FAFixedAsset>(axios.post(API, data)),
  updateAsset: (id: string, data: Partial<FAFixedAsset>) =>
    r<FAFixedAsset>(axios.patch(`${API}/${id}`, data)),

  // Lifecycle actions
  capitalize: (id: string, data: { capitalization_date: string; in_service_date?: string; notes?: string }) =>
    r<FAFixedAsset>(axios.post(`${API}/${id}/capitalize`, data)),
  transfer: (id: string, data: object) =>
    r<FAAssetEvent>(axios.post(`${API}/${id}/transfer`, data)),
  revalue: (id: string, data: object) =>
    r<FAAssetEvent>(axios.post(`${API}/${id}/revalue`, data)),
  impair: (id: string, data: object) =>
    r<FAAssetEvent>(axios.post(`${API}/${id}/impair`, data)),
  dispose: (id: string, data: object) =>
    r<FADisposal>(axios.post(`${API}/${id}/dispose`, data)),

  // Depreciation
  getSchedule: (id: string, statusFilter?: ScheduleStatus) =>
    r<FADepreciationScheduleRow[]>(
      axios.get(`${API}/${id}/depreciation-schedule`, { params: { status_filter: statusFilter } })
    ),
  generateSchedule: (data: { asset_ids?: string[]; through_date: string }) =>
    r<{ assets_processed: number; lines_generated: number }>(
      axios.post(`${API}/depreciation/generate`, data)
    ),
  postDepreciation: (data: {
    period_start: string; period_end: string; asset_ids?: string[]; dry_run?: boolean;
  }) => r<FADeprPostResult>(axios.post(`${API}/depreciation/post`, data)),

  // Events / history
  getEvents: (id: string) => r<FAAssetEvent[]>(axios.get(`${API}/${id}/events`)),

  // Components
  getComponents: (id: string) => r<FAComponent[]>(axios.get(`${API}/${id}/components`)),
  addComponent: (id: string, data: object) =>
    r<FAComponent>(axios.post(`${API}/${id}/components`, data)),

  // Legacy import
  importLegacy: (data: object) =>
    r<{ total: number; succeeded: number; failed: string[] }>(axios.post(`${API}/import-legacy`, data)),

  // Reports
  getNBVReport: (params?: { as_of_date?: string; category_id?: string; cost_center?: string }) =>
    r<FANBVReportRow[]>(axios.get(`${API}/reports/nbv`, { params })),
  getRegister: (status?: FAAssetStatus) =>
    r<FAFixedAsset[]>(axios.get(`${API}/reports/register`, { params: { status } })),

  // AI
  getAIRecs: (status?: FAIRecStatus) =>
    r<FAAIRecommendation[]>(axios.get(`${API}/ai/recommendations`, { params: { status } })),
  runAIAgents: () => r<{ recommendations_generated: number }>(axios.post(`${API}/ai/run-agents`)),
  ackAIRec: (id: string, data: { status: FAIRecStatus; action_taken?: string }) =>
    r<FAAIRecommendation>(axios.patch(`${API}/ai/recommendations/${id}`, data)),
};

// ── Formatting helpers ─────────────────────────────────────────────────────────

export const fmtCurrency = (v: number, currency = "KES") =>
  `${currency} ${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const STATUS_BADGE: Record<FAAssetStatus, string> = {
  DRAFT:     "bg-gray-100 text-gray-600",
  ACTIVE:    "bg-green-100 text-green-700",
  SUSPENDED: "bg-yellow-100 text-yellow-700",
  IMPAIRED:  "bg-orange-100 text-orange-700",
  DISPOSED:  "bg-red-100 text-red-700",
  RETIRED:   "bg-purple-100 text-purple-700",
  ARCHIVED:  "bg-gray-100 text-gray-500",
};

export const DEPR_METHOD_LABEL: Record<DepreciationMethod, string> = {
  STRAIGHT_LINE:       "Straight-Line",
  DECLINING_BALANCE:   "Declining Balance",
  UNITS_OF_PRODUCTION: "Units of Production",
  MANUAL:              "Manual",
};

export const EVENT_COLOR: Record<AssetEventType, string> = {
  ACQUISITION:          "text-blue-600",
  CAPITALIZATION:       "text-green-600",
  TRANSFER:             "text-indigo-600",
  REVALUATION:          "text-purple-600",
  IMPAIRMENT:           "text-orange-600",
  REPAIR_CAPITALIZATION:"text-teal-600",
  DEPRECIATION:         "text-gray-600",
  DISPOSAL:             "text-red-600",
  WRITEOFF:             "text-red-700",
  RETIREMENT:           "text-red-500",
  SUSPENSION:           "text-yellow-600",
  REACTIVATION:         "text-green-500",
  LEGACY_IMPORT:        "text-cyan-600",
};
