const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/supplier-portal`;

async function r<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type SPAccountStatus = "PENDING" | "ACTIVE" | "SUSPENDED" | "CLOSED";
export type SPUserRole = "OWNER" | "SALES" | "LOGISTICS" | "FINANCE" | "QUALITY" | "VIEWER" | "CUSTOM";
export type SPActivityType = "LOGIN" | "VIEW_PO" | "ACKNOWLEDGE_PO" | "PROPOSE_ETA" | "UPLOAD_INVOICE" | "UPLOAD_DOC" | "VIEW_PAYMENT" | "UPDATE_PROFILE" | "INVITE_USER" | "DEACTIVATE_USER" | "OTHER";
export type SPPOResponseStatus = "PENDING_RESPONSE" | "ACCEPTED" | "ACCEPTED_REVISED_ETA" | "PARTIALLY_ACCEPTED" | "REJECTED" | "UNDER_REVIEW";
export type SPETAStatus = "ORIGINAL" | "REVISED" | "APPROVED" | "REJECTED";
export type SPDocUploadType = "INVOICE" | "DELIVERY_NOTE" | "PACKING_LIST" | "BILL_OF_LADING" | "COA" | "MSDS" | "SPECIFICATION" | "COMPLIANCE_CERT" | "FOOD_SAFETY_CERT" | "HALAL_CERT" | "TEST_RESULT" | "TAX_DOC" | "OTHER";
export type SPDocReviewStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "SUPERSEDED";
export type SPAIAgentType = "COLLABORATION_MONITOR" | "FRICTION_ASSISTANT" | "RISK_SIGNAL";
export type SPAIRecStatus = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

export interface SPAccount {
  id: string;
  supplier_id: string;
  portal_status: SPAccountStatus;
  default_currency: string;
  preferred_language: string;
  primary_contact_name?: string;
  primary_contact_email?: string;
  primary_contact_phone?: string;
  timezone: string;
  can_view_prices: boolean;
  can_view_payment: boolean;
  notes?: string;
  created_at?: string;
}

export interface SPUser {
  id: string;
  account_id: string;
  full_name: string;
  email: string;
  phone?: string;
  role_type: SPUserRole;
  is_active: boolean;
  last_login_at?: string;
  invited_by?: string;
  created_at?: string;
}

export interface SPDocument {
  id: string;
  account_id: string;
  supplier_id: string;
  upload_type: SPDocUploadType;
  linked_po_id?: string;
  linked_grn_id?: string;
  linked_invoice_id?: string;
  file_name: string;
  file_path: string;
  file_size_kb?: number;
  uploaded_at: string;
  review_status: SPDocReviewStatus;
  reviewed_by?: string;
  reviewed_at?: string;
  expiry_date?: string;
  notes?: string;
  created_at?: string;
}

export interface SPPOResponse {
  id: string;
  account_id: string;
  po_id: string;
  response_status: SPPOResponseStatus;
  accepted_qty_json?: Record<string, any>;
  supplier_comment?: string;
  rejection_reason?: string;
  proposed_eta?: string;
  responded_at?: string;
  created_at?: string;
}

export interface SPETALog {
  id: string;
  account_id: string;
  po_id: string;
  proposed_date: string;
  original_date?: string;
  eta_status: SPETAStatus;
  revision_no: number;
  supplier_reason?: string;
  buyer_notes?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at?: string;
}

export interface SPAIRec {
  id: string;
  account_id?: string;
  agent_type: SPAIAgentType;
  status: SPAIRecStatus;
  title: string;
  body: string;
  severity: string;
  reference_type?: string;
  reference_id?: string;
  actioned_by?: string;
  actioned_at?: string;
  created_at?: string;
}

export interface SPActivityLog {
  id: string;
  account_id: string;
  user_id?: string;
  activity_type: SPActivityType;
  reference_type?: string;
  reference_id?: string;
  activity_datetime: string;
  ip_or_session?: string;
  notes?: string;
}

export interface SPDashboard {
  account_id: string;
  supplier_name: string;
  open_pos: number;
  pending_acknowledgment: number;
  uploaded_invoices_30d: number;
  uploaded_docs_30d: number;
  expiring_certs: number;
  recent_activity: SPActivityLog[];
  ai_alerts: SPAIRec[];
}

// ── Color / Label Maps ────────────────────────────────────────────────────────

export const SP_STATUS_COLORS: Record<SPAccountStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACTIVE: "bg-green-100 text-green-800",
  SUSPENDED: "bg-red-100 text-red-800",
  CLOSED: "bg-gray-100 text-gray-700",
};

export const SP_PO_RESPONSE_COLORS: Record<SPPOResponseStatus, string> = {
  PENDING_RESPONSE: "bg-yellow-100 text-yellow-800",
  ACCEPTED: "bg-green-100 text-green-800",
  ACCEPTED_REVISED_ETA: "bg-blue-100 text-blue-800",
  PARTIALLY_ACCEPTED: "bg-orange-100 text-orange-800",
  REJECTED: "bg-red-100 text-red-800",
  UNDER_REVIEW: "bg-purple-100 text-purple-800",
};

export const SP_DOC_REVIEW_COLORS: Record<SPDocReviewStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACCEPTED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  SUPERSEDED: "bg-gray-100 text-gray-700",
};

export const SP_SEVERITY_COLORS: Record<string, string> = {
  INFO: "bg-blue-100 text-blue-800",
  WARNING: "bg-yellow-100 text-yellow-800",
  CRITICAL: "bg-red-100 text-red-800",
};

// ── API Client ────────────────────────────────────────────────────────────────

export const spApi = {
  // Accounts
  listAccounts: (status?: string) =>
    fetch(`${BASE}/accounts${status ? `?status=${status}` : ""}`).then(r<SPAccount[]>),
  getAccount: (id: string) => fetch(`${BASE}/accounts/${id}`).then(r<SPAccount>),
  createAccount: (body: Partial<SPAccount>) =>
    fetch(`${BASE}/accounts`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(r<SPAccount>),
  updateAccount: (id: string, body: Partial<SPAccount>) =>
    fetch(`${BASE}/accounts/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(r<SPAccount>),

  // Users
  listUsers: (accountId: string) => fetch(`${BASE}/accounts/${accountId}/users`).then(r<SPUser[]>),
  inviteUser: (accountId: string, body: Partial<SPUser>, invitedBy = "internal") =>
    fetch(`${BASE}/accounts/${accountId}/users/invite?invited_by=${encodeURIComponent(invitedBy)}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPUser>),
  deactivateUser: (userId: string) =>
    fetch(`${BASE}/users/${userId}/deactivate`, { method: "POST" }).then(r<SPUser>),

  // Dashboard
  getDashboard: (accountId: string) => fetch(`${BASE}/accounts/${accountId}/dashboard`).then(r<SPDashboard>),

  // Purchase Orders
  listPOs: (accountId: string, status?: string) =>
    fetch(`${BASE}/accounts/${accountId}/purchase-orders${status ? `?status=${status}` : ""}`).then(r<any[]>),
  getPO: (accountId: string, poId: string) =>
    fetch(`${BASE}/accounts/${accountId}/purchase-orders/${poId}`).then(r<any>),
  acknowledgePO: (accountId: string, poId: string, body: Partial<SPPOResponse>) =>
    fetch(`${BASE}/accounts/${accountId}/purchase-orders/${poId}/acknowledge`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPPOResponse>),

  // ETA
  proposeETA: (accountId: string, body: { po_id: string; proposed_date: string; supplier_reason?: string }) =>
    fetch(`${BASE}/accounts/${accountId}/propose-eta`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPETALog>),
  getETAHistory: (accountId: string, poId: string) =>
    fetch(`${BASE}/accounts/${accountId}/eta-history?po_id=${poId}`).then(r<SPETALog[]>),
  reviewETA: (etaId: string, body: { eta_status: string; reviewed_by: string; buyer_notes?: string }) =>
    fetch(`${BASE}/eta/${etaId}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPETALog>),

  // Documents
  listDocuments: (accountId: string, uploadType?: string, reviewStatus?: string) => {
    const p = new URLSearchParams();
    if (uploadType) p.set("upload_type", uploadType);
    if (reviewStatus) p.set("review_status", reviewStatus);
    const qs = p.toString() ? `?${p}` : "";
    return fetch(`${BASE}/accounts/${accountId}/documents${qs}`).then(r<SPDocument[]>);
  },
  uploadDocument: (accountId: string, body: Partial<SPDocument>) =>
    fetch(`${BASE}/accounts/${accountId}/documents`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPDocument>),
  reviewDocument: (docId: string, body: { review_status: string; reviewed_by: string; notes?: string }) =>
    fetch(`${BASE}/documents/${docId}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPDocument>),
  expiringDocuments: (days = 30) => fetch(`${BASE}/documents/expiring?days=${days}`).then(r<SPDocument[]>),

  // Payment Status
  getPaymentStatus: (accountId: string) =>
    fetch(`${BASE}/accounts/${accountId}/payment-status`).then(r<any[]>),

  // Activity
  listActivity: (accountId: string, limit = 100) =>
    fetch(`${BASE}/accounts/${accountId}/activity?limit=${limit}`).then(r<SPActivityLog[]>),

  // AI
  runAI: () => fetch(`${BASE}/ai/run`, { method: "POST" }).then(r<{ generated: number }>),
  listAIRecs: (accountId?: string) =>
    fetch(`${BASE}/ai/recommendations${accountId ? `?account_id=${accountId}` : ""}`).then(r<SPAIRec[]>),
  ackAIRec: (recId: string, body: { status: string; actioned_by: string }) =>
    fetch(`${BASE}/ai/recommendations/${recId}/ack`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r<SPAIRec>),

  // Auth
  login: (email: string, password: string) =>
    fetch(`${BASE}/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
    }).then(r<any>),
  resetPassword: (email: string, new_password: string) =>
    fetch(`${BASE}/auth/reset-password`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, new_password }),
    }).then(r<{ detail: string }>),

  // Reports
  reportAckTime: () => fetch(`${BASE}/reports/po-acknowledgment-time`).then(r<any[]>),
  reportETA: () => fetch(`${BASE}/reports/eta-revisions`).then(r<any[]>),
  reportAdoption: () => fetch(`${BASE}/reports/adoption`).then(r<any[]>),
  reportNotResponding: () => fetch(`${BASE}/reports/not-responding`).then(r<any[]>),
};
