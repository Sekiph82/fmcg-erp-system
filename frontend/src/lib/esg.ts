import { apiClient } from "@/lib/api";

export type SourceType =
  | "FUEL_DIESEL" | "FUEL_PETROL" | "FUEL_LPG"
  | "ELECTRICITY_GRID" | "ELECTRICITY_SOLAR"
  | "TRANSPORT_ROAD" | "TRANSPORT_AIR"
  | "MATERIAL" | "WATER"
  | "WASTE_GENERAL" | "WASTE_HAZARDOUS" | "WASTE_RECYCLED";

export type EmissionScope = "SCOPE1" | "SCOPE2" | "SCOPE3";
export type ESGMetricType = "ENERGY" | "WATER" | "WASTE" | "RECYCLING" | "EMISSIONS";
export type SupplierSustainabilityRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type SupplierSustainabilityStatus = "DRAFT" | "ACTIVE" | "UNDER_REVIEW" | "ARCHIVED";

export interface Activity {
  id: string;
  source_type: SourceType;
  source_reference?: string;
  activity_date: string;
  quantity: number;
  unit: string;
  location_id?: string;
  location_name?: string;
  supplier_id?: string;
  supplier_name?: string;
  notes?: string;
  is_auto_imported: boolean;
  calculated_emission_kgco2e?: number;
  scope?: EmissionScope;
}

export interface EmissionFactor {
  id: string;
  factor_code: string;
  source_type: SourceType;
  region: string;
  valid_from: string;
  valid_to?: string;
  factor_value: number;
  unit: string;
  scope: EmissionScope;
  source_reference?: string;
  is_active: boolean;
  notes?: string;
}

export interface EmissionRecord {
  id: string;
  activity_id: string;
  factor_id: string;
  calculated_emission_kgco2e: number;
  scope: EmissionScope;
  calculated_at: string;
  source_type?: SourceType;
  activity_date?: string;
  quantity?: number;
  unit?: string;
  factor_code?: string;
  factor_value?: number;
  location_name?: string;
}

export interface ResourceMetric {
  id: string;
  metric_type: ESGMetricType;
  quantity: number;
  unit: string;
  location_id?: string;
  location_name?: string;
  period_from: string;
  period_to: string;
  notes?: string;
}

export interface ESGTarget {
  id: string;
  metric_type: ESGMetricType;
  scope?: EmissionScope;
  baseline_year: number;
  baseline_value: number;
  target_value: number;
  unit: string;
  target_date: string;
  is_active: boolean;
  notes?: string;
  actual_value?: number;
  progress_pct?: number;
}

export interface ESGDashboard {
  total_emissions_kgco2e: number;
  scope1_kgco2e: number;
  scope2_kgco2e: number;
  scope3_kgco2e: number;
  total_energy_kwh: number;
  total_water_m3: number;
  total_waste_kg: number;
  recycling_rate_pct?: number;
  activity_count: number;
  last_updated: string;
}

export interface EmissionSummary {
  scope: EmissionScope;
  total_kgco2e: number;
  total_tco2e: number;
  activity_count: number;
}

export interface EmissionBySource {
  source_type: SourceType;
  scope: EmissionScope;
  total_kgco2e: number;
  activity_count: number;
}

export interface ResourceSummary {
  metric_type: ESGMetricType;
  total_quantity: number;
  unit: string;
  period: string;
}

export interface ESGInsight {
  agent: string;
  insights: string[];
  details?: any[];
  generated_at: string;
}

export interface FleetImportResult {
  imported_activities: number;
  imported_emissions: number;
  skipped: number;
  message: string;
}

export interface SupplierSustainabilityScore {
  id: string;
  supplier_id?: string;
  supplier_name: string;
  assessment_period_start: string;
  assessment_period_end: string;
  overall_score: number;
  risk_level: SupplierSustainabilityRisk;
  status: SupplierSustainabilityStatus;
  emissions_score?: number;
  energy_score?: number;
  water_score?: number;
  waste_score?: number;
  compliance_score?: number;
  labor_score?: number;
  renewable_energy_pct?: number;
  has_ghg_disclosure: boolean;
  has_science_based_target: boolean;
  iso14001_certified: boolean;
  wastewater_policy_verified: boolean;
  audit_findings?: string;
  improvement_plan?: string;
  notes?: string;
  assessed_by?: string;
  reviewed_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface EnergyIntensityRow {
  product_id?: string;
  product_sku?: string;
  product_name: string;
  batches: number;
  allocation_count: number;
  total_energy_kwh: number;
  production_volume_kg: number;
  kwh_per_kg?: number;
  kwh_per_ton?: number;
  total_energy_cost: number;
  currency_code?: string;
  data_quality: string;
}

export interface WastewaterComplianceSnapshot {
  total_records: number;
  compliant_records: number;
  borderline_records: number;
  non_compliant_records: number;
  not_tested_records: number;
  compliance_rate_pct?: number;
  avg_effluent_cod_mgl?: number;
  avg_effluent_bod_mgl?: number;
  avg_effluent_tss_mgl?: number;
  avg_effluent_ph?: number;
  total_power_kwh: number;
  latest_deviations: Array<Record<string, any>>;
}

export interface ESGIntelligenceDashboard {
  supplier_score_count: number;
  average_supplier_score?: number;
  high_risk_supplier_count: number;
  energy_intensity_rows: EnergyIntensityRow[];
  wastewater_compliance: WastewaterComplianceSnapshot;
}

const BASE = "/api/v1/esg";

export const esgApi = {
  // Dashboard
  async getDashboard(params?: { date_from?: string; date_to?: string }): Promise<ESGDashboard> {
    const res = await apiClient.get(`${BASE}/dashboard`, { params });
    return res.data?.data ?? res.data;
  },

  // Activities
  async listActivities(params?: { source_type?: string; date_from?: string; date_to?: string; limit?: number }): Promise<Activity[]> {
    const res = await apiClient.get(`${BASE}/activities`, { params });
    return res.data?.data ?? res.data;
  },
  async createActivity(data: Omit<Activity, "id" | "is_auto_imported" | "location_name" | "supplier_name" | "calculated_emission_kgco2e" | "scope">): Promise<Activity> {
    const res = await apiClient.post(`${BASE}/activities`, data);
    return res.data?.data ?? res.data;
  },

  // Factors
  async listFactors(params?: { source_type?: string; is_active?: boolean }): Promise<EmissionFactor[]> {
    const res = await apiClient.get(`${BASE}/factors`, { params });
    return res.data?.data ?? res.data;
  },
  async createFactor(data: Omit<EmissionFactor, "id">): Promise<EmissionFactor> {
    const res = await apiClient.post(`${BASE}/factors`, data);
    return res.data?.data ?? res.data;
  },
  async updateFactor(id: string, data: Partial<EmissionFactor>): Promise<EmissionFactor> {
    const res = await apiClient.patch(`${BASE}/factors/${id}`, data);
    return res.data?.data ?? res.data;
  },
  async seedFactors(): Promise<{ seeded: number; message: string }> {
    const res = await apiClient.post(`${BASE}/factors/seed`);
    return res.data?.data ?? res.data;
  },

  // Emissions
  async listEmissions(params?: { scope?: string; date_from?: string; date_to?: string; limit?: number }): Promise<EmissionRecord[]> {
    const res = await apiClient.get(`${BASE}/emissions`, { params });
    return res.data?.data ?? res.data;
  },

  // Metrics
  async listMetrics(params?: { metric_type?: string; date_from?: string; date_to?: string }): Promise<ResourceMetric[]> {
    const res = await apiClient.get(`${BASE}/metrics`, { params });
    return res.data?.data ?? res.data;
  },
  async createMetric(data: Omit<ResourceMetric, "id" | "location_name">): Promise<ResourceMetric> {
    const res = await apiClient.post(`${BASE}/metrics`, data);
    return res.data?.data ?? res.data;
  },

  // Targets
  async listTargets(params?: { is_active?: boolean }): Promise<ESGTarget[]> {
    const res = await apiClient.get(`${BASE}/targets`, { params });
    return res.data?.data ?? res.data;
  },
  async createTarget(data: Omit<ESGTarget, "id" | "actual_value" | "progress_pct">): Promise<ESGTarget> {
    const res = await apiClient.post(`${BASE}/targets`, data);
    return res.data?.data ?? res.data;
  },

  // Reports
  async emissionSummary(params?: { date_from?: string; date_to?: string }): Promise<EmissionSummary[]> {
    const res = await apiClient.get(`${BASE}/reports/emission-summary`, { params });
    return res.data?.data ?? res.data;
  },
  async emissionBySource(params?: { date_from?: string; date_to?: string }): Promise<EmissionBySource[]> {
    const res = await apiClient.get(`${BASE}/reports/emission-by-source`, { params });
    return res.data?.data ?? res.data;
  },
  async resourceSummary(params?: { date_from?: string; date_to?: string }): Promise<ResourceSummary[]> {
    const res = await apiClient.get(`${BASE}/reports/resources`, { params });
    return res.data?.data ?? res.data;
  },
  async targetPerformance(): Promise<any[]> {
    const res = await apiClient.get(`${BASE}/reports/targets`);
    return res.data?.data ?? res.data;
  },

  // Intelligence
  async intelligenceDashboard(params?: { date_from?: string; date_to?: string }): Promise<ESGIntelligenceDashboard> {
    const res = await apiClient.get(`${BASE}/intelligence/dashboard`, { params });
    return res.data?.data ?? res.data;
  },
  async energyIntensity(params?: { date_from?: string; date_to?: string; limit?: number }): Promise<EnergyIntensityRow[]> {
    const res = await apiClient.get(`${BASE}/intelligence/energy-intensity`, { params });
    return res.data?.data ?? res.data;
  },
  async wastewaterCompliance(params?: { date_from?: string; date_to?: string }): Promise<WastewaterComplianceSnapshot> {
    const res = await apiClient.get(`${BASE}/intelligence/wastewater-compliance`, { params });
    return res.data?.data ?? res.data;
  },
  async listSupplierScores(params?: { supplier_id?: string; risk_level?: SupplierSustainabilityRisk; limit?: number }): Promise<SupplierSustainabilityScore[]> {
    const res = await apiClient.get(`${BASE}/supplier-scores`, { params });
    return res.data?.data ?? res.data;
  },
  async createSupplierScore(data: Omit<SupplierSustainabilityScore, "id" | "assessed_by" | "reviewed_at" | "created_at" | "updated_at">): Promise<SupplierSustainabilityScore> {
    const res = await apiClient.post(`${BASE}/supplier-scores`, data);
    return res.data?.data ?? res.data;
  },
  async updateSupplierScore(id: string, data: Partial<SupplierSustainabilityScore>): Promise<SupplierSustainabilityScore> {
    const res = await apiClient.patch(`${BASE}/supplier-scores/${id}`, data);
    return res.data?.data ?? res.data;
  },

  // Import
  async importFleet(params?: { date_from?: string; date_to?: string }): Promise<FleetImportResult> {
    const res = await apiClient.post(`${BASE}/import/fleet`, null, { params });
    return res.data?.data ?? res.data;
  },

  // AI
  async aiHotspot(params?: { date_from?: string; date_to?: string }): Promise<ESGInsight> {
    const res = await apiClient.get(`${BASE}/ai/hotspot`, { params });
    return res.data?.data ?? res.data;
  },
  async aiReduction(params?: { date_from?: string; date_to?: string }): Promise<ESGInsight> {
    const res = await apiClient.get(`${BASE}/ai/reduction-advisor`, { params });
    return res.data?.data ?? res.data;
  },
  async aiDataQuality(params?: { date_from?: string; date_to?: string }): Promise<ESGInsight> {
    const res = await apiClient.get(`${BASE}/ai/data-quality`, { params });
    return res.data?.data ?? res.data;
  },
};

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  FUEL_DIESEL: "Diesel Fuel",
  FUEL_PETROL: "Petrol Fuel",
  FUEL_LPG: "LPG",
  ELECTRICITY_GRID: "Grid Electricity",
  ELECTRICITY_SOLAR: "Solar Electricity",
  TRANSPORT_ROAD: "Road Transport",
  TRANSPORT_AIR: "Air Transport",
  MATERIAL: "Raw Material",
  WATER: "Water",
  WASTE_GENERAL: "General Waste",
  WASTE_HAZARDOUS: "Hazardous Waste",
  WASTE_RECYCLED: "Recycled Waste",
};

export const SOURCE_UNITS: Record<SourceType, string> = {
  FUEL_DIESEL: "liters",
  FUEL_PETROL: "liters",
  FUEL_LPG: "liters",
  ELECTRICITY_GRID: "kWh",
  ELECTRICITY_SOLAR: "kWh",
  TRANSPORT_ROAD: "tonne-km",
  TRANSPORT_AIR: "tonne-km",
  MATERIAL: "kg",
  WATER: "liters",
  WASTE_GENERAL: "kg",
  WASTE_HAZARDOUS: "kg",
  WASTE_RECYCLED: "kg",
};
