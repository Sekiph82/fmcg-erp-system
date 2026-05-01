const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API}/api/v1/chatter`;

export type ReferenceType =
  | "sales_order" | "invoice" | "customer" | "purchase_order"
  | "contract" | "employee" | "product" | "other";

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
  reference_type: ReferenceType;
  reference_id: string;
  activity_type: ActivityType;
  title: string;
  message?: string;
  created_by?: string;
  visibility: Visibility;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
  comments: CommentOut[];
  attachments: AttachmentOut[];
  mentions: MentionOut[];
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

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function qs(params?: Record<string, string | number | undefined>): string {
  if (!params) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "" && v !== null) p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const chatterApi = {
  listActivities: (params?: {
    reference_type?: string; reference_id?: string;
    activity_type?: string; created_by?: string;
    search?: string; page?: number; per_page?: number;
  }) => api<ActivityPage>(`/activities${qs(params)}`),

  createActivity: (data: object) =>
    api<ActivityOut>("/activities", { method: "POST", body: JSON.stringify(data) }),

  getActivity: (id: string) => api<ActivityOut>(`/activities/${id}`),

  pinActivity: (id: string) =>
    api<ActivityOut>(`/activities/${id}/pin`, { method: "POST" }),

  getFeed: (limit = 50) => api<ActivityOut[]>(`/feed?limit=${limit}`),

  getStats: () => api<ChatterStats>("/stats"),

  postComment: (activityId: string, data: object) =>
    api<ActivityOut>(`/activities/${activityId}/comment`, {
      method: "POST", body: JSON.stringify(data),
    }),

  editComment: (commentId: string, message: string) =>
    api<CommentOut>(`/comments/${commentId}`, {
      method: "PATCH", body: JSON.stringify({ message }),
    }),

  deleteComment: (commentId: string) =>
    api<{ ok: boolean }>(`/comments/${commentId}`, { method: "DELETE" }),

  addAttachment: (activityId: string, data: object) =>
    api<ActivityOut>(`/activities/${activityId}/attach`, {
      method: "POST", body: JSON.stringify(data),
    }),

  listAIRecs: () => api<CTAIRec[]>("/ai/recs"),
  runActivitySummarizer: () =>
    api<{ generated: number }>("/ai/run/activity-summarizer", { method: "POST" }),
  runFollowUpAssistant: () =>
    api<{ generated: number }>("/ai/run/follow-up-assistant", { method: "POST" }),
  runInsightExtractor: () =>
    api<{ generated: number }>("/ai/run/insight-extractor", { method: "POST" }),
  ackAIRec: (id: string, data: { status: CTAIRecStatus }) =>
    api<CTAIRec>(`/ai/recs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
};

export const TYPE_ICON: Record<ActivityType, string> = {
  comment: "💬",
  system_event: "⚙️",
  status_change: "🔄",
  assignment: "👤",
  attachment_added: "📎",
  approval_action: "✅",
  notification_event: "🔔",
};

export const TYPE_COLOR: Record<ActivityType, string> = {
  comment: "bg-blue-50 text-blue-700",
  system_event: "bg-gray-50 text-gray-600",
  status_change: "bg-orange-50 text-orange-700",
  assignment: "bg-purple-50 text-purple-700",
  attachment_added: "bg-green-50 text-green-700",
  approval_action: "bg-emerald-50 text-emerald-700",
  notification_event: "bg-yellow-50 text-yellow-700",
};

export const TYPE_BADGE: Record<ActivityType, string> = {
  comment: "bg-blue-100 text-blue-700",
  system_event: "bg-gray-100 text-gray-600",
  status_change: "bg-orange-100 text-orange-700",
  assignment: "bg-purple-100 text-purple-700",
  attachment_added: "bg-green-100 text-green-700",
  approval_action: "bg-emerald-100 text-emerald-700",
  notification_event: "bg-yellow-100 text-yellow-700",
};

export const REF_LABEL: Record<ReferenceType, string> = {
  sales_order: "Sales Order",
  invoice: "Invoice",
  customer: "Customer",
  purchase_order: "Purchase Order",
  contract: "Contract",
  employee: "Employee",
  product: "Product",
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
