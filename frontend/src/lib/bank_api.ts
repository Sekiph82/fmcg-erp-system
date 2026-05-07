import { apiClient } from "@/lib/api";

const BASE = "/api/v1/bank-api";

export type BankConnectionStatus = "ACTIVE" | "DISCONNECTED";
export type BankApiType = "DIRECT" | "MOCK";
export type BankTxnDirection = "DEBIT" | "CREDIT";
export type BankTxnClassification =
  | "SALES_RECEIPT"
  | "PAYMENT"
  | "SUPPLIER_PAYMENT"
  | "PAYROLL"
  | "BANK_CHARGE"
  | "TAX"
  | "UTILITIES"
  | "RENT"
  | "TRANSFER"
  | "OTHER";
export type BankSyncStatus = "SUCCESS" | "FAILED";

export interface BankConnection {
  id: string;
  connection_no: string;
  bank_name: string;
  account_name: string;
  account_number: string;
  bank_code: string | null;
  currency: string;
  status: BankConnectionStatus;
  last_synced_at: string | null;
  api_type: BankApiType;
  credentials_ref: string | null;
  created_at: string;
}

export interface BankTransaction {
  id: string;
  connection_id: string;
  txn_date: string;
  value_date: string | null;
  description: string;
  amount: number;
  direction: BankTxnDirection;
  reference: string;
  balance_after: number | null;
  classification: BankTxnClassification;
  is_reconciled: boolean;
  matched_record_id: string | null;
  matched_record_type: string | null;
  created_at: string;
}

export interface BankSyncLog {
  id: string;
  connection_id: string;
  synced_at: string;
  transactions_fetched: number;
  status: BankSyncStatus;
  message: string | null;
  created_at: string;
}

export interface BankApiDashboard {
  total_connections: number;
  active_connections: number;
  total_balance: number;
  unreconciled_count: number;
  unreconciled_amount: number;
  last_sync_at: string | null;
  recent_sync_logs: BankSyncLog[];
}

export interface BankSyncResult {
  connection: BankConnection;
  log: BankSyncLog;
  transactions: BankTransaction[];
}

export interface CreateBankConnection {
  bank_name: string;
  account_name: string;
  account_number: string;
  bank_code?: string;
  currency: string;
  api_type: BankApiType;
  credentials_ref?: string;
}

export const BANK_CLASSIFICATIONS: BankTxnClassification[] = [
  "SALES_RECEIPT",
  "PAYMENT",
  "SUPPLIER_PAYMENT",
  "PAYROLL",
  "BANK_CHARGE",
  "TAX",
  "UTILITIES",
  "RENT",
  "TRANSFER",
  "OTHER",
];

export const bankApi = {
  dashboard: () =>
    apiClient.get<BankApiDashboard>(`${BASE}/dashboard`).then((r) => r.data),
  listConnections: () =>
    apiClient.get<BankConnection[]>(`${BASE}/connections`).then((r) => r.data),
  createConnection: (body: CreateBankConnection) =>
    apiClient.post<BankConnection>(`${BASE}/connections`, body).then((r) => r.data),
  syncConnection: (id: string) =>
    apiClient.post<BankSyncResult>(`${BASE}/connections/${id}/sync`).then((r) => r.data),
  listTransactions: (params?: {
    connection_id?: string;
    start_date?: string;
    end_date?: string;
    reconciled?: boolean;
    limit?: number;
  }) =>
    apiClient.get<BankTransaction[]>(`${BASE}/transactions`, { params }).then((r) => r.data),
  classifyTransaction: (id: string, classification: BankTxnClassification) =>
    apiClient.post<BankTransaction>(`${BASE}/transactions/${id}/classify`, { classification }).then((r) => r.data),
  reconcileTransaction: (id: string, matched_record_type: string, matched_record_id?: string) =>
    apiClient.post<BankTransaction>(`${BASE}/transactions/${id}/reconcile`, {
      matched_record_type,
      matched_record_id: matched_record_id || undefined,
    }).then((r) => r.data),
};

export function fmtMoney(v: number, currency = "KES") {
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(v);
}

export function classificationLabel(v: BankTxnClassification) {
  return v.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());
}
