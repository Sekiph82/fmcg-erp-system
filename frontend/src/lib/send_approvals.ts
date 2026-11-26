// M48.S01.T023: second-editor approval for direct marketing sends (ABM group campaigns, design single-send).
import { apiClient } from "@/lib/api";

export type SendKind = "abm" | "design";
export interface SendApproval {
  id: string; kind: string; target_id: string; company_id: string | null; payload: Record<string, unknown>;
  content_hash: string; status: "PENDING" | "APPROVED" | "REJECTED" | "USED"; requested_by: string;
  decided_by: string | null; created_at: string; decided_at: string | null;
}
export interface SendPolicy { approval_required: boolean; daily_cap: number; used_today: number }

const base = (k: SendKind) => (k === "abm" ? "/api/v1/abm/campaign-approvals" : "/api/v1/email-designs/send-approvals");

export const sendApprovalsApi = {
  policy: (k: SendKind) => apiClient.get<SendPolicy>(`${base(k)}/policy`).then((r) => r.data),
  list: (k: SendKind, status: SendApproval["status"]) =>
    apiClient.get<SendApproval[]>(base(k), { params: { status } }).then((r) => r.data),
  decide: (k: SendKind, id: string, action: "approve" | "reject") =>
    apiClient.post<SendApproval>(`${base(k)}/${id}/${action}`).then((r) => r.data),
  requestAbm: (groupId: string, body: Record<string, unknown>) =>
    apiClient.post<SendApproval>(`/api/v1/abm/groups/${groupId}/campaign/approval`, body).then((r) => r.data),
  requestDesign: (designId: string, body: Record<string, unknown>) =>
    apiClient.post<SendApproval>(`/api/v1/email-designs/${designId}/send/approval`, body).then((r) => r.data),
};

export const apiError = (e: unknown, fallback = "Request failed.") => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && "detail" in d && typeof (d as { detail: unknown }).detail === "string") return (d as { detail: string }).detail;
  return fallback;
};
