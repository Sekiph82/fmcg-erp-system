import { apiClient } from "@/lib/api";

const BASE = "/api/v1/contracts";

export type ContractType =
  | "CUSTOMER_SALES" | "DISTRIBUTOR" | "SUPPLIER" | "REBATE"
  | "VOLUME_INCENTIVE" | "LISTING_DISPLAY" | "SERVICE_FEE" | "FRAMEWORK";

export type PartyType = "CUSTOMER" | "DISTRIBUTOR" | "SUPPLIER";

export type ContractStatus =
  | "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "ACTIVE"
  | "EXPIRED" | "TERMINATED" | "ARCHIVED";

export type TermType =
  | "PRICE" | "REBATE" | "DISCOUNT" | "VOLUME_TARGET"
  | "SERVICE_FEE" | "PENALTY" | "PAYMENT_TERMS" | "OTHER";

export interface ContractTerm {
  id: string;
  contract_id: string;
  term_type: TermType;
  item_id?: string;
  value_type: string;
  value: number;
  min_threshold?: number;
  max_threshold?: number;
  valid_from?: string;
  valid_to?: string;
  active_flag: boolean;
  notes?: string;
}

export interface ContractRebate {
  id: string;
  contract_id: string;
  rebate_name?: string;
  rebate_type: string;
  calculation_basis: string;
  item_id?: string;
  threshold?: number;
  rebate_pct?: number;
  rebate_amount?: number;
  settlement_frequency: string;
  accrued_amount: number;
  settled_amount: number;
  active_flag: boolean;
  notes?: string;
}

export interface ContractPerformance {
  id: string;
  contract_id: string;
  period: string;
  target_value?: number;
  actual_value?: number;
  achievement_pct?: number;
  rebate_earned?: number;
  status: string;
  notes?: string;
  created_at: string;
}

export interface ContractVersion {
  id: string;
  contract_id: string;
  version_no: number;
  change_summary?: string;
  effective_date?: string;
  approved_by?: string;
  created_at: string;
}

export interface ContractApproval {
  id: string;
  contract_id: string;
  action: string;
  actioned_by?: string;
  comments?: string;
  created_at: string;
}

export interface Contract {
  id: string;
  contract_code: string;
  contract_name: string;
  contract_type: ContractType;
  party_type: PartyType;
  party_id: string;
  start_date: string;
  end_date?: string;
  status: ContractStatus;
  currency: string;
  payment_terms_id?: string;
  price_list_id?: string;
  auto_renew: boolean;
  renewal_notice_days: number;
  linked_promo_ids?: string[];
  linked_tpm_plan_id?: string;
  notes?: string;
  created_by?: string;
  approved_by?: string;
  approved_at?: string;
  current_version: number;
  created_at: string;
  updated_at: string;
  terms: ContractTerm[];
  rebates: ContractRebate[];
}

export interface CTAIRec {
  id: string;
  agent_type: string;
  status: string;
  severity: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  contract_id?: string;
  party_id?: string;
  created_at: string;
}

// ── Colors ────────────────────────────────────────────────────────────────────

export const STATUS_COLORS: Record<ContractStatus, string> = {
  DRAFT:        "bg-slate-500/20 text-slate-400",
  UNDER_REVIEW: "bg-blue-500/20 text-blue-300",
  APPROVED:     "bg-indigo-500/20 text-indigo-300",
  ACTIVE:       "bg-emerald-500/20 text-emerald-300",
  EXPIRED:      "bg-red-500/20 text-red-300",
  TERMINATED:   "bg-red-700/20 text-red-400",
  ARCHIVED:     "bg-slate-700/20 text-slate-500",
};

export const PARTY_COLORS: Record<PartyType, string> = {
  CUSTOMER:    "bg-blue-500/20 text-blue-300",
  DISTRIBUTOR: "bg-purple-500/20 text-purple-300",
  SUPPLIER:    "bg-amber-500/20 text-amber-300",
};

export const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
  CUSTOMER_SALES:   "Customer Sales",
  DISTRIBUTOR:      "Distributor Agreement",
  SUPPLIER:         "Supplier Contract",
  REBATE:           "Rebate Agreement",
  VOLUME_INCENTIVE: "Volume Incentive",
  LISTING_DISPLAY:  "Listing / Display",
  SERVICE_FEE:      "Service / Fee",
  FRAMEWORK:        "Framework Agreement",
};

export const SEVERITY_COLORS: Record<string, string> = {
  INFO:     "bg-blue-500/20 text-blue-300",
  WARNING:  "bg-amber-500/20 text-amber-300",
  CRITICAL: "bg-red-500/20 text-red-300",
};

// ── API ───────────────────────────────────────────────────────────────────────

export const contractsApi = {
  list: (params?: { party_type?: string; status?: string; party_id?: string; skip?: number; limit?: number }) =>
    apiClient.get<Contract[]>(BASE, { params }).then((r) => r.data),
  create: (data: any) => apiClient.post<Contract>(BASE, data).then((r) => r.data),
  get: (id: string) => apiClient.get<Contract>(`${BASE}/${id}`).then((r) => r.data),
  update: (id: string, data: any) => apiClient.patch<Contract>(`${BASE}/${id}`, data).then((r) => r.data),

  submit: (id: string, comments?: string) =>
    apiClient.post<Contract>(`${BASE}/${id}/submit`, { comments }).then((r) => r.data),
  approve: (id: string, comments?: string) =>
    apiClient.post<Contract>(`${BASE}/${id}/approve`, { comments }).then((r) => r.data),
  reject: (id: string, comments?: string) =>
    apiClient.post<Contract>(`${BASE}/${id}/reject`, { comments }).then((r) => r.data),
  activate: (id: string) =>
    apiClient.post<Contract>(`${BASE}/${id}/activate`, {}).then((r) => r.data),
  terminate: (id: string, reason: string) =>
    apiClient.post<Contract>(`${BASE}/${id}/terminate`, { reason }).then((r) => r.data),
  archive: (id: string) =>
    apiClient.post<Contract>(`${BASE}/${id}/archive`, {}).then((r) => r.data),

  addTerm: (id: string, data: Partial<ContractTerm>) =>
    apiClient.post<ContractTerm>(`${BASE}/${id}/terms`, data).then((r) => r.data),
  deleteTerm: (termId: string) =>
    apiClient.delete(`${BASE}/terms/${termId}`).then((r) => r.data),

  addRebate: (id: string, data: Partial<ContractRebate>) =>
    apiClient.post<ContractRebate>(`${BASE}/${id}/rebates`, data).then((r) => r.data),

  listPerformance: (id: string) =>
    apiClient.get<ContractPerformance[]>(`${BASE}/${id}/performance`).then((r) => r.data),
  upsertPerformance: (id: string, data: any) =>
    apiClient.post<ContractPerformance>(`${BASE}/${id}/performance`, data).then((r) => r.data),

  history: (id: string) => apiClient.get<ContractVersion[]>(`${BASE}/${id}/history`).then((r) => r.data),
  approvals: (id: string) => apiClient.get<ContractApproval[]>(`${BASE}/${id}/approvals`).then((r) => r.data),

  reportSummary: () =>
    apiClient.get<{ total: number; active: number; expiring_30_days: number; draft: number; under_review: number }>(
      `${BASE}/reports/summary`
    ).then((r) => r.data),
  reportExpiring: (days = 60) =>
    apiClient.get<Contract[]>(`${BASE}/reports/expiring`, { params: { days } }).then((r) => r.data),
  reportPerformance: () =>
    apiClient.get<{ contract_id: string; avg_achievement_pct: number; total_rebate_earned: number; periods: number }[]>(
      `${BASE}/reports/performance`
    ).then((r) => r.data),

  runAI: () => apiClient.post<CTAIRec[]>(`${BASE}/ai/run`, {}).then((r) => r.data),
  aiRecs: (params?: { agent_type?: string; status?: string }) =>
    apiClient.get<CTAIRec[]>(`${BASE}/ai/recommendations`, { params }).then((r) => r.data),
  ackRec: (id: string, status: string) =>
    apiClient.patch<CTAIRec>(`${BASE}/ai/recommendations/${id}`, { status }).then((r) => r.data),
};
