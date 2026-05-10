import { apiClient } from "./api";
import { UtilityType, UTILITY_TYPE_LABELS } from "./utilityManagement";
import { SourceMethod, DataQuality } from "./utilityDevices";

export type { SourceMethod, DataQuality };
export { UTILITY_TYPE_LABELS };

// ── Transaction-specific enums ────────────────────────────────────────────────

export type TxReferenceType =
  | "READING"
  | "BILL"
  | "BILL_ALLOCATION"
  | "BOILER_RECORD"
  | "COMPRESSOR_RECORD"
  | "SOLAR_RECORD"
  | "SOFT_WATER_RECORD"
  | "TREATMENT_RECORD"
  | "WASTEWATER_RECORD"
  | "MANUAL"
  | "CALCULATION"
  | "IMPORT"
  | "IOT";

// ── Label maps ─────────────────────────────────────────────────────────────────

export const TX_REFERENCE_TYPE_LABELS: Record<TxReferenceType, string> = {
  READING:           "Meter Reading",
  BILL:              "Utility Bill",
  BILL_ALLOCATION:   "Bill Allocation",
  BOILER_RECORD:     "Boiler Record",
  COMPRESSOR_RECORD: "Compressor Record",
  SOLAR_RECORD:      "Solar Record",
  SOFT_WATER_RECORD: "Soft Water Record",
  TREATMENT_RECORD:  "Treatment Record",
  WASTEWATER_RECORD: "Wastewater Record",
  MANUAL:            "Manual Entry",
  CALCULATION:       "Calculated",
  IMPORT:            "CSV Import",
  IOT:               "IoT / Sensor",
};

export const TX_REFERENCE_TYPE_OPTIONS = Object.entries(TX_REFERENCE_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const SOURCE_METHOD_LABELS: Record<SourceMethod, string> = {
  MANUAL:     "Manual",
  IMPORTED:   "Imported",
  API:        "External API",
  IOT:        "IoT",
  CALCULATED: "Calculated",
  ESTIMATED:  "Estimated",
};

export const SOURCE_METHOD_OPTIONS = Object.entries(SOURCE_METHOD_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const DATA_QUALITY_LABELS: Record<DataQuality, string> = {
  GOOD:      "Good",
  ESTIMATED: "Estimated",
  SUSPECT:   "Suspect",
  MISSING:   "Missing",
};

export const DATA_QUALITY_OPTIONS = Object.entries(DATA_QUALITY_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const UTILITY_TYPE_OPTIONS = Object.entries(UTILITY_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

// ── Interfaces ─────────────────────────────────────────────────────────────────

export interface UtilityTransaction {
  id: string;
  transaction_no: string;
  utility_type: UtilityType;

  transaction_date: string;
  transaction_time: string | null;
  period_start: string | null;
  period_end: string | null;

  source_meter_id: string | null;
  source_asset_id: string | null;
  device_code: string | null;
  device_name: string | null;
  asset_no: string | null;
  asset_name: string | null;

  reference_type: TxReferenceType | null;
  reference_id: string | null;

  department: string | null;
  building_area: string | null;
  line_id: string | null;
  machine_id: string | null;
  shift_id: string | null;

  production_order_id: string | null;
  batch_id: string | null;
  product_id: string | null;

  quantity: string;
  uom: string;

  tariff_id: string | null;
  tariff_code: string | null;
  cost_rate: string | null;
  total_cost: string | null;
  currency_code: string | null;

  variance_from_standard: string | null;

  source_method: SourceMethod;
  quality: DataQuality;
  estimated_or_actual: boolean;
  anomaly_flag: boolean;
  anomaly_note: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface UtilityTransactionCreate {
  transaction_no?: string | null;
  utility_type: UtilityType;
  transaction_date: string;
  transaction_time?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  source_meter_id?: string | null;
  source_asset_id?: string | null;
  reference_type?: TxReferenceType | null;
  reference_id?: string | null;
  department?: string | null;
  building_area?: string | null;
  line_id?: string | null;
  machine_id?: string | null;
  shift_id?: string | null;
  production_order_id?: string | null;
  batch_id?: string | null;
  product_id?: string | null;
  quantity: number | string;
  uom: string;
  tariff_id?: string | null;
  cost_rate?: number | string | null;
  total_cost?: number | string | null;
  currency_code?: string;
  variance_from_standard?: number | string | null;
  source_method?: SourceMethod;
  quality?: DataQuality;
  estimated_or_actual?: boolean;
  anomaly_flag?: boolean;
  anomaly_note?: string | null;
  notes?: string | null;
}

export type UtilityTransactionUpdate = Partial<UtilityTransactionCreate>;

export interface TransactionFilters {
  utility_type?: UtilityType;
  department?: string;
  building_area?: string;
  line_id?: string;
  machine_id?: string;
  shift_id?: string;
  source_meter_id?: string;
  source_asset_id?: string;
  reference_type?: TxReferenceType;
  source_method?: SourceMethod;
  quality?: DataQuality;
  is_anomaly?: boolean;
  date_from?: string;
  date_to?: string;
  batch_id?: string;
  skip?: number;
  limit?: number;
}

export interface UtilityTransactionSummaryRow {
  group_key: string;
  label: string;
  tx_count: number;
  total_quantity: string;
  uom: string;
  total_cost: string | null;
  anomaly_count: number;
}

export interface UtilityTransactionSummary {
  by_utility_type: UtilityTransactionSummaryRow[];
  by_department: UtilityTransactionSummaryRow[];
  grand_total_cost: string | null;
  grand_total_tx: number;
}

// ── API client ─────────────────────────────────────────────────────────────────

const BASE = "/api/v1/utility-management";

export const utilityTransactionsApi = {
  async list(params?: TransactionFilters): Promise<UtilityTransaction[]> {
    const res = await apiClient.get<UtilityTransaction[]>(`${BASE}/transactions`, { params });
    return res.data;
  },

  async get(id: string): Promise<UtilityTransaction> {
    const res = await apiClient.get<UtilityTransaction>(`${BASE}/transactions/${id}`);
    return res.data;
  },

  async create(data: UtilityTransactionCreate): Promise<UtilityTransaction> {
    const res = await apiClient.post<UtilityTransaction>(`${BASE}/transactions`, data);
    return res.data;
  },

  async update(id: string, data: UtilityTransactionUpdate): Promise<UtilityTransaction> {
    const res = await apiClient.patch<UtilityTransaction>(`${BASE}/transactions/${id}`, data);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/transactions/${id}`).then((r) => r.data);
  },

  async summary(params?: {
    date_from?: string;
    date_to?: string;
    department?: string;
    utility_type?: UtilityType;
  }): Promise<UtilityTransactionSummary> {
    const res = await apiClient.get<UtilityTransactionSummary>(`${BASE}/transactions/summary`, {
      params,
    });
    return res.data;
  },
};

// ── Authenticated CSV download helper ────────────────────────────────────────

export async function downloadAuthenticatedCsvTransactions(
  path: string,
  filename: string
): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const res = await fetch(`${base}${path}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
