/**
 * Compressor & Compressed Air Management — TypeScript types, label maps, API client.
 *
 * Data flows:
 *  compressor_records    → operational log per compressor per shift/period
 *  utility_transactions  → COMPRESSED_AIR type, cost allocation by line/dept/batch
 */
import { apiClient } from "./api";
import type {
  UtilityTransaction,
  UtilityTransactionCreate,
  UtilityTransactionUpdate,
} from "./utilityTransactions";

// ── Enums & label maps ────────────────────────────────────────────────────────

export type CompressorStatus = "RUNNING" | "STANDBY" | "FAULT" | "MAINTENANCE";

export const COMPRESSOR_STATUS_LABELS: Record<CompressorStatus, string> = {
  RUNNING:     "Running",
  STANDBY:     "Standby",
  FAULT:       "Fault",
  MAINTENANCE: "Maintenance",
};

export const COMPRESSOR_STATUS_COLORS: Record<CompressorStatus, string> = {
  RUNNING:     "text-emerald-400",
  STANDBY:     "text-amber-400",
  FAULT:       "text-red-400",
  MAINTENANCE: "text-violet-400",
};

export const COMPRESSOR_STATUS_BG: Record<CompressorStatus, string> = {
  RUNNING:     "bg-emerald-500/10 border-emerald-500/20",
  STANDBY:     "bg-amber-500/10 border-amber-500/20",
  FAULT:       "bg-red-500/10 border-red-500/20",
  MAINTENANCE: "bg-violet-500/10 border-violet-500/20",
};

export const DRYER_STATUS_COLORS: Record<string, string> = {
  ON:      "text-emerald-400",
  OFF:     "text-slate-400",
  FAULT:   "text-red-400",
  BYPASS:  "text-amber-400",
};

// ── CRUD types ────────────────────────────────────────────────────────────────

export interface CompressorRecord {
  id:        string;
  record_no: string;
  asset_id:  string;
  asset_name?: string | null;
  asset_no?:   string | null;

  record_datetime: string;
  shift_ref?:      string | null;
  department?:     string | null;
  production_line?: string | null;
  period_hours?:   number | null;

  // Period totals
  air_generated_nm3?:    number | null;
  air_unit?:             string | null;
  electricity_used_kwh?: number | null;

  // Time breakdown
  runtime_hours?:     number | null;
  load_time_hours?:   number | null;
  unload_time_hours?: number | null;
  idle_time_hours?:   number | null;

  // Pressure
  inlet_pressure_bar?:         number | null;
  discharge_pressure_bar?:     number | null;
  system_pressure_bar?:        number | null;
  receiver_tank_pressure_bar?: number | null;
  line_pressure_bar?:          number | null;

  // Flow & power
  flow_rate_m3h?:          number | null;
  power_kw?:               number | null;
  specific_energy_kwh_m3?: number | null;

  // Load
  load_pct?:                  number | null;
  running_hours_cumulative?:  number | null;
  loaded_hours_cumulative?:   number | null;

  // Air quality
  air_temperature_c?:    number | null;
  dew_point_c?:          number | null;
  pressure_dew_point_c?: number | null;

  // Dryer
  dryer_status?:      string | null;
  dryer_dew_point_c?: number | null;

  // Oil & filter
  oil_pressure_bar?: number | null;
  oil_temp_c?:       number | null;
  filter_dp_bar?:    number | null;
  oil_level?:        string | null;

  // Leak
  leak_test_done:      boolean;
  leak_estimation_pct?: number | null;
  leak_volume_nm3?:     number | null;

  // Night
  night_idle_kwh?: number | null;
  night_idle_nm3?: number | null;

  // Operational
  start_stop_count?:  number | null;
  downtime_minutes?:  number | null;
  downtime_reason?:   string | null;
  maintenance_flag:   boolean;
  status:             CompressorStatus;
  source_method:      string;
  is_anomaly:         boolean;
  anomaly_note?:      string | null;
  notes?:             string | null;

  created_at?: string | null;
  updated_at?: string | null;
}

export type CompressorRecordCreate = Omit<CompressorRecord,
  "id" | "record_no" | "asset_name" | "asset_no" | "created_at" | "updated_at"
>;

export type CompressorRecordUpdate = Partial<Omit<CompressorRecord,
  "id" | "record_no" | "asset_name" | "asset_no" | "created_at" | "updated_at"
>>;

// ── KPI & analytics types ─────────────────────────────────────────────────────

export interface AirKPIs {
  date_from?: string | null;
  date_to?:   string | null;

  total_air_nm3:          number;
  total_electricity_kwh:  number;
  specific_energy_kwh_nm3?: number | null;

  total_runtime_hours?:   number | null;
  total_load_hours?:      number | null;
  total_unload_hours?:    number | null;
  total_idle_hours?:      number | null;

  utilization_pct?:  number | null;
  idle_run_ratio?:   number | null;

  avg_discharge_pressure_bar?:     number | null;
  avg_system_pressure_bar?:        number | null;
  avg_receiver_pressure_bar?:      number | null;
  avg_line_pressure_bar?:          number | null;
  avg_pressure_drop_bar?:          number | null;

  avg_dryer_dew_point_c?: number | null;

  leak_test_count:  number;
  avg_leak_pct?:    number | null;
  total_leak_nm3?:  number | null;

  total_night_kwh?: number | null;
  night_pct?:       number | null;

  air_cost_total?:   number | null;
  air_cost_per_nm3?: number | null;

  record_count:       number;
  anomaly_count:      number;
  maintenance_count:  number;
  start_stop_total:   number;

  flag_high_idle:       boolean;
  flag_leak_detected:   boolean;
  flag_pressure_drop:   boolean;
  flag_high_night:      boolean;
  flag_poor_efficiency: boolean;
}

export interface AirTrendPoint {
  date:                string;
  air_nm3:             number;
  electricity_kwh:     number;
  load_hours:          number;
  idle_hours:          number;
  night_kwh:           number;
  avg_discharge_bar?:  number | null;
  avg_line_bar?:       number | null;
  avg_specific_energy?: number | null;
  anomaly_count:       number;
  record_count:        number;
}

export interface AirShiftPoint {
  shift_id?:       string | null;
  label:           string;
  air_nm3:         number;
  electricity_kwh: number;
  avg_specific_energy?: number | null;
  record_count:    number;
  anomaly_count:   number;
}

export interface AirBreakdownRow {
  dimension:   string;
  group_key?:  string | null;
  label:       string;
  total_nm3:   number;
  total_cost?: number | null;
  pct_of_total?: number | null;
  tx_count:    number;
}

export interface AirBreakdown {
  dimension:       string;
  rows:            AirBreakdownRow[];
  grand_total_nm3: number;
}

// ── Filters ────────────────────────────────────────────────────────────────────

export interface CompressorFilters {
  asset_id?:        string;
  department?:      string;
  shift_ref?:       string;
  prod_line?:       string;
  date_from?:       string;
  date_to?:         string;
  is_anomaly?:      boolean;
  maintenance_flag?: boolean;
  leak_test_done?:  boolean;
  status?:          CompressorStatus;
  skip?:            number;
  limit?:           number;
}

export interface CompressorAsset {
  id:       string;
  asset_no: string;
  name:     string;
}

// ── CSV download helpers ───────────────────────────────────────────────────────

export async function downloadCompressorCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename: string,
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const qs    = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
  const res = await fetch(
    `${base}/api/v1/compressor/records/export/csv${qs ? "?" + qs : ""}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob      = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a         = document.createElement("a");
  a.href          = objectUrl;
  a.download      = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

// ── API client ─────────────────────────────────────────────────────────────────

export const compressorApi = {
  async kpis(params?: Partial<CompressorFilters>): Promise<AirKPIs> {
    const r = await apiClient.get<AirKPIs>("/api/v1/compressor/kpis", { params });
    return r.data;
  },

  async dailyTrend(params?: Partial<CompressorFilters>): Promise<AirTrendPoint[]> {
    const r = await apiClient.get<AirTrendPoint[]>("/api/v1/compressor/trend/daily", { params });
    return r.data;
  },

  async shiftAnalysis(params?: Partial<CompressorFilters>): Promise<AirShiftPoint[]> {
    const r = await apiClient.get<AirShiftPoint[]>("/api/v1/compressor/trend/shift", { params });
    return r.data;
  },

  async breakdown(
    dimension: "department" | "line" | "machine" | "building_area" | "shift",
    params?: Partial<CompressorFilters>,
  ): Promise<AirBreakdown> {
    const r = await apiClient.get<AirBreakdown>("/api/v1/compressor/breakdown", {
      params: { ...params, dimension },
    });
    return r.data;
  },

  async listAssets(): Promise<CompressorAsset[]> {
    const r = await apiClient.get<CompressorAsset[]>("/api/v1/compressor/assets");
    return r.data;
  },

  async listRecords(params?: Partial<CompressorFilters>): Promise<CompressorRecord[]> {
    const r = await apiClient.get<CompressorRecord[]>("/api/v1/compressor/records", { params });
    return r.data;
  },

  async getRecord(id: string): Promise<CompressorRecord> {
    const r = await apiClient.get<CompressorRecord>(`/api/v1/compressor/records/${id}`);
    return r.data;
  },

  async createRecord(data: CompressorRecordCreate): Promise<CompressorRecord> {
    const r = await apiClient.post<CompressorRecord>("/api/v1/compressor/records", data);
    return r.data;
  },

  async updateRecord(id: string, data: CompressorRecordUpdate): Promise<CompressorRecord> {
    const r = await apiClient.patch<CompressorRecord>(`/api/v1/compressor/records/${id}`, data);
    return r.data;
  },

  async deleteRecord(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/compressor/records/${id}`).then((r) => r.data);
  },

  async listTransactions(params?: Record<string, unknown>): Promise<UtilityTransaction[]> {
    const r = await apiClient.get<UtilityTransaction[]>("/api/v1/compressor/transactions", { params });
    return r.data;
  },

  async createTransaction(data: UtilityTransactionCreate): Promise<UtilityTransaction> {
    const r = await apiClient.post<UtilityTransaction>("/api/v1/compressor/transactions", data);
    return r.data;
  },

  async updateTransaction(id: string, data: UtilityTransactionUpdate): Promise<UtilityTransaction> {
    const r = await apiClient.patch<UtilityTransaction>(`/api/v1/compressor/transactions/${id}`, data);
    return r.data;
  },

  async deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/compressor/transactions/${id}`).then((r) => r.data);
  },
};
