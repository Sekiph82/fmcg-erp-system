import { apiClient } from "./api";

const BASE = "/api/v1/chatter";

export type ReferenceType =
  | "sales_order" | "invoice" | "customer" | "purchase_order"
  | "contract" | "employee" | "product"
  | "crm_record" | "ticket" | "project" | "production" | "document" | "batch" | "batch_recall"
  | "other";

export type ActivityType =
  | "comment" | "system_event" | "status_change" | "assignment"
  | "attachment_added" | "approval_action" | "notification_event";

export type Visibility = "private" | "team" | "global";
export type CTAIAgentType = "activity_summarizer" | "follow_up_assistant" | "insight_extractor";
export type CTAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface CommentOut {
  comment_id: string;
  activity_id: string;
  user_id?: string;
  user_name?: string;
  message: string;
  created_at: string;
  edited_at?: string;
  deleted_flag: boolean;
}

export interface AttachmentOut {
  attachment_id: string;
  activity_id: string;
  file_name: string;
  file_path?: string;
  file_size?: string;
  uploaded_by?: string;
  uploaded_at: string;
}

export interface MentionOut {
  mention_id: string;
  mentioned_user: string;
  notified_flag: boolean;
  created_at: string;
}

export interface ActivityOut {
  activity_id: string;
  reference_type: string;
  reference_id: string;
  activity_type: string;
  title: string;
  message?: string;
  created_by?: string;
  visibility: string;
  is_pinned: boolean;
  sla_due_at?: string;
  sla_breached: boolean;
  created_at: string;
  updated_at: string;
  comments: CommentOut[];
  attachments: AttachmentOut[];
  mentions: MentionOut[];
}

export interface TimelineResponse {
  items: ActivityOut[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  module_breakdown: { module: string; count: number }[];
  sla_breached_count: number;
}

export interface ActivityPage {
  items: ActivityOut[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ChatterStats {
  total_activities: number;
  total_comments: number;
  pending_mentions: number;
  by_module: { reference_type: string; count: number }[];
}

export interface CTAIRec {
  rec_id: string;
  agent_type: CTAIAgentType;
  reference_type?: string;
  reference_id?: string;
  title: string;
  body: string;
  score?: number;
  status: CTAIRecStatus;
  rec_metadata: Record<string, unknown>;
  created_at: string;
}

export const chatterApi = {
  listActivities: (params?: {
    reference_type?: string; reference_id?: string;
    activity_type?: string; created_by?: string;
    search?: string; page?: number; per_page?: number;
  }) => apiClient.get<ActivityPage>(`${BASE}/activities`, { params }).then(r => r.data),

  createActivity: (data: object) =>
    apiClient.post<ActivityOut>(`${BASE}/activities`, data).then(r => r.data),

  getActivity: (id: string) =>
    apiClient.get<ActivityOut>(`${BASE}/activities/${id}`).then(r => r.data),

  pinActivity: (id: string) =>
    apiClient.post<ActivityOut>(`${BASE}/activities/${id}/pin`).then(r => r.data),

  getFeed: (limit = 50) =>
    apiClient.get<ActivityOut[]>(`${BASE}/feed`, { params: { limit } }).then(r => r.data),

  getStats: () =>
    apiClient.get<ChatterStats>(`${BASE}/stats`).then(r => r.data),

  postComment: (activityId: string, data: object) =>
    apiClient.post<ActivityOut>(`${BASE}/activities/${activityId}/comment`, data).then(r => r.data),

  editComment: (commentId: string, message: string) =>
    apiClient.patch<CommentOut>(`${BASE}/comments/${commentId}`, { message }).then(r => r.data),

  deleteComment: (commentId: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/comments/${commentId}`).then(r => r.data),

  addAttachment: (activityId: string, data: object) =>
    apiClient.post<ActivityOut>(`${BASE}/activities/${activityId}/attach`, data).then(r => r.data),

  listAIRecs: () =>
    apiClient.get<CTAIRec[]>(`${BASE}/ai/recs`).then(r => r.data),
  runActivitySummarizer: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/activity-summarizer`).then(r => r.data),
  runFollowUpAssistant: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/follow-up-assistant`).then(r => r.data),
  runInsightExtractor: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/insight-extractor`).then(r => r.data),
  ackAIRec: (id: string, data: { status: CTAIRecStatus }) =>
    apiClient.patch<CTAIRec>(`${BASE}/ai/recs/${id}`, data).then(r => r.data),

  getTimeline: (params?: {
    reference_types?: string; created_by?: string; search?: string;
    sla_overdue_only?: boolean; page?: number; per_page?: number;
  }) => apiClient.get<TimelineResponse>(`${BASE}/timeline`, { params }).then(r => r.data),

  getSLABreached: (limit = 50) =>
    apiClient.get<ActivityOut[]>(`${BASE}/sla/breached`, { params: { limit } }).then(r => r.data),
};

export const TYPE_ICON: Record<string, string> = {
  comment: "💬",
  system_event: "⚙️",
  status_change: "🔄",
  assignment: "👤",
  attachment_added: "📎",
  approval_action: "✅",
  notification_event: "🔔",
};

export const TYPE_COLOR: Record<string, string> = {
  comment: "bg-blue-50 text-blue-700",
  system_event: "bg-gray-50 text-gray-600",
  status_change: "bg-orange-50 text-orange-700",
  assignment: "bg-purple-50 text-purple-700",
  attachment_added: "bg-green-50 text-green-700",
  approval_action: "bg-emerald-50 text-emerald-700",
  notification_event: "bg-yellow-50 text-yellow-700",
};

export const TYPE_BADGE: Record<string, string> = {
  comment: "bg-blue-100 text-blue-700",
  system_event: "bg-gray-100 text-gray-600",
  status_change: "bg-orange-100 text-orange-700",
  assignment: "bg-purple-100 text-purple-700",
  attachment_added: "bg-green-100 text-green-700",
  approval_action: "bg-emerald-100 text-emerald-700",
  notification_event: "bg-yellow-100 text-yellow-700",
};

export const REF_LABEL: Partial<Record<string, string>> & { other: string } = {
  sales_order: "Sales Order",
  invoice: "Invoice",
  customer: "Customer",
  purchase_order: "Purchase Order",
  contract: "Contract",
  employee: "Employee",
  product: "Product",
  crm_record: "CRM / Lead",
  ticket: "Helpdesk Ticket",
  project: "Project",
  production: "Production",
  document: "Document",
  batch: "Batch / Lot",
  batch_recall: "Batch Recall",
  other: "Other",
};

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}
