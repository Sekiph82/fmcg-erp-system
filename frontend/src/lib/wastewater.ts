/**
 * Biological / Wastewater Treatment — TypeScript types, label maps, API client.
 *
 * Data source: wastewater_records (WastewaterRecord model)
 *
 * KPIs:
 *  cod_removal_pct        COD removal efficiency %
 *  bod_removal_pct        BOD removal efficiency %
 *  compliance_pct         Compliant records %
 *  treatment_cost_per_m3  Treatment cost per m³ effluent
 *  blower_energy_per_m3   Blower energy per m³ effluent
 *  sludge_gen_rate        Sludge generation rate (kg/m³ influent)
 *  non_compliance_risk    Risk flag from recent trend
 *
 * Alarm flags (on WastewaterKPIs):
 *  alarm_ph_out_of_range          effluent pH < 6.0 or > 9.0
 *  alarm_cod_high                 effluent COD > 150 mg/L
 *  alarm_low_do                   dissolved oxygen < 1.5 mg/L
 *  alarm_blower_failure           aeration runtime = 0
 *  alarm_overflow_risk            influent flow > threshold
 *  alarm_non_compliant_discharge  any non-compliant record in period
 */
import { apiClient } from "./api";

// ── Enums & label maps ────────────────────────────────────────────────────────

export type WastewaterProcess =
  | "PRIMARY"
  | "SECONDARY"
  | "TERTIARY"
  | "SLUDGE_HANDLING";

export const PROCESS_STAGE_LABELS: Record<WastewaterProcess, string> = {
  PRIMARY:         "Primary Treatment",
  SECONDARY:       "Secondary (Biological)",
  TERTIARY:        "Tertiary / Polishing",
  SLUDGE_HANDLING: "Sludge Handling",
};

export const PROCESS_STAGE_COLORS: Record<WastewaterProcess, string> = {
  PRIMARY:         "text-blue-400",
  SECONDARY:       "text-emerald-400",
  TERTIARY:        "text-cyan-400",
  SLUDGE_HANDLING: "text-amber-400",
};

export const PROCESS_STAGE_BG: Record<WastewaterProcess, string> = {
  PRIMARY:         "bg-blue-500/10 border-blue-500/20",
  SECONDARY:       "bg-emerald-500/10 border-emerald-500/20",
  TERTIARY:        "bg-cyan-500/10 border-cyan-500/20",
  SLUDGE_HANDLING: "bg-amber-500/10 border-amber-500/20",
};

export type ComplianceStatus =
  | "COMPLIANT"
  | "NON_COMPLIANT"
  | "BORDERLINE"
  | "NOT_TESTED";

export const COMPLIANCE_LABELS: Record<ComplianceStatus, string> = {
  COMPLIANT:     "Compliant",
  NON_COMPLIANT: "Non-Compliant",
  BORDERLINE:    "Borderline",
  NOT_TESTED:    "Not Tested",
};

export const COMPLIANCE_COLORS: Record<ComplianceStatus, string> = {
  COMPLIANT:     "text-emerald-400",
  NON_COMPLIANT: "text-red-400",
  BORDERLINE:    "text-amber-400",
  NOT_TESTED:    "text-slate-400",
};

export const COMPLIANCE_BG: Record<ComplianceStatus, string> = {
  COMPLIANT:     "bg-emerald-500/10 border-emerald-500/20",
  NON_COMPLIANT: "bg-red-500/10 border-red-500/20",
  BORDERLINE:    "bg-amber-500/10 border-amber-500/20",
  NOT_TESTED:    "bg-slate-500/10 border-slate-500/20",
};

// ── CRUD types ────────────────────────────────────────────────────────────────

export interface WastewaterRecord {
  id:        string;
  record_no: string;
  asset_id:  string;
  asset_name?: string | null;
  asset_no?:   string | null;

  record_datetime:  string;
  process_stage:    WastewaterProcess;
  shift_ref?:       string | null;
  operator_id?:     string | null;
  operator_name?:   string | null;

  // Flow
  influent_flow_m3h?: number | null;
  effluent_flow_m3h?: number | null;

  // Organic load
  influent_cod_mgl?:  number | null;
  effluent_cod_mgl?:  number | null;
  influent_bod_mgl?:  number | null;
  effluent_bod_mgl?:  number | null;
  influent_tss_mgl?:  number | null;
  effluent_tss_mgl?:  number | null;

  // pH
  influent_ph?: number | null;
  effluent_ph?: number | null;

  // Biological
  do_mgl?:    number | null;
  mlss_mgl?:  number | null;
  mlvss_mgl?: number | null;
  svi?:       number | null;
  srt_days?:  number | null;

  // Additional
  conductivity_us_cm?: number | null;
  temperature_c?:      number | null;

  // Energy
  power_consumed_kwh?:     number | null;
  aeration_runtime_hours?: number | null;   // blower_runtime
  blower_power_kw?:        number | null;   // blower_power

  // Dosing
  nutrient_dose_kg?:  number | null;
  antifoam_dose_kg?:  number | null;

  // Sludge
  sludge_produced_kg?:     number | null;
  sludge_dewatered_pct?:   number | null;
  sludge_volume_m3?:       number | null;
  sludge_disposal_qty_kg?: number | null;

  // Compliance
  compliance_status:   ComplianceStatus;
  permit_limit_ref?:   string | null;
  deviation_reason?:   string | null;
  corrective_action?:  string | null;

  source_method: string;
  is_anomaly:    boolean;
  anomaly_note?: string | null;
  notes?:        string | null;

  created_at?: string | null;
  updated_at?: string | null;
}

export type WastewaterRecordCreate = Omit<WastewaterRecord,
  "id" | "record_no" | "asset_name" | "asset_no" | "operator_name" | "created_at" | "updated_at"
>;

export type WastewaterRecordUpdate = Partial<Omit<WastewaterRecord,
  "id" | "record_no" | "asset_name" | "asset_no" | "operator_name" | "created_at" | "updated_at"
>>;

// ── KPI & analytics types ─────────────────────────────────────────────────────

export interface WastewaterKPIs {
  date_from?: string | null;
  date_to?:   string | null;

  // Volume
  total_influent_m3:      number;
  total_effluent_m3:      number;
  avg_influent_flow_m3h?: number | null;
  avg_effluent_flow_m3h?: number | null;

  // Organic
  avg_influent_cod?: number | null;
  avg_effluent_cod?: number | null;
  avg_influent_bod?: number | null;
  avg_effluent_bod?: number | null;
  avg_influent_tss?: number | null;
  avg_effluent_tss?: number | null;

  // KPI 1 & 2
  cod_removal_pct?: number | null;
  bod_removal_pct?: number | null;

  // pH
  avg_influent_ph?: number | null;
  avg_effluent_ph?: number | null;

  // Biological
  avg_do_mgl?:   number | null;
  avg_mlss_mgl?: number | null;
  avg_svi?:      number | null;

  // Physical
  avg_conductivity_us_cm?: number | null;
  avg_temperature_c?:      number | null;

  // Energy
  total_power_kwh:          number;
  total_aeration_hours?:    number | null;
  total_blower_power_kwh?:  number | null;

  // KPI 5
  blower_energy_per_m3?: number | null;

  // Dosing
  total_nutrient_dose_kg?: number | null;
  total_antifoam_dose_kg?: number | null;
  chemical_cost_per_m3?:   number | null;

  // Sludge
  total_sludge_produced_kg: number;
  total_sludge_volume_m3?:  number | null;
  total_sludge_disposal_kg?: number | null;
  // KPI 7
  sludge_gen_rate?: number | null;

  // KPI 3
  compliance_pct?:    number | null;
  compliant_count:    number;
  non_compliant_count: number;
  borderline_count:   number;

  // KPI 4
  treatment_cost_per_m3?: number | null;
  treatment_cost_total?:  number | null;

  record_count:  number;
  anomaly_count: number;

  // KPI 8
  non_compliance_risk: boolean;

  // Alarm flags
  alarm_ph_out_of_range:         boolean;
  alarm_cod_high:                boolean;
  alarm_low_do:                  boolean;
  alarm_blower_failure:          boolean;
  alarm_overflow_risk:           boolean;
  alarm_non_compliant_discharge: boolean;
}

export interface WastewaterTrendPoint {
  date:              string;
  influent_flow_m3h: number;
  effluent_flow_m3h: number;
  avg_cod_influent?: number | null;
  avg_cod_effluent?: number | null;
  avg_bod_influent?: number | null;
  avg_bod_effluent?: number | null;
  avg_do?:           number | null;
  avg_ph_effluent?:  number | null;
  power_kwh:         number;
  sludge_kg:         number;
  non_compliant_cnt: number;
  record_count:      number;
}

export interface WastewaterStagePoint {
  stage?:          string | null;
  label:           string;
  record_count:    number;
  avg_cod_removal?: number | null;
  avg_bod_removal?: number | null;
  avg_do?:          number | null;
  non_compliant_cnt: number;
}

export interface WastewaterComplianceSummary {
  period_label:   string;
  total_records:  number;
  compliant:      number;
  non_compliant:  number;
  borderline:     number;
  not_tested:     number;
  compliance_pct?: number | null;
}

export interface WastewaterAlarm {
  alarm_key:       string;
  severity:        "INFO" | "WARNING" | "ALERT" | "CRITICAL";
  message:         string;
  triggered_value?: number | null;
  threshold_value?: number | null;
  record_id?:      string | null;
  triggered_at?:   string | null;
}

export interface WastewaterAsset {
  id:       string;
  asset_no: string;
  name:     string;
}

// ── Filters ────────────────────────────────────────────────────────────────────

export interface WastewaterFilters {
  asset_id?:          string;
  process_stage?:     WastewaterProcess;
  compliance_status?: ComplianceStatus;
  shift_ref?:         string;
  date_from?:         string;
  date_to?:           string;
  is_anomaly?:        boolean;
  skip?:              number;
  limit?:             number;
}

// ── CSV download helper ────────────────────────────────────────────────────────

export async function downloadWastewaterCsv(
  params: Record<string, string | number | boolean | undefined>,
  filename = "wastewater_records.csv",
): Promise<void> {
  const base  = process.env.NEXT_PUBLIC_API_URL ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const qs    = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
  const res = await fetch(
    `${base}/api/v1/wastewater/records/export/csv${qs ? "?" + qs : ""}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
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

export const wastewaterApi = {
  async kpis(params?: Partial<WastewaterFilters>): Promise<WastewaterKPIs> {
    const r = await apiClient.get<WastewaterKPIs>("/api/v1/wastewater/kpis", { params });
    return r.data;
  },

  async dailyTrend(params?: Partial<WastewaterFilters>): Promise<WastewaterTrendPoint[]> {
    const r = await apiClient.get<WastewaterTrendPoint[]>("/api/v1/wastewater/trend/daily", { params });
    return r.data;
  },

  async stageAnalysis(params?: Partial<WastewaterFilters>): Promise<WastewaterStagePoint[]> {
    const r = await apiClient.get<WastewaterStagePoint[]>("/api/v1/wastewater/trend/stage", { params });
    return r.data;
  },

  async complianceSummary(params?: Partial<WastewaterFilters>): Promise<WastewaterComplianceSummary> {
    const r = await apiClient.get<WastewaterComplianceSummary>("/api/v1/wastewater/compliance/summary", { params });
    return r.data;
  },

  async evaluateAlarms(recordId: string): Promise<WastewaterAlarm[]> {
    const r = await apiClient.get<WastewaterAlarm[]>(`/api/v1/wastewater/alarms/evaluate/${recordId}`);
    return r.data;
  },

  async listAssets(): Promise<WastewaterAsset[]> {
    const r = await apiClient.get<WastewaterAsset[]>("/api/v1/wastewater/assets");
    return r.data;
  },

  async listRecords(params?: Partial<WastewaterFilters>): Promise<WastewaterRecord[]> {
    const r = await apiClient.get<WastewaterRecord[]>("/api/v1/wastewater/records", { params });
    return r.data;
  },

  async getRecord(id: string): Promise<WastewaterRecord> {
    const r = await apiClient.get<WastewaterRecord>(`/api/v1/wastewater/records/${id}`);
    return r.data;
  },

  async createRecord(data: WastewaterRecordCreate): Promise<WastewaterRecord> {
    const r = await apiClient.post<WastewaterRecord>("/api/v1/wastewater/records", data);
    return r.data;
  },

  async updateRecord(id: string, data: WastewaterRecordUpdate): Promise<WastewaterRecord> {
    const r = await apiClient.patch<WastewaterRecord>(`/api/v1/wastewater/records/${id}`, data);
    return r.data;
  },

  async deleteRecord(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/wastewater/records/${id}`);
  },
};
