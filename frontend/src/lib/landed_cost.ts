import { apiClient } from "@/lib/api";

// ── Enums / Types ─────────────────────────────────────────────────────────────

export type LCStatus = "DRAFT" | "VALIDATED" | "POSTED" | "CANCELLED";

export type LandedCostType =
  | "FREIGHT_SEA" | "FREIGHT_AIR" | "FREIGHT_LAND"
  | "CUSTOMS_DUTY" | "IMPORT_TAX" | "INSURANCE"
  | "PORT_HANDLING" | "CLEARING_AGENT" | "INLAND_TRANSPORT"
  | "STORAGE" | "INSPECTION" | "DEMURRAGE" | "DETENTION" | "OTHER";

export type LCAllocationMethod =
  | "BY_QUANTITY" | "BY_WEIGHT" | "BY_VOLUME" | "BY_VALUE" | "EQUAL_SPLIT" | "CUSTOM";

export type LCReferenceType = "GRN" | "SHIPMENT" | "PO" | "MANUAL";
export type LCAIAgentType = "COST_ANALYZER" | "ROUTE_OPTIMIZER" | "VARIANCE_DETECTOR";
export type LCAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED";

// ── Interfaces ────────────────────────────────────────────────────────────────

export interface LandedCostLine {
  id: string;
  header_id: string;
  cost_type: LandedCostType;
  description: string | null;
  vendor_name: string | null;
  amount_fc: number;
  currency_code: string;
  exchange_rate: number;
  amount_base: number;
  allocation_method: LCAllocationMethod | null;
  is_included_in_valuation: boolean;
  account_code: string | null;
  remarks: string | null;
}

export interface LandedCostGRNLink {
  id: string;
  header_id: string;
  grn_id: string;
  grn_no: string | null;
  po_no: string | null;
  grn_value_base: number | null;
  grn_total_qty: number | null;
  grn_total_weight: number | null;
  grn_total_volume: number | null;
  allocation_share: number | null;
}

export interface LandedCostAllocationLine {
  id: string;
  header_id: string;
  lc_line_id: string;
  grn_id: string | null;
  grn_line_id: string | null;
  material_id: string | null;
  material_name: string | null;
  lot_no: string | null;
  received_qty: number | null;
  purchase_value: number | null;
  allocation_share: number | null;
  allocated_amount: number;
  per_unit_lc_cost: number | null;
  is_posted: boolean;
}

export interface LandedCostSummary {
  id: string;
  lc_no: string;
  reference_type: LCReferenceType;
  vendor_name: string | null;
  bill_no: string | null;
  bill_date: string | null;
  currency_code: string;
  exchange_rate: number;
  total_lc_amount_fc: number;
  total_lc_amount_base: number;
  allocation_method: LCAllocationMethod;
  status: LCStatus;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LandedCostOut extends LandedCostSummary {
  posted_by: string | null;
  notes: string | null;
  cost_lines: LandedCostLine[];
  grn_links: LandedCostGRNLink[];
  allocation_lines: LandedCostAllocationLine[];
}

export interface LCAIRec {
  id: string;
  header_id: string | null;
  agent_type: LCAIAgentType;
  status: LCAIRecStatus;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  suggested_action: string | null;
  confidence_score: number | null;
  actioned_at: string | null;
  created_at: string;
}

export interface LCDashboard {
  total_documents: number;
  draft_count: number;
  validated_count: number;
  posted_count: number;
  cancelled_count: number;
  total_lc_cost_mtd: number;
  total_lc_cost_ytd: number;
  pending_ai_recs: number;
  top_cost_types: { cost_type: string; total: number }[];
  recent_documents: LandedCostSummary[];
}

// ── Color / Label maps ────────────────────────────────────────────────────────

export const LC_STATUS_COLOR: Record<LCStatus, string> = {
  DRAFT:     "bg-gray-100 text-gray-600",
  VALIDATED: "bg-blue-100 text-blue-700",
  POSTED:    "bg-green-100 text-green-700",
  CANCELLED: "bg-red-100 text-red-600",
};

export const COST_TYPE_LABEL: Record<LandedCostType, string> = {
  FREIGHT_SEA:      "Sea Freight",
  FREIGHT_AIR:      "Air Freight",
  FREIGHT_LAND:     "Land Freight",
  CUSTOMS_DUTY:     "Customs Duty",
  IMPORT_TAX:       "Import Tax",
  INSURANCE:        "Insurance",
  PORT_HANDLING:    "Port Handling",
  CLEARING_AGENT:   "Clearing Agent",
  INLAND_TRANSPORT: "Inland Transport",
  STORAGE:          "Storage",
  INSPECTION:       "Inspection",
  DEMURRAGE:        "Demurrage",
  DETENTION:        "Detention",
  OTHER:            "Other",
};

export const COST_TYPE_COLOR: Partial<Record<LandedCostType, string>> = {
  FREIGHT_SEA:      "bg-blue-100 text-blue-700",
  FREIGHT_AIR:      "bg-sky-100 text-sky-700",
  FREIGHT_LAND:     "bg-cyan-100 text-cyan-700",
  CUSTOMS_DUTY:     "bg-orange-100 text-orange-700",
  IMPORT_TAX:       "bg-red-100 text-red-700",
  INSURANCE:        "bg-teal-100 text-teal-700",
  PORT_HANDLING:    "bg-indigo-100 text-indigo-700",
  CLEARING_AGENT:   "bg-purple-100 text-purple-700",
  INLAND_TRANSPORT: "bg-emerald-100 text-emerald-700",
  STORAGE:          "bg-yellow-100 text-yellow-700",
  INSPECTION:       "bg-lime-100 text-lime-700",
  DEMURRAGE:        "bg-rose-100 text-rose-700",
  DETENTION:        "bg-pink-100 text-pink-700",
  OTHER:            "bg-gray-100 text-gray-600",
};

export const ALLOC_METHOD_LABEL: Record<LCAllocationMethod, string> = {
  BY_QUANTITY:  "By Quantity",
  BY_WEIGHT:    "By Weight",
  BY_VOLUME:    "By Volume",
  BY_VALUE:     "By Value",
  EQUAL_SPLIT:  "Equal Split",
  CUSTOM:       "Custom",
};

export const AI_AGENT_LABEL: Record<LCAIAgentType, string> = {
  COST_ANALYZER:     "Cost Analyzer",
  ROUTE_OPTIMIZER:   "Route Optimizer",
  VARIANCE_DETECTOR: "Variance Detector",
};

export const AI_REC_STATUS_COLOR: Record<LCAIRecStatus, string> = {
  PENDING:  "bg-yellow-100 text-yellow-700",
  ACCEPTED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

export function fmtCurrency(val: number | null | undefined, code = "USD"): string {
  const n = val == null ? 0 : Number(val);
  return `${code} ${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ── API ───────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/landed-cost";

export const lcApi = {
  // Dashboard
  getDashboard: () => apiClient.get<LCDashboard>(`${BASE}/dashboard`).then((r) => r.data),

  // CRUD
  list: (params?: { status?: string }) => {
    const qs = params?.status ? `?status=${params.status}` : "";
    return apiClient.get<LandedCostSummary[]>(`${BASE}${qs}`).then((r) => r.data);
  },
  create: (body: Record<string, unknown>) => apiClient.post<LandedCostOut>(BASE, body).then((r) => r.data),
  get: (id: string) => apiClient.get<LandedCostOut>(`${BASE}/${id}`).then((r) => r.data),
  update: (id: string, body: Record<string, unknown>) => apiClient.patch<LandedCostOut>(`${BASE}/${id}`, body).then((r) => r.data),

  // Cost lines
  addCostLine: (headerId: string, body: Record<string, unknown>) =>
    apiClient.post<LandedCostOut>(`${BASE}/${headerId}/lines`, body).then((r) => r.data),

  // GRN links
  addGRNLink: (headerId: string, body: Record<string, unknown>) =>
    apiClient.post<LandedCostOut>(`${BASE}/${headerId}/grn-links`, body).then((r) => r.data),

  // Allocation
  allocate: (headerId: string) => apiClient.post<LandedCostOut>(`${BASE}/${headerId}/allocate`, {}).then((r) => r.data),

  // Post / Cancel
  post: (headerId: string) => apiClient.post<LandedCostOut>(`${BASE}/${headerId}/post`, {}).then((r) => r.data),
  cancel: (headerId: string) => apiClient.post<LandedCostOut>(`${BASE}/${headerId}/cancel`, {}).then((r) => r.data),

  // Reports
  reportCostByType: (params?: { date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).filter(([, v]) => v) as [string, string][]
    ).toString();
    return apiClient.get<Record<string, unknown>[]>(`${BASE}/reports/cost-by-type${qs ? `?${qs}` : ""}`).then((r) => r.data);
  },
  reportAllocationByMaterial: (params?: { date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).filter(([, v]) => v) as [string, string][]
    ).toString();
    return apiClient.get<Record<string, unknown>[]>(`${BASE}/reports/allocation-by-material${qs ? `?${qs}` : ""}`).then((r) => r.data);
  },

  // AI
  runAI: () => apiClient.post<{ recommendations_created: number }>(`${BASE}/ai/run`, {}).then((r) => r.data),
  runAIForDoc: (headerId: string) => apiClient.post<{ recommendations_created: number }>(`${BASE}/${headerId}/ai/run`, {}).then((r) => r.data),
  listAIRecs: (params?: { status?: string }) => {
    const qs = params?.status ? `?status=${params.status}` : "";
    return apiClient.get<LCAIRec[]>(`${BASE}/ai/recs${qs}`).then((r) => r.data);
  },
  listAIRecsForDoc: (headerId: string) =>
    apiClient.get<LCAIRec[]>(`${BASE}/${headerId}/ai/recs`).then((r) => r.data),
  actionAIRec: (recId: string, status: "ACCEPTED" | "REJECTED") =>
    apiClient.post<LCAIRec>(`${BASE}/ai/recs/${recId}/action`, { status }).then((r) => r.data),
};
