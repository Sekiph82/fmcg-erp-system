import { apiClient } from "./api";

export type ApprovalModule =
  | "PURCHASE_ORDER" | "PURCHASE_REQUISITION" | "BUDGET"
  | "PRODUCTION_ORDER" | "SALES_INVOICE" | "EXPENSE"
  | "CONTRACT" | "PRICE_LIST" | "CREDIT_NOTE" | "OTHER";

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "ESCALATED" | "CANCELLED";

export interface ApprovalStep {
  id: string;
  request_id: string;
  level: number;
  required_role: string;
  status: ApprovalStatus;
  sla_deadline?: string | null;
  action_at?: string | null;
  action_by_id?: string | null;
  action_by_name?: string | null;
  notes?: string | null;
  rejection_reason?: string | null;
  created_at: string;
}

export interface ApprovalRequest {
  id: string;
  module: ApprovalModule;
  object_id: string;
  object_ref: string;
  amount?: number | null;
  currency: string;
  status: ApprovalStatus;
  current_level: number;
  max_level: number;
  description?: string | null;
  requested_by_id?: string | null;
  requested_by_name?: string | null;
  final_action_at?: string | null;
  created_at: string;
  steps: ApprovalStep[];
}

export interface ApprovalRule {
  id: string;
  module: ApprovalModule;
  level: number;
  required_role: string;
  amount_min: number;
  amount_max?: number | null;
  sla_hours: number;
  is_active: boolean;
  description?: string | null;
  created_at: string;
}

const BASE = "/api/v1/approvals";

export const approvalsApi = {
  async myPending(): Promise<ApprovalRequest[]> {
    const r = await apiClient.get<ApprovalRequest[]>(`${BASE}/`);
    return r.data;
  },
  async all(params?: { status?: string; module?: string }): Promise<ApprovalRequest[]> {
    const r = await apiClient.get<ApprovalRequest[]>(`${BASE}/all`, { params });
    return r.data;
  },
  async get(id: string): Promise<ApprovalRequest> {
    const r = await apiClient.get<ApprovalRequest>(`${BASE}/${id}`);
    return r.data;
  },
  async submit(data: {
    module: ApprovalModule; object_id: string; object_ref: string;
    amount?: number; currency?: string; description?: string;
  }): Promise<ApprovalRequest> {
    const r = await apiClient.post<ApprovalRequest>(`${BASE}/submit`, data);
    return r.data;
  },
  async approve(id: string, notes?: string): Promise<ApprovalRequest> {
    const r = await apiClient.post<ApprovalRequest>(`${BASE}/${id}/approve`, { notes });
    return r.data;
  },
  async reject(id: string, reason: string): Promise<ApprovalRequest> {
    const r = await apiClient.post<ApprovalRequest>(`${BASE}/${id}/reject`, { reason });
    return r.data;
  },
  async cancel(id: string): Promise<ApprovalRequest> {
    const r = await apiClient.post<ApprovalRequest>(`${BASE}/${id}/cancel`);
    return r.data;
  },
  async listRules(module?: string): Promise<ApprovalRule[]> {
    const r = await apiClient.get<ApprovalRule[]>(`${BASE}/rules/`, { params: module ? { module } : undefined });
    return r.data;
  },
  async createRule(data: {
    module: ApprovalModule; level: number; required_role: string;
    amount_min?: number; amount_max?: number; sla_hours?: number; description?: string;
  }): Promise<ApprovalRule> {
    const r = await apiClient.post<ApprovalRule>(`${BASE}/rules/`, data);
    return r.data;
  },
  async updateRule(id: string, data: Partial<{
    required_role: string; amount_min: number; amount_max: number;
    sla_hours: number; is_active: boolean; description: string;
  }>): Promise<ApprovalRule> {
    const r = await apiClient.patch<ApprovalRule>(`${BASE}/rules/${id}`, data);
    return r.data;
  },
  async deleteRule(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/rules/${id}`);
  },
};

export const STATUS_COLOR: Record<ApprovalStatus, string> = {
  PENDING:   "bg-amber-100 text-amber-700",
  APPROVED:  "bg-green-100 text-green-700",
  REJECTED:  "bg-red-100 text-red-700",
  ESCALATED: "bg-orange-100 text-orange-700",
  CANCELLED: "bg-gray-100 text-gray-500",
};
