/**
 * Water Management & Soft Water Management — API client
 *
 * Water transactions use utility_transactions with utility_type in:
 *   WATER | PROCESS_WATER | WASTEWATER
 *
 * Soft water records use the dedicated soft_water_records table.
 */
import { apiClient } from "./api";

// ── Water types ───────────────────────────────────────────────────────────────

export type WaterUtilityType = "WATER" | "PROCESS_WATER" | "WASTEWATER";

export const WATER_TYPE_LABELS: Record<WaterUtilityType, string> = {
  WATER:         "Raw Water",
  PROCESS_WATER: "Process Water",
  WASTEWATER:    "Wastewater",
};

export const WATER_TYPE_COLORS: Record<WaterUtilityType, string> = {
  WATER:         "#38bdf8",   // sky-400
  PROCESS_WATER: "#34d399",   // emerald-400
  WASTEWATER:    "#f87171",   // red-400
};

// ── Water KPIs & analytics ────────────────────────────────────────────────────

export interface WaterKPIs {
  date_from:       string | null;
  date_to:         string | null;
  water_in_m3:     string;
  process_m3:      string;
  wastewater_m3:   string;
  balance_m3:      string | null;
  loss_m3:         string | null;
  loss_pct:        string | null;
  recovery_pct:    string | null;
  avg_m3_per_day:  string | null;
  total_cost:      string | null;
  avg_cost_per_day: string | null;
  avg_cost_per_m3: string | null;
  tx_count:        number;
  anomaly_count:   number;
  estimated_count: number;
  estimated_pct:   string | null;
}

export interface WaterTrendPoint {
  date:          string;
  water_in_m3:   string;
  process_m3:    string;
  wastewater_m3: string;
  total_cost:    string | null;
  anomaly_count: number;
  tx_count:      number;
}

export interface WaterBreakdownRow {
  dimension:    string;
  group_key:    string | null;
  label:        string;
  total_m3:     string;
  pct_of_total: string | null;
  total_cost:   string | null;
  tx_count:     number;
  anomaly_count: number;
}

export interface WaterBreakdown {
  dimension:      string;
  rows:           WaterBreakdownRow[];
  grand_total_m3: string;
}

export interface WaterScope {
  date_from?:    string;
  date_to?:      string;
  department?:   string;
  building_area?: string;
  line_id?:      string;
  machine_id?:   string;
  shift_id?:     string;
}

// ── Soft Water ────────────────────────────────────────────────────────────────

export type SoftenerStatus = "ONLINE" | "REGENERATING" | "STANDBY" | "FAULT";

export const SOFTENER_STATUS_LABELS: Record<SoftenerStatus, string> = {
  ONLINE:       "Online",
  REGENERATING: "Regenerating",
  STANDBY:      "Standby",
  FAULT:        "Fault",
};

export const SOFTENER_STATUS_COLORS: Record<SoftenerStatus, string> = {
  ONLINE:       "text-emerald-400",
  REGENERATING: "text-blue-400",
  STANDBY:      "text-amber-400",
  FAULT:        "text-red-400",
};

export interface SoftWaterRecord {
  id:        string;
  record_no: string;
  asset_id:  string;
  asset_name: string | null;
  asset_no:   string | null;

  record_datetime: string;

  feed_water_hardness_ppm:    number | null;
  product_water_hardness_ppm: number | null;
  feed_water_tds_ppm:         number | null;
  product_water_tds_ppm:      number | null;
  feed_ph:                    number | null;
  product_ph:                 number | null;
  conductivity_feed_uscm:     number | null;
  conductivity_product_uscm:  number | null;

  flow_rate_lpm:       number | null;
  volume_treated_m3:   number | null;
  raw_water_input_m3:  number | null;

  salt_consumed_kg:    number | null;
  resin_volume_litres: number | null;

  regen_start:        string | null;
  regen_end:          string | null;
  regeneration_count: number | null;
  service_run_hours:  number | null;

  efficiency_pct:  number | null;
  status:          SoftenerStatus;

  downtime_minutes: number | null;
  maintenance_flag: boolean;
  destination_tag:  string | null;
  department:       string | null;

  source_method: string;
  is_anomaly:    boolean;
  anomaly_note:  string | null;
  shift_ref:     string | null;
  notes:         string | null;

  created_at: string | null;
  updated_at: string | null;
}

export interface SoftWaterRecordCreate {
  asset_id:   string;
  record_datetime: string;
  feed_water_hardness_ppm?:    number | null;
  product_water_hardness_ppm?: number | null;
  feed_water_tds_ppm?:         number | null;
  product_water_tds_ppm?:      number | null;
  feed_ph?:                    number | null;
  product_ph?:                 number | null;
  conductivity_feed_uscm?:     number | null;
  conductivity_product_uscm?:  number | null;
  flow_rate_lpm?:       number | null;
  volume_treated_m3?:   number | null;
  raw_water_input_m3?:  number | null;
  salt_consumed_kg?:    number | null;
  resin_volume_litres?: number | null;
  regen_start?:         string | null;
  regen_end?:           string | null;
  regeneration_count?:  number | null;
  service_run_hours?:   number | null;
  efficiency_pct?:  number | null;
  status?:          string;
  downtime_minutes?: number | null;
  maintenance_flag?: boolean;
  destination_tag?:  string | null;
  department?:       string | null;
  source_method?:    string;
  is_anomaly?:       boolean;
  anomaly_note?:     string | null;
  shift_ref?:        string | null;
  notes?:            string | null;
}

export type SoftWaterRecordUpdate = Partial<SoftWaterRecordCreate>;

export interface SoftWaterKPIs {
  date_from: string | null;
  date_to:   string | null;
  total_volume_m3:    string;
  total_raw_input_m3: string;
  total_salt_kg:      string;
  conversion_eff_pct:   string | null;
  salt_per_m3:          string | null;
  regen_count:          number;
  regen_frequency:      string | null;
  hardness_removal_pct: string | null;
  loss_ratio:           string | null;
  compliance_pct:       string | null;
  record_count:         number;
  anomaly_count:        number;
  maintenance_count:    number;
  avg_downtime_min:     string | null;
}

export interface SoftWaterTrendPoint {
  date:               string;
  volume_treated_m3:  string;
  salt_consumed_kg:   string;
  avg_efficiency_pct: string | null;
  regen_count:        number;
  anomaly_count:      number;
  maintenance_count:  number;
  record_count:       number;
}

export interface SoftenerAsset {
  id:       string;
  asset_no: string;
  name:     string;
}

// ── Filters ───────────────────────────────────────────────────────────────────

export interface SoftWaterFilters {
  date_from?:        string;
  date_to?:          string;
  asset_id?:         string;
  department?:       string;
  shift_ref?:        string;
  is_anomaly?:       boolean;
  maintenance_flag?: boolean;
  status?:           string;
  skip?:             number;
  limit?:            number;
}

// ── Re-exports from utilityTransactions ──────────────────────────────────────

export type { UtilityTransaction, UtilityTransactionCreate, UtilityTransactionUpdate }
  from "./utilityTransactions";

// ── CSV download helper ───────────────────────────────────────────────────────

export async function downloadWaterCsv(
  params: Record<string, string | boolean | undefined>,
  filename: string,
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  const res = await fetch(`${base}/api/v1/water/transactions/export/csv?${qs}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function downloadSoftWaterCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename: string,
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  const res = await fetch(`${base}/api/v1/soft-water/records/export/csv?${qs}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── API client ────────────────────────────────────────────────────────────────

export const waterApi = {
  // ── Water analytics ──────────────────────────────────────────────────────
  async kpis(scope?: WaterScope): Promise<WaterKPIs> {
    const r = await apiClient.get<WaterKPIs>("/api/v1/water/kpis", { params: scope });
    return r.data;
  },

  async dailyTrend(scope?: WaterScope): Promise<WaterTrendPoint[]> {
    const r = await apiClient.get<WaterTrendPoint[]>("/api/v1/water/trend/daily", { params: scope });
    return r.data;
  },

  async breakdown(
    dimension: string,
    water_type: string,
    scope?: WaterScope,
  ): Promise<WaterBreakdown> {
    const r = await apiClient.get<WaterBreakdown>("/api/v1/water/breakdown", {
      params: { dimension, water_type, ...scope },
    });
    return r.data;
  },

  // ── Water transactions ────────────────────────────────────────────────────
  async listTransactions(params?: Record<string, unknown>) {
    const r = await apiClient.get("/api/v1/water/transactions", { params });
    return r.data;
  },

  async createTransaction(data: unknown) {
    const r = await apiClient.post("/api/v1/water/transactions", data);
    return r.data;
  },

  async updateTransaction(id: string, data: unknown) {
    const r = await apiClient.patch(`/api/v1/water/transactions/${id}`, data);
    return r.data;
  },

  async deleteTransaction(id: string) {
    await apiClient.delete(`/api/v1/water/transactions/${id}`).then((r) => r.data);
  },
};

export const softWaterApi = {
  // ── Soft water analytics ──────────────────────────────────────────────────
  async kpis(params?: {
    date_from?: string; date_to?: string;
    asset_id?: string; department?: string; shift_ref?: string;
  }): Promise<SoftWaterKPIs> {
    const r = await apiClient.get<SoftWaterKPIs>("/api/v1/soft-water/kpis", { params });
    return r.data;
  },

  async dailyTrend(params?: {
    date_from?: string; date_to?: string;
    asset_id?: string; department?: string;
  }): Promise<SoftWaterTrendPoint[]> {
    const r = await apiClient.get<SoftWaterTrendPoint[]>("/api/v1/soft-water/trend/daily", { params });
    return r.data;
  },

  async listAssets(): Promise<SoftenerAsset[]> {
    const r = await apiClient.get<SoftenerAsset[]>("/api/v1/soft-water/assets");
    return r.data;
  },

  // ── Records CRUD ──────────────────────────────────────────────────────────
  async listRecords(filters?: SoftWaterFilters): Promise<SoftWaterRecord[]> {
    const r = await apiClient.get<SoftWaterRecord[]>("/api/v1/soft-water/records", { params: filters });
    return r.data;
  },

  async getRecord(id: string): Promise<SoftWaterRecord> {
    const r = await apiClient.get<SoftWaterRecord>(`/api/v1/soft-water/records/${id}`);
    return r.data;
  },

  async createRecord(data: SoftWaterRecordCreate): Promise<SoftWaterRecord> {
    const r = await apiClient.post<SoftWaterRecord>("/api/v1/soft-water/records", data);
    return r.data;
  },

  async updateRecord(id: string, data: SoftWaterRecordUpdate): Promise<SoftWaterRecord> {
    const r = await apiClient.patch<SoftWaterRecord>(`/api/v1/soft-water/records/${id}`, data);
    return r.data;
  },

  async deleteRecord(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/soft-water/records/${id}`).then((r) => r.data);
  },
};
