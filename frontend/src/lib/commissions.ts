import { apiClient } from "@/lib/api";

const BASE = "/api/v1/commissions";

export type CommissionAppliesTo = "SALES_REP" | "DISTRIBUTOR" | "TEAM";
export type CommissionScope = "GLOBAL" | "CUSTOMER" | "CHANNEL" | "REGION" | "PRODUCT" | "CATEGORY" | "BRAND";
export type RuleStatus = "DRAFT" | "ACTIVE" | "EXPIRED" | "ARCHIVED";
export type CommissionType = "PERCENTAGE" | "FIXED" | "TIERED";
export type TxnStatus = "PENDING" | "APPROVED" | "PAID" | "REJECTED" | "REVERSED";
export type PayoutStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "PAID" | "CANCELLED";

export interface CommissionRuleLine {
  id: string;
  rule_id: string;
  condition_type: string;
  min_threshold?: number;
  max_threshold?: number;
  commission_type: CommissionType;
  commission_value: number;
  target_flag: boolean;
  sort_order: number;
  notes?: string;
}

export interface CommissionRule {
  id: string;
  rule_code: string;
  rule_name: string;
  applies_to: CommissionAppliesTo;
  applicable_scope: CommissionScope;
  scope_ref_id?: string;
  priority: number;
  start_date: string;
  end_date?: string;
  status: RuleStatus;
  contract_id?: string;
  notes?: string;
  created_at: string;
  lines: CommissionRuleLine[];
}

export interface CommissionTarget {
  id: string;
  entity_id: string;
  applies_to: CommissionAppliesTo;
  period: string;
  target_value: number;
  actual_value: number;
  achievement_pct?: number;
  bonus_earned?: number;
  notes?: string;
  created_at: string;
}

export interface CommissionTxn {
  id: string;
  rule_id?: string;
  sales_order_id?: string;
  invoice_id?: string;
  sales_rep_id?: string;
  distributor_id?: string;
  customer_id?: string;
  base_amount: number;
  commission_pct?: number;
  commission_amount: number;
  calculation_date: string;
  period: string;
  status: TxnStatus;
  is_reversal: boolean;
  calc_detail?: Record<string, unknown>;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  notes?: string;
  created_at: string;
}

export interface CommissionAdjustment {
  id: string;
  txn_id: string;
  adjustment_amount: number;
  reason: string;
  approved_by?: string;
  notes?: string;
  created_at: string;
}

export interface CommissionPayout {
  id: string;
  entity_id: string;
  applies_to: CommissionAppliesTo;
  period: string;
  total_commission: number;
  adjustments_total: number;
  net_commission: number;
  paid_amount: number;
  payment_date?: string;
  status: PayoutStatus;
  txn_ids?: string[];
  approved_by?: string;
  notes?: string;
  created_at: string;
}

export interface CMAIRec {
  id: string;
  agent_type: string;
  status: string;
  severity: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  entity_id?: string;
  rule_id?: string;
  created_at: string;
}

// ── Colors ────────────────────────────────────────────────────────────────────

export const RULE_STATUS_COLORS: Record<RuleStatus, string> = {
  DRAFT:    "bg-slate-500/20 text-slate-400",
  ACTIVE:   "bg-emerald-500/20 text-emerald-300",
  EXPIRED:  "bg-red-500/20 text-red-300",
  ARCHIVED: "bg-slate-700/20 text-slate-500",
};

export const TXN_STATUS_COLORS: Record<TxnStatus, string> = {
  PENDING:  "bg-amber-500/20 text-amber-300",
  APPROVED: "bg-blue-500/20 text-blue-300",
  PAID:     "bg-emerald-500/20 text-emerald-300",
  REJECTED: "bg-red-500/20 text-red-300",
  REVERSED: "bg-slate-500/20 text-slate-400",
};

export const PAYOUT_STATUS_COLORS: Record<PayoutStatus, string> = {
  DRAFT:     "bg-slate-500/20 text-slate-400",
  SUBMITTED: "bg-blue-500/20 text-blue-300",
  APPROVED:  "bg-indigo-500/20 text-indigo-300",
  PAID:      "bg-emerald-500/20 text-emerald-300",
  CANCELLED: "bg-red-500/20 text-red-300",
};

export const SEVERITY_COLORS: Record<string, string> = {
  INFO:     "bg-blue-500/20 text-blue-300",
  WARNING:  "bg-amber-500/20 text-amber-300",
  CRITICAL: "bg-red-500/20 text-red-300",
};

export const AGENT_LABELS: Record<string, string> = {
  INCENTIVE_OPTIMIZER: "Incentive Optimizer",
  FRAUD_DETECTION:     "Fraud Detection",
  PERFORMANCE_ADVISOR: "Performance Advisor",
};

// ── API ───────────────────────────────────────────────────────────────────────

export const commissionsApi = {
  // Rules
  listRules: (params?: { applies_to?: string; status?: string }) =>
    apiClient.get<CommissionRule[]>(`${BASE}/rules`, { params }).then((r) => r.data),
  createRule: (data: any) =>
    apiClient.post<CommissionRule>(`${BASE}/rules`, data).then((r) => r.data),
  getRule: (id: string) =>
    apiClient.get<CommissionRule>(`${BASE}/rules/${id}`).then((r) => r.data),
  updateRule: (id: string, data: any) =>
    apiClient.patch<CommissionRule>(`${BASE}/rules/${id}`, data).then((r) => r.data),
  activateRule: (id: string) =>
    apiClient.post<CommissionRule>(`${BASE}/rules/${id}/activate`, {}).then((r) => r.data),

  // Targets
  listTargets: (params?: { entity_id?: string; period?: string }) =>
    apiClient.get<CommissionTarget[]>(`${BASE}/targets`, { params }).then((r) => r.data),
  upsertTarget: (data: any) =>
    apiClient.post<CommissionTarget>(`${BASE}/targets`, data).then((r) => r.data),

  // Calculate
  calculate: (data: any) =>
    apiClient.post<CommissionTxn>(`${BASE}/calculate`, data).then((r) => r.data),

  // Transactions
  listTransactions: (params?: { sales_rep_id?: string; period?: string; status?: string; limit?: number }) =>
    apiClient.get<CommissionTxn[]>(`${BASE}/transactions`, { params }).then((r) => r.data),
  getTransaction: (id: string) =>
    apiClient.get<CommissionTxn>(`${BASE}/transactions/${id}`).then((r) => r.data),
  approveTxn: (id: string, comments?: string) =>
    apiClient.post<CommissionTxn>(`${BASE}/transactions/${id}/approve`, { comments }).then((r) => r.data),
  rejectTxn: (id: string, reason: string) =>
    apiClient.post<CommissionTxn>(`${BASE}/transactions/${id}/reject`, { reason }).then((r) => r.data),
  addAdjustment: (id: string, data: any) =>
    apiClient.post<CommissionAdjustment>(`${BASE}/transactions/${id}/adjustments`, data).then((r) => r.data),

  // Payouts
  listPayouts: (params?: { entity_id?: string; period?: string; status?: string }) =>
    apiClient.get<CommissionPayout[]>(`${BASE}/payouts`, { params }).then((r) => r.data),
  createPayout: (data: any) =>
    apiClient.post<CommissionPayout>(`${BASE}/payouts`, data).then((r) => r.data),
  approvePayout: (id: string) =>
    apiClient.post<CommissionPayout>(`${BASE}/payouts/${id}/approve`, {}).then((r) => r.data),
  markPaid: (id: string, payment_date: string) =>
    apiClient.post<CommissionPayout>(`${BASE}/payouts/${id}/mark-paid`, {}, { params: { payment_date } }).then((r) => r.data),

  // Reports
  reportSummary: () =>
    apiClient.get<{ total_txns: number; pending: number; approved: number; total_commission: number; paid_commission: number }>(
      `${BASE}/reports/summary`
    ).then((r) => r.data),
  reportByPeriod: (period?: string) =>
    apiClient.get<{ period: string; sales_rep_id: string; total_commission: number; txn_count: number }[]>(
      `${BASE}/reports/by-period`, { params: { period } }
    ).then((r) => r.data),

  // AI
  runAI: () => apiClient.post<CMAIRec[]>(`${BASE}/ai/run`, {}).then((r) => r.data),
  aiRecs: (params?: { agent_type?: string; status?: string }) =>
    apiClient.get<CMAIRec[]>(`${BASE}/ai/recommendations`, { params }).then((r) => r.data),
  ackRec: (id: string, status: string) =>
    apiClient.patch<CMAIRec>(`${BASE}/ai/recommendations/${id}`, { status }).then((r) => r.data),
};
