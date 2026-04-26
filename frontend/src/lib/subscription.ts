import { apiClient } from "@/lib/api";

const BASE = "/api/v1/recurring-orders";

// ── Types ─────────────────────────────────────────────────────────────────────

export type RecurrenceType =
  | "WEEKLY" | "BIWEEKLY" | "MONTHLY_DATE" | "MONTHLY_DAY"
  | "CUSTOM_DAYS" | "ROUTE_BASED";

export type SubscriptionStatus =
  | "DRAFT" | "ACTIVE" | "PAUSED" | "EXPIRED" | "CANCELLED" | "ARCHIVED";

export type GenerationMode =
  | "DRAFT_ONLY" | "APPROVAL_REQUIRED" | "AUTO_CONFIRM";

export type PriceSource =
  | "CURRENT_PRICE_LIST" | "FIXED_CONTRACT" | "PROMOTION";

export type GenerationStatus =
  | "GENERATED" | "SKIPPED" | "FAILED" | "PENDING_APPROVAL" | "CANCELLED";

export type PauseSkipAction =
  | "PAUSE" | "SKIP_ONE_CYCLE" | "RESUME" | "CANCEL";

export interface SubscriptionLine {
  id: string;
  template_id: string;
  item_id: string;
  item_variant_id?: string;
  uom: string;
  quantity: number;
  min_quantity?: number;
  max_quantity?: number;
  allow_quantity_change: boolean;
  price_source: PriceSource;
  fixed_price?: number;
  active_flag: boolean;
  sort_order: number;
  notes?: string;
}

export interface SubscriptionTemplate {
  id: string;
  template_code: string;
  template_name: string;
  customer_id: string;
  distributor_id?: string;
  price_list_id?: string;
  contract_id?: string;
  currency: string;
  recurrence_type: RecurrenceType;
  recurrence_interval?: number;
  recurrence_day_of_month?: number;
  recurrence_weekday?: number;
  recurrence_week_ordinal?: number;
  start_date: string;
  end_date?: string;
  next_generation_date?: string;
  last_generation_date?: string;
  status: SubscriptionStatus;
  generation_mode: GenerationMode;
  delivery_address_id?: string;
  route_id?: string;
  payment_terms_id?: string;
  allow_promotion_eval: boolean;
  price_change_threshold_pct?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
  lines: SubscriptionLine[];
}

export interface GenerationLog {
  id: string;
  template_id: string;
  generated_so_id?: string;
  scheduled_date: string;
  actual_generation_date?: string;
  generation_status: GenerationStatus;
  failure_reason?: string;
  validation_warnings?: string[];
  generated_by_system: boolean;
  notes?: string;
  created_at: string;
}

export interface PauseSkip {
  id: string;
  template_id: string;
  action_type: PauseSkipAction;
  effective_from: string;
  effective_to?: string;
  reason?: string;
  portal_request: boolean;
  notes?: string;
  requested_by?: string;
  created_at: string;
}

export interface SubAIRec {
  id: string;
  agent_type: string;
  status: string;
  severity: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  template_id?: string;
  customer_id?: string;
  created_at: string;
}

export interface UpcomingDemand {
  template_id: string;
  template_code: string;
  customer_id: string;
  item_id: string;
  uom: string;
  quantity: number;
  scheduled_date: string;
}

// ── Color / label helpers ─────────────────────────────────────────────────────

export const STATUS_COLORS: Record<SubscriptionStatus, string> = {
  DRAFT:     "bg-slate-500/20 text-slate-300",
  ACTIVE:    "bg-emerald-500/20 text-emerald-300",
  PAUSED:    "bg-amber-500/20 text-amber-300",
  EXPIRED:   "bg-red-500/20 text-red-300",
  CANCELLED: "bg-red-700/20 text-red-400",
  ARCHIVED:  "bg-slate-700/20 text-slate-500",
};

export const GEN_STATUS_COLORS: Record<GenerationStatus, string> = {
  GENERATED:        "bg-emerald-500/20 text-emerald-300",
  SKIPPED:          "bg-amber-500/20 text-amber-300",
  FAILED:           "bg-red-500/20 text-red-300",
  PENDING_APPROVAL: "bg-blue-500/20 text-blue-300",
  CANCELLED:        "bg-slate-500/20 text-slate-400",
};

export const RECURRENCE_LABELS: Record<RecurrenceType, string> = {
  WEEKLY:       "Every week",
  BIWEEKLY:     "Every 2 weeks",
  MONTHLY_DATE: "Monthly (fixed date)",
  MONTHLY_DAY:  "Monthly (weekday)",
  CUSTOM_DAYS:  "Custom interval",
  ROUTE_BASED:  "Route-based",
};

export const SEVERITY_COLORS: Record<string, string> = {
  INFO:     "bg-blue-500/20 text-blue-300",
  WARNING:  "bg-amber-500/20 text-amber-300",
  CRITICAL: "bg-red-500/20 text-red-300",
};

// ── API client ────────────────────────────────────────────────────────────────

export const subscriptionApi = {
  listTemplates: (params?: { customer_id?: string; status?: string; skip?: number; limit?: number }) =>
    apiClient.get<SubscriptionTemplate[]>(BASE, { params }),

  createTemplate: (data: Partial<SubscriptionTemplate>) =>
    apiClient.post<SubscriptionTemplate>(BASE, data),

  getTemplate: (id: string) =>
    apiClient.get<SubscriptionTemplate>(`${BASE}/${id}`),

  updateTemplate: (id: string, data: Partial<SubscriptionTemplate>) =>
    apiClient.patch<SubscriptionTemplate>(`${BASE}/${id}`, data),

  activate: (id: string) =>
    apiClient.post<SubscriptionTemplate>(`${BASE}/${id}/activate`, {}),

  cancel: (id: string) =>
    apiClient.post<SubscriptionTemplate>(`${BASE}/${id}/cancel`, {}),

  archive: (id: string) =>
    apiClient.post<SubscriptionTemplate>(`${BASE}/${id}/archive`, {}),

  pause: (id: string, data: Partial<PauseSkip>) =>
    apiClient.post<PauseSkip>(`${BASE}/${id}/pause`, data),

  skipCycle: (id: string, data: Partial<PauseSkip>) =>
    apiClient.post<PauseSkip>(`${BASE}/${id}/skip-cycle`, data),

  resume: (id: string, data: Partial<PauseSkip>) =>
    apiClient.post<PauseSkip>(`${BASE}/${id}/resume`, data),

  pauseHistory: (id: string) =>
    apiClient.get<PauseSkip[]>(`${BASE}/${id}/pause-history`),

  generateNow: (id: string, data?: { force?: boolean; notes?: string }) =>
    apiClient.post<GenerationLog>(`${BASE}/${id}/generate-now`, data ?? {}),

  generationLog: (id: string, params?: { skip?: number; limit?: number }) =>
    apiClient.get<GenerationLog[]>(`${BASE}/${id}/generation-log`, { params }),

  runScheduler: () =>
    apiClient.post<{ generated: number; skipped: number; failed: number }>(
      `${BASE}/scheduler/run`, {}
    ),

  upcomingDemand: (from_date?: string, to_date?: string) =>
    apiClient.get<UpcomingDemand[]>(`${BASE}/upcoming-demand`, {
      params: { from_date, to_date },
    }),

  reportTemplates: () =>
    apiClient.get<{ total: number; active: number; paused: number; expired: number }>(
      `${BASE}/reports/templates`
    ),

  reportGeneration: (days = 30) =>
    apiClient.get<{ status: string; count: number }[]>(`${BASE}/reports/generation`, {
      params: { days },
    }),

  reportFailed: (days = 30) =>
    apiClient.get<GenerationLog[]>(`${BASE}/reports/failed`, { params: { days } }),

  runAI: () =>
    apiClient.post<SubAIRec[]>(`${BASE}/ai/run`, {}),

  aiRecs: (params?: { agent_type?: string; status?: string }) =>
    apiClient.get<SubAIRec[]>(`${BASE}/ai/recommendations`, { params }),

  ackAIRec: (id: string, status: string) =>
    apiClient.patch<SubAIRec>(`${BASE}/ai/recommendations/${id}`, { status }),
};
