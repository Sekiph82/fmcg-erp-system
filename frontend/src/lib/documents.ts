import { apiClient } from "./api";

export type DocumentCategory =
  | "SOP"
  | "WORK_INSTRUCTION"
  | "QC_DOCUMENT"
  | "CUSTOMS_DOCUMENT"
  | "INVOICE"
  | "SHIPMENT_DOCUMENT"
  | "PAYMENT_PROOF"
  | "RECONCILIATION"
  | "MAINTENANCE_MANUAL"
  | "HR_DOCUMENT"
  // Marketing categories
  | "CAMPAIGN_DOCUMENT"
  | "INFLUENCER_CONTRACT"
  | "SURVEY_DOCUMENT"
  | "BRAND_SPEND_INVOICE"
  | "TRADE_SPEND_APPROVAL"
  | "MARKETING_CREATIVE"
  | "OTHER";

export type DocumentStatus = "DRAFT" | "APPROVED" | "OBSOLETE" | "ARCHIVED";

export const CATEGORY_LABELS: Record<DocumentCategory, string> = {
  SOP: "SOP",
  WORK_INSTRUCTION: "Work Instruction",
  QC_DOCUMENT: "QC Document",
  CUSTOMS_DOCUMENT: "Customs Document",
  INVOICE: "Invoice",
  SHIPMENT_DOCUMENT: "Shipment Document",
  PAYMENT_PROOF: "Payment Proof",
  RECONCILIATION: "Reconciliation",
  MAINTENANCE_MANUAL: "Maintenance Manual",
  HR_DOCUMENT: "HR Document",
  // Marketing
  CAMPAIGN_DOCUMENT: "Campaign Document",
  INFLUENCER_CONTRACT: "Influencer Contract",
  SURVEY_DOCUMENT: "Survey Document",
  BRAND_SPEND_INVOICE: "Brand Spend Invoice",
  TRADE_SPEND_APPROVAL: "Trade Spend Approval",
  MARKETING_CREATIVE: "Marketing Creative",
  OTHER: "Other",
};

// Marketing document entity types
export const MARKETING_ENTITY_TYPES = {
  CAMPAIGN: "mkt_campaign",
  PROMOTION: "mkt_promotion",
  INFLUENCER: "mkt_influencer",
  SURVEY: "mkt_survey",
  BRAND_SPEND: "mkt_brand_spend",
  TRADE_SPEND: "mkt_trade_spend",
  STORE: "mkt_store",
} as const;

// Entity type constants – use these when linking documents to ERP records
export const ENTITY_TYPES = {
  MPESA_TRANSACTION: "mpesa_transaction",
  PURCHASE_ORDER: "purchase_order",
  SALES_ORDER: "sales_order",
  INVOICE: "invoice",
  SHIPMENT: "shipment",
  INTERNATIONAL_SHIPMENT: "international_shipment",
  QC_INSPECTION: "qc_inspection",
  PRODUCTION_ORDER: "production_order",
  GOODS_RECEIPT: "goods_receipt",
  SUPPLIER: "supplier",
  EMPLOYEE: "employee",
  ASSET: "asset",
  DELIVERY_TRIP: "delivery_trip",
  CASH_TRANSACTION: "cash_transaction",
  PAYROLL_PERIOD: "payroll_period",
  // Marketing
  CAMPAIGN: "mkt_campaign",
  PROMOTION: "mkt_promotion",
  INFLUENCER: "mkt_influencer",
  SURVEY: "mkt_survey",
  BRAND_SPEND: "mkt_brand_spend",
  TRADE_SPEND: "mkt_trade_spend",
} as const;

export interface DocumentShort {
  id: string;
  title: string;
  category: DocumentCategory;
  version: number;
  status: DocumentStatus;
  is_latest: boolean;
  related_entity_type: string | null;
  related_entity_id: string | null;
  file_name: string | null;
  created_at: string;
}

export interface DocumentRead extends DocumentShort {
  description: string | null;
  revision_note: string | null;
  previous_version_id: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  owner_user_id: string | null;
  approved_by_id: string | null;
  file_url: string | null;
  file_size_bytes: number | null;
  mime_type: string | null;
  updated_at: string;
}

export interface DocumentVersionHistory {
  id: string;
  version: number;
  status: DocumentStatus;
  is_latest: boolean;
  revision_note: string | null;
  created_at: string;
}

export interface DocumentStats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  expiring_soon_count: number;
  expired_count: number;
  latest_only_count: number;
}

const base = "/api/v1/documents";

export const docsApi = {
  list: (params?: {
    category?: string;
    status?: string;
    related_entity_type?: string;
    related_entity_id?: string;
    owner_user_id?: string;
    latest_only?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }) => apiClient.get<DocumentShort[]>(`${base}/`, { params }).then((r) => r.data),

  listByEntity: (entity_type: string, entity_id: string) =>
    apiClient.get<DocumentShort[]>(`${base}/by-entity/`, {
      params: { entity_type, entity_id },
    }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<DocumentRead>(`${base}/${id}`).then((r) => r.data),

  stats: () =>
    apiClient.get<DocumentStats>(`${base}/stats/summary`).then((r) => r.data),

  create: (data: Record<string, unknown>) =>
    apiClient.post<DocumentRead>(`${base}/`, data).then((r) => r.data),

  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch<DocumentRead>(`${base}/${id}`, data).then((r) => r.data),

  approve: (id: string, data?: { effective_date?: string; expiry_date?: string }) =>
    apiClient.post<DocumentRead>(`${base}/${id}/approve`, data ?? {}).then((r) => r.data),

  obsolete: (id: string) =>
    apiClient.post<DocumentRead>(`${base}/${id}/obsolete`).then((r) => r.data),

  archive: (id: string) =>
    apiClient.post<DocumentRead>(`${base}/${id}/archive`).then((r) => r.data),

  newVersion: (id: string, data: Record<string, unknown>) =>
    apiClient.post<DocumentRead>(`${base}/${id}/new-version`, data).then((r) => r.data),

  versions: (id: string) =>
    apiClient.get<DocumentVersionHistory[]>(`${base}/${id}/versions`).then((r) => r.data),
};
