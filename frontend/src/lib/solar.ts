import { apiClient } from "./api";
import type {
  UtilityTransaction,
  UtilityTransactionCreate,
  UtilityTransactionUpdate,
} from "./utilityTransactions";

export type { UtilityTransaction, UtilityTransactionCreate, UtilityTransactionUpdate };

// ── Analytics response types ──────────────────────────────────────────────────

export interface SolarKPIs {
  date_from: string | null;
  date_to:   string | null;

  total_generated_kwh:       string;
  avg_generated_kwh_per_day: string | null;
  peak_generation_kwh:       string | null;

  total_self_consumption_kwh: string | null;
  total_grid_export_kwh:      string | null;
  self_consumption_ratio:     string | null;
  solar_contribution_pct:     string | null;

  avg_pr_ratio:                string | null;
  avg_inverter_efficiency_pct: string | null;
  avg_capacity_factor_pct:     string | null;

  total_cost_offset: string | null;
  avg_cost_per_kwh:  string | null;

  tx_count:      number;
  record_count:  number;
  anomaly_count: number;
}

export interface SolarTrendPoint {
  date:                 string;
  total_generated_kwh:  string;
  grid_export_kwh:      string | null;
  self_consumption_kwh: string | null;
  avg_pr_ratio:         string | null;
  total_cost:           string | null;
  anomaly_count:        number;
  tx_count:             number;
}

export interface SolarBreakdownRow {
  dimension:            string;
  group_key:            string | null;
  label:                string;
  total_generated_kwh:  string;
  pct_of_total:         string | null;
  total_cost:           string | null;
  tx_count:             number;
  anomaly_count:        number;
}

export interface SolarBreakdown {
  dimension:                 string;
  rows:                      SolarBreakdownRow[];
  grand_total_generated_kwh: string;
}

export interface SolarTariff {
  id:            string;
  tariff_code:   string;
  name:          string;
  tariff_type:   string;
  base_rate:     string;
  unit:          string;
  currency_code: string;
  effective_from: string;
  effective_to:   string | null;
  is_active:     boolean;
}

export interface SolarRecord {
  id:        string;
  record_no: string;
  asset_id:  string;
  asset_name: string | null;
  asset_no:   string | null;

  record_datetime: string;

  irradiance_wm2:  string | null;
  panel_temp_c:    string | null;
  ambient_temp_c:  string | null;

  dc_voltage_v:  string | null;
  dc_current_a:  string | null;
  dc_power_kw:   string | null;

  ac_power_kw:            string | null;
  energy_generated_kwh:   string | null;
  grid_export_kwh:        string | null;
  self_consumption_kwh:   string | null;

  inverter_efficiency_pct: string | null;
  pr_ratio:                string | null;
  availability_pct:        string | null;
  capacity_factor_pct:     string | null;

  source_method: string;
  is_anomaly:    boolean;
  anomaly_note:  string | null;
  notes:         string | null;
}

export interface SolarRecordCreate {
  asset_id:        string;
  record_datetime: string;

  irradiance_wm2?:  string | null;
  panel_temp_c?:    string | null;
  ambient_temp_c?:  string | null;

  dc_voltage_v?:  string | null;
  dc_current_a?:  string | null;
  dc_power_kw?:   string | null;

  ac_power_kw?:            string | null;
  energy_generated_kwh?:   string | null;
  grid_export_kwh?:        string | null;
  self_consumption_kwh?:   string | null;

  inverter_efficiency_pct?: string | null;
  pr_ratio?:                string | null;
  availability_pct?:        string | null;
  capacity_factor_pct?:     string | null;

  source_method?: string;
  is_anomaly?:    boolean;
  anomaly_note?:  string | null;
  notes?:         string | null;
}

// ── Filter types ──────────────────────────────────────────────────────────────

export interface SolarScope {
  date_from?:    string;
  date_to?:      string;
  department?:   string;
  building_area?: string;
  line_id?:      string;
  machine_id?:   string;
  shift_id?:     string;
  asset_id?:     string;
}

export interface SolarTxFilters extends SolarScope {
  source_meter_id?: string;
  source_asset_id?: string;
  batch_id?:        string;
  source_method?:   string;
  quality?:         string;
  is_anomaly?:      boolean;
  is_estimated?:    boolean;
  search?:          string;
  skip?:            number;
  limit?:           number;
}

export interface SolarRecordFilters {
  asset_id?:   string;
  date_from?:  string;
  date_to?:    string;
  is_anomaly?: boolean;
  skip?:       number;
  limit?:      number;
}

// ── API client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/solar";

export const solarApi = {
  // Analytics
  async kpis(scope?: SolarScope): Promise<SolarKPIs> {
    const res = await apiClient.get<SolarKPIs>(`${BASE}/kpis`, { params: scope }).then((r) => r.data);
    return res.data;
  },

  async dailyTrend(scope?: SolarScope): Promise<SolarTrendPoint[]> {
    const res = await apiClient.get<SolarTrendPoint[]>(`${BASE}/trend/daily`, { params: scope }).then((r) => r.data);
    return res.data;
  },

  async breakdown(dimension: string, scope?: SolarScope): Promise<SolarBreakdown> {
    const res = await apiClient.get<SolarBreakdown>(`${BASE}/breakdown`, {
      params: { dimension, ...scope },
    });
    return res.data;
  },

  // Tariffs
  async tariffs(isActive?: boolean): Promise<SolarTariff[]> {
    const res = await apiClient.get<SolarTariff[]>(`${BASE}/tariffs`, {
      params: isActive !== undefined ? { is_active: isActive } : undefined,
    });
    return res.data;
  },

  // Transactions
  async listTransactions(params?: SolarTxFilters): Promise<UtilityTransaction[]> {
    const res = await apiClient.get<UtilityTransaction[]>(`${BASE}/transactions`, { params }).then((r) => r.data);
    return res.data;
  },

  async getTransaction(id: string): Promise<UtilityTransaction> {
    const res = await apiClient.get<UtilityTransaction>(`${BASE}/transactions/${id}`).then((r) => r.data);
    return res.data;
  },

  async createTransaction(data: UtilityTransactionCreate): Promise<UtilityTransaction> {
    const res = await apiClient.post<UtilityTransaction>(`${BASE}/transactions`, data).then((r) => r.data);
    return res.data;
  },

  async updateTransaction(id: string, data: UtilityTransactionUpdate): Promise<UtilityTransaction> {
    const res = await apiClient.patch<UtilityTransaction>(`${BASE}/transactions/${id}`, data).then((r) => r.data);
    return res.data;
  },

  async deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/transactions/${id}`).then((r) => r.data);
  },

  // Operational records
  async listRecords(params?: SolarRecordFilters): Promise<SolarRecord[]> {
    const res = await apiClient.get<SolarRecord[]>(`${BASE}/records`, { params }).then((r) => r.data);
    return res.data;
  },

  async createRecord(data: SolarRecordCreate): Promise<SolarRecord> {
    const res = await apiClient.post<SolarRecord>(`${BASE}/records`, data).then((r) => r.data);
    return res.data;
  },

  async updateRecord(id: string, data: Partial<SolarRecordCreate>): Promise<SolarRecord> {
    const res = await apiClient.patch<SolarRecord>(`${BASE}/records/${id}`, data).then((r) => r.data);
    return res.data;
  },

  async deleteRecord(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/records/${id}`).then((r) => r.data);
  },
};

// ── CSV download ──────────────────────────────────────────────────────────────

export async function downloadSolarCsv(
  params: SolarScope & { is_anomaly?: boolean },
  filename: string
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const qs    = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => [k, String(v)])
  ).toString();
  const url = `${base}${BASE}/transactions/export/csv${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const objUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objUrl; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(objUrl);
}
