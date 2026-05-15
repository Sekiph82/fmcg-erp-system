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
};

export function statusColor(s: SignatureRequestStatus | SignatureRecordStatus): string {
  switch (s) {
    case "PENDING":  return "bg-yellow-100 text-yellow-800";
    case "SIGNED":   return "bg-green-100 text-green-800";
    case "DECLINED": return "bg-red-100 text-red-800";
    case "EXPIRED":  return "bg-gray-100 text-gray-600";
  }
}
