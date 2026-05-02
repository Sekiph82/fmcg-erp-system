import { apiClient } from "./api";
import type { UtilityType } from "./utilityManagement";
import type {
  UtilityTransaction,
  UtilityTransactionCreate,
  UtilityTransactionUpdate,
} from "./utilityTransactions";

// Re-export transaction types (pre-scoped to ELECTRICITY in the API layer)
export type { UtilityTransaction, UtilityTransactionCreate, UtilityTransactionUpdate };

// ── Analytics response types ──────────────────────────────────────────────────

export interface ElectricityKPIs {
  date_from:        string | null;
  date_to:          string | null;

  total_kwh:        string;
  avg_kwh_per_day:  string | null;
  peak_demand_kwh:  string | null;
  base_load_kwh:    string | null;
  idle_kwh:         string | null;
  solar_offset_kwh: string | null;
  net_kwh:          string | null;

  total_cost:       string | null;
  avg_cost_per_day: string | null;
  avg_cost_per_kwh: string | null;

  tx_count:         number;
  anomaly_count:    number;
  estimated_count:  number;
  estimated_pct:    string | null;
  has_tariff_data:  boolean;
}

export interface ElectricityTrendPoint {
  date:          string;
  total_kwh:     string;
  peak_kwh:      string | null;
  total_cost:    string | null;
  anomaly_count: number;
  tx_count:      number;
}

export interface ElectricityShiftPoint {
  shift_id:      string | null;
  label:         string;
  total_kwh:     string;
  total_cost:    string | null;
  tx_count:      number;
  anomaly_count: number;
}

export interface ElectricityBreakdownRow {
  dimension:    string;
  group_key:    string | null;
  label:        string;
  total_kwh:    string;
  pct_of_total: string | null;
  total_cost:   string | null;
  tx_count:     number;
  anomaly_count: number;
}

export interface ElectricityBreakdown {
  dimension:       string;
  rows:            ElectricityBreakdownRow[];
  grand_total_kwh: string;
}

export interface ElectricityTariff {
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

// ── Filter types ───────────────────────────────────────────────────────────────

export interface ElectricityScope {
  date_from?:    string;
  date_to?:      string;
  department?:   string;
  building_area?: string;
  line_id?:      string;
  machine_id?:   string;
  shift_id?:     string;
}

export interface ElectricityTxFilters extends ElectricityScope {
  source_meter_id?:  string;
  source_asset_id?:  string;
  batch_id?:         string;
  source_method?:    string;
  quality?:          string;
  is_anomaly?:       boolean;
  is_estimated?:     boolean;
  search?:           string;
  skip?:             number;
  limit?:            number;
}

// ── API client ─────────────────────────────────────────────────────────────────

const BASE = "/api/v1/electricity";

export const electricityApi = {
  // Analytics
  async kpis(scope?: ElectricityScope): Promise<ElectricityKPIs> {
    const res = await apiClient.get<ElectricityKPIs>(`${BASE}/kpis`, { params: scope });
    return res.data;
  },

  async dailyTrend(scope?: ElectricityScope): Promise<ElectricityTrendPoint[]> {
    const res = await apiClient.get<ElectricityTrendPoint[]>(`${BASE}/trend/daily`, { params: scope });
    return res.data;
  },

  async shiftTrend(params?: {
    date_from?: string; date_to?: string; department?: string; line_id?: string;
  }): Promise<ElectricityShiftPoint[]> {
    const res = await apiClient.get<ElectricityShiftPoint[]>(`${BASE}/trend/shift`, { params });
    return res.data;
  },

  async breakdown(dimension: string, scope?: ElectricityScope): Promise<ElectricityBreakdown> {
    const res = await apiClient.get<ElectricityBreakdown>(`${BASE}/breakdown`, {
      params: { dimension, ...scope },
    });
    return res.data;
  },

  // Tariffs
  async tariffs(isActive?: boolean): Promise<ElectricityTariff[]> {
    const res = await apiClient.get<ElectricityTariff[]>(`${BASE}/tariffs`, {
      params: isActive !== undefined ? { is_active: isActive } : undefined,
    });
    return res.data;
  },

  // Transactions
  async listTransactions(params?: ElectricityTxFilters): Promise<UtilityTransaction[]> {
    const res = await apiClient.get<UtilityTransaction[]>(`${BASE}/transactions`, { params });
    return res.data;
  },

  async getTransaction(id: string): Promise<UtilityTransaction> {
    const res = await apiClient.get<UtilityTransaction>(`${BASE}/transactions/${id}`);
    return res.data;
  },

  async createTransaction(data: UtilityTransactionCreate): Promise<UtilityTransaction> {
    const res = await apiClient.post<UtilityTransaction>(`${BASE}/transactions`, data);
    return res.data;
  },

  async updateTransaction(id: string, data: UtilityTransactionUpdate): Promise<UtilityTransaction> {
    const res = await apiClient.patch<UtilityTransaction>(`${BASE}/transactions/${id}`, data);
    return res.data;
  },

  async deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/transactions/${id}`).then((r) => r.data);
  },
};

// ── CSV download ───────────────────────────────────────────────────────────────

export async function downloadElectricityCsv(
  params: ElectricityScope & { is_anomaly?: boolean },
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
