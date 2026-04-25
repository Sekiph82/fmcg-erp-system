/**
 * Utility Alarm & Anomaly Detection — TypeScript types and API client.
 */
import { apiClient } from "./api";

// ── Enums ─────────────────────────────────────────────────────────────────────

export type AlarmSeverity = "INFO" | "WARNING" | "ALERT" | "CRITICAL";
export type AlarmStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "SUPPRESSED";
export type AlarmDetectionType =
  | "THRESHOLD"
  | "SUDDEN_JUMP"
  | "ROLLING_DEVIATION"
  | "SHIFT_COMPARISON"
  | "MACHINE_COMPARISON"
  | "VS_STANDARD";
export type AlarmCategory =
  | "ENERGY"
  | "WATER"
  | "BOILER_STEAM"
  | "COMPRESSED_AIR"
  | "SOLAR"
  | "WASTEWATER"
  | "CHEMICAL"
  | "COMPLIANCE"
  | "COST"
  | "GENERAL";
export type AlarmOperator = "GT" | "LT" | "GTE" | "LTE" | "EQ" | "NEQ" | "DELTA_PCT";
export type UtilityType =
  | "ELECTRICITY"
  | "WATER"
  | "SOFT_WATER"
  | "PROCESS_WATER"
  | "STEAM"
  | "COMPRESSED_AIR"
  | "SOLAR"
  | "NATURAL_GAS"
  | "WASTEWATER"
  | "DIESEL"
  | "CHILLED_WATER"
  | "OTHER";

// ── Interfaces ────────────────────────────────────────────────────────────────

export interface AlarmRule {
  id: string;
  rule_code: string;
  name: string;
  description?: string | null;
  utility_type: UtilityType;
  alarm_type?: string | null;
  source_module?: string | null;
  alarm_category: AlarmCategory;
  detection_type: AlarmDetectionType;
  parameter: string;
  operator: AlarmOperator;
  threshold_value: number;
  threshold_unit?: string | null;
  rolling_window_hours?: number | null;
  delta_pct_threshold?: number | null;
  standard_value?: number | null;
  severity: AlarmSeverity;
  cooldown_minutes: number;
  evaluation_frequency_min: number;
  is_active: boolean;
  notification_emails?: string | null;
  notification_channel?: string | null;
  notes?: string | null;
  device_name?: string | null;
  asset_name?: string | null;
  created_by_name?: string | null;
  event_count: number;
  created_at: string;
}

export interface AlarmEvent {
  id: string;
  event_no: string;
  rule_id: string;
  rule_code?: string | null;
  rule_name?: string | null;
  triggered_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  status: AlarmStatus;
  severity: AlarmSeverity;
  alarm_type?: string | null;
  source_module?: string | null;
  detection_type?: string | null;
  parameter?: string | null;
  triggered_value?: number | null;
  expected_value?: number | null;
  threshold_value?: number | null;
  threshold_unit?: string | null;
  deviation_pct?: number | null;
  root_cause?: string | null;
  corrective_action?: string | null;
  device_name?: string | null;
  asset_name?: string | null;
  assigned_to_name?: string | null;
  acknowledged_by_name?: string | null;
  resolved_by_name?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface AlarmSummary {
  total_active: number;
  total_acknowledged: number;
  critical_count: number;
  alert_count: number;
  warning_count: number;
  info_count: number;
  by_utility_type: Record<string, number>;
  by_category: Record<string, number>;
}

export interface AlarmRuleTemplate {
  template_key: string;
  name: string;
  description: string;
  alarm_type: string;
  source_module: string;
  utility_type: UtilityType;
  alarm_category: AlarmCategory;
  detection_type: AlarmDetectionType;
  parameter: string;
  operator: AlarmOperator;
  threshold_value: number;
  threshold_unit: string;
  severity: AlarmSeverity;
  rolling_window_hours?: number | null;
  delta_pct_threshold?: number | null;
  standard_value?: number | null;
}

export interface AlarmRuleFilters {
  utility_type?: UtilityType;
  severity?: AlarmSeverity;
  is_active?: boolean;
  detection_type?: AlarmDetectionType;
  skip?: number;
  limit?: number;
}

export interface AlarmEventFilters {
  status?: AlarmStatus;
  severity?: AlarmSeverity;
  utility_type?: UtilityType;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
}

export type AlarmRuleCreate = Omit<AlarmRule, "id" | "event_count" | "created_at" | "created_by_name">;
export type AlarmRuleUpdate = Partial<Omit<AlarmRule, "id" | "rule_code" | "event_count" | "created_at" | "created_by_name">>;

// ── Color maps ────────────────────────────────────────────────────────────────

export const SEVERITY_COLOR: Record<AlarmSeverity, string> = {
  CRITICAL: "#ef4444",
  ALERT:    "#f97316",
  WARNING:  "#eab308",
  INFO:     "#60a5fa",
};

export const SEVERITY_BG_CLASS: Record<AlarmSeverity, string> = {
  CRITICAL: "bg-red-600 text-white",
  ALERT:    "bg-orange-500 text-white",
  WARNING:  "bg-yellow-500 text-white",
  INFO:     "bg-blue-500 text-white",
};

export const SEVERITY_SOFT_CLASS: Record<AlarmSeverity, string> = {
  CRITICAL: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  ALERT:    "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  WARNING:  "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  INFO:     "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
};

export const STATUS_SOFT_CLASS: Record<AlarmStatus, string> = {
  ACTIVE:       "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  ACKNOWLEDGED: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  RESOLVED:     "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  SUPPRESSED:   "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
};

// ── Label maps ────────────────────────────────────────────────────────────────

export const DETECTION_TYPE_LABELS: Record<AlarmDetectionType, string> = {
  THRESHOLD:          "Threshold",
  SUDDEN_JUMP:        "Sudden Jump",
  ROLLING_DEVIATION:  "Rolling Avg",
  SHIFT_COMPARISON:   "Shift Comparison",
  MACHINE_COMPARISON: "Machine Compare",
  VS_STANDARD:        "vs. Standard",
};

export const DETECTION_TYPE_DESCRIPTIONS: Record<AlarmDetectionType, string> = {
  THRESHOLD:          "Triggers when value exceeds a fixed threshold",
  SUDDEN_JUMP:        "Triggers on rapid percentage change between readings",
  ROLLING_DEVIATION:  "Triggers when value deviates from rolling average",
  SHIFT_COMPARISON:   "Compares current shift data to previous shift",
  MACHINE_COMPARISON: "Compares machine performance against similar machines",
  VS_STANDARD:        "Triggers when value deviates from standard/benchmark",
};

export const ALARM_CATEGORY_LABELS: Record<AlarmCategory, string> = {
  ENERGY:        "Energy",
  WATER:         "Water",
  BOILER_STEAM:  "Boiler / Steam",
  COMPRESSED_AIR:"Compressed Air",
  SOLAR:         "Solar",
  WASTEWATER:    "Wastewater",
  CHEMICAL:      "Chemical",
  COMPLIANCE:    "Compliance",
  COST:          "Cost",
  GENERAL:       "General",
};

export const OPERATOR_LABELS: Record<AlarmOperator, string> = {
  GT:        "Greater than (>)",
  LT:        "Less than (<)",
  GTE:       "Greater than or equal (≥)",
  LTE:       "Less than or equal (≤)",
  EQ:        "Equals (=)",
  NEQ:       "Not equal (≠)",
  DELTA_PCT: "Delta percentage (%Δ)",
};

export const OPERATOR_SYMBOLS: Record<AlarmOperator, string> = {
  GT:        ">",
  LT:        "<",
  GTE:       "≥",
  LTE:       "≤",
  EQ:        "=",
  NEQ:       "≠",
  DELTA_PCT: "%Δ",
};

export const UTILITY_TYPE_LABELS: Record<UtilityType, string> = {
  ELECTRICITY:    "Electricity",
  WATER:          "Water",
  SOFT_WATER:     "Soft Water",
  PROCESS_WATER:  "Process Water",
  STEAM:          "Steam",
  COMPRESSED_AIR: "Compressed Air",
  SOLAR:          "Solar",
  NATURAL_GAS:    "Natural Gas",
  WASTEWATER:     "Wastewater",
  DIESEL:         "Diesel",
  CHILLED_WATER:  "Chilled Water",
  OTHER:          "Other",
};

export const UTILITY_TYPE_ICONS: Record<UtilityType, string> = {
  ELECTRICITY:    "⚡",
  WATER:          "💧",
  SOFT_WATER:     "🌊",
  PROCESS_WATER:  "🔵",
  STEAM:          "♨️",
  COMPRESSED_AIR: "💨",
  SOLAR:          "☀️",
  NATURAL_GAS:    "🔥",
  WASTEWATER:     "♻️",
  DIESEL:         "🛢️",
  CHILLED_WATER:  "❄️",
  OTHER:          "🔧",
};

export const ALARM_CATEGORY_ICONS: Record<AlarmCategory, string> = {
  ENERGY:         "⚡",
  WATER:          "💧",
  BOILER_STEAM:   "♨️",
  COMPRESSED_AIR: "💨",
  SOLAR:          "☀️",
  WASTEWATER:     "♻️",
  CHEMICAL:       "🧪",
  COMPLIANCE:     "📋",
  COST:           "💰",
  GENERAL:        "🔔",
};

export const SEVERITY_ICONS: Record<AlarmSeverity, string> = {
  CRITICAL: "🔴",
  ALERT:    "🟠",
  WARNING:  "⚠",
  INFO:     "ℹ",
};

// ── API client ────────────────────────────────────────────────────────────────

export const alarmApi = {
  // Rules
  async listRules(params?: AlarmRuleFilters): Promise<AlarmRule[]> {
    const filtered = params
      ? Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ""))
      : {};
    const r = await apiClient.get<AlarmRule[]>("/api/v1/alarms/rules", { params: filtered }).then((r) => r.data);
    return r.data;
  },

  async getRuleTemplates(): Promise<AlarmRuleTemplate[]> {
    const r = await apiClient.get<AlarmRuleTemplate[]>("/api/v1/alarms/rules/templates").then((r) => r.data);
    return r.data;
  },

  async createRule(data: AlarmRuleCreate): Promise<AlarmRule> {
    const r = await apiClient.post<AlarmRule>("/api/v1/alarms/rules", data).then((r) => r.data);
    return r.data;
  },

  async getRule(id: string): Promise<AlarmRule> {
    const r = await apiClient.get<AlarmRule>(`/api/v1/alarms/rules/${id}`).then((r) => r.data);
    return r.data;
  },

  async updateRule(id: string, data: AlarmRuleUpdate): Promise<AlarmRule> {
    const r = await apiClient.patch<AlarmRule>(`/api/v1/alarms/rules/${id}`, data).then((r) => r.data);
    return r.data;
  },

  async deleteRule(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/alarms/rules/${id}`).then((r) => r.data);
  },

  async toggleRule(id: string): Promise<AlarmRule> {
    const r = await apiClient.post<AlarmRule>(`/api/v1/alarms/rules/${id}/toggle`).then((r) => r.data);
    return r.data;
  },

  // Events
  async getEventsSummary(): Promise<AlarmSummary> {
    const r = await apiClient.get<AlarmSummary>("/api/v1/alarms/events/summary").then((r) => r.data);
    return r.data;
  },

  async listEvents(params?: AlarmEventFilters): Promise<AlarmEvent[]> {
    const filtered = params
      ? Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ""))
      : {};
    const r = await apiClient.get<AlarmEvent[]>("/api/v1/alarms/events", { params: filtered }).then((r) => r.data);
    return r.data;
  },

  async getEvent(id: string): Promise<AlarmEvent> {
    const r = await apiClient.get<AlarmEvent>(`/api/v1/alarms/events/${id}`).then((r) => r.data);
    return r.data;
  },

  async acknowledgeEvent(id: string, notes?: string): Promise<AlarmEvent> {
    const r = await apiClient.post<AlarmEvent>(`/api/v1/alarms/events/${id}/acknowledge`, { notes }).then((r) => r.data);
    return r.data;
  },

  async assignEvent(id: string, assigned_to_id: string): Promise<AlarmEvent> {
    const r = await apiClient.post<AlarmEvent>(`/api/v1/alarms/events/${id}/assign`, { assigned_to_id }).then((r) => r.data);
    return r.data;
  },

  async resolveEvent(
    id: string,
    payload: { root_cause: string; corrective_action: string; notes?: string },
  ): Promise<AlarmEvent> {
    const r = await apiClient.post<AlarmEvent>(`/api/v1/alarms/events/${id}/resolve`, payload).then((r) => r.data);
    return r.data;
  },

  async suppressEvent(id: string): Promise<AlarmEvent> {
    const r = await apiClient.post<AlarmEvent>(`/api/v1/alarms/events/${id}/suppress`).then((r) => r.data);
    return r.data;
  },

  // Evaluation
  async evaluate(): Promise<{ new_alarms: number; message: string }> {
    const r = await apiClient.post<{ new_alarms: number; message: string }>("/api/v1/alarms/evaluate").then((r) => r.data);
    return r.data;
  },
};
