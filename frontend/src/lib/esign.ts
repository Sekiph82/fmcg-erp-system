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
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const esignApi = {
  dashboard: () =>
    apiFetch<ESignDashboard>(`${BASE}/dashboard`),

  listRequests: (status?: string) =>
    apiFetch<SignatureRequest[]>(`${BASE}/requests${status ? `?status=${status}` : ""}`),

  pendingForMe: () =>
    apiFetch<SignatureRequest[]>(`${BASE}/requests/pending-for-me`),

  getRequest: (id: string) =>
    apiFetch<SignatureRequest>(`${BASE}/requests/${id}`),

  createRequest: (body: CreateSignatureRequest) =>
    apiFetch<SignatureRequest>(`${BASE}/requests`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  sign: (id: string, signatureData: string) =>
    apiFetch<SignatureRequest>(`${BASE}/requests/${id}/sign`, {
      method: "POST",
      body: JSON.stringify({ signature_data: signatureData }),
    }),

  decline: (id: string, reason?: string) =>
    apiFetch<SignatureRequest>(`${BASE}/requests/${id}/decline`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};

export function statusColor(s: SignatureRequestStatus | SignatureRecordStatus): string {
  switch (s) {
    case "PENDING":  return "bg-yellow-100 text-yellow-800";
    case "SIGNED":   return "bg-green-100 text-green-800";
    case "DECLINED": return "bg-red-100 text-red-800";
    case "EXPIRED":  return "bg-gray-100 text-gray-600";
  }
}
