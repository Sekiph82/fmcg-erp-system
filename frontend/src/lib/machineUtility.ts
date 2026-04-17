/**
 * Machine Utility Consumption Mapping — TypeScript types, label maps, API client.
 *
 * Two-layer design:
 *   MachineUtilityMapping     master config: machine ↔ meter link + rated consumption
 *   MachineConsumptionRecord  operational log: actual consumption per machine/shift
 *
 * KPIs:
 *   electricity_per_runtime_h  kWh / runtime hour
 *   water_per_batch            m³  / batch
 *   air_per_batch              Nm³ / batch
 *   standby_pct                standby share of total consumption %
 *   cost_per_batch             total_cost / batch count
 *   avg_variance_pct           deviation from nominal rate
 */
import { apiClient } from "./api";

// ── Enums & label maps ────────────────────────────────────────────────────────

export type UtilityType =
  | "ELECTRICITY"
  | "WATER"
  | "SOFT_WATER"
  | "PROCESS_WATER"
  | "STEAM"
  | "COMPRESSED_AIR"
  | "NATURAL_GAS"
  | "SOLAR"
  | "DIESEL"
  | "CHILLED_WATER"
  | "OTHER";

export const UTILITY_TYPE_LABELS: Record<UtilityType, string> = {
  ELECTRICITY:    "Electricity",
  WATER:          "Water",
  SOFT_WATER:     "Soft Water",
  PROCESS_WATER:  "Process Water",
  STEAM:          "Steam",
  COMPRESSED_AIR: "Compressed Air",
  NATURAL_GAS:    "Natural Gas",
  SOLAR:          "Solar",
  DIESEL:         "Diesel",
  CHILLED_WATER:  "Chilled Water",
  OTHER:          "Other",
};

export const UTILITY_TYPE_COLORS: Record<UtilityType, string> = {
  ELECTRICITY:    "#fbbf24",
  WATER:          "#60a5fa",
  SOFT_WATER:     "#93c5fd",
  PROCESS_WATER:  "#3b82f6",
  STEAM:          "#f97316",
  COMPRESSED_AIR: "#22d3ee",
  NATURAL_GAS:    "#a78bfa",
  SOLAR:          "#facc15",
  DIESEL:         "#94a3b8",
  CHILLED_WATER:  "#67e8f9",
  OTHER:          "#6b7280",
};

export const SOURCE_METHOD_LABELS: Record<string, string> = {
  MANUAL:     "Manual Entry",
  ESTIMATED:  "Estimated",
  CALCULATED: "Calculated",
  IOT:        "IoT / SCADA",
  API:        "External API",
  IMPORTED:   "CSV Import",
};

// ── Mapping master types ───────────────────────────────────────────────────────

export interface MachineUtilityMapping {
  id:              string;
  machine_ref:     string;
  machine_name:    string;
  work_center_id?: string | null;
  department?:     string | null;
  production_line?: string | null;
  building_area?:  string | null;
  utility_type:    UtilityType;
  device_id?:      string | null;
  device_name?:    string | null;
  asset_id?:       string | null;
  allocation_pct?: number | null;
  rated_consumption?: number | null;
  rated_unit?:     string | null;
  is_active:       boolean;
  notes?:          string | null;
  created_at?:     string | null;
  updated_at?:     string | null;
}

export type MachineUtilityMappingCreate = Omit<MachineUtilityMapping,
  "id" | "device_name" | "created_at" | "updated_at"
>;

export type MachineUtilityMappingUpdate = Partial<Omit<MachineUtilityMapping,
  "id" | "machine_ref" | "device_name" | "created_at" | "updated_at"
>>;

// ── Consumption record types ───────────────────────────────────────────────────

export interface MachineConsumptionRecord {
  id:              string;
  record_no:       string;
  mapping_id?:     string | null;
  work_center_id:  string;
  machine_ref:     string;
  machine_name?:   string | null;
  utility_type:    UtilityType;
  device_id?:      string | null;
  device_name?:    string | null;

  record_date:     string;
  shift_ref?:      string | null;
  department?:     string | null;
  production_line?: string | null;

  source_method:   string;
  is_estimated:    boolean;
  is_standby:      boolean;

  runtime_hours?:  number | null;

  nominal_rate?:   number | null;
  nominal_unit?:   string | null;

  actual_consumption?: number | null;
  actual_unit?:    string | null;
  variance_pct?:   number | null;

  production_order_id?: string | null;
  production_order_no?: string | null;
  batch_no?:       string | null;
  batch_lot_id?:   string | null;

  cost_rate?:      number | null;
  total_cost?:     number | null;
  currency_code?:  string | null;

  is_anomaly:      boolean;
  anomaly_note?:   string | null;
  notes?:          string | null;

  entered_by_id?:   string | null;
  entered_by_name?: string | null;

  created_at?: string | null;
  updated_at?: string | null;
}

export type MachineConsumptionRecordCreate = Omit<MachineConsumptionRecord,
  "id" | "record_no" | "machine_ref" | "machine_name" | "device_name"
  | "production_order_no" | "entered_by_id" | "entered_by_name"
  | "created_at" | "updated_at"
>;

export type MachineConsumptionRecordUpdate = Partial<Omit<MachineConsumptionRecord,
  "id" | "record_no" | "work_center_id" | "machine_ref" | "machine_name"
  | "device_name" | "production_order_no" | "entered_by_id" | "entered_by_name"
  | "created_at" | "updated_at"
>>;

// ── KPI & analytics types ─────────────────────────────────────────────────────

export interface MachineUtilityKPIs {
  date_from?: string | null;
  date_to?:   string | null;
  machine_ref?: string | null;
  utility_type?: string | null;

  total_consumption:          number;
  total_runtime_hours?:       number | null;
  total_standby_consumption?: number | null;
  consumption_unit?:          string | null;

  electricity_per_runtime_h?: number | null;
  water_per_batch?:           number | null;
  air_per_batch?:             number | null;
  standby_pct?:               number | null;
  cost_per_batch?:            number | null;
  cost_per_unit?:             number | null;

  total_cost?:     number | null;
  avg_cost_rate?:  number | null;
  avg_variance_pct?: number | null;

  record_count:    number;
  batch_count:     number;
  order_count:     number;
  anomaly_count:   number;

  flag_high_variance:  boolean;
  flag_standby_waste:  boolean;
}

export interface MachineUtilityTrendPoint {
  date:              string;
  machine_ref?:      string | null;
  utility_type?:     string | null;
  total_consumption: number;
  standby:           number;
  runtime_hours:     number;
  total_cost?:       number | null;
  batch_count:       number;
  record_count:      number;
}

export interface MachineUtilityBreakdownRow {
  group_key?:        string | null;
  label:             string;
  total_consumption: number;
  total_cost?:       number | null;
  pct_of_total?:     number | null;
  runtime_hours?:    number | null;
  record_count:      number;
}

export interface MachineUtilityBreakdown {
  dimension:    string;
  rows:         MachineUtilityBreakdownRow[];
  grand_total:  number;
}

// ── Dropdown types ─────────────────────────────────────────────────────────────

export interface WorkCenterDropdown {
  id:             string;
  work_center_id: string;
  name:           string;
  department?:    string | null;
  type:           string;
}

export interface MappingDropdown {
  id:           string;
  machine_ref:  string;
  machine_name: string;
  utility_type: UtilityType;
  rated_consumption?: number | null;
  rated_unit?:  string | null;
}

export interface DeviceDropdown {
  id:              string;
  device_code:     string;
  name:            string;
  utility_type:    string;
  unit_of_measure?: string | null;
}

export interface ProductionOrderDropdown {
  id:       string;
  order_no: string;
  batch_no?: string | null;
  status:   string;
}

// ── Filters ────────────────────────────────────────────────────────────────────

export interface MachineUtilityFilters {
  work_center_id?:      string;
  machine_ref?:         string;
  utility_type?:        UtilityType;
  production_line?:     string;
  department?:          string;
  shift_ref?:           string;
  date_from?:           string;
  date_to?:             string;
  batch_no?:            string;
  production_order_id?: string;
  is_standby?:          boolean;
  is_anomaly?:          boolean;
  is_estimated?:        boolean;
  skip?:                number;
  limit?:               number;
}

// ── CSV download ───────────────────────────────────────────────────────────────

export async function downloadMachineUtilityCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename = "machine_consumption.csv",
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const qs    = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
  const res = await fetch(
    `${base}/api/v1/machine-utility/records/export/csv${qs ? "?" + qs : ""}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ── API client ─────────────────────────────────────────────────────────────────

export const machineUtilityApi = {
  // ── Dropdowns
  async workCenters(): Promise<WorkCenterDropdown[]> {
    const r = await apiClient.get<WorkCenterDropdown[]>("/api/v1/machine-utility/work-centers");
    return r.data;
  },
  async devices(utilityType?: UtilityType): Promise<DeviceDropdown[]> {
    const r = await apiClient.get<DeviceDropdown[]>("/api/v1/machine-utility/devices",
      { params: utilityType ? { utility_type: utilityType } : {} });
    return r.data;
  },
  async productionOrders(): Promise<ProductionOrderDropdown[]> {
    const r = await apiClient.get<ProductionOrderDropdown[]>("/api/v1/machine-utility/production-orders");
    return r.data;
  },
  async mappingDropdown(workCenterId?: string, utilityType?: UtilityType): Promise<MappingDropdown[]> {
    const r = await apiClient.get<MappingDropdown[]>("/api/v1/machine-utility/mappings/dropdown",
      { params: { work_center_id: workCenterId, utility_type: utilityType } });
    return r.data;
  },

  // ── Mapping master CRUD
  async listMappings(params?: Partial<MachineUtilityFilters>): Promise<MachineUtilityMapping[]> {
    const r = await apiClient.get<MachineUtilityMapping[]>("/api/v1/machine-utility/mappings", { params });
    return r.data;
  },
  async createMapping(data: MachineUtilityMappingCreate): Promise<MachineUtilityMapping> {
    const r = await apiClient.post<MachineUtilityMapping>("/api/v1/machine-utility/mappings", data);
    return r.data;
  },
  async updateMapping(id: string, data: MachineUtilityMappingUpdate): Promise<MachineUtilityMapping> {
    const r = await apiClient.patch<MachineUtilityMapping>(`/api/v1/machine-utility/mappings/${id}`, data);
    return r.data;
  },
  async deleteMapping(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/machine-utility/mappings/${id}`);
  },

  // ── Consumption records CRUD
  async listRecords(params?: Partial<MachineUtilityFilters>): Promise<MachineConsumptionRecord[]> {
    const r = await apiClient.get<MachineConsumptionRecord[]>("/api/v1/machine-utility/records", { params });
    return r.data;
  },
  async createRecord(data: MachineConsumptionRecordCreate): Promise<MachineConsumptionRecord> {
    const r = await apiClient.post<MachineConsumptionRecord>("/api/v1/machine-utility/records", data);
    return r.data;
  },
  async updateRecord(id: string, data: MachineConsumptionRecordUpdate): Promise<MachineConsumptionRecord> {
    const r = await apiClient.patch<MachineConsumptionRecord>(`/api/v1/machine-utility/records/${id}`, data);
    return r.data;
  },
  async deleteRecord(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/machine-utility/records/${id}`);
  },

  // ── Analytics
  async kpis(params?: Partial<MachineUtilityFilters>): Promise<MachineUtilityKPIs> {
    const r = await apiClient.get<MachineUtilityKPIs>("/api/v1/machine-utility/kpis", { params });
    return r.data;
  },
  async dailyTrend(params?: Partial<MachineUtilityFilters>): Promise<MachineUtilityTrendPoint[]> {
    const r = await apiClient.get<MachineUtilityTrendPoint[]>("/api/v1/machine-utility/trend/daily", { params });
    return r.data;
  },
  async breakdown(
    dimension: "machine" | "utility" | "shift" | "line" | "department",
    params?: Partial<MachineUtilityFilters>,
  ): Promise<MachineUtilityBreakdown> {
    const r = await apiClient.get<MachineUtilityBreakdown>("/api/v1/machine-utility/breakdown",
      { params: { ...params, dimension } });
    return r.data;
  },
};
