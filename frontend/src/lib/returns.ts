import { apiClient } from "./api";

export type ReturnReason = "DAMAGED" | "EXPIRED" | "WRONG_ITEM" | "OVERSTOCKED" | "QUALITY_ISSUE" | "CUSTOMER_REFUSED" | "OTHER";
export type ReturnCondition = "RESALEABLE" | "DAMAGED" | "EXPIRED";
export type ReturnStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED" | "PROCESSED";

export interface ReturnLine {
  id: string;
  product_id: string;
  product_name?: string;
  lot_id?: string;
  quantity: number;
  unit: string;
  unit_price: number;
  return_reason?: ReturnReason;
  condition: ReturnCondition;
  notes?: string;
}

export interface ReturnOrder {
  id: string;
  return_no: string;
  original_so_id?: string;
  customer_id: string;
  customer_name?: string;
  return_date: string;
  reason: ReturnReason;
  status: ReturnStatus;
  notes?: string;
  credit_note_no?: string;
  approved_at?: string;
  created_at: string;
  lines: ReturnLine[];
  line_count: number;
}

export interface ReturnCreate {
  return_no: string;
  original_so_id?: string;
  customer_id: string;
  return_date: string;
  reason: ReturnReason;
  notes?: string;
  lines: Partial<ReturnLine>[];
}

export const returnsApi = {
  list: (params?: { customer_id?: string; status?: ReturnStatus }) =>
    apiClient.get<ReturnOrder[]>("/api/v1/returns/", { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get<ReturnOrder>(`/api/v1/returns/${id}`).then((r) => r.data),
  create: (data: ReturnCreate) =>
    apiClient.post<ReturnOrder>("/api/v1/returns/", data).then((r) => r.data),
  update: (id: string, data: Partial<ReturnOrder>) =>
    apiClient.patch<ReturnOrder>(`/api/v1/returns/${id}`, data).then((r) => r.data),
  approve: (id: string) =>
    apiClient.post(`/api/v1/returns/${id}/approve`).then((r) => r.data),
};
