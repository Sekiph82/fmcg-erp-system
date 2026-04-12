import { apiClient } from "./api";

export interface AuditLog {
  id: string;
  actor_id?: string;
  actor_email?: string;
  event_type: string;
  target_type?: string;
  target_id?: string;
  target_name?: string;
  details?: Record<string, unknown>;
  ip_address?: string;
  created_at: string;
}

export const auditApi = {
  list: (params?: {
    event_type?: string;
    actor_id?: string;
    target_type?: string;
    target_id?: string;
    skip?: number;
    limit?: number;
  }) =>
    apiClient.get<AuditLog[]>("/api/v1/audit/", { params }).then((r) => r.data),

  userHistory: (userId: string, params?: { skip?: number; limit?: number }) =>
    apiClient
      .get<AuditLog[]>(`/api/v1/audit/user/${userId}`, { params })
      .then((r) => r.data),
};

export const EVENT_LABELS: Record<string, string> = {
  LOGIN_SUCCESS: "Login",
  LOGIN_FAILED: "Login Failed",
  LOGOUT: "Logout",
  USER_CREATED: "User Created",
  USER_UPDATED: "User Updated",
  USER_ACTIVATED: "User Activated",
  USER_DEACTIVATED: "User Deactivated",
  PASSWORD_RESET: "Password Reset",
  USER_ROLE_ASSIGNED: "Role Assigned",
  USER_ROLE_REMOVED: "Role Removed",
  ROLE_CREATED: "Role Created",
  ROLE_UPDATED: "Role Updated",
  ROLE_ACTIVATED: "Role Activated",
  ROLE_DEACTIVATED: "Role Deactivated",
  ROLE_PERMISSION_ASSIGNED: "Permission Assigned",
  ROLE_PERMISSION_REMOVED: "Permission Removed",
  MPESA_PAYMENT_INITIATED: "M-Pesa Initiated",
  MPESA_PAYMENT_RETRIED: "M-Pesa Retried",
  MPESA_PAYMENT_CANCELLED: "M-Pesa Cancelled",
  MPESA_PAYMENT_RECONCILED: "M-Pesa Reconciled",
  MPESA_PAYMENT_VIEWED: "M-Pesa Viewed",
};

export function eventBadgeColor(event: string): string {
  if (event.includes("FAILED") || event.includes("DEACTIVATED") || event.includes("REMOVED") || event.includes("CANCELLED"))
    return "bg-red-100 text-red-700";
  if (event.includes("CREATED") || event.includes("SUCCESS") || event.includes("ACTIVATED") || event.includes("ASSIGNED"))
    return "bg-green-100 text-green-700";
  if (event.includes("MPESA"))
    return "bg-emerald-100 text-emerald-700";
  return "bg-gray-100 text-gray-600";
}
