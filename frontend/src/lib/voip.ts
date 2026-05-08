import { apiClient } from "@/lib/api";

const BASE = "/api/v1/calls";

export interface CallLog {
  id: string;
  call_ref: string;
  direction: "INBOUND" | "OUTBOUND";
  phone_number: string;
  customer_id?: string;
  customer_name?: string;
  agent_id?: string;
  agent_name?: string;
  started_at?: string;
  duration_seconds?: number;
  outcome?: string;
  notes?: string;
  recording_url?: string;
  follow_up_required: boolean;
  follow_up_date?: string;
  tags?: string;
  created_at: string;
}

export interface CallScript {
  id: string;
  title: string;
  purpose: string;
  script_text: string;
  talking_points?: string;
  objection_handlers?: string;
}

export interface CallStats {
  total_calls: number;
  answered_calls: number;
  answer_rate: number;
  follow_ups_pending: number;
  avg_duration_seconds: number;
  by_outcome: Record<string, number>;
}

export const voipApi = {
  listCalls: (params?: { customer_id?: string; direction?: string; outcome?: string; limit?: number }) =>
    apiClient.get<CallLog[]>(`${BASE}/logs`, { params }).then(r => r.data),
  createCall: (data: object) =>
    apiClient.post<{ id: string; call_ref: string }>(`${BASE}/logs`, data).then(r => r.data),
  updateCall: (id: string, data: object) =>
    apiClient.patch<{ id: string }>(`${BASE}/logs/${id}`, data).then(r => r.data),

  listScripts: (purpose?: string) =>
    apiClient.get<CallScript[]>(`${BASE}/scripts`, { params: purpose ? { purpose } : {} }).then(r => r.data),
  createScript: (data: object) =>
    apiClient.post<{ id: string; title: string }>(`${BASE}/scripts`, data).then(r => r.data),

  getStats: () =>
    apiClient.get<CallStats>(`${BASE}/stats`).then(r => r.data),
};

export const OUTCOME_COLORS: Record<string, string> = {
  ANSWERED: "bg-green-100 text-green-700",
  NO_ANSWER: "bg-gray-100 text-gray-600",
  BUSY: "bg-amber-100 text-amber-700",
  VOICEMAIL: "bg-blue-100 text-blue-700",
  FAILED: "bg-red-100 text-red-600",
};

export function fmtDuration(secs?: number): string {
  if (!secs) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}m ${s}s`;
}
