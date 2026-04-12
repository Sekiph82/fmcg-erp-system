import { apiClient } from "./api";

export type CollectionMethod = "CASH" | "MPESA" | "BANK_TRANSFER" | "CHEQUE" | "CREDIT_NOTE";
export type CollectionStatus = "PENDING" | "CONFIRMED" | "RECONCILED" | "BOUNCED" | "CANCELLED";

export interface Collection {
  id: string;
  collection_no: string;
  customer_id: string;
  customer_name?: string;
  sales_order_id?: string;
  order_no?: string;
  invoice_id?: string;
  invoice_no?: string;
  rep_id?: string;
  rep_name?: string;
  collection_date: string;
  method: CollectionMethod;
  amount: number;
  currency: string;
  reference?: string;
  mpesa_code?: string;
  mpesa_phone?: string;
  bank_ref?: string;
  status: CollectionStatus;
  notes?: string;
  reconciled_at?: string;
  created_at: string;
}

export interface CollectionCreate {
  collection_no: string;
  customer_id: string;
  sales_order_id?: string;
  invoice_id?: string;
  rep_id?: string;
  collection_date: string;
  method: CollectionMethod;
  amount: number;
  currency: string;
  reference?: string;
  mpesa_code?: string;
  mpesa_phone?: string;
  notes?: string;
}

export const collectionsApi = {
  list: (params?: { customer_id?: string; status?: CollectionStatus; method?: CollectionMethod; from_date?: string; to_date?: string }) =>
    apiClient.get<Collection[]>("/api/v1/collections/", { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get<Collection>(`/api/v1/collections/${id}`).then((r) => r.data),
  create: (data: CollectionCreate) =>
    apiClient.post<Collection>("/api/v1/collections/", data).then((r) => r.data),
  confirm: (id: string) =>
    apiClient.post(`/api/v1/collections/${id}/confirm`).then((r) => r.data),
  reconcile: (id: string) =>
    apiClient.post(`/api/v1/collections/${id}/reconcile`).then((r) => r.data),
};

export const METHOD_COLORS: Record<CollectionMethod, string> = {
  CASH: "bg-green-100 text-green-700",
  MPESA: "bg-emerald-100 text-emerald-700",
  BANK_TRANSFER: "bg-blue-100 text-blue-700",
  CHEQUE: "bg-purple-100 text-purple-700",
  CREDIT_NOTE: "bg-gray-100 text-gray-700",
};

export const METHOD_ICONS: Record<CollectionMethod, string> = {
  CASH: "💵",
  MPESA: "📱",
  BANK_TRANSFER: "🏦",
  CHEQUE: "📄",
  CREDIT_NOTE: "📝",
};

export const STATUS_COLORS: Record<CollectionStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-700",
  CONFIRMED: "bg-blue-100 text-blue-700",
  RECONCILED: "bg-green-100 text-green-700",
  BOUNCED: "bg-red-100 text-red-700",
  CANCELLED: "bg-gray-100 text-gray-500",
};
