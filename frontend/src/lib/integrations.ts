import { apiClient } from "./api";

// ── Enums ─────────────────────────────────────────────────────────────────────

export type IntegrationProvider =
  | "MPESA"
  | "CRM"
  | "SHOPIFY"
  | "WOOCOMMERCE"
  | "BARCODE"
  | "IOT"
  | "GENERIC"
  // Marketing / AdTech
  | "META_ADS"
  | "GOOGLE_ADS"
  | "TIKTOK_ADS"
  | "SOCIAL_ANALYTICS"
  | "ECOMMERCE_ANALYTICS";

export type IntegrationStatus = "ACTIVE" | "INACTIVE" | "ERROR" | "TESTING";
export type IntegrationLogStatus = "SUCCESS" | "FAILED" | "PENDING" | "RETRYING";
export type MpesaTxStatus =
  | "PENDING"
  | "SUCCESS"
  | "FAILED"
  | "CANCELLED"
  | "TIMEOUT"
  | "REVERSED";
export type SyncStatus = "PENDING" | "SYNCED" | "FAILED" | "CONFLICT";
export type BarcodeFormat = "CODE128" | "QR" | "EAN13" | "CODE39";

// ── Provider / Config ─────────────────────────────────────────────────────────

export interface IntegrationConfig {
  id: string;
  provider: IntegrationProvider;
  name: string;
  is_active: boolean;
  webhook_url?: string;
  settings_json?: string;
  created_at: string;
  updated_at: string;
}

export interface ProviderStatus {
  provider: IntegrationProvider;
  name: string;
  status: IntegrationStatus;
  environment: string;
  is_active: boolean;
  last_tested_at?: string;
  recent_success: number;
  recent_failures: number;
}

// ── Integration Logs ──────────────────────────────────────────────────────────

export interface IntegrationLog {
  id: string;
  provider: IntegrationProvider;
  integration_type: string;
  endpoint?: string;
  status: IntegrationLogStatus;
  http_status?: number;
  duration_ms?: number;
  error_message?: string;
  request_payload?: string;
  response_payload?: string;
  created_at: string;
}

// ── M-Pesa ────────────────────────────────────────────────────────────────────

export interface MpesaInitiateRequest {
  phone_number: string;
  amount: number;
  merchant_reference: string;
  related_entity_type?: string;
  related_entity_id?: string;
}

export interface MpesaTransaction {
  id: string;
  merchant_reference: string;
  phone_number: string;
  amount: number;
  currency: string;
  status: MpesaTxStatus;
  checkout_request_id?: string;
  mpesa_receipt_number?: string;
  result_code?: number;
  result_description?: string;
  error_message?: string;
  related_entity_type?: string;
  related_entity_id?: string;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

export interface MpesaConfigStatus {
  configured: boolean;
  environment: string;
  shortcode: string;
  callback_url: string;
}

// ── Barcode ───────────────────────────────────────────────────────────────────

export interface BarcodeGenerateRequest {
  entity_type: "PRODUCT" | "LOT" | "LOCATION" | "MATERIAL";
  entity_id: string;
  barcode_format?: BarcodeFormat;
  label_template?: string;
}

export interface BarcodeLabel {
  id: string;
  entity_type: string;
  entity_id: string;
  entity_name?: string;
  barcode_value: string;
  barcode_format: BarcodeFormat;
  label_template: string;
  print_count: number;
  last_printed_at?: string;
  created_at: string;
}

export interface BarcodeGenerateResponse {
  label: BarcodeLabel;
  svg: string;
}

export interface BarcodeScanResult {
  barcode_value: string;
  entity_type: string;
  entity_id: string;
  entity_name?: string;
  details: Record<string, unknown>;
}

// ── CRM ───────────────────────────────────────────────────────────────────────

export interface CrmSyncRequest {
  direction?: "PUSH" | "PULL";
  customer_ids?: string[];
  crm_provider?: string;
}

export interface CrmSyncResult {
  total: number;
  synced: number;
  errors: string[];
}

export interface CrmCustomerMapping {
  id: string;
  customer_id: string;
  crm_provider: string;
  external_crm_id: string;
  sync_status: SyncStatus;
  sync_direction: string;
  last_sync_at?: string;
  created_at: string;
}

// ── E-commerce ────────────────────────────────────────────────────────────────

export interface EcommerceImportRequest {
  platform: string;
  since_date?: string;
  limit?: number;
}

export interface EcommerceImportResult {
  platform: string;
  imported: number;
  mapped: number;
  errors: string[];
}

export interface EcommerceOrderMapping {
  id: string;
  source_platform: string;
  external_order_id: string;
  external_order_no?: string;
  internal_order_id?: string;
  sync_status: SyncStatus;
  last_sync_at?: string;
  created_at: string;
}

// ── IoT ───────────────────────────────────────────────────────────────────────

export interface IotEventCreate {
  machine_id: string;
  event_type: string;
  value_str?: string;
  value_numeric?: number;
  unit?: string;
  machine_name?: string;
  production_order_id?: string;
  raw_payload?: string;
}

export interface IotEvent {
  id: string;
  machine_id: string;
  machine_name?: string;
  event_type: string;
  value_str?: string;
  value_numeric?: number;
  unit?: string;
  production_order_id?: string;
  received_at: string;
}

export interface MachineStatusRow {
  machine_id: string;
  machine_name?: string;
  last_event_type: string;
  last_value?: string;
  last_seen: string;
  event_count_24h: number;
}

// ── Marketing sync types ──────────────────────────────────────────────────────

export interface MarketingSyncStatus {
  provider: string;
  status: "PENDING" | "SUCCESS" | "FAILED" | "NOT_CONFIGURED";
  message: string;
  records_synced: number;
  last_sync: string | null;
}

export interface MarketingProviderSyncRow {
  provider: string;
  status: string;
  last_sync: string | null;
  error: string | null;
}

// ── API client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/integrations";

export const integrationsApi = {
  // Providers
  getProviders: async (): Promise<ProviderStatus[]> => {
    const res = await apiClient.get<ProviderStatus[]>(`${BASE}/providers`).then((r) => r.data);
    return res.data;
  },

  // Configs
  listConfigs: async (): Promise<IntegrationConfig[]> => {
    const res = await apiClient.get<IntegrationConfig[]>(`${BASE}/configs`).then((r) => r.data);
    return res.data;
  },

  // Logs
  listLogs: async (params?: {
    provider?: IntegrationProvider;
    status?: IntegrationLogStatus;
    limit?: number;
    offset?: number;
  }): Promise<IntegrationLog[]> => {
    const res = await apiClient.get<IntegrationLog[]>(`${BASE}/logs`, { params }).then((r) => r.data);
    return res.data;
  },

  getLog: async (id: string): Promise<IntegrationLog> => {
    const res = await apiClient.get<IntegrationLog>(`${BASE}/logs/${id}`).then((r) => r.data);
    return res.data;
  },

  // M-Pesa
  initiateMpesa: async (data: MpesaInitiateRequest): Promise<MpesaTransaction> => {
    const res = await apiClient.post<MpesaTransaction>(`${BASE}/mpesa/initiate`, data).then((r) => r.data);
    return res.data;
  },

  listMpesaTransactions: async (params?: {
    status?: MpesaTxStatus;
    limit?: number;
    offset?: number;
  }): Promise<MpesaTransaction[]> => {
    const res = await apiClient.get<MpesaTransaction[]>(`${BASE}/mpesa/transactions`, { params }).then((r) => r.data);
    return res.data;
  },

  getMpesaTransaction: async (id: string): Promise<MpesaTransaction> => {
    const res = await apiClient.get<MpesaTransaction>(`${BASE}/mpesa/transactions/${id}`).then((r) => r.data);
    return res.data;
  },

  retryMpesa: async (id: string): Promise<MpesaTransaction> => {
    const res = await apiClient.post<MpesaTransaction>(`${BASE}/mpesa/transactions/${id}/retry`).then((r) => r.data);
    return res.data;
  },

  checkMpesaStatus: async (id: string): Promise<MpesaTransaction> => {
    const res = await apiClient.get<MpesaTransaction>(`${BASE}/mpesa/transactions/${id}/status`).then((r) => r.data);
    return res.data;
  },

  getMpesaConfig: async (): Promise<MpesaConfigStatus> => {
    const res = await apiClient.get<MpesaConfigStatus>(`${BASE}/mpesa/config`).then((r) => r.data);
    return res.data;
  },

  // Barcode
  generateBarcode: async (data: BarcodeGenerateRequest): Promise<BarcodeGenerateResponse> => {
    const res = await apiClient.post<BarcodeGenerateResponse>(`${BASE}/barcode/generate`, data).then((r) => r.data);
    return res.data;
  },

  scanBarcode: async (barcode_value: string): Promise<BarcodeScanResult | null> => {
    const res = await apiClient.post<BarcodeScanResult | null>(`${BASE}/barcode/scan`, { barcode_value }).then((r) => r.data);
    return res.data;
  },

  listBarcodeLabels: async (entity_type?: string): Promise<BarcodeLabel[]> => {
    const res = await apiClient.get<BarcodeLabel[]>(`${BASE}/barcode/labels`, {
      params: entity_type ? { entity_type } : undefined,
    });
    return res.data;
  },

  printBarcode: async (label_id: string): Promise<BarcodeLabel> => {
    const res = await apiClient.post<BarcodeLabel>(`${BASE}/barcode/print`, { label_id }).then((r) => r.data);
    return res.data;
  },

  // CRM
  syncCrm: async (data: CrmSyncRequest): Promise<CrmSyncResult> => {
    const res = await apiClient.post<CrmSyncResult>(`${BASE}/crm/sync/customers`, data).then((r) => r.data);
    return res.data;
  },

  listCrmMappings: async (): Promise<CrmCustomerMapping[]> => {
    const res = await apiClient.get<CrmCustomerMapping[]>(`${BASE}/crm/mappings`).then((r) => r.data);
    return res.data;
  },

  getCrmStatus: async (): Promise<Record<string, unknown>> => {
    const res = await apiClient.get<Record<string, unknown>>(`${BASE}/crm/status`);
    return res.data;
  },

  // E-commerce
  importOrders: async (data: EcommerceImportRequest): Promise<EcommerceImportResult> => {
    const res = await apiClient.post<EcommerceImportResult>(`${BASE}/ecommerce/import-orders`, data).then((r) => r.data);
    return res.data;
  },

  syncInventory: async (platform: string): Promise<Record<string, unknown>> => {
    const res = await apiClient.post<Record<string, unknown>>(`${BASE}/ecommerce/sync-inventory`, null, { params: { platform } });
    return res.data;
  },

  listEcommerceOrders: async (): Promise<EcommerceOrderMapping[]> => {
    const res = await apiClient.get<EcommerceOrderMapping[]>(`${BASE}/ecommerce/orders`).then((r) => r.data);
    return res.data;
  },

  // IoT
  ingestIotEvent: async (data: IotEventCreate): Promise<IotEvent> => {
    const res = await apiClient.post<IotEvent>(`${BASE}/iot/events`, data).then((r) => r.data);
    return res.data;
  },

  listIotEvents: async (params?: {
    machine_id?: string;
    event_type?: string;
    hours?: number;
    limit?: number;
  }): Promise<IotEvent[]> => {
    const res = await apiClient.get<IotEvent[]>(`${BASE}/iot/events`, { params }).then((r) => r.data);
    return res.data;
  },

  getMachineStatus: async (): Promise<MachineStatusRow[]> => {
    const res = await apiClient.get<MachineStatusRow[]>(`${BASE}/iot/machines`).then((r) => r.data);
    return res.data;
  },

  // ── Marketing sync (placeholder hooks) ─────────────────────────────────────

  triggerAdsSync: async (provider: string = "META_ADS") => {
    const res = await apiClient.post<MarketingSyncStatus>(`${BASE}/marketing/ads-sync`, null, { params: { provider } }).then((r) => r.data);
    return res.data;
  },

  triggerSocialSync: async (provider: string = "SOCIAL_ANALYTICS") => {
    const res = await apiClient.post<MarketingSyncStatus>(`${BASE}/marketing/social-sync`, null, { params: { provider } }).then((r) => r.data);
    return res.data;
  },

  triggerEcommerceSync: async (provider: string = "SHOPIFY") => {
    const res = await apiClient.post<MarketingSyncStatus>(`${BASE}/marketing/ecommerce-sync`, null, { params: { provider } }).then((r) => r.data);
    return res.data;
  },

  getMarketingSyncStatus: async (): Promise<MarketingProviderSyncRow[]> => {
    const res = await apiClient.get<MarketingProviderSyncRow[]>(`${BASE}/marketing/sync-status`).then((r) => r.data);
    return res.data;
  },
};
