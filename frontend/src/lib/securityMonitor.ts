import { apiClient } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SecurityDashboard {
  window_hours: number;
  risk_level: "low" | "medium" | "high" | "critical";
  stats: {
    failed_logins: number;
    successful_logins: number;
    unique_attacker_ips: number;
    security_events_total: number;
    ai_injection_attempts: number;
    blocked_tokens_in_memory: number;
  };
  top_attacker_ips: { ip: string; failures: number }[];
  as_of: string;
}

export interface FailedLoginEntry {
  id: string;
  actor_email: string | null;
  ip_address: string | null;
  reason: string | null;
  failure_count: number | null;
  created_at: string | null;
}

export interface AnomalyEntry {
  id: string;
  event_type: string;
  actor_email: string | null;
  target_name: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AccountStatus {
  username: string;
  locked: boolean;
  recent_failures: number;
}

// ── API ───────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/security";

export const securityApi = {
  dashboard: (hours = 24): Promise<SecurityDashboard> =>
    apiClient.get<SecurityDashboard>(`${BASE}/dashboard/`, { params: { hours } }).then((r) => r.data),

  failedLogins: (hours = 24, limit = 50): Promise<FailedLoginEntry[]> =>
    apiClient.get<FailedLoginEntry[]>(`${BASE}/failed-logins/`, { params: { hours, limit } }).then((r) => r.data),

  anomalies: (hours = 72, limit = 50): Promise<AnomalyEntry[]> =>
    apiClient.get<AnomalyEntry[]>(`${BASE}/anomalies/`, { params: { hours, limit } }).then((r) => r.data),

  accountStatus: (username: string): Promise<AccountStatus> =>
    apiClient.get<AccountStatus>(`${BASE}/account-status/${encodeURIComponent(username)}`).then((r) => r.data),

  unlock: (identifier: string): Promise<{ detail: string }> =>
    apiClient.post<{ detail: string }>(`${BASE}/unlock/${encodeURIComponent(identifier)}`).then((r) => r.data),
};

// ── Helpers ───────────────────────────────────────────────────────────────────

export const RISK_COLORS: Record<string, string> = {
  low: "text-green-600 bg-green-50 border-green-200",
  medium: "text-yellow-700 bg-yellow-50 border-yellow-200",
  high: "text-orange-700 bg-orange-50 border-orange-200",
  critical: "text-red-700 bg-red-50 border-red-200",
};

export const EVENT_LABELS: Record<string, string> = {
  AI_INJECTION_DETECTED: "AI Injection Attempt",
  MARGIN_FLOOR_OVERRIDE: "Margin Override",
  DUPLICATE_PAYMENT_BLOCKED: "Duplicate Payment Blocked",
  STOCK_NEGATIVE_FLAGGED: "Negative Stock Flagged",
  ACCOUNT_LOCKED: "Account Locked",
  TWO_FA_FAILED: "2FA Failed",
  SUSPICIOUS_ACTIVITY: "Suspicious Activity",
  PASSWORD_POLICY_VIOLATION: "Password Policy Violation",
};
