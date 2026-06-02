import { apiClient } from "@/lib/api";

export type TaxType =
  | "VAT" | "EXCISE" | "CUSTOMS_DUTY" | "WITHHOLDING_TAX"
  | "RAILWAY_DEV_LEVY" | "IDF_FEE" | "STAMP_DUTY" | "CORPORATE_TAX" | "OTHER";

export type TaxAppliesTo = "PURCHASE" | "SALE" | "IMPORT" | "EXPORT" | "ALL";

export type RegulatoryFlagType =
  | "CHEMICAL_COMPLIANCE" | "RESTRICTED_GOODS" | "IMPORT_LICENSE"
  | "EXPORT_LICENSE" | "PHYTOSANITARY" | "HALAL_CERTIFICATION"
  | "KEBS_STANDARD" | "KEPHIS" | "REACH_COMPLIANCE" | "OTHER";

export type ComplianceStatus =
  | "COMPLIANT" | "NON_COMPLIANT" | "PENDING" | "EXPIRED" | "NOT_APPLICABLE";

export type TxTaxStatus = "DRAFT" | "CONFIRMED" | "POSTED" | "REVERSED";

export interface CountryTaxConfig {
  id: string;
  country_code: string;
  country_name: string;
  currency: string;
  standard_vat_rate: number | null;
  reduced_vat_rate: number | null;
  zero_rated_vat: boolean;
  standard_wht_rate: number | null;
  corporate_tax_rate: number | null;
  import_duty_default_rate: number | null;
  fiscal_year_start_month: number;
  tax_authority: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface TaxCategory {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface TaxRule {
  id: string;
  country_code: string;
  tax_category_id: string;
  tax_type: TaxType;
  applies_to: TaxAppliesTo;
  rate: number;
  is_compound: boolean;
  effective_from: string | null;
  effective_to: string | null;
  description: string | null;
  is_active: boolean;
  category?: TaxCategory;
}

export interface ProductTaxMapping {
  id: string;
  country_code: string;
  tax_category_id: string;
  product_id: string | null;
  material_id: string | null;
  hs_code: string | null;
  is_zero_rated: boolean;
  is_exempt: boolean;
  notes: string | null;
  category?: TaxCategory;
}

export interface RegulatoryFlag {
  id: string;
  country_code: string;
  flag_type: RegulatoryFlagType;
  product_id: string | null;
  material_id: string | null;
  hs_code: string | null;
  status: ComplianceStatus;
  authority: string | null;
  license_no: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  document_ref: string | null;
  restriction_details: string | null;
  notes: string | null;
}

export interface TransactionTax {
  id: string;
  entity_type: string;
  entity_id: string;
  country_code: string;
  tax_rule_id: string | null;
  tax_type: TaxType;
  tax_category_code: string | null;
  description: string | null;
  taxable_amount: number;
  rate: number;
  tax_amount: number;
  currency: string;
  status: TxTaxStatus;
  notes: string | null;
}

export interface TaxSummaryRow {
  country_code: string;
  tax_type: string;
  currency: string;
  total_taxable_amount: number;
  total_tax_amount: number;
  transaction_count: number;
}

export interface RegulatoryStatusRow {
  country_code: string;
  flag_type: string;
  status: string;
  count: number;
  expiring_soon: number;
}

const BASE = "/api/v1/tax";

export const taxApi = {
  listCountries: async () => {
    const res = await apiClient.get<CountryTaxConfig[]>(`${BASE}/countries`);
    return res.data;
  },
  getCountry: async (code: string) => {
    const res = await apiClient.get<CountryTaxConfig>(`${BASE}/countries/${code}`);
    return res.data;
  },
  createCountry: async (d: object) => {
    const res = await apiClient.post<CountryTaxConfig>(`${BASE}/countries`, d);
    return res.data;
  },
  updateCountry: async (code: string, d: object) => {
    const res = await apiClient.patch<CountryTaxConfig>(`${BASE}/countries/${code}`, d);
    return res.data;
  },

  listCategories: async () => {
    const res = await apiClient.get<TaxCategory[]>(`${BASE}/categories`);
    return res.data;
  },
  createCategory: async (d: object) => {
    const res = await apiClient.post<TaxCategory>(`${BASE}/categories`, d);
    return res.data;
  },
  updateCategory: async (id: string, d: object) => {
    const res = await apiClient.patch<TaxCategory>(`${BASE}/categories/${id}`, d);
    return res.data;
  },

  listRules: async (countryCode?: string) => {
    const res = await apiClient.get<TaxRule[]>(`${BASE}/rules`, {
      params: countryCode ? { country_code: countryCode } : {},
    });
    return res.data;
  },
  createRule: async (d: object) => {
    const res = await apiClient.post<TaxRule>(`${BASE}/rules`, d);
    return res.data;
  },
  updateRule: async (id: string, d: object) => {
    const res = await apiClient.patch<TaxRule>(`${BASE}/rules/${id}`, d);
    return res.data;
  },

  listMappings: async (params?: { country_code?: string; product_id?: string; material_id?: string }) => {
    const res = await apiClient.get<ProductTaxMapping[]>(`${BASE}/mappings`, { params });
    return res.data;
  },
  createMapping: async (d: object) => {
    const res = await apiClient.post<ProductTaxMapping>(`${BASE}/mappings`, d);
    return res.data;
  },
  updateMapping: async (id: string, d: object) => {
    const res = await apiClient.patch<ProductTaxMapping>(`${BASE}/mappings/${id}`, d);
    return res.data;
  },
  deleteMapping: (id: string) => apiClient.delete(`${BASE}/mappings/${id}`).then((r) => r.data),

  listFlags: async (params?: { country_code?: string; status?: string }) => {
    const res = await apiClient.get<RegulatoryFlag[]>(`${BASE}/regulatory-flags`, { params });
    return res.data;
  },
  getExpiringFlags: async (days = 30) => {
    const res = await apiClient.get<RegulatoryFlag[]>(`${BASE}/regulatory-flags/expiring`, {
      params: { days },
    });
    return res.data;
  },
  createFlag: async (d: object) => {
    const res = await apiClient.post<RegulatoryFlag>(`${BASE}/regulatory-flags`, d);
    return res.data;
  },
  updateFlag: async (id: string, d: object) => {
    const res = await apiClient.patch<RegulatoryFlag>(`${BASE}/regulatory-flags/${id}`, d);
    return res.data;
  },
  deleteFlag: (id: string) => apiClient.delete(`${BASE}/regulatory-flags/${id}`).then((r) => r.data),

  listTransactionTaxes: async (params?: {
    entity_type?: string;
    entity_id?: string;
    country_code?: string;
  }) => {
    const res = await apiClient.get<TransactionTax[]>(`${BASE}/transaction-taxes`, { params });
    return res.data;
  },
  createTransactionTax: async (d: object) => {
    const res = await apiClient.post<TransactionTax>(`${BASE}/transaction-taxes`, d);
    return res.data;
  },
  applyTaxes: async (d: object) => {
    const res = await apiClient.post<TransactionTax[]>(`${BASE}/transaction-taxes/apply`, d);
    return res.data;
  },
  updateTransactionTax: async (id: string, d: object) => {
    const res = await apiClient.patch<TransactionTax>(`${BASE}/transaction-taxes/${id}`, d);
    return res.data;
  },
  bulkPost: async (entityType: string, entityId: string) => {
    const res = await apiClient.post<{ posted: number }>(
      `${BASE}/transaction-taxes/post/${entityType}/${entityId}`
    );
    return res.data;
  },

  getTaxSummary: async (countryCode?: string) => {
    const res = await apiClient.get<TaxSummaryRow[]>(`${BASE}/reports/tax-summary`, {
      params: countryCode ? { country_code: countryCode } : {},
    });
    return res.data;
  },
  getRegulatoryStatus: async (countryCode?: string) => {
    const res = await apiClient.get<RegulatoryStatusRow[]>(`${BASE}/reports/regulatory-status`, {
      params: countryCode ? { country_code: countryCode } : {},
    });
    return res.data;
  },
};

// ── eTIMS / KRA e-Invoice ─────────────────────────────────────────────────────

export type ETimsStatus =
  | "DRAFT"
  | "READY"
  | "PENDING"
  | "SUBMITTED"
  | "ACCEPTED"
  | "REJECTED"
  | "RETRY_PENDING"
  | "CANCELLED"
  | "FAILED"
  | "ERROR";

export interface ETimsSubmission {
  id: string;
  invoice_id: string;
  status: ETimsStatus;
  control_unit_invoice_no?: string | null;
  signed_invoice_hash?: string | null;
  invoice_qr_data?: string | null;
  transmitted_at?: string | null;
  kra_response_code?: string | null;
  kra_response_message?: string | null;
  error_message?: string | null;
  retry_count: number;
  provider_name?: string | null;
  provider_reference?: string | null;
  environment?: string | null;
  request_payload?: Record<string, unknown> | null;
  response_payload?: Record<string, unknown> | null;
  accepted_at?: string | null;
  last_attempt_at?: string | null;
  attempt_count: number;
  error_code?: string | null;
  created_at: string;
}

export interface ETimsCancelRequest {
  reason: string;
  allow_cancel_accepted?: boolean;
}

export interface ETimsProviderHealth {
  status?: string;
  provider?: string;
  environment?: string;
  live?: boolean;
  production_execution_allowed: boolean;
  detail?: string;
  note?: string;
  [key: string]: unknown;
}

const ETIMS_BASE = "/api/v1/tax/etims";

export const etimsApi = {
  listSubmissions: async (params?: { status?: ETimsStatus; limit?: number }): Promise<ETimsSubmission[]> => {
    const { data } = await apiClient.get<ETimsSubmission[]>(`${ETIMS_BASE}/submissions`, { params });
    return data;
  },

  getByInvoice: async (invoiceId: string): Promise<ETimsSubmission> => {
    const { data } = await apiClient.get<ETimsSubmission>(`${ETIMS_BASE}/submissions/${invoiceId}`);
    return data;
  },

  submit: async (invoiceId: string): Promise<ETimsSubmission> => {
    const { data } = await apiClient.post<ETimsSubmission>(`${ETIMS_BASE}/submit/${invoiceId}`);
    return data;
  },

  retry: async (submissionId: string): Promise<ETimsSubmission> => {
    const { data } = await apiClient.post<ETimsSubmission>(`${ETIMS_BASE}/retry/${submissionId}`);
    return data;
  },

  cancel: async (submissionId: string, body: ETimsCancelRequest): Promise<ETimsSubmission> => {
    const { data } = await apiClient.post<ETimsSubmission>(`${ETIMS_BASE}/cancel/${submissionId}`, body);
    return data;
  },

  poll: async (submissionId: string): Promise<ETimsSubmission> => {
    const { data } = await apiClient.post<ETimsSubmission>(`${ETIMS_BASE}/status/${submissionId}/poll`);
    return data;
  },

  health: async (): Promise<ETimsProviderHealth> => {
    const { data } = await apiClient.get<ETimsProviderHealth>(`${ETIMS_BASE}/provider/health`);
    return data;
  },
};
