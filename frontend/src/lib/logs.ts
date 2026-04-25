import { apiClient } from "./api";

export interface OperationalLog {
  id: string;
  module_name: string;
  entity_type: string;
  entity_id: string | null;
  action_type: string;
  status: "SUCCESS" | "FAILED" | "PENDING";
  error_message: string | null;
  request_payload: Record<string, unknown> | null;
  response_payload: Record<string, unknown> | null;
  created_by_id: string | null;
  created_by_email: string | null;
  created_at: string;
}

export interface MpesaStatusHistory {
  id: string;
  transaction_id: string;
  old_status: string | null;
  new_status: string;
  reason: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface SecurityLog {
  id: string;
  actor_id: string | null;
  actor_email: string | null;
  event_type: string;
  target_type: string | null;
  target_id: string | null;
  target_name: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface LogsPageResponse {
  items: OperationalLog[];
  total: number;
  skip: number;
  limit: number;
}

export interface OperationalLogFilters {
  module_name?: string;
  entity_type?: string;
  entity_id?: string;
  action_type?: string;
  status?: string;
  error_only?: boolean;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
}

export interface SecurityLogFilters {
  event_type?: string;
  actor_id?: string;
  target_type?: string;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
}

function buildParams(obj: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  return p.toString() ? `?${p.toString()}` : "";
}

export const logsApi = {
  listOperational: (filters: OperationalLogFilters = {}): Promise<LogsPageResponse> =>
    apiClient.get(`/logs/operational${buildParams(filters as Record<string, unknown>)}`).then((r) => r.data),

  listMpesa: (filters: Omit<OperationalLogFilters, "module_name"> = {}): Promise<LogsPageResponse> =>
    apiClient.get(`/logs/mpesa${buildParams(filters as Record<string, unknown>)}`).then((r) => r.data),

  mpesaTransactionHistory: (txId: string): Promise<MpesaStatusHistory[]> =>
    apiClient.get(`/logs/mpesa/transaction/${txId}/history`).then((r) => r.data),

  listSecurity: (filters: SecurityLogFilters = {}): Promise<SecurityLog[]> =>
    apiClient.get(`/logs/security${buildParams(filters as Record<string, unknown>)}`).then((r) => r.data),

  exportUrl: (filters: OperationalLogFilters = {}): string =>
    `/api/v1/logs/operational/export${buildParams(filters as Record<string, unknown>)}`,
};
