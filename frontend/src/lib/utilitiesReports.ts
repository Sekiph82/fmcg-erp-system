/**
 * Utilities Reports & Analytics — TypeScript types and API client.
 * Mirrors backend/app/schemas/utilities_reports.py and the 30 endpoints in
 * backend/app/api/v1/endpoints/utilities_reports.py
 */
import { apiClient } from "./api";

// ── Shared primitives ──────────────────────────────────────────────────────────

export interface TrendPoint {
  date: string;
  value?: number | null;
  value2?: number | null;
  label?: string | null;
}

export interface DistributionSlice {
  label: string;
  value?: number | null;
  pct?: number | null;
}

// ── Common filter params ───────────────────────────────────────────────────────

export interface DateRangeParams {
  date_from?: string;
  date_to?: string;
}

export interface CommonParams extends DateRangeParams {
  department?: string;
  shift_ref?: string;
  skip?: number;
  limit?: number;
}

// ── 1. Daily Consumption Report ────────────────────────────────────────────────

export interface DailyConsumptionRow {
  date: string;
  utility_type: string;
  quantity?: number | null;
  unit?: string | null;
  total_cost?: number | null;
  currency?: string | null;
  department?: string | null;
  shift_ref?: string | null;
  tx_count?: number | null;
}

export interface DailyConsumptionReport {
  date_from: string;
  date_to: string;
  utility_type?: string | null;
  total_quantity?: number | null;
  total_cost?: number | null;
  unit?: string | null;
  rows: DailyConsumptionRow[];
  trend: TrendPoint[];
}

// ── 2. Daily Utility Summary ───────────────────────────────────────────────────

export interface UtilityTypeSummaryRow {
  utility_type: string;
  quantity?: number | null;
  unit?: string | null;
  total_cost?: number | null;
  tx_count?: number | null;
  avg_daily?: number | null;
}

export interface DailySummaryReport {
  date_from: string;
  date_to: string;
  total_cost?: number | null;
  rows: UtilityTypeSummaryRow[];
  trend: TrendPoint[];
}

// ── 3. Boiler Efficiency Report ────────────────────────────────────────────────

export interface BoilerEfficiencyRow {
  record_no: string;
  asset_no?: string | null;
  record_datetime: string;
  shift_ref?: string | null;
  department?: string | null;
  period_hours?: number | null;
  steam_generated_kg?: number | null;
  fuel_type?: string | null;
  fuel_consumption?: number | null;
  fuel_unit?: string | null;
  boiler_efficiency_pct?: number | null;
  boiler_load_pct?: number | null;
  blowdown_pct?: number | null;
  feedwater_consumed_m3?: number | null;
  condensate_returned_m3?: number | null;
  steam_pressure_bar?: number | null;
  steam_temp_c?: number | null;
  status?: string | null;
  is_anomaly?: boolean | null;
}

export interface BoilerEfficiencyReport {
  date_from: string;
  date_to: string;
  avg_efficiency_pct?: number | null;
  total_steam_kg?: number | null;
  total_fuel?: number | null;
  avg_load_pct?: number | null;
  condensate_recovery_pct?: number | null;
  rows: BoilerEfficiencyRow[];
  trend: TrendPoint[];
}

// ── 4. Steam Generation Report ─────────────────────────────────────────────────

export interface SteamGenerationRow {
  date: string;
  asset_no?: string | null;
  steam_generated_kg?: number | null;
  steam_pressure_bar?: number | null;
  steam_temp_c?: number | null;
  steam_flow_kgh?: number | null;
  steam_quality_pct?: number | null;
  feedwater_m3?: number | null;
  blowdown_litres?: number | null;
}

export interface SteamGenerationReport {
  date_from: string;
  date_to: string;
  total_steam_kg?: number | null;
  avg_pressure_bar?: number | null;
  avg_temp_c?: number | null;
  avg_quality_pct?: number | null;
  rows: SteamGenerationRow[];
  trend: TrendPoint[];
}

// ── 5. Compressor Performance & Leak Report ────────────────────────────────────

export interface CompressorPerformanceRow {
  record_no: string;
  asset_no?: string | null;
  record_datetime: string;
  shift_ref?: string | null;
  department?: string | null;
  period_hours?: number | null;
  air_generated_nm3?: number | null;
  electricity_used_kwh?: number | null;
  specific_energy_kwh_m3?: number | null;
  load_pct?: number | null;
  discharge_pressure_bar?: number | null;
  leak_test_done?: boolean | null;
  leak_estimation_pct?: number | null;
  leak_volume_nm3?: number | null;
  night_idle_kwh?: number | null;
  status?: string | null;
  is_anomaly?: boolean | null;
}

export interface CompressorPerformanceReport {
  date_from: string;
  date_to: string;
  total_air_nm3?: number | null;
  total_kwh?: number | null;
  avg_specific_energy?: number | null;
  avg_load_pct?: number | null;
  avg_leak_pct?: number | null;
  total_leak_nm3?: number | null;
  rows: CompressorPerformanceRow[];
  trend: TrendPoint[];
}

// ── 6. Soft Water Production & Salt Report ─────────────────────────────────────

export interface SoftWaterProductionRow {
  record_no: string;
  asset_no?: string | null;
  record_datetime: string;
  shift_ref?: string | null;
  department?: string | null;
  volume_treated_m3?: number | null;
  raw_water_input_m3?: number | null;
  salt_consumed_kg?: number | null;
  salt_per_m3?: number | null;
  efficiency_pct?: number | null;
  feed_water_hardness_ppm?: number | null;
  product_water_hardness_ppm?: number | null;
  regeneration_count?: number | null;
  destination_tag?: string | null;
}

export interface SoftWaterProductionReport {
  date_from: string;
  date_to: string;
  total_volume_treated_m3?: number | null;
  total_raw_water_m3?: number | null;
  total_salt_kg?: number | null;
  avg_salt_per_m3?: number | null;
  avg_efficiency_pct?: number | null;
  conversion_pct?: number | null;
  rows: SoftWaterProductionRow[];
  trend: TrendPoint[];
}

// ── 7. Chemical Treatment Report ──────────────────────────────────────────────

export interface ChemicalTreatmentRow {
  record_no: string;
  asset_no?: string | null;
  record_datetime: string;
  treatment_type?: string | null;
  chemical_name?: string | null;
  chemical_category?: string | null;
  treatment_area?: string | null;
  quantity_dosed?: number | null;
  unit?: string | null;
  target_dose_ppm?: number | null;
  actual_dose_ppm?: number | null;
  unit_cost?: number | null;
  total_cost?: number | null;
  overdose_flag?: boolean | null;
  underdose_flag?: boolean | null;
  feed_ph?: number | null;
  product_ph?: number | null;
  residual_chlorine_ppm?: number | null;
}

export interface ChemicalTreatmentReport {
  date_from: string;
  date_to: string;
  total_dosed?: number | null;
  total_cost?: number | null;
  overdose_count?: number | null;
  underdose_count?: number | null;
  rows: ChemicalTreatmentRow[];
  by_chemical: DistributionSlice[];
  by_area: DistributionSlice[];
}

// ── 8. Solar Generation vs Consumption Report ──────────────────────────────────

export interface SolarGenerationRow {
  date: string;
  asset_no?: string | null;
  energy_generated_kwh?: number | null;
  self_consumption_kwh?: number | null;
  grid_export_kwh?: number | null;
  irradiance_wm2?: number | null;
  pr_ratio?: number | null;
  inverter_efficiency_pct?: number | null;
  availability_pct?: number | null;
  capacity_factor_pct?: number | null;
  total_elec_consumption_kwh?: number | null;
  solar_contribution_pct?: number | null;
}

export interface SolarGenerationReport {
  date_from: string;
  date_to: string;
  total_generated_kwh?: number | null;
  total_self_consumption_kwh?: number | null;
  total_grid_export_kwh?: number | null;
  avg_pr_ratio?: number | null;
  avg_contribution_pct?: number | null;
  rows: SolarGenerationRow[];
  trend: TrendPoint[];
}

// ── 9. Wastewater Compliance Report ───────────────────────────────────────────

export interface WastewaterComplianceRow {
  record_no: string;
  asset_no?: string | null;
  record_datetime: string;
  process_stage?: string | null;
  shift_ref?: string | null;
  influent_cod_mgl?: number | null;
  effluent_cod_mgl?: number | null;
  cod_removal_pct?: number | null;
  influent_bod_mgl?: number | null;
  effluent_bod_mgl?: number | null;
  influent_tss_mgl?: number | null;
  effluent_tss_mgl?: number | null;
  effluent_ph?: number | null;
  do_mgl?: number | null;
  compliance_status?: string | null;
  permit_limit_ref?: string | null;
  deviation_reason?: string | null;
  power_consumed_kwh?: number | null;
  sludge_produced_kg?: number | null;
}

export interface WastewaterComplianceReport {
  date_from: string;
  date_to: string;
  compliant_count?: number | null;
  non_compliant_count?: number | null;
  borderline_count?: number | null;
  compliance_rate_pct?: number | null;
  avg_cod_removal_pct?: number | null;
  rows: WastewaterComplianceRow[];
  trend: TrendPoint[];
}

// ── 10. Cost Allocation Report ─────────────────────────────────────────────────

export interface CostAllocationRow {
  dimension: string;
  utility_type?: string | null;
  allocated_cost?: number | null;
  allocated_quantity?: number | null;
  quantity_unit?: string | null;
  cost_per_unit?: number | null;
  cost_per_ton?: number | null;
  production_volume_kg?: number | null;
  allocation_count?: number | null;
  pct_of_total?: number | null;
}

export interface CostAllocationReport {
  date_from: string;
  date_to: string;
  group_by: string;
  utility_type?: string | null;
  total_cost?: number | null;
  rows: CostAllocationRow[];
  by_utility: DistributionSlice[];
}

// ── 11. Base Load Analysis ─────────────────────────────────────────────────────

export interface BaseLoadRow {
  utility_type: string;
  unit?: string | null;
  min_daily?: number | null;
  p10_daily?: number | null;
  p25_daily?: number | null;
  median_daily?: number | null;
  mean_daily?: number | null;
  p75_daily?: number | null;
  p90_daily?: number | null;
  max_daily?: number | null;
  base_load_est?: number | null;
  base_load_pct?: number | null;
  cost_base_load?: number | null;
}

export interface BaseLoadAnalysis {
  date_from: string;
  date_to: string;
  rows: BaseLoadRow[];
  trend: TrendPoint[];
}

// ── 12. Peak Demand Analysis ───────────────────────────────────────────────────

export interface PeakDemandRow {
  date: string;
  utility_type: string;
  department?: string | null;
  quantity?: number | null;
  unit?: string | null;
  total_cost?: number | null;
  is_anomaly?: boolean | null;
}

export interface PeakDemandAnalysis {
  date_from: string;
  date_to: string;
  utility_type?: string | null;
  peak_date?: string | null;
  peak_value?: number | null;
  peak_unit?: string | null;
  top_days: PeakDemandRow[];
  trend: TrendPoint[];
}

// ── 13. Alarm Trend Report ────────────────────────────────────────────────────

export interface AlarmTrendRow {
  date: string;
  critical?: number | null;
  alert?: number | null;
  warning?: number | null;
  info?: number | null;
  total?: number | null;
}

export interface AlarmDetailRow {
  event_no: string;
  rule_code?: string | null;
  rule_name?: string | null;
  utility_type?: string | null;
  asset_no?: string | null;
  device_code?: string | null;
  severity?: string | null;
  triggered_at: string;
  status?: string | null;
  triggered_value?: number | null;
  threshold_value?: number | null;
  parameter?: string | null;
}

export interface AlarmTrendReport {
  date_from: string;
  date_to: string;
  total_events?: number | null;
  critical_count?: number | null;
  unresolved_count?: number | null;
  trend: AlarmTrendRow[];
  top_rules: DistributionSlice[];
  recent: AlarmDetailRow[];
}

// ── 14. Abnormal Consumption Report ───────────────────────────────────────────

export interface AbnormalConsumptionRow {
  date: string;
  utility_type: string;
  department?: string | null;
  quantity?: number | null;
  unit?: string | null;
  mean_baseline?: number | null;
  deviation_pct?: number | null;
  total_cost?: number | null;
  is_anomaly?: boolean | null;
  anomaly_note?: string | null;
}

export interface AbnormalConsumptionReport {
  date_from: string;
  date_to: string;
  utility_type?: string | null;
  anomaly_count?: number | null;
  high_deviation_count?: number | null;
  rows: AbnormalConsumptionRow[];
}

// ── 15. Sustainability Summary ─────────────────────────────────────────────────

export interface SustainabilityMetric {
  label: string;
  value?: number | null;
  unit?: string | null;
  benchmark?: number | null;
  trend?: string | null;
}

export interface SustainabilityReport {
  date_from: string;
  date_to: string;
  total_electricity_kwh?: number | null;
  solar_kwh?: number | null;
  solar_pct?: number | null;
  total_water_m3?: number | null;
  process_water_m3?: number | null;
  wastewater_treated_m3?: number | null;
  compliance_rate_pct?: number | null;
  total_utility_cost?: number | null;
  estimated_co2e_kg?: number | null;
  metrics: SustainabilityMetric[];
  trend: TrendPoint[];
}

// ── Authenticated file download helper ────────────────────────────────────────

async function _downloadCsv(path: string, filename: string): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${base}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Export failed (${res.status}): ${text}`);
  }
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

// ── API client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/utilities-reports";

export const reportsApi = {
  // 1. Daily Consumption
  async dailyConsumption(params?: CommonParams & { utility_type?: string }): Promise<DailyConsumptionReport> {
    const r = await apiClient.get<DailyConsumptionReport>(`${BASE}/daily-consumption`, { params }).then((r) => r.data);
    return r.data;
  },
  exportDailyConsumption(params?: CommonParams & { utility_type?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/daily-consumption/export/csv?${qs}`, "daily_consumption.csv");
  },

  // 2. Daily Summary
  async dailySummary(params?: DateRangeParams): Promise<DailySummaryReport> {
    const r = await apiClient.get<DailySummaryReport>(`${BASE}/daily-summary`, { params }).then((r) => r.data);
    return r.data;
  },
  exportDailySummary(params?: DateRangeParams): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/daily-summary/export/csv?${qs}`, "daily_summary.csv");
  },

  // 3. Boiler Efficiency
  async boilerEfficiency(params?: CommonParams & { asset_no?: string }): Promise<BoilerEfficiencyReport> {
    const r = await apiClient.get<BoilerEfficiencyReport>(`${BASE}/boiler-efficiency`, { params }).then((r) => r.data);
    return r.data;
  },
  exportBoilerEfficiency(params?: CommonParams & { asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/boiler-efficiency/export/csv?${qs}`, "boiler_efficiency.csv");
  },

  // 4. Steam Generation
  async steamGeneration(params?: DateRangeParams & { asset_no?: string; skip?: number; limit?: number }): Promise<SteamGenerationReport> {
    const r = await apiClient.get<SteamGenerationReport>(`${BASE}/steam-generation`, { params }).then((r) => r.data);
    return r.data;
  },
  exportSteamGeneration(params?: DateRangeParams & { asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/steam-generation/export/csv?${qs}`, "steam_generation.csv");
  },

  // 5. Compressor Performance
  async compressorPerformance(params?: CommonParams & { asset_no?: string }): Promise<CompressorPerformanceReport> {
    const r = await apiClient.get<CompressorPerformanceReport>(`${BASE}/compressor-performance`, { params }).then((r) => r.data);
    return r.data;
  },
  exportCompressorPerformance(params?: CommonParams & { asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/compressor-performance/export/csv?${qs}`, "compressor_performance.csv");
  },

  // 6. Soft Water Production
  async softWater(params?: CommonParams & { asset_no?: string }): Promise<SoftWaterProductionReport> {
    const r = await apiClient.get<SoftWaterProductionReport>(`${BASE}/soft-water`, { params }).then((r) => r.data);
    return r.data;
  },
  exportSoftWater(params?: CommonParams & { asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/soft-water/export/csv?${qs}`, "soft_water_production.csv");
  },

  // 7. Chemical Treatment
  async chemicalTreatment(params?: DateRangeParams & { treatment_type?: string; asset_no?: string; skip?: number; limit?: number }): Promise<ChemicalTreatmentReport> {
    const r = await apiClient.get<ChemicalTreatmentReport>(`${BASE}/chemical-treatment`, { params }).then((r) => r.data);
    return r.data;
  },
  exportChemicalTreatment(params?: DateRangeParams & { treatment_type?: string; asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/chemical-treatment/export/csv?${qs}`, "chemical_treatment.csv");
  },

  // 8. Solar Generation
  async solarGeneration(params?: DateRangeParams & { asset_no?: string; skip?: number; limit?: number }): Promise<SolarGenerationReport> {
    const r = await apiClient.get<SolarGenerationReport>(`${BASE}/solar-generation`, { params }).then((r) => r.data);
    return r.data;
  },
  exportSolarGeneration(params?: DateRangeParams & { asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/solar-generation/export/csv?${qs}`, "solar_generation.csv");
  },

  // 9. Wastewater Compliance
  async wastewaterCompliance(params?: CommonParams & { asset_no?: string }): Promise<WastewaterComplianceReport> {
    const r = await apiClient.get<WastewaterComplianceReport>(`${BASE}/wastewater-compliance`, { params }).then((r) => r.data);
    return r.data;
  },
  exportWastewaterCompliance(params?: CommonParams & { asset_no?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/wastewater-compliance/export/csv?${qs}`, "wastewater_compliance.csv");
  },

  // 10. Cost Allocation
  async costAllocation(params?: DateRangeParams & { group_by?: string; utility_type?: string; skip?: number; limit?: number }): Promise<CostAllocationReport> {
    const r = await apiClient.get<CostAllocationReport>(`${BASE}/cost-allocation`, { params }).then((r) => r.data);
    return r.data;
  },
  exportCostAllocation(params?: DateRangeParams & { group_by?: string; utility_type?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/cost-allocation/export/csv?${qs}`, "cost_allocation.csv");
  },

  // 11. Base Load Analysis
  async baseLoad(params?: DateRangeParams & { utility_type?: string }): Promise<BaseLoadAnalysis> {
    const r = await apiClient.get<BaseLoadAnalysis>(`${BASE}/base-load`, { params }).then((r) => r.data);
    return r.data;
  },
  exportBaseLoad(params?: DateRangeParams & { utility_type?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/base-load/export/csv?${qs}`, "base_load_analysis.csv");
  },

  // 12. Peak Demand
  async peakDemand(params?: DateRangeParams & { utility_type?: string; top_n?: number }): Promise<PeakDemandAnalysis> {
    const r = await apiClient.get<PeakDemandAnalysis>(`${BASE}/peak-demand`, { params }).then((r) => r.data);
    return r.data;
  },
  exportPeakDemand(params?: DateRangeParams & { utility_type?: string; top_n?: number }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/peak-demand/export/csv?${qs}`, "peak_demand.csv");
  },

  // 13. Alarm Trends
  async alarmTrends(params?: DateRangeParams & { utility_type?: string; severity?: string }): Promise<AlarmTrendReport> {
    const r = await apiClient.get<AlarmTrendReport>(`${BASE}/alarm-trends`, { params }).then((r) => r.data);
    return r.data;
  },
  exportAlarmTrends(params?: DateRangeParams & { utility_type?: string; severity?: string }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/alarm-trends/export/csv?${qs}`, "alarm_trends.csv");
  },

  // 14. Abnormal Consumption
  async abnormalConsumption(params?: DateRangeParams & { utility_type?: string; department?: string; deviation_threshold_pct?: number; skip?: number; limit?: number }): Promise<AbnormalConsumptionReport> {
    const r = await apiClient.get<AbnormalConsumptionReport>(`${BASE}/abnormal-consumption`, { params }).then((r) => r.data);
    return r.data;
  },
  exportAbnormalConsumption(params?: DateRangeParams & { utility_type?: string; department?: string; deviation_threshold_pct?: number }): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/abnormal-consumption/export/csv?${qs}`, "abnormal_consumption.csv");
  },

  // 15. Sustainability
  async sustainability(params?: DateRangeParams): Promise<SustainabilityReport> {
    const r = await apiClient.get<SustainabilityReport>(`${BASE}/sustainability`, { params }).then((r) => r.data);
    return r.data;
  },
  exportSustainability(params?: DateRangeParams): Promise<void> {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return _downloadCsv(`${BASE}/sustainability/export/csv?${qs}`, "sustainability_summary.csv");
  },
};
