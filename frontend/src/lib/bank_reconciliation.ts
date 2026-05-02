import { apiClient } from "@/lib/api";

const BASE = "/api/v1/bank-reconciliation";

// ─── Enums ────────────────────────────────────────────────────────────────────

export type BRAccountType = "CURRENT" | "SAVINGS" | "MOBILE_MONEY" | "OVERDRAFT";
export type BRImportSource = "CSV" | "OFX" | "MANUAL" | "MPESA" | "API";
export type BRStatementStatus =
  | "DRAFT" | "IMPORTED" | "IN_RECONCILIATION" | "RECONCILED" | "CLOSED" | "LOCKED";
export type BRLineMatchStatus =
  | "UNMATCHED" | "SUGGESTED_MATCH" | "PARTIALLY_MATCHED" | "MATCHED"
  | "IGNORED" | "DUPLICATE_SUSPECTED" | "NEEDS_REVIEW";
export type BRMatchMethod = "AUTO" | "MANUAL" | "SPLIT" | "RULE_BASED";
export type BRERPTransactionType =
  | "AR_PAYMENT" | "AP_PAYMENT" | "PURCHASE_PAYMENT" | "EXPENSE_PAYMENT"
  | "PAYROLL" | "TRANSFER" | "MPESA_COLLECTION" | "MPESA_PAYOUT"
  | "BANK_CHARGE" | "INTEREST" | "REFUND" | "JOURNAL_ENTRY";
export type BRAdjustmentType =
  | "BANK_CHARGE" | "INTEREST" | "ROUNDING" | "FX_DIFFERENCE" | "WRITE_OFF" | "OTHER";
export type BRRuleConditionType =
  | "NARRATION_CONTAINS" | "REFERENCE_STARTS_WITH" | "REFERENCE_CONTAINS"
  | "AMOUNT_EQUALS" | "AMOUNT_RANGE" | "PAYEE_NAME_CONTAINS" | "ACCOUNT_SPECIFIC";
export type BRAIAgentType = "MATCH_CONFIDENCE" | "CASH_ANOMALY" | "RULE_OPTIMIZER";
export type BRAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "DISMISSED";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BRBankAccount {
  id: string;
  bank_name: string;
  branch_name: string | null;
  account_name: string;
  account_number_masked: string | null;
  currency: string;
  country: string;
  account_type: BRAccountType;
  reconciliation_enabled: boolean;
  mobile_money_flag: boolean;
  mpesa_till_or_paybill_no: string | null;
  gl_account_id: string | null;
  cash_account_id: string | null;
  active: boolean;
  notes: string | null;
  created_at: string;
}

export interface BRStatement {
  id: string;
  statement_no: string;
  bank_account_id: string;
  statement_date: string;
  period_start_date: string;
  period_end_date: string;
  opening_balance: number;
  closing_balance: number;
  statement_currency: string;
  import_source: BRImportSource;
  import_file_name: string | null;
  status: BRStatementStatus;
  imported_by: string | null;
  imported_at: string | null;
  closed_by: string | null;
  closed_at: string | null;
  notes: string | null;
  total_credits: number;
  total_debits: number;
  total_lines: number;
  created_at: string;
}

export interface BRStatementLine {
  id: string;
  statement_id: string;
  line_no: number;
  transaction_date: string;
  value_date: string | null;
  external_reference: string | null;
  bank_reference: string | null;
  narration: string | null;
  counterparty_name: string | null;
  amount: number;
  debit_credit_indicator: string;
  running_balance: number | null;
  normalized_reference: string | null;
  normalized_narration: string | null;
  match_status: BRLineMatchStatus;
  matched_amount: number;
  unmatched_amount: number;
  reconciliation_notes: string | null;
  is_duplicate_suspected: boolean;
  created_at: string;
}

export interface BRMatch {
  id: string;
  statement_line_id: string;
  erp_transaction_type: BRERPTransactionType;
  erp_transaction_id: string | null;
  erp_reference: string | null;
  erp_transaction_date: string | null;
  erp_amount: number | null;
  erp_description: string | null;
  matched_amount: number;
  match_method: BRMatchMethod;
  confidence_score: number | null;
  is_active: boolean;
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface BRRule {
  id: string;
  bank_account_id: string | null;
  rule_name: string;
  condition_type: BRRuleConditionType;
  condition_value: string;
  target_transaction_type: BRERPTransactionType;
  auto_apply: boolean;
  confidence_weight: number;
  priority: number;
  active: boolean;
  notes: string | null;
  created_at: string;
}

export interface BRAdjustment {
  id: string;
  statement_id: string;
  statement_line_id: string | null;
  adjustment_type: BRAdjustmentType;
  amount: number;
  description: string;
  gl_account_id: string | null;
  auto_created: boolean;
  posted: boolean;
  posted_by: string | null;
  posted_at: string | null;
  created_by: string | null;
  created_at: string;
}

export interface BRAIRec {
  id: string;
  statement_id: string | null;
  statement_line_id: string | null;
  agent_type: BRAIAgentType;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  suggested_action: string | null;
  priority: string;
  confidence_score: number | null;
  status: BRAIRecStatus;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

export interface BRDashboard {
  total_accounts: number;
  active_statements: number;
  unmatched_items: number;
  partially_matched_items: number;
  total_unmatched_amount: number;
  statements_in_recon: number;
  statements_locked: number;
  pending_ai_recs: number;
  recent_statements: BRStatement[];
}

export interface BROpenItem {
  line_id: string;
  statement_no: string;
  bank_account_name: string;
  transaction_date: string;
  amount: number;
  debit_credit: string;
  unmatched_amount: number;
  match_status: BRLineMatchStatus;
  narration: string | null;
  days_outstanding: number;
}

export interface BRBalanceSummary {
  bank_account_id: string;
  bank_account_name: string;
  currency: string;
  last_statement_no: string | null;
  statement_closing: number;
  erp_book_balance: number;
  variance: number;
  status: string;
}

// ─── Color Helpers ────────────────────────────────────────────────────────────

export const STATUS_COLOR: Record<BRStatementStatus, string> = {
  DRAFT:             "bg-gray-100 text-gray-600",
  IMPORTED:          "bg-blue-100 text-blue-700",
  IN_RECONCILIATION: "bg-yellow-100 text-yellow-700",
  RECONCILED:        "bg-green-100 text-green-700",
  CLOSED:            "bg-purple-100 text-purple-700",
  LOCKED:            "bg-gray-700 text-white",
};

export const LINE_STATUS_COLOR: Record<BRLineMatchStatus, string> = {
  UNMATCHED:           "bg-red-100 text-red-700",
  SUGGESTED_MATCH:     "bg-yellow-100 text-yellow-700",
  PARTIALLY_MATCHED:   "bg-orange-100 text-orange-700",
  MATCHED:             "bg-green-100 text-green-700",
  IGNORED:             "bg-gray-100 text-gray-500",
  DUPLICATE_SUSPECTED: "bg-red-200 text-red-800",
  NEEDS_REVIEW:        "bg-purple-100 text-purple-700",
};

export const AI_AGENT_LABEL: Record<BRAIAgentType, string> = {
  MATCH_CONFIDENCE: "Match Confidence",
  CASH_ANOMALY:     "Cash Anomaly",
  RULE_OPTIMIZER:   "Rule Optimizer",
};

export const AI_PRIORITY_COLOR: Record<string, string> = {
  HIGH:   "bg-red-100 text-red-700",
  MEDIUM: "bg-yellow-100 text-yellow-700",
  LOW:    "bg-green-100 text-green-700",
};

export const ERP_TX_LABEL: Record<BRERPTransactionType, string> = {
  AR_PAYMENT:       "AR Payment",
  AP_PAYMENT:       "AP Payment",
  PURCHASE_PAYMENT: "Purchase Payment",
  EXPENSE_PAYMENT:  "Expense",
  PAYROLL:          "Payroll",
  TRANSFER:         "Transfer",
  MPESA_COLLECTION: "M-Pesa Collection",
  MPESA_PAYOUT:     "M-Pesa Payout",
  BANK_CHARGE:      "Bank Charge",
  INTEREST:         "Interest",
  REFUND:           "Refund",
  JOURNAL_ENTRY:    "Journal Entry",
};

// ─── API Client ───────────────────────────────────────────────────────────────

export const brApi = {
  // Dashboard
  getDashboard: () =>
    apiClient.get<BRDashboard>(`${BASE}/dashboard`).then((r) => r.data),

  // Bank accounts
  listAccounts: (activeOnly = true) =>
    apiClient.get<BRBankAccount[]>(`${BASE}/accounts`, { params: { active_only: activeOnly } }).then((r) => r.data),
  createAccount: (data: Partial<BRBankAccount>) =>
    apiClient.post<BRBankAccount>(`${BASE}/accounts`, data).then((r) => r.data),
  getAccount: (id: string) =>
    apiClient.get<BRBankAccount>(`${BASE}/accounts/${id}`).then((r) => r.data),
  updateAccount: (id: string, data: Partial<BRBankAccount>) =>
    apiClient.patch<BRBankAccount>(`${BASE}/accounts/${id}`, data).then((r) => r.data),

  // Statements
  listStatements: (params?: { bank_account_id?: string; status?: BRStatementStatus; limit?: number }) =>
    apiClient.get<BRStatement[]>(`${BASE}/statements`, { params }).then((r) => r.data),
  createStatement: (data: object) =>
    apiClient.post<BRStatement>(`${BASE}/statements`, data).then((r) => r.data),
  importStatement: (data: object) =>
    apiClient.post<BRStatement>(`${BASE}/statements/import`, data).then((r) => r.data),
  getStatement: (id: string) =>
    apiClient.get<BRStatement>(`${BASE}/statements/${id}`).then((r) => r.data),
  getLines: (id: string) =>
    apiClient.get<BRStatementLine[]>(`${BASE}/statements/${id}/lines`).then((r) => r.data),
  addLine: (id: string, data: object) =>
    apiClient.post<BRStatementLine>(`${BASE}/statements/${id}/lines`, data).then((r) => r.data),
  autoMatch: (id: string, params?: { confidence_threshold?: number; auto_apply_threshold?: number }) =>
    apiClient.post<object>(`${BASE}/statements/${id}/auto-match`, null, { params }).then((r) => r.data),
  closeStatement: (id: string, closedBy?: string) =>
    apiClient.post<BRStatement>(`${BASE}/statements/${id}/close`, null, { params: { closed_by: closedBy } }).then((r) => r.data),
  lockStatement: (id: string, lockedBy?: string) =>
    apiClient.post<BRStatement>(`${BASE}/statements/${id}/lock`, null, { params: { locked_by: lockedBy } }).then((r) => r.data),
  reopenStatement: (id: string, reopenedBy?: string) =>
    apiClient.post<BRStatement>(`${BASE}/statements/${id}/reopen`, null, { params: { reopened_by: reopenedBy } }).then((r) => r.data),
  getStatementReport: (id: string) =>
    apiClient.get<object>(`${BASE}/statements/${id}/report`).then((r) => r.data),
  listAdjustments: (id: string) =>
    apiClient.get<BRAdjustment[]>(`${BASE}/statements/${id}/adjustments`).then((r) => r.data),
  listStmtAIRecs: (id: string) =>
    apiClient.get<BRAIRec[]>(`${BASE}/statements/${id}/ai-recs`).then((r) => r.data),

  // Line actions
  manualMatch: (lineId: string, data: object) =>
    apiClient.post<BRMatch>(`${BASE}/lines/${lineId}/manual-match`, data).then((r) => r.data),
  splitMatch: (lineId: string, data: object) =>
    apiClient.post<BRMatch[]>(`${BASE}/lines/${lineId}/split-match`, data).then((r) => r.data),
  unmatch: (lineId: string) =>
    apiClient.post<BRStatementLine>(`${BASE}/lines/${lineId}/unmatch`).then((r) => r.data),
  ignoreLine: (lineId: string, notes?: string) =>
    apiClient.post<BRStatementLine>(`${BASE}/lines/${lineId}/ignore`, null, { params: { notes } }).then((r) => r.data),
  confirmSuggestion: (matchId: string, approvedBy?: string) =>
    apiClient.post<BRMatch>(`${BASE}/matches/${matchId}/confirm`, null, { params: { approved_by: approvedBy } }).then((r) => r.data),

  // Adjustments
  createAdjustment: (data: object) =>
    apiClient.post<BRAdjustment>(`${BASE}/adjustments`, data).then((r) => r.data),
  postAdjustment: (adjId: string, postedBy?: string) =>
    apiClient.post<BRAdjustment>(`${BASE}/adjustments/${adjId}/post`, null, { params: { posted_by: postedBy } }).then((r) => r.data),

  // Rules
  listRules: (bankAccountId?: string) =>
    apiClient.get<BRRule[]>(`${BASE}/rules`, { params: { bank_account_id: bankAccountId } }).then((r) => r.data),
  createRule: (data: object) =>
    apiClient.post<BRRule>(`${BASE}/rules`, data).then((r) => r.data),
  updateRule: (id: string, data: object) =>
    apiClient.patch<BRRule>(`${BASE}/rules/${id}`, data).then((r) => r.data),
  deleteRule: (id: string) =>
    apiClient.delete(`${BASE}/rules/${id}`),

  // Open items
  getOpenItems: (params?: { bank_account_id?: string; min_days?: number; limit?: number }) =>
    apiClient.get<BROpenItem[]>(`${BASE}/open-items`, { params }).then((r) => r.data),

  // Balance summary
  getBalanceSummary: () =>
    apiClient.get<BRBalanceSummary[]>(`${BASE}/balance-summary`).then((r) => r.data),

  // Reports
  reportUnreconciled: () =>
    apiClient.get<Record<string, unknown>[]>(`${BASE}/reports/unreconciled`).then((r) => r.data),
  reportAgedOpenItems: () =>
    apiClient.get<Record<string, unknown>[]>(`${BASE}/reports/aged-open-items`).then((r) => r.data),

  // AI
  runAI: (stmtId?: string) =>
    apiClient.post<{ recommendations_created: number }>(`${BASE}/ai/run`, null, { params: stmtId ? { stmt_id: stmtId } : undefined }).then((r) => r.data),
  listAIRecs: (params?: { status?: BRAIRecStatus }) =>
    apiClient.get<BRAIRec[]>(`${BASE}/ai/recs`, { params }).then((r) => r.data),
  actionAIRec: (id: string, status: BRAIRecStatus, actionedBy?: string) =>
    apiClient.post<BRAIRec>(`${BASE}/ai/recs/${id}/action`, null, { params: { status, actioned_by: actionedBy } }).then((r) => r.data),
};
