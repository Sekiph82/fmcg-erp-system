import { apiClient } from "@/lib/api";

const BASE = "/api/v1/van-sales";

// ── Types ─────────────────────────────────────────────────────────────────────

export type VanStatus = "ACTIVE" | "INACTIVE" | "ON_ROUTE" | "IN_REPAIR";
export type TxnType = "SALE" | "RETURN" | "EXCHANGE" | "CREDIT";
export type TxnStatus = "DRAFT" | "CONFIRMED" | "INVOICED" | "CANCELLED" | "SYNCED" | "PENDING_SYNC";
export type PaymentStatus = "UNPAID" | "PARTIAL" | "PAID" | "REFUNDED";
export type PaymentMethod = "CASH" | "MPESA" | "CARD" | "CREDIT" | "MIXED";
export type VisitStatus = "PLANNED" | "CHECKED_IN" | "COMPLETED" | "MISSED" | "SKIPPED";
export type ReconciliationStatus = "OPEN" | "SUBMITTED" | "APPROVED" | "DISCREPANCY";

export interface Van {
  id: string;
  van_code: string;
  plate_number?: string;
  driver_id?: string;
  route_id?: string;
  warehouse_id?: string;
  capacity_kg?: number;
  status: VanStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface VanStock {
  id: string;
  van_id: string;
  item_id: string;
  batch_id?: string;
  quantity: number;
  reserved_qty: number;
  unit_cost?: number;
  uom: string;
}

export interface VanVisit {
  id: string;
  van_id: string;
  route_id?: string;
  customer_id: string;
  route_date: string;
  sequence_no?: number;
  planned_time?: string;
  check_in_time?: string;
  check_out_time?: string;
  status: VisitStatus;
  gps_lat?: number;
  gps_lng?: number;
  missed_reason?: string;
  offline_id?: string;
  created_at: string;
}

export interface TxnLine {
  id: string;
  txn_id: string;
  item_id: string;
  batch_id?: string;
  uom: string;
  quantity: number;
  unit_price: number;
  discount_pct: number;
  discount_amt: number;
  tax_pct: number;
  tax_amt: number;
  line_total: number;
  return_reason?: string;
}

export interface VanPayment {
  id: string;
  txn_id: string;
  method: PaymentMethod;
  amount: number;
  reference_no?: string;
  collected_at: string;
  receipt_no?: string;
  notes?: string;
  created_at: string;
}

export interface VanSalesTxn {
  id: string;
  txn_no: string;
  van_id: string;
  route_id?: string;
  customer_id: string;
  visit_id?: string;
  driver_id?: string;
  txn_type: TxnType;
  txn_datetime: string;
  status: TxnStatus;
  payment_status: PaymentStatus;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  balance_due: number;
  currency: string;
  offline_id?: string;
  synced_at?: string;
  notes?: string;
  created_at: string;
  lines: TxnLine[];
  payments: VanPayment[];
}

export interface VanReconciliation {
  id: string;
  van_id: string;
  route_date: string;
  status: ReconciliationStatus;
  opening_stock?: Record<string, number>;
  closing_stock?: Record<string, number>;
  sales_qty?: Record<string, number>;
  returns_qty?: Record<string, number>;
  discrepancy?: Record<string, number>;
  total_sales?: number;
  total_cash?: number;
  total_mpesa?: number;
  total_credit?: number;
  total_returns?: number;
  submitted_by?: string;
  approved_by?: string;
  approved_at?: string;
  notes?: string;
  created_at: string;
}

export interface VSAIRec {
  id: string;
  agent_type: string;
  status: string;
  severity: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  van_id?: string;
  driver_id?: string;
  route_id?: string;
  created_at: string;
}

export interface SyncResult {
  visits_created: number;
  txns_created: number;
  payments_created: number;
  errors: string[];
  duplicates_skipped: number;
}

// ── Color helpers ─────────────────────────────────────────────────────────────

export const VAN_STATUS_COLORS: Record<VanStatus, string> = {
  ACTIVE:    "bg-emerald-500/20 text-emerald-300",
  INACTIVE:  "bg-slate-500/20 text-slate-400",
  ON_ROUTE:  "bg-blue-500/20 text-blue-300",
  IN_REPAIR: "bg-amber-500/20 text-amber-300",
};

export const VISIT_STATUS_COLORS: Record<VisitStatus, string> = {
  PLANNED:    "bg-slate-500/20 text-slate-400",
  CHECKED_IN: "bg-blue-500/20 text-blue-300",
  COMPLETED:  "bg-emerald-500/20 text-emerald-300",
  MISSED:     "bg-red-500/20 text-red-300",
  SKIPPED:    "bg-amber-500/20 text-amber-300",
};

export const TXN_STATUS_COLORS: Record<TxnStatus, string> = {
  DRAFT:        "bg-slate-500/20 text-slate-400",
  CONFIRMED:    "bg-blue-500/20 text-blue-300",
  INVOICED:     "bg-emerald-500/20 text-emerald-300",
  CANCELLED:    "bg-red-500/20 text-red-400",
  SYNCED:       "bg-indigo-500/20 text-indigo-300",
  PENDING_SYNC: "bg-amber-500/20 text-amber-300",
};

export const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  UNPAID:   "bg-red-500/20 text-red-300",
  PARTIAL:  "bg-amber-500/20 text-amber-300",
  PAID:     "bg-emerald-500/20 text-emerald-300",
  REFUNDED: "bg-slate-500/20 text-slate-400",
};

export const RECON_STATUS_COLORS: Record<ReconciliationStatus, string> = {
  OPEN:        "bg-slate-500/20 text-slate-400",
  SUBMITTED:   "bg-blue-500/20 text-blue-300",
  APPROVED:    "bg-emerald-500/20 text-emerald-300",
  DISCREPANCY: "bg-red-500/20 text-red-300",
};

export const SEVERITY_COLORS: Record<string, string> = {
  INFO:     "bg-blue-500/20 text-blue-300",
  WARNING:  "bg-amber-500/20 text-amber-300",
  CRITICAL: "bg-red-500/20 text-red-300",
};

// ── API client ────────────────────────────────────────────────────────────────

export const vanSalesApi = {
  // Vans
  listVans: (params?: { status?: string }) =>
    apiClient.get<Van[]>(`${BASE}/vans`, { params }).then((r) => r.data),
  createVan: (data: Partial<Van>) =>
    apiClient.post<Van>(`${BASE}/vans`, data).then((r) => r.data),
  getVan: (id: string) =>
    apiClient.get<Van>(`${BASE}/vans/${id}`).then((r) => r.data),
  updateVan: (id: string, data: Partial<Van>) =>
    apiClient.patch<Van>(`${BASE}/vans/${id}`, data).then((r) => r.data),

  // Stock
  getStock: (vanId: string) =>
    apiClient.get<VanStock[]>(`${BASE}/vans/${vanId}/stock`).then((r) => r.data),
  loadStock: (vanId: string, data: { lines: Partial<VanStock>[]; notes?: string }) =>
    apiClient.post<VanStock[]>(`${BASE}/vans/${vanId}/stock/load`, data).then((r) => r.data),

  // Visits
  listVisits: (vanId: string, route_date?: string) =>
    apiClient.get<VanVisit[]>(`${BASE}/vans/${vanId}/visits`, { params: { route_date } }).then((r) => r.data),
  createVisit: (vanId: string, data: Partial<VanVisit>) =>
    apiClient.post<VanVisit>(`${BASE}/vans/${vanId}/visits`, data).then((r) => r.data),
  checkIn: (visitId: string, data: { gps_lat?: number; gps_lng?: number }) =>
    apiClient.post<VanVisit>(`${BASE}/visits/${visitId}/check-in`, data).then((r) => r.data),
  checkOut: (visitId: string, notes?: string) =>
    apiClient.post<VanVisit>(`${BASE}/visits/${visitId}/check-out`, {}, { params: { notes } }).then((r) => r.data),
  markMissed: (visitId: string, reason?: string) =>
    apiClient.post<VanVisit>(`${BASE}/visits/${visitId}/missed`, {}, { params: { reason } }).then((r) => r.data),

  // Transactions
  listTransactions: (vanId: string, route_date?: string, params?: { skip?: number; limit?: number }) =>
    apiClient.get<VanSalesTxn[]>(`${BASE}/vans/${vanId}/transactions`, { params: { route_date, ...params } }).then((r) => r.data),
  createTransaction: (vanId: string, data: any) =>
    apiClient.post<VanSalesTxn>(`${BASE}/vans/${vanId}/transactions`, data).then((r) => r.data),
  getTransaction: (txnId: string) =>
    apiClient.get<VanSalesTxn>(`${BASE}/transactions/${txnId}`).then((r) => r.data),

  // Payments
  addPayment: (txnId: string, data: Partial<VanPayment>) =>
    apiClient.post<VanPayment>(`${BASE}/transactions/${txnId}/payments`, data).then((r) => r.data),

  // Reconciliation
  listReconciliations: (vanId: string) =>
    apiClient.get<VanReconciliation[]>(`${BASE}/vans/${vanId}/reconciliations`).then((r) => r.data),
  createReconciliation: (vanId: string, data: { route_date: string; notes?: string }) =>
    apiClient.post<VanReconciliation>(`${BASE}/vans/${vanId}/reconciliations`, data).then((r) => r.data),
  approveReconciliation: (reconId: string) =>
    apiClient.post<VanReconciliation>(`${BASE}/reconciliations/${reconId}/approve`, {}).then((r) => r.data),

  // Sync
  sync: (vanId: string, payload: any) =>
    apiClient.post<SyncResult>(`${BASE}/vans/${vanId}/sync`, payload).then((r) => r.data),

  // Reports
  vanSummary: (vanId: string, days = 30) =>
    apiClient.get<{ txn_count: number; total_sales: number; total_collected: number; days: number }>(
      `${BASE}/reports/van/${vanId}/summary`, { params: { days } }
    ).then((r) => r.data),
  routePerformance: (days = 30) =>
    apiClient.get<{ route_id: string; txn_count: number; total_sales: number }[]>(
      `${BASE}/reports/route-performance`, { params: { days } }
    ).then((r) => r.data),
  driverPerformance: (days = 30) =>
    apiClient.get<{ driver_id: string; txn_count: number; total_sales: number }[]>(
      `${BASE}/reports/driver-performance`, { params: { days } }
    ).then((r) => r.data),

  // AI
  runAI: () => apiClient.post<VSAIRec[]>(`${BASE}/ai/run`, {}).then((r) => r.data),
  aiRecs: (params?: { agent_type?: string; status?: string }) =>
    apiClient.get<VSAIRec[]>(`${BASE}/ai/recommendations`, { params }).then((r) => r.data),
  ackRec: (id: string, status: string) =>
    apiClient.patch<VSAIRec>(`${BASE}/ai/recommendations/${id}`, { status }).then((r) => r.data),
};
