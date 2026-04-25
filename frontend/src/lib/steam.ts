/**
 * Steam & Boiler Management — TypeScript types, label maps, API client.
 *
 * Data flows:
 *  boiler_steam_records  → operational log per boiler per shift/period
 *  utility_transactions  → STEAM type, cost allocation by line/dept/batch
 */
import { apiClient } from "./api";
import type { UtilityTransaction, UtilityTransactionCreate, UtilityTransactionUpdate } from "./utilityTransactions";

// ── Enums & label maps ────────────────────────────────────────────────────────

export type BoilerStatus = "RUNNING" | "STANDBY" | "SHUTDOWN" | "FAULT";

export const BOILER_STATUS_LABELS: Record<BoilerStatus, string> = {
  RUNNING:  "Running",
  STANDBY:  "Standby",
  SHUTDOWN: "Shutdown",
  FAULT:    "Fault",
};

export const BOILER_STATUS_COLORS: Record<BoilerStatus, string> = {
  RUNNING:  "text-emerald-400",
  STANDBY:  "text-amber-400",
  SHUTDOWN: "text-slate-400",
  FAULT:    "text-red-400",
};

export const BOILER_STATUS_BG: Record<BoilerStatus, string> = {
  RUNNING:  "bg-emerald-500/10 border-emerald-500/20",
  STANDBY:  "bg-amber-500/10 border-amber-500/20",
  SHUTDOWN: "bg-slate-500/10 border-slate-500/20",
  FAULT:    "bg-red-500/10 border-red-500/20",
};

// ── CRUD types ────────────────────────────────────────────────────────────────

export interface BoilerRecord {
  id:        string;
  record_no: string;
  asset_id:  string;
  asset_name?: string | null;
  asset_no?:   string | null;

  record_datetime: string;
  shift_ref?:      string | null;
  department?:     string | null;
  period_hours?:   number | null;

  steam_pressure_bar?:  number | null;
  steam_temp_c?:        number | null;
  steam_flow_kgh?:      number | null;
  steam_quality_pct?:   number | null;
  steam_generated_kg?:  number | null;
  feedwater_consumed_m3?: number | null;
  condensate_returned_m3?: number | null;

  feed_water_temp_c?:   number | null;
  feed_water_flow_lpm?: number | null;
  feed_water_ph?:       number | null;
  feed_water_tds_ppm?:  number | null;

  blowdown_pct?:           number | null;
  blowdown_volume_litres?: number | null;

  fuel_type?:        string | null;
  fuel_consumption?: number | null;
  fuel_unit?:        string | null;

  boiler_efficiency_pct?: number | null;
  flue_gas_temp_c?:       number | null;
  o2_pct?:  number | null;
  co2_pct?: number | null;
  co_ppm?:  number | null;

  boiler_tds_ppm?:      number | null;
  boiler_ph?:           number | null;
  boiler_hardness_ppm?: number | null;
  conductivity_uscm?:   number | null;

  boiler_load_pct?:      number | null;
  burner_runtime_hours?: number | null;
  start_stop_count?:     number | null;
  running_hours_cumulative?: number | null;

  chemical_dosing_amount?: number | null;
  chemical_dosing_unit?:   string | null;

  downtime_minutes?: number | null;
  downtime_reason?:  string | null;

  maintenance_flag: boolean;
  status:           BoilerStatus;
  source_method:    string;
  is_anomaly:       boolean;
  anomaly_note?:    string | null;
  notes?:           string | null;

  created_at?: string | null;
  updated_at?: string | null;
}

export type BoilerRecordCreate = Omit<BoilerRecord,
  "id" | "record_no" | "asset_name" | "asset_no" | "created_at" | "updated_at"
>;

export type BoilerRecordUpdate = Partial<Omit<BoilerRecord,
  "id" | "record_no" | "asset_name" | "asset_no" | "created_at" | "updated_at"
>>;

// ── KPI & analytics types ─────────────────────────────────────────────────────

export interface SteamKPIs {
  date_from?: string | null;
  date_to?:   string | null;

  total_steam_generated_kg:   number;
  total_steam_generated_tons: number;
  total_feedwater_m3:         number;
  total_condensate_m3:        number;
  total_blowdown_litres:      number;
  total_fuel_consumed:        number;
  fuel_unit?:                 string | null;

  gas_per_ton_steam?:   number | null;
  water_per_ton_steam?: number | null;

  condensate_recovery_pct?: number | null;
  blowdown_loss_pct?:       number | null;

  avg_efficiency_pct?:  number | null;
  avg_boiler_load_pct?: number | null;
  avg_flue_temp_c?:     number | null;
  avg_o2_pct?:          number | null;

  total_burner_hours?:   number | null;
  total_downtime_hours?: number | null;
  availability_pct?:     number | null;
  total_start_stops:     number;

  steam_cost_total?:    number | null;
  steam_cost_per_ton?:  number | null;

  total_chemical_dosing?: number | null;

  record_count:       number;
  anomaly_count:      number;
  maintenance_count:  number;

  flag_low_condensate: boolean;
  flag_high_blowdown:  boolean;
  flag_low_efficiency: boolean;
}

export interface SteamTrendPoint {
  date:                string;
  steam_generated_kg:  number;
  fuel_consumed:       number;
  feedwater_m3:        number;
  condensate_m3:       number;
  blowdown_litres:     number;
  avg_efficiency_pct?: number | null;
  avg_boiler_load_pct?: number | null;
  downtime_minutes:    number;
  anomaly_count:       number;
  record_count:        number;
}

export interface SteamShiftPoint {
  shift_id?:          string | null;
  label:              string;
  steam_generated_kg: number;
  fuel_consumed:      number;
  avg_efficiency_pct?: number | null;
  record_count:       number;
  anomaly_count:      number;
}

export interface SteamBreakdownRow {
  dimension:   string;
  group_key?:  string | null;
  label:       string;
  total_kg:    number;
  total_cost?: number | null;
  pct_of_total?: number | null;
  tx_count:    number;
}

export interface SteamBreakdown {
  dimension:      string;
  rows:           SteamBreakdownRow[];
  grand_total_kg: number;
}

// ── Filters ────────────────────────────────────────────────────────────────────

export interface SteamFilters {
  asset_id?:    string;
  department?:  string;
  shift_ref?:   string;
  date_from?:   string;
  date_to?:     string;
  is_anomaly?:  boolean;
  maintenance_flag?: boolean;
  status?:      BoilerStatus;
  skip?:        number;
  limit?:       number;
}

export interface BoilerAsset {
  id:       string;
  asset_no: string;
  name:     string;
}

// ── CSV download helper ────────────────────────────────────────────────────────

export async function downloadBoilerCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename: string,
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const qs    = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
  const res = await fetch(`${base}/api/v1/steam/records/export/csv${qs ? "?" + qs : ""}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Export failed (${res.status}): ${text}`);
  }
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

export async function downloadSteamTxCsv(filename: string): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${base}/api/v1/steam/transactions/export/csv`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
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

export const boilerApi = {
  // ── KPIs & analytics ────────────────────────────────────────────────────────
  async kpis(params?: Partial<SteamFilters>): Promise<SteamKPIs> {
    const r = await apiClient.get<SteamKPIs>("/api/v1/steam/kpis", { params }).then((r) => r.data);
    return r.data;
  },

  async dailyTrend(params?: Partial<SteamFilters>): Promise<SteamTrendPoint[]> {
    const r = await apiClient.get<SteamTrendPoint[]>("/api/v1/steam/trend/daily", { params }).then((r) => r.data);
    return r.data;
  },

  async shiftAnalysis(params?: Partial<SteamFilters>): Promise<SteamShiftPoint[]> {
    const r = await apiClient.get<SteamShiftPoint[]>("/api/v1/steam/trend/shift", { params }).then((r) => r.data);
    return r.data;
  },

  async breakdown(
    dimension: "department" | "line" | "machine" | "building_area" | "shift",
    params?: Partial<SteamFilters>,
  ): Promise<SteamBreakdown> {
    const r = await apiClient.get<SteamBreakdown>("/api/v1/steam/breakdown", {
      params: { ...params, dimension },
    });
    return r.data;
  },

  // ── Assets dropdown ──────────────────────────────────────────────────────────
  async listAssets(): Promise<BoilerAsset[]> {
    const r = await apiClient.get<BoilerAsset[]>("/api/v1/steam/assets").then((r) => r.data);
    return r.data;
  },

  // ── Boiler records CRUD ──────────────────────────────────────────────────────
  async listRecords(params?: Partial<SteamFilters>): Promise<BoilerRecord[]> {
    const r = await apiClient.get<BoilerRecord[]>("/api/v1/steam/records", { params }).then((r) => r.data);
    return r.data;
  },

  async getRecord(id: string): Promise<BoilerRecord> {
    const r = await apiClient.get<BoilerRecord>(`/api/v1/steam/records/${id}`).then((r) => r.data);
    return r.data;
  },

  async createRecord(data: BoilerRecordCreate): Promise<BoilerRecord> {
    const r = await apiClient.post<BoilerRecord>("/api/v1/steam/records", data).then((r) => r.data);
    return r.data;
  },

  async updateRecord(id: string, data: BoilerRecordUpdate): Promise<BoilerRecord> {
    const r = await apiClient.patch<BoilerRecord>(`/api/v1/steam/records/${id}`, data).then((r) => r.data);
    return r.data;
  },

  async deleteRecord(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/steam/records/${id}`).then((r) => r.data);
  },

  // ── STEAM transactions CRUD ──────────────────────────────────────────────────
  async listTransactions(params?: Record<string, unknown>): Promise<UtilityTransaction[]> {
    const r = await apiClient.get<UtilityTransaction[]>("/api/v1/steam/transactions", { params }).then((r) => r.data);
    return r.data;
  },

  async createTransaction(data: UtilityTransactionCreate): Promise<UtilityTransaction> {
    const r = await apiClient.post<UtilityTransaction>("/api/v1/steam/transactions", data).then((r) => r.data);
    return r.data;
  },

  async updateTransaction(id: string, data: UtilityTransactionUpdate): Promise<UtilityTransaction> {
    const r = await apiClient.patch<UtilityTransaction>(`/api/v1/steam/transactions/${id}`, data).then((r) => r.data);
    return r.data;
  },

  async deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/steam/transactions/${id}`).then((r) => r.data);
  },
};
