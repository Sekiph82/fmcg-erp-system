const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/notifications`;

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type NotificationType =
  | "info" | "warning" | "error" | "approval_required"
  | "task_assigned" | "reminder" | "system_alert" | "announcement";

export type NotificationPriority = "low" | "normal" | "high" | "critical";
export type NotificationChannel = "in_app" | "email" | "sms" | "whatsapp";
export type NotificationStatus = "pending" | "sent" | "failed" | "read";
export type NCNotifAIAgentType = "optimizer" | "behavior_analyzer";
export type NCNotifAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface NCNotification {
  notification_id: string;
  user_id: string;
  user_name: string | null;
  title: string;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  channel: NotificationChannel;
  status: NotificationStatus;
  reference_type: string | null;
  reference_id: string | null;
  module: string | null;
  read_flag: boolean;
  read_at: string | null;
  sent_at: string | null;
  scheduled_for: string | null;
  retry_count: number;
  error_message: string | null;
  created_by: string | null;
  created_at: string;
}

export interface NCPreference {
  preference_id: string;
  user_id: string;
  notification_type: NotificationType;
  channel: NotificationChannel;
  enabled_flag: boolean;
  muted_until: string | null;
  updated_at: string;
}

export interface NCTemplate {
  template_id: string;
  template_code: string;
  template_name: string;
  notification_type: NotificationType;
  channel: NotificationChannel;
  title_template: string;
  message_template: string;
  language: string;
  active_flag: boolean;
  module: string | null;
  created_at: string;
}

export interface NCSchedule {
  schedule_id: string;
  user_id: string;
  title: string;
  message: string;
  notification_type: NotificationType;
  channel: NotificationChannel;
  scheduled_for: string;
  recurring: boolean;
  recurrence_days: number | null;
  reference_type: string | null;
  reference_id: string | null;
  active_flag: boolean;
  last_sent_at: string | null;
  created_at: string;
}

export interface NCDashboard {
  total_notifications: number;
  unread_count: number;
  sent_today: number;
  failed_count: number;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
  by_channel: Record<string, number>;
  top_modules: { module: string; count: number }[];
  pending_schedules: number;
}

export interface NCNotifAIRec {
  rec_id: string;
  agent_type: NCNotifAIAgentType;
  status: NCNotifAIRecStatus;
  title: string;
  body: string;
  user_id: string | null;
  score: number | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Color / Label Maps ────────────────────────────────────────────────────────

export const TYPE_COLOR: Record<NotificationType, string> = {
  info: "bg-blue-100 text-blue-700",
  warning: "bg-yellow-100 text-yellow-800",
  error: "bg-red-100 text-red-700",
  approval_required: "bg-purple-100 text-purple-700",
  task_assigned: "bg-teal-100 text-teal-700",
  reminder: "bg-orange-100 text-orange-700",
  system_alert: "bg-red-200 text-red-800",
  announcement: "bg-indigo-100 text-indigo-700",
};

export const TYPE_ICON: Record<NotificationType, string> = {
  info: "ℹ",
  warning: "⚠",
  error: "✖",
  approval_required: "✓",
  task_assigned: "📋",
  reminder: "🔔",
  system_alert: "🚨",
  announcement: "📢",
};

export const PRIORITY_COLOR: Record<NotificationPriority, string> = {
  low: "bg-gray-100 text-gray-500",
  normal: "bg-blue-100 text-blue-600",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export const CHANNEL_LABEL: Record<NotificationChannel, string> = {
  in_app: "In-App",
  email: "Email",
  sms: "SMS",
  whatsapp: "WhatsApp",
};

export const STATUS_COLOR: Record<NotificationStatus, string> = {
  pending: "text-yellow-600",
  sent: "text-green-600",
  failed: "text-red-600",
  read: "text-gray-400",
};

export const NOTIFICATION_TYPES: NotificationType[] = [
  "info","warning","error","approval_required","task_assigned","reminder","system_alert","announcement"
];

export const CHANNELS: NotificationChannel[] = ["in_app","email","sms","whatsapp"];
export const PRIORITIES: NotificationPriority[] = ["low","normal","high","critical"];

// ── API ───────────────────────────────────────────────────────────────────────

export const notificationsApi = {
  getDashboard: () => req<NCDashboard>("/dashboard"),

  list: (params?: {
    user_id?: string; notification_type?: string; priority?: string;
    read_flag?: boolean; module?: string; limit?: number; offset?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.user_id) q.set("user_id", params.user_id);
    if (params?.notification_type) q.set("notification_type", params.notification_type);
    if (params?.priority) q.set("priority", params.priority);
    if (params?.read_flag != null) q.set("read_flag", String(params.read_flag));
    if (params?.module) q.set("module", params.module);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    return req<NCNotification[]>(`/?${q}`);
  },
  create: (d: object) => req<NCNotification>("/", { method: "POST", body: JSON.stringify(d) }),
  get: (id: string) => req<NCNotification>(`/${id}`),
  markRead: (id: string) => req<NCNotification>(`/${id}/read`, { method: "PATCH" }),
  markAllRead: (user_id: string) =>
    req<{ marked_read: number }>(`/mark-all-read?user_id=${user_id}`, { method: "POST" }),
  delete: (id: string) => req<void>(`/${id}`, { method: "DELETE" }),
  getUnreadCount: (user_id: string) =>
    req<{ user_id: string; unread_count: number }>(`/unread-count?user_id=${user_id}`),

  sendBulk: (d: object) => req<NCNotification[]>("/send/bulk", { method: "POST", body: JSON.stringify(d) }),
  sendFromTemplate: (d: object) =>
    req<NCNotification>("/send/from-template", { method: "POST", body: JSON.stringify(d) }),

  listPreferences: (user_id: string) => req<NCPreference[]>(`/preferences/${user_id}`),
  upsertPreference: (user_id: string, d: object) =>
    req<NCPreference>(`/preferences/${user_id}`, { method: "POST", body: JSON.stringify(d) }),
  seedPreferences: (user_id: string) =>
    req<{ created: number }>(`/preferences/${user_id}/seed-defaults`, { method: "POST" }),

  listTemplates: (module?: string, active_only?: boolean) => {
    const q = new URLSearchParams();
    if (module) q.set("module", module);
    if (active_only) q.set("active_only", "true");
    return req<NCTemplate[]>(`/templates?${q}`);
  },
  createTemplate: (d: object) => req<NCTemplate>("/templates", { method: "POST", body: JSON.stringify(d) }),
  seedTemplates: () => req<{ created: number }>("/templates/seed-defaults", { method: "POST" }),

  listSchedules: (user_id?: string) =>
    req<NCSchedule[]>(`/schedules${user_id ? `?user_id=${user_id}` : ""}`),
  createSchedule: (d: object) => req<NCSchedule>("/schedules", { method: "POST", body: JSON.stringify(d) }),
  processDueSchedules: () => req<{ processed: number }>("/schedules/process-due", { method: "POST" }),
  deactivateSchedule: (id: string) => req<void>(`/schedules/${id}`, { method: "DELETE" }),

  reportDelivery: () => req<object[]>("/reports/delivery"),
  reportUnread: () => req<object[]>("/reports/unread"),
  reportFailed: () => req<NCNotification[]>("/reports/failed"),

  runOptimizer: () => req<NCNotifAIRec[]>("/ai/run-optimizer", { method: "POST" }),
  runBehaviorAnalyzer: () => req<NCNotifAIRec[]>("/ai/run-behavior-analyzer", { method: "POST" }),
  listAIRecs: (status?: string) =>
    req<NCNotifAIRec[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackAIRec: (id: string, d: object) =>
    req<NCNotifAIRec>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
