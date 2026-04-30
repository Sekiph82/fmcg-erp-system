import { apiClient } from "@/lib/api";

const BASE = "/api/v1/moto-sales";

// ── Types ─────────────────────────────────────────────────────────────────────

export type MpesaStatus = "PENDING" | "SUCCESS" | "FAILED" | "TIMEOUT" | "CANCELLED";

export type FraudType =
  | "ABNORMAL_DISCOUNT" | "PRICE_OVERRIDE" | "REPEATED_RETURN"
  | "STOCK_MISMATCH" | "DUPLICATE_TXN" | "PAYMENT_MISMATCH"
  | "OFFLINE_MANIPULATION" | "UNUSUAL_PATTERN";

export type FraudSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type FraudAlertStatus = "OPEN" | "REVIEWED" | "DISMISSED" | "ESCALATED" | "CONFIRMED";

export interface VanMpesaPayment {
  id: string;
  txn_id: string;
  phone_number: string;
  amount: number;
  merchant_request_id?: string;
  checkout_request_id?: string;
  mpesa_receipt_no?: string;
  status: MpesaStatus;
  result_code?: string;
  result_desc?: string;
  request_time: string;
  callback_time?: string;
  created_at: string;
}

export interface VanFraudAlert {
  id: string;
  txn_id?: string;
  van_id?: string;
  driver_id?: string;
  fraud_type: FraudType;
  risk_score: number;
  severity: FraudSeverity;
  status: FraudAlertStatus;
  description?: string;
  data?: Record<string, unknown>;
  reviewed_by?: string;
  reviewed_at?: string;
  resolution?: string;
  created_at: string;
}

export interface VanRiderPerformance {
  id: string;
  driver_id: string;
  van_id?: string;
  route_id?: string;
  perf_date: string;
  total_sales: number;
  total_orders: number;
  total_visits: number;
  completed_visits: number;
  missed_visits: number;
  route_completion_pct?: number;
  collection_rate_pct?: number;
  expected_cash?: number;
  actual_cash?: number;
  cash_variance?: number;
  stock_variance_pct?: number;
  fraud_flag_count: number;
  performance_score?: number;
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  driver_id: string;
  avg_score: number;
  total_sales: number;
  total_orders: number;
  avg_route_completion: number;
  avg_collection_rate: number;
  total_fraud_flags: number;
}

// ── Colors ────────────────────────────────────────────────────────────────────

export const MPESA_STATUS_COLORS: Record<MpesaStatus, string> = {
  PENDING:   "bg-amber-500/20 text-amber-300",
  SUCCESS:   "bg-emerald-500/20 text-emerald-300",
  FAILED:    "bg-red-500/20 text-red-300",
  TIMEOUT:   "bg-slate-500/20 text-slate-400",
  CANCELLED: "bg-slate-600/20 text-slate-500",
};

export const FRAUD_SEVERITY_COLORS: Record<FraudSeverity, string> = {
  LOW:      "bg-slate-500/20 text-slate-400",
  MEDIUM:   "bg-amber-500/20 text-amber-300",
  HIGH:     "bg-orange-500/20 text-orange-300",
  CRITICAL: "bg-red-500/20 text-red-300",
};

export const FRAUD_STATUS_COLORS: Record<FraudAlertStatus, string> = {
  OPEN:      "bg-red-500/20 text-red-300",
  REVIEWED:  "bg-blue-500/20 text-blue-300",
  DISMISSED: "bg-slate-500/20 text-slate-400",
  ESCALATED: "bg-orange-500/20 text-orange-300",
  CONFIRMED: "bg-red-700/20 text-red-400",
};

export function scoreColor(score?: number): string {
  if (!score) return "text-slate-400";
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

// ── API ───────────────────────────────────────────────────────────────────────

export const motoSalesApi = {
  // M-Pesa
  stkPush: (data: { txn_id: string; phone_number: string; amount: number }) =>
    apiClient.post<VanMpesaPayment>(`${BASE}/mpesa/stk-push`, data).then((r) => r.data),
  listMpesa: (params?: { txn_id?: string; status?: string }) =>
    apiClient.get<VanMpesaPayment[]>(`${BASE}/mpesa/payments`, { params }).then((r) => r.data),

  // Fraud
  runFraudScan: (days = 7) =>
    apiClient.post<VanFraudAlert[]>(`${BASE}/fraud/scan`, {}, { params: { days } }).then((r) => r.data),
  listFraudAlerts: (params?: { van_id?: string; driver_id?: string; status?: string; severity?: string }) =>
    apiClient.get<VanFraudAlert[]>(`${BASE}/fraud/alerts`, { params }).then((r) => r.data),
  reviewAlert: (id: string, data: { status: string; resolution?: string }) =>
    apiClient.patch<VanFraudAlert>(`${BASE}/fraud/alerts/${id}`, data).then((r) => r.data),

  // Performance
  computePerformance: (driver_id: string, perf_date: string) =>
    apiClient.post<VanRiderPerformance>(`${BASE}/performance/compute`, { driver_id, perf_date }).then((r) => r.data),
  listPerformance: (params?: { driver_id?: string; from_date?: string; to_date?: string }) =>
    apiClient.get<VanRiderPerformance[]>(`${BASE}/performance`, { params }).then((r) => r.data),
  leaderboard: (params?: { from_date?: string; to_date?: string }) =>
    apiClient.get<LeaderboardEntry[]>(`${BASE}/performance/leaderboard`, { params }).then((r) => r.data),
};
