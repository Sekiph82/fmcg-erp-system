import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);
const ax = axios.create({ baseURL: API });

// ── Types ─────────────────────────────────────────────────────────────────────

export type PortalAccountType   = "CUSTOMER" | "DISTRIBUTOR" | "KEY_ACCOUNT" | "RETAILER" | "INSTITUTIONAL" | "MIXED";
export type PortalAccountStatus = "PENDING" | "ACTIVE" | "SUSPENDED" | "CLOSED";
export type PortalUserRole      = "OWNER" | "FINANCE" | "BUYER" | "LOGISTICS" | "VIEWER" | "CUSTOM";
export type PortalActivityType  = "LOGIN" | "VIEW_ORDER" | "DOWNLOAD_INVOICE" | "SUBMIT_ORDER" | "INITIATE_PAYMENT" | "SUBMIT_RETURN" | "SUBMIT_CLAIM" | "DOWNLOAD_STATEMENT" | "VIEW_SHIPMENT" | "DOWNLOAD_DOCUMENT" | "INVITE_USER" | "OTHER";
export type PortalClaimType     = "RETURN_REQUEST" | "SHORTAGE_CLAIM" | "DAMAGE_CLAIM" | "DELIVERY_DISCREPANCY" | "PRICING_DISPUTE" | "PRODUCT_COMPLAINT" | "INVOICE_DISPUTE" | "OTHER";
export type PortalClaimStatus   = "SUBMITTED" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED" | "CLOSED";
export type PortalOrderMode     = "DIRECT_SUBMIT" | "DRAFT_REQUEST" | "REORDER_ONLY";
export type PortalDraftStatus   = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED" | "CONVERTED";
export type PortalAIAgentType   = "SUPPORT_ASSISTANT" | "FRICTION_MONITOR" | "COMMERCIAL_OPPORTUNITY";
export type PortalAIRecStatus   = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

export interface PortalAccount {
  id: string;
  account_code: string;
  account_type: PortalAccountType;
  linked_customer_id?: string;
  linked_distributor_id?: string;
  portal_status: PortalAccountStatus;
  default_currency: string;
  preferred_language: string;
  order_mode: PortalOrderMode;
  primary_contact_name?: string;
  primary_contact_email?: string;
  primary_contact_phone?: string;
  timezone: string;
  can_view_prices: boolean;
  can_view_promotions: boolean;
  can_initiate_payment: boolean;
  notes?: string;
  created_at?: string;
}

export interface PortalUser {
  id: string;
  portal_account_id: string;
  full_name: string;
  email: string;
  phone?: string;
  role_type: PortalUserRole;
  is_active: boolean;
  last_login_at?: string;
  invited_by?: string;
  created_at?: string;
}

export interface PortalClaim {
  id: string;
  claim_no: string;
  portal_account_id: string;
  submitted_by?: string;
  claim_type: PortalClaimType;
  linked_order_id?: string;
  linked_invoice_id?: string;
  quantity_involved?: number;
  reason: string;
  description?: string;
  status: PortalClaimStatus;
  resolution_notes?: string;
  resolved_date?: string;
  created_at?: string;
}

export interface PortalDraftOrderLine {
  id: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  quantity: number;
  unit: string;
  unit_price?: number;
  line_total?: number;
}

export interface PortalDraftOrder {
  id: string;
  draft_no: string;
  portal_account_id: string;
  submitted_by?: string;
  source_order_id?: string;
  requested_delivery_date?: string;
  delivery_address?: string;
  order_comments?: string;
  status: PortalDraftStatus;
  total_amount?: number;
  currency: string;
  converted_order_id?: string;
  review_notes?: string;
  created_at?: string;
  lines: PortalDraftOrderLine[];
}

export interface PortalActivityLog {
  id: string;
  portal_user_id: string;
  activity_type: PortalActivityType;
  reference_type?: string;
  reference_id?: string;
  activity_datetime: string;
  notes?: string;
}

export interface PortalAIRec {
  id: string;
  agent_type: PortalAIAgentType;
  portal_account_id?: string;
  title: string;
  body: string;
  priority?: string;
  action_label?: string;
  status: PortalAIRecStatus;
  acknowledged_by?: string;
  notes?: string;
  created_at?: string;
}

export interface PortalDashboard {
  account_code: string;
  account_type: string;
  outstanding_balance: number;
  overdue_balance: number;
  current_due: number;
  aging_0_30: number;
  aging_31_60: number;
  aging_61_90: number;
  aging_90_plus: number;
  open_orders: number;
  recent_orders: Record<string, unknown>[];
  recent_invoices: Record<string, unknown>[];
  recent_payments: Record<string, unknown>[];
  open_claims: number;
  credit_limit?: number;
}

// ── Labels ─────────────────────────────────────────────────────────────────────

export const ACCOUNT_TYPE_LABELS: Record<PortalAccountType, string> = {
  CUSTOMER: "Customer", DISTRIBUTOR: "Distributor", KEY_ACCOUNT: "Key Account",
  RETAILER: "Retailer", INSTITUTIONAL: "Institutional", MIXED: "Mixed",
};

export const ACCOUNT_STATUS_COLORS: Record<PortalAccountStatus, string> = {
  PENDING: "#F59E0B", ACTIVE: "#10B981", SUSPENDED: "#EF4444", CLOSED: "#6B7280",
};

export const USER_ROLE_LABELS: Record<PortalUserRole, string> = {
  OWNER: "Owner", FINANCE: "Finance", BUYER: "Buyer",
  LOGISTICS: "Logistics", VIEWER: "Viewer", CUSTOM: "Custom",
};

export const CLAIM_TYPE_LABELS: Record<PortalClaimType, string> = {
  RETURN_REQUEST: "Return Request", SHORTAGE_CLAIM: "Shortage Claim", DAMAGE_CLAIM: "Damage Claim",
  DELIVERY_DISCREPANCY: "Delivery Discrepancy", PRICING_DISPUTE: "Pricing Dispute",
  PRODUCT_COMPLAINT: "Product Complaint", INVOICE_DISPUTE: "Invoice Dispute", OTHER: "Other",
};

export const CLAIM_STATUS_COLORS: Record<PortalClaimStatus, string> = {
  SUBMITTED: "#3B82F6", UNDER_REVIEW: "#F59E0B", RESOLVED: "#10B981", REJECTED: "#EF4444", CLOSED: "#6B7280",
};

export const DRAFT_STATUS_COLORS: Record<PortalDraftStatus, string> = {
  DRAFT: "#6B7280", SUBMITTED: "#3B82F6", APPROVED: "#10B981", REJECTED: "#EF4444", CONVERTED: "#8B5CF6",
};

export const ORDER_MODE_LABELS: Record<PortalOrderMode, string> = {
  DIRECT_SUBMIT: "Direct Submit", DRAFT_REQUEST: "Draft Request (requires approval)", REORDER_ONLY: "Reorder Only",
};

export const AI_AGENT_LABELS: Record<PortalAIAgentType, string> = {
  SUPPORT_ASSISTANT: "Portal Support Assistant",
  FRICTION_MONITOR: "Portal Friction Monitor",
  COMMERCIAL_OPPORTUNITY: "Commercial Opportunity Assistant",
};

export function fmtCurrency(val?: number | null, currency = "KES"): string {
  if (val == null) return "—";
  return `${currency} ${val.toLocaleString("en-KE", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

// ── API ────────────────────────────────────────────────────────────────────────

export const portalApi = {
  // Auth
  login: (data: { email: string; password: string }) => r(ax.post(`/portal/auth/login`, data)),
  activate: (data: { token: string; new_password: string }) => r(ax.post(`/portal/auth/activate`, data)),

  // Accounts (admin)
  getAccounts: (params?: Record<string, unknown>) => r(ax.get<PortalAccount[]>(`/portal/accounts`, { params })),
  createAccount: (data: Partial<PortalAccount>) => r(ax.post<PortalAccount>(`/portal/accounts`, data)),
  getAccount: (id: string) => r(ax.get<PortalAccount>(`/portal/accounts/${id}`)),
  updateAccount: (id: string, data: Partial<PortalAccount>) => r(ax.patch<PortalAccount>(`/portal/accounts/${id}`, data)),
  activateAccount: (id: string) => r(ax.post<PortalAccount>(`/portal/accounts/${id}/activate`)),
  suspendAccount: (id: string) => r(ax.post<PortalAccount>(`/portal/accounts/${id}/suspend`)),

  // Users
  getUsers: (accountId: string) => r(ax.get<PortalUser[]>(`/portal/accounts/${accountId}/users`)),
  inviteUser: (accountId: string, data: Partial<PortalUser> & { invited_by?: string }) =>
    r(ax.post<PortalUser>(`/portal/accounts/${accountId}/users/invite`, data)),
  deactivateUser: (userId: string) => r(ax.post<PortalUser>(`/portal/users/${userId}/deactivate`)),

  // Self-service (per account)
  getDashboard: (accountId: string) => r(ax.get<PortalDashboard>(`/portal/accounts/${accountId}/dashboard`)),
  getOrders: (accountId: string, params?: Record<string, unknown>) => r(ax.get(`/portal/accounts/${accountId}/orders`, { params })),
  getOrder: (accountId: string, orderId: string) => r(ax.get(`/portal/accounts/${accountId}/orders/${orderId}`)),
  getShipments: (accountId: string, params?: Record<string, unknown>) => r(ax.get(`/portal/accounts/${accountId}/shipments`, { params })),
  getInvoices: (accountId: string, params?: Record<string, unknown>) => r(ax.get(`/portal/accounts/${accountId}/invoices`, { params })),
  getPayments: (accountId: string, params?: Record<string, unknown>) => r(ax.get(`/portal/accounts/${accountId}/payments`, { params })),
  getStatement: (accountId: string, params?: Record<string, unknown>) => r(ax.get(`/portal/accounts/${accountId}/statement`, { params })),

  // Claims
  getClaims: (accountId: string, params?: Record<string, unknown>) => r(ax.get<PortalClaim[]>(`/portal/accounts/${accountId}/claims`, { params })),
  submitClaim: (accountId: string, data: Partial<PortalClaim>, submittedBy?: string) =>
    r(ax.post<PortalClaim>(`/portal/accounts/${accountId}/claims`, data, { params: { submitted_by: submittedBy } })),
  reviewClaim: (claimId: string, data: Record<string, unknown>) => r(ax.patch<PortalClaim>(`/portal/claims/${claimId}/review`, data)),

  // Draft Orders
  getDraftOrders: (accountId: string, params?: Record<string, unknown>) => r(ax.get<PortalDraftOrder[]>(`/portal/accounts/${accountId}/draft-orders`, { params })),
  createDraftOrder: (accountId: string, data: Record<string, unknown>, submittedBy?: string) =>
    r(ax.post<PortalDraftOrder>(`/portal/accounts/${accountId}/draft-orders`, data, { params: { submitted_by: submittedBy } })),
  submitDraftOrder: (accountId: string, draftId: string) =>
    r(ax.post<PortalDraftOrder>(`/portal/accounts/${accountId}/draft-orders/${draftId}/submit`)),
  reviewDraftOrder: (draftId: string, data: Record<string, unknown>) => r(ax.patch<PortalDraftOrder>(`/portal/draft-orders/${draftId}/review`, data)),
  reorder: (accountId: string, sourceOrderId: string, submittedBy?: string) =>
    r(ax.post<PortalDraftOrder>(`/portal/accounts/${accountId}/reorder/${sourceOrderId}`, null, { params: { submitted_by: submittedBy } })),

  // Activity
  getActivity: (accountId: string, limit?: number) => r(ax.get<PortalActivityLog[]>(`/portal/accounts/${accountId}/activity`, { params: { limit } })),

  // Reports
  getAdoptionReport: () => r(ax.get(`/portal/reports/adoption`)),

  // AI
  runSupportAssistant: () => r(ax.post<{ generated: number; message: string }>(`/portal/ai/run-support-assistant`)),
  runFrictionMonitor: () => r(ax.post<{ generated: number; message: string }>(`/portal/ai/run-friction-monitor`)),
  runCommercialOpportunity: () => r(ax.post<{ generated: number; message: string }>(`/portal/ai/run-commercial-opportunity`)),
  getAIRecs: (params?: Record<string, unknown>) => r(ax.get<PortalAIRec[]>(`/portal/ai/recommendations`, { params })),
  ackAIRec: (id: string, data: Record<string, unknown>) => r(ax.patch<PortalAIRec>(`/portal/ai/recommendations/${id}`, data)),
};
