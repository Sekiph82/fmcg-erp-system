import { apiClient } from "@/lib/api";

const BASE = "/api/v1/esign";

export type SignatureRequestStatus = "PENDING" | "SIGNED" | "DECLINED" | "EXPIRED";
export type SignatureRecordStatus  = "PENDING" | "SIGNED" | "DECLINED";

export interface SignatureRecord {
  id:             string;
  request_id:     string;
  signer_id:      string | null;
  signer_name:    string | null;
  signer_email:   string | null;
  status:         SignatureRecordStatus;
  signed_at:      string | null;
  declined_at:    string | null;
  ip_address:     string | null;
  user_agent:     string | null;
  signature_data: string | null;
  signed_payload_hash_sha256?: string | null;
  decline_reason?: string | null;
  evidence_hash_sha256?: string | null;
  auth_method?: string | null;
  signed_document_version?: number | null;
  signed_document_id?: string | null;
}

export interface SignatureRequest {
  id:               string;
  request_no:       string;
  document_id:      string | null;
  document_type:    string;
  document_ref:     string;
  requester_id:     string | null;
  requester_name:   string | null;
  subject:          string;
  message:          string | null;
  status:           SignatureRequestStatus;
  expires_at:       string | null;
  required_count:   number;
  signed_count:     number;
  declined_count:   number;
  company_id?:       string | null;
  branch_id?:        string | null;
  department_id?:    string | null;
  factory_id?:       string | null;
  module_key?:       string | null;
  related_entity_type?: string | null;
  related_entity_id?:   string | null;
  document_hash_sha256?: string | null;
  payload_hash_sha256?:  string | null;
  completed_at?:     string | null;
  expired_at?:       string | null;
  cancelled_at?:     string | null;
  cancelled_by_id?:  string | null;
  evidence_summary?: unknown;
  audit_request_id?: string | null;
  created_at:       string;
  signature_records: SignatureRecord[];
}

export interface ESignDashboard {
  total_requests:        number;
  pending:               number;
  signed:                number;
  declined:              number;
  expired:               number;
  my_pending_signatures: number;
}

export interface CreateSignatureRequest {
  document_type: string;
  document_ref:  string;
  subject:       string;
  message?:      string;
  signer_ids:    string[];
  expires_at?:   string;
  document_id?:   string;
  company_id?:    string;
  branch_id?:     string;
  department_id?: string;
  factory_id?:    string;
  module_key?:    string;
  related_entity_type?: string;
  related_entity_id?:   string;
  document_hash_sha256?: string;
  payload_hash_sha256?:  string;
}

export const esignApi = {
  dashboard: () =>
    apiClient.get<ESignDashboard>(`${BASE}/dashboard`).then(res => res.data),

  listRequests: (status?: string) =>
    apiClient.get<SignatureRequest[]>(`${BASE}/requests${status ? `?status=${status}` : ""}`).then(res => res.data),

  pendingForMe: () =>
    apiClient.get<SignatureRequest[]>(`${BASE}/requests/pending-for-me`).then(res => res.data),

  getRequest: (id: string) =>
    apiClient.get<SignatureRequest>(`${BASE}/requests/${id}`).then(res => res.data),

  createRequest: (body: CreateSignatureRequest) =>
    apiClient.post<SignatureRequest>(`${BASE}/requests`, body).then(res => res.data),

  sign: (id: string, signatureData: string, signedPayloadHash?: string) =>
    apiClient.post<SignatureRequest>(`${BASE}/requests/${id}/sign`, {
      signature_data: signatureData,
      signed_payload_hash_sha256: signedPayloadHash,
    }).then(res => res.data),

  decline: (id: string, reason?: string) =>
    apiClient.post<SignatureRequest>(`${BASE}/requests/${id}/decline`, { reason }).then(res => res.data),

  /** The caller's own IT-registered signature (nobody can read anyone else's). */
  mySignature: () =>
    apiClient.get<MySignature>(`${BASE}/my-signature`).then(res => res.data),
  /** IT only: who has a signature on file (metadata, never images). */
  listRegistered: (search?: string) =>
    apiClient.get<RegisteredSignature[]>(`${BASE}/signatures`, { params: { search } }).then(res => res.data),
  register: (userId: string, signatureImage: string) =>
    apiClient.put(`${BASE}/signatures/${userId}`, { signature_image: signatureImage }).then(res => res.data),
  revoke: (userId: string, reason: string) =>
    apiClient.delete(`${BASE}/signatures/${userId}`, { params: { reason } }).then(res => res.data),
};

// ── M48.S01.T009 provider e-signature (DocuSign / Adobe Acrobat Sign) ─────────
export type ProviderCode = "LOCAL" | "DOCUSIGN" | "ADOBE_SIGN";
export interface ProviderReadiness {
  provider: ProviderCode; label: string; mode: "LOCAL" | "SIMULATED" | "LIVE"; ready: boolean; reasons: string[];
  live_enabled: boolean; settings: Record<string, string | null>; secrets_set: Record<string, boolean>; updated_by: string | null;
}
export interface ProviderEnvelope {
  id: string; provider: "DOCUSIGN" | "ADOBE_SIGN"; provider_label: string; mode: "SIMULATED" | "LIVE";
  source_type: "QUOTATION" | "CONTRACT"; source_id: string; source_ref: string; status: string;
  provider_ref: string | null; provider_status: string | null; signer_name: string; signer_email: string; expire_days: number;
  snapshot_sha256: string; source_fingerprint: string; signed_sha256: string | null; evidence_sha256: string | null;
  provider_certified: boolean; evidence_label: string | null; erp_applied: string | null; error: string | null;
  timeline: { at: string; status: string; via: string; note: string | null; provider_status: string | null }[];
  completed_at: string | null; created_at: string | null; last_checked_at: string | null; can_cancel: boolean; can_reconcile: boolean;
}
export interface ProviderSendBody {
  provider: "DOCUSIGN" | "ADOBE_SIGN"; source_type: "QUOTATION" | "CONTRACT"; source_id: string;
  signer_name: string; signer_email: string; expire_days: number;
}

export const providerSignApi = {
  readiness: () => apiClient.get<ProviderReadiness[]>(`${BASE}/providers`).then(r => r.data),
  configure: (provider: string, body: { settings: Record<string, string>; secrets: Record<string, string>; live_enabled?: boolean }) =>
    apiClient.put<ProviderReadiness>(`${BASE}/providers/${provider}`, body).then(r => r.data),
  send: (body: ProviderSendBody, idempotencyKey: string) =>
    apiClient.post<ProviderEnvelope>(`${BASE}/providers/send`, body, { headers: { "Idempotency-Key": idempotencyKey } }).then(r => r.data),
  list: (sourceType?: string, sourceId?: string) =>
    apiClient.get<ProviderEnvelope[]>(`${BASE}/providers/envelopes`, { params: { source_type: sourceType, source_id: sourceId } }).then(r => r.data),
  reconcile: (id: string) => apiClient.post<ProviderEnvelope>(`${BASE}/providers/envelopes/${id}/reconcile`).then(r => r.data),
  cancel: (id: string, reason: string) => apiClient.post<ProviderEnvelope>(`${BASE}/providers/envelopes/${id}/cancel`, { reason }).then(r => r.data),
  /** snapshot | signed | evidence: the server checks the stored SHA-256 before serving. */
  download: async (id: string, kind: "snapshot" | "signed" | "evidence", fileName: string) => {
    const r = await apiClient.get(`${BASE}/providers/envelopes/${id}/files/${kind}`, { responseType: "blob" });
    const url = URL.createObjectURL(r.data as Blob);
    const a = document.createElement("a");
    a.href = url; a.download = fileName; a.click();
    URL.revokeObjectURL(url);
    return { sha256: r.headers["x-content-sha256"] as string, evidence: r.headers["x-evidence-status"] as string };
  },
};

export interface MySignature { has_signature: boolean; signature_image?: string; image_sha256?: string; registered_at?: string }
export interface RegisteredSignature {
  user_id: string; username: string; full_name: string | null; has_signature: boolean;
  registered_at: string | null; image_sha256: string | null;
}

export function statusColor(s: SignatureRequestStatus | SignatureRecordStatus): string {
  switch (s) {
    case "PENDING":  return "bg-yellow-100 text-yellow-800";
    case "SIGNED":   return "bg-green-100 text-green-800";
    case "DECLINED": return "bg-red-100 text-red-800";
    case "EXPIRED":  return "bg-gray-100 text-gray-600";
  }
}
