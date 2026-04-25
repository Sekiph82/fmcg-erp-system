/**
 * Utility KPI Center — TypeScript types and API client.
 * All KPI formulas are computed server-side; this file only declares shapes.
 */
import { apiClient } from "./api";

// ── Shared types ──────────────────────────────────────────────────────────────

export interface TopConsumerRow {
  label:        string;
  consumption:  number;
  unit:         string;
  cost?:        number | null;
  pct_of_total?: number | null;
  record_count: number;
}

export interface TopConsumers {
  dimension:    string;
  utility_type?: string | null;
  date_from?:   string | null;
  date_to?:     string | null;
  rows:         TopConsumerRow[];
  grand_total:  number;
}

export interface DailyTrendPoint {
  date:              string;
  electricity_kwh?:  number | null;
  water_m3?:         number | null;
  gas_nm3?:          number | null;
  steam_ton?:        number | null;
  solar_kwh?:        number | null;
  compressed_air_nm3?: number | null;
  total_cost?:       number | null;
  is_estimated:      boolean;
}

// ── Main dashboard KPIs ───────────────────────────────────────────────────────

export interface MainDashboardKPIs {
  report_date:   string;
  period_label:  string;

  electricity_kwh_today?:     number | null;
  electricity_kwh_mtd?:       number | null;
  electricity_kwh_per_ton?:   number | null;
  peak_demand_kw?:            number | null;
  night_base_load_kwh?:       number | null;

  water_m3_today?:            number | null;
  water_m3_per_ton?:          number | null;

  gas_nm3_today?:             number | null;
  gas_nm3_per_ton?:           number | null;

  steam_ton_today?:           number | null;
  gas_per_ton_steam?:         number | null;
  condensate_recovery_pct?:   number | null;
  blowdown_loss_pct?:         number | null;
  boiler_efficiency_pct?:     number | null;

  air_nm3_today?:             number | null;
  air_kwh_per_nm3?:           number | null;
  leak_estimate_pct?:         number | null;
  compressor_efficiency_pct?: number | null;

  soft_water_m3_today?:       number | null;
  soft_water_conversion_pct?: number | null;
  salt_per_m3_soft?:          number | null;

  solar_kwh_today?:           number | null;
  solar_contribution_pct?:    number | null;
  solar_vs_expected_pct?:     number | null;

  wastewater_cost_per_m3?:    number | null;
  cod_removal_pct?:           number | null;
  wastewater_compliance?:     string | null;

  chemical_cost_today?:       number | null;

  utility_cost_today?:        number | null;
  utility_cost_mtd?:          number | null;
  utility_cost_per_ton?:      number | null;
  utility_cost_per_batch?:    number | null;
  currency_code:              string;

  machine_standby_pct?:       number | null;
  dept_utility_intensity?:    number | null;

  production_tons_today?:     number | null;
  critical_alarm_count:       number;
  warning_alarm_count:        number;
  has_estimated_data:         boolean;
}

// ── Per-utility KPI types ─────────────────────────────────────────────────────

export interface ElectricityDashboardKPIs {
  date_from: string; date_to: string;
  kwh_total?:            number | null;
  kwh_per_ton?:          number | null;
  peak_demand_kw?:       number | null;
  night_base_load_kwh?:  number | null;
  solar_offset_kwh?:     number | null;
  solar_contribution_pct?: number | null;
  total_cost?:           number | null;
  cost_per_kwh?:         number | null;
  estimated_pct?:        number | null;
  anomaly_count:         number;
}

export interface WaterDashboardKPIs {
  date_from: string; date_to: string;
  water_m3_total?:  number | null;
  water_m3_per_ton?: number | null;
  process_water_m3?: number | null;
  total_cost?:       number | null;
  cost_per_m3?:      number | null;
  estimated_pct?:    number | null;
  anomaly_count:     number;
}

export interface BoilerDashboardKPIs {
  date_from: string; date_to: string;
  steam_ton_total?:         number | null;
  fuel_consumed_total?:     number | null;
  fuel_unit?:               string | null;
  gas_per_ton_steam?:       number | null;
  boiler_efficiency_pct?:   number | null;
  condensate_recovery_pct?: number | null;
  blowdown_loss_pct?:       number | null;
  feedwater_m3_total?:      number | null;
  burner_runtime_hours?:    number | null;
  avg_boiler_load_pct?:     number | null;
  anomaly_count:            number;
}

export interface CompressorDashboardKPIs {
  date_from: string; date_to: string;
  air_nm3_total?:         number | null;
  electricity_kwh_total?: number | null;
  air_kwh_per_nm3?:       number | null;
  leak_estimate_pct?:     number | null;
  night_idle_kwh?:        number | null;
  avg_load_pct?:          number | null;
  runtime_hours?:         number | null;
  anomaly_count:          number;
}

export interface SoftWaterDashboardKPIs {
  date_from: string; date_to: string;
  sw_volume_m3?:             number | null;
  raw_input_m3?:             number | null;
  conversion_efficiency_pct?: number | null;
  salt_consumed_kg?:         number | null;
  salt_per_m3?:              number | null;
  avg_product_hardness?:     number | null;
  regen_count?:              number | null;
  anomaly_count:             number;
}

export interface SolarDashboardKPIs {
  date_from: string; date_to: string;
  kwh_generated?:          number | null;
  kwh_self_consumed?:      number | null;
  kwh_exported?:           number | null;
  solar_contribution_pct?: number | null;
  avg_pr_ratio?:           number | null;
  avg_capacity_factor?:    number | null;
  avg_inverter_efficiency?: number | null;
  anomaly_count:           number;
}

export interface ChemicalDashboardKPIs {
  date_from: string; date_to: string;
  total_cost?:        number | null;
  total_consumed_kg?: number | null;
  cost_per_day?:      number | null;
  distinct_chemicals: number;
  boiler_cost?:       number | null;
  cooling_cost?:      number | null;
  wwtp_cost?:         number | null;
}

export interface WastewaterDashboardKPIs {
  date_from: string; date_to: string;
  cod_removal_pct?:     number | null;
  bod_removal_pct?:     number | null;
  avg_do_mgl?:          number | null;
  avg_effluent_ph?:     number | null;
  sludge_kg_total?:     number | null;
  power_kwh_total?:     number | null;
  power_per_m3?:        number | null;
  compliant_pct?:       number | null;
  non_compliant_count:  number;
  anomaly_count:        number;
}

export interface MachineDashboardKPIs {
  date_from: string; date_to: string;
  total_consumption?:       number | null;
  consumption_unit?:        string | null;
  electricity_per_runtime_h?: number | null;
  water_per_batch?:         number | null;
  air_per_batch?:           number | null;
  standby_pct?:             number | null;
  cost_per_batch?:          number | null;
  avg_variance_pct?:        number | null;
  anomaly_count:            number;
  flag_high_variance:       boolean;
  flag_standby_waste:       boolean;
}

export interface UtilityCostDashboardKPIs {
  date_from: string; date_to: string;
  total_cost?:      number | null;
  electricity_cost?: number | null;
  water_cost?:      number | null;
  gas_cost?:        number | null;
  steam_cost?:      number | null;
  other_cost?:      number | null;
  cost_per_ton?:    number | null;
  cost_per_batch?:  number | null;
  total_bills:      number;
  unpaid_amount?:   number | null;
  currency_code:    string;
}

// ── Color / label maps for charts ─────────────────────────────────────────────

export const UTILITY_CHART_COLORS: Record<string, string> = {
  electricity_kwh:     "#fbbf24",
  water_m3:            "#60a5fa",
  gas_nm3:             "#a78bfa",
  steam_ton:           "#f97316",
  solar_kwh:           "#facc15",
  compressed_air_nm3:  "#22d3ee",
  total_cost:          "#94a3b8",
};

export const UTILITY_CHART_LABELS: Record<string, string> = {
  electricity_kwh:    "Electricity (kWh)",
  water_m3:           "Water (m³)",
  gas_nm3:            "Gas (Nm³)",
  steam_ton:          "Steam (t)",
  solar_kwh:          "Solar (kWh)",
  compressed_air_nm3: "Compressed Air (Nm³)",
  total_cost:         "Cost",
};

// ── API client ────────────────────────────────────────────────────────────────

export const kpiApi = {
  // Main dashboard
  async mainDashboard(params?: { report_date?: string; production_tons?: number }): Promise<MainDashboardKPIs> {
    const r = await apiClient.get<MainDashboardKPIs>("/api/v1/kpi/dashboard", { params }).then((r) => r.data);
    return r.data;
  },

  // Top consumers
  async topConsumers(params?: {
    dimension?: string; utility_type?: string;
    date_from?: string; date_to?: string; top_n?: number;
  }): Promise<TopConsumers> {
    const r = await apiClient.get<TopConsumers>("/api/v1/kpi/top-consumers", { params }).then((r) => r.data);
    return r.data;
  },

  // Daily trend
  async dailyTrend(params?: { date_from?: string; date_to?: string }): Promise<DailyTrendPoint[]> {
    const r = await apiClient.get<DailyTrendPoint[]>("/api/v1/kpi/trend", { params }).then((r) => r.data);
    return r.data;
  },

  // Sub-dashboards
  async electricity(params?: { date_from?: string; date_to?: string }): Promise<ElectricityDashboardKPIs> {
    const r = await apiClient.get<ElectricityDashboardKPIs>("/api/v1/kpi/electricity", { params }).then((r) => r.data);
    return r.data;
  },
  async water(params?: { date_from?: string; date_to?: string }): Promise<WaterDashboardKPIs> {
    const r = await apiClient.get<WaterDashboardKPIs>("/api/v1/kpi/water", { params }).then((r) => r.data);
    return r.data;
  },
  async boiler(params?: { date_from?: string; date_to?: string }): Promise<BoilerDashboardKPIs> {
    const r = await apiClient.get<BoilerDashboardKPIs>("/api/v1/kpi/boiler", { params }).then((r) => r.data);
    return r.data;
  },
  async compressor(params?: { date_from?: string; date_to?: string }): Promise<CompressorDashboardKPIs> {
    const r = await apiClient.get<CompressorDashboardKPIs>("/api/v1/kpi/compressor", { params }).then((r) => r.data);
    return r.data;
  },
  async softWater(params?: { date_from?: string; date_to?: string }): Promise<SoftWaterDashboardKPIs> {
    const r = await apiClient.get<SoftWaterDashboardKPIs>("/api/v1/kpi/soft-water", { params }).then((r) => r.data);
    return r.data;
  },
  async solar(params?: { date_from?: string; date_to?: string }): Promise<SolarDashboardKPIs> {
    const r = await apiClient.get<SolarDashboardKPIs>("/api/v1/kpi/solar", { params }).then((r) => r.data);
    return r.data;
  },
  async chemicals(params?: { date_from?: string; date_to?: string }): Promise<ChemicalDashboardKPIs> {
    const r = await apiClient.get<ChemicalDashboardKPIs>("/api/v1/kpi/chemicals", { params }).then((r) => r.data);
    return r.data;
  },
  async wastewater(params?: { date_from?: string; date_to?: string }): Promise<WastewaterDashboardKPIs> {
    const r = await apiClient.get<WastewaterDashboardKPIs>("/api/v1/kpi/wastewater", { params }).then((r) => r.data);
    return r.data;
  },
  async machineUtility(params?: { date_from?: string; date_to?: string }): Promise<MachineDashboardKPIs> {
    const r = await apiClient.get<MachineDashboardKPIs>("/api/v1/kpi/machine-utility", { params }).then((r) => r.data);
    return r.data;
  },
  async utilityCost(params?: { date_from?: string; date_to?: string }): Promise<UtilityCostDashboardKPIs> {
    const r = await apiClient.get<UtilityCostDashboardKPIs>("/api/v1/kpi/utility-cost", { params }).then((r) => r.data);
    return r.data;
  },
};
