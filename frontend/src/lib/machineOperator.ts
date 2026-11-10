import { apiClient } from "@/lib/api";

export type MachineStatus = "ACTIVE" | "MAINTENANCE" | "INACTIVE" | "RETIRED";
export type MachineFamily = "FILLING" | "MIXING" | "PACKAGING" | "LABELING" | "PALLETIZING" | "CONVEYOR" | "WEIGHING" | "INSPECTION" | "UTILITY" | "OTHER";
export type SkillLevel = "TRAINEE" | "BASIC" | "INTERMEDIATE" | "ADVANCED" | "EXPERT";
export type CertStatus = "VALID" | "EXPIRING_SOON" | "EXPIRED" | "PENDING" | "BLOCKED";
export type RuntimeActivity = "SETUP" | "RUNNING" | "PAUSED" | "IDLE" | "DOWNTIME" | "CLEANUP" | "CHANGEOVER" | "MAINTENANCE" | "QC_WAIT";
export type DowntimeClass = "MECHANICAL_BREAKDOWN" | "ELECTRICAL_ISSUE" | "PNEUMATIC_ISSUE" | "MATERIAL_SHORTAGE" | "PACKAGING_SHORTAGE" | "OPERATOR_UNAVAILABLE" | "QC_WAITING" | "CHANGEOVER_DELAY" | "CLEANING_DELAY" | "MAINTENANCE_INTERVENTION" | "SPEED_LOSS" | "MICRO_STOP" | "PLANNED_STOP" | "UNPLANNED_STOP" | "UTILITY_ISSUE" | "OTHER";
export type LaborActivity = "SETUP" | "RUN" | "CLEANUP" | "DOWNTIME_SUPPORT" | "QC_SUPPORT" | "REWORK" | "MAINTENANCE_ASSIST" | "CHANGEOVER";
export type MOAIAgentType = "PERFORMANCE_ANOMALY" | "PRODUCTIVITY_OPTIMIZER" | "COST_VARIANCE";
export type MOAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "APPLIED";

export interface DowntimeReasonCode {
  code: string;
  label: string;
  parent_code?: string | null;
  is_selectable: boolean;
  is_active: boolean;
  sort_order: number;
}

export interface Machine {
  id: string;
  machine_code: string;
  machine_name: string;
  machine_family: MachineFamily;
  machine_type?: string;
  plant_id?: string;
  line_id?: string;
  work_center_id?: string;
  work_center_name?: string;
  manufacturer?: string;
  model_no?: string;
  serial_no?: string;
  commission_date?: string;
  status: MachineStatus;
  rated_capacity_per_hour?: number;
  capacity_uom?: string;
  standard_speed?: number;
  setup_time_standard_min?: number;
  cleanup_time_standard_min?: number;
  changeover_time_standard_min?: number;
  hourly_cost_rate?: number;
  energy_cost_per_hour?: number;
  oee_tracking_enabled: boolean;
  active_flag: boolean;
  notes?: string;
}

export interface OperatorProfile {
  id: string;
  operator_code: string;
  full_name: string;
  department?: string;
  skill_level: SkillLevel;
  primary_work_center_id?: string;
  primary_machine_id?: string;
  labor_rate_per_hour?: number;
  active_flag: boolean;
  cert_count?: number;
  expiring_cert_count?: number;
}

export interface ProductionTeam {
  id: string;
  team_code: string;
  team_name: string;
  supervisor_id?: string;
  active_flag: boolean;
  member_count?: number;
}

export interface TeamMember {
  id: string;
  team_id: string;
  operator_id: string;
  operator_name?: string;
  role_in_team?: string;
  active_flag: boolean;
}

export interface SkillCert {
  id: string;
  operator_id: string;
  machine_id?: string;
  work_center_id?: string;
  operation_code?: string;
  skill_level: SkillLevel;
  cert_status: CertStatus;
  certification_required: boolean;
  certification_expiry?: string;
  operator_name?: string;
  machine_name?: string;
}

export interface AssignmentValidateResult {
  valid: boolean;
  warnings: string[];
  blocks: string[];
  operator_certified: boolean;
  machine_available: boolean;
}

export interface WorkOrderAssignment {
  id: string;
  work_order_id: string;
  machine_id?: string;
  operator_id?: string;
  team_id?: string;
  shift_id?: string;
  assigned_at: string;
  cert_validation_passed: boolean;
  cert_override_flag: boolean;
  machine_name?: string;
  operator_name?: string;
  team_name?: string;
}

export interface AssignmentHistory {
  id: string;
  work_order_id: string;
  assignment_type: string;
  old_value?: string;
  new_value?: string;
  changed_at: string;
  reason?: string;
}

export interface RuntimeLog {
  id: string;
  machine_id: string;
  work_order_id?: string;
  activity_type: RuntimeActivity;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  operator_id?: string;
  reason_code?: string;
  notes?: string;
  machine_name?: string;
  operator_name?: string;
}

export interface MachineRuntimeActivityKpi {
  activity_type: RuntimeActivity;
  duration_minutes: number;
  log_count: number;
  source_runtime_log_ids: string[];
}

export interface MachineRuntimeKpis {
  machine_id: string;
  machine_code: string;
  machine_name: string;
  period_start: string;
  period_end: string;
  recorded_activity_log_minutes: number;
  activities: MachineRuntimeActivityKpi[];
  unavailable_runtime_log_ids: string[];
  data_notes: string[];
}

export interface LaborTimeLog {
  id: string;
  operator_id: string;
  work_order_id?: string;
  activity_type: LaborActivity;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  cost_rate_at_time?: number;
  overtime_flag: boolean;
  overtime_minutes?: number;
  approved_flag: boolean;
  operator_name?: string;
}

export interface OperatorProductivityByUom {
  uom: string;
  allocated_output_quantity: number;
  operator_labor_minutes_for_completed_orders: number;
  output_quantity_per_operator_labor_hour?: number | null;
  source_work_order_ids: string[];
  source_labor_log_ids: string[];
  allocation_labor_log_ids: string[];
}

export interface OperatorProductivity {
  operator_id: string;
  period_start: string;
  period_end: string;
  approved_labor_log_count: number;
  unapproved_labor_log_count: number;
  approved_labor_minutes: number;
  approved_labor_hours: number;
  completed_work_order_count: number;
  unavailable_output_work_order_ids: string[];
  output_by_uom: OperatorProductivityByUom[];
  period_labor_log_ids: string[];
  data_notes: string[];
}

export interface ComparisonOutputByUom {
  uom: string;
  allocated_output_quantity: number;
  labor_minutes_for_completed_orders: number;
  output_quantity_per_labor_hour?: number | null;
  source_work_order_ids: string[];
  source_labor_log_ids: string[];
  allocation_labor_log_ids: string[];
}

export interface ComparisonRuntimeActivity {
  activity_type: RuntimeActivity;
  duration_minutes: number;
  source_runtime_log_ids: string[];
}

export interface ShiftTeamComparisonGroup {
  group_id?: string | null;
  group_code: string;
  group_name: string;
  approved_labor_log_count: number;
  unapproved_labor_log_count: number;
  approved_labor_minutes: number;
  approved_labor_hours: number;
  runtime_log_count: number;
  recorded_runtime_minutes: number;
  unavailable_runtime_log_ids: string[];
  runtime_by_activity: ComparisonRuntimeActivity[];
  source_labor_log_ids: string[];
  source_runtime_log_ids: string[];
  output_by_uom: ComparisonOutputByUom[];
}

export interface ShiftTeamComparisons {
  period_start: string;
  period_end: string;
  teams: ShiftTeamComparisonGroup[];
  shifts: ShiftTeamComparisonGroup[];
  unavailable_output_work_order_ids: string[];
  period_labor_log_ids: string[];
  period_runtime_log_ids: string[];
  data_notes: string[];
}

export interface MachinePerformanceAnomaly {
  machine_id: string;
  machine_code: string;
  machine_name: string;
  runtime_log_id: string;
  event_start: string;
  event_end: string;
  observed_downtime_minutes: number;
  baseline_event_count: number;
  baseline_median_minutes: number;
  baseline_mad_minutes: number;
  alert_threshold_minutes: number;
  source_baseline_runtime_log_ids: string[];
}

export interface PerformanceAnomalyReport {
  period_start: string;
  period_end: string;
  baseline_start: string;
  anomalies: MachinePerformanceAnomaly[];
  insufficient_baseline_machine_ids: string[];
  unavailable_runtime_log_ids: string[];
  overlapping_runtime_log_ids: string[];
  data_notes: string[];
}

export interface CorrelatedQualityInspection {
  inspection_id: string;
  qc_id: string;
  status: string;
  inspection_type: string;
  inspected_at?: string | null;
  work_order_id?: string | null;
  production_order_id?: string | null;
  results: { result_id: string; test_type: string; result: string; actual_value?: number | null; unit?: string | null }[];
}

export interface CorrelatedWasteRecord {
  waste_record_id: string;
  waste_id: string;
  work_order_id?: string | null;
  production_order_id: string;
  waste_type: string;
  waste_category: string;
  expected_qty: number;
  actual_qty: number;
  loss_qty: number;
  loss_pct?: number | null;
  uom?: string | null;
  is_anomaly: boolean;
}

export interface DowntimeProductionCorrelation {
  downtime_id: string;
  machine_id: string;
  machine_code: string;
  machine_name: string;
  work_order_id?: string | null;
  production_order_id?: string | null;
  downtime_class: string;
  start_time: string;
  end_time?: string | null;
  duration_minutes?: number | null;
  reported_by_operator_id?: string | null;
  observed_operator_ids: string[];
  runtime_log_ids: string[];
  labor_logs: { labor_log_id: string; operator_id: string; approved_flag: boolean; start_time: string; end_time?: string | null; duration_minutes?: number | null }[];
  quality_inspections: CorrelatedQualityInspection[];
  waste_records: CorrelatedWasteRecord[];
  correlation_basis: string[];
}

export interface DowntimeProductionCorrelationReport {
  period_start: string;
  period_end: string;
  events: DowntimeProductionCorrelation[];
  follow_up_handoffs: {
    handoff_id: string;
    destination: "maintenance" | "training" | "planning";
    destination_path: string;
    title: string;
    rationale: string;
    machine_id: string;
    machine_code: string;
    downtime_id: string;
    work_order_id?: string | null;
    production_order_id?: string | null;
    source_ids: string[];
    attribution_note: string;
  }[];
  data_notes: string[];
}

export interface PerformanceSnapshot {
  id: string;
  machine_id: string;
  machine_code?: string;
  machine_name?: string;
  snapshot_date: string;
  planned_time_min: number;
  setup_time_min: number;
  run_time_min: number;
  downtime_min: number;
  cleanup_time_min: number;
  changeover_time_min: number;
  idle_time_min: number;
  units_produced: number;
  good_units: number;
  scrap_units: number;
  actual_speed?: number;
  rated_speed?: number;
  availability?: number;
  performance?: number;
  quality_rate?: number;
  oee?: number;
  utilization_pct?: number;
  machine_cost_actual?: number;
  labor_cost_actual?: number;
  anomaly_flag: boolean;
  low_oee_flag: boolean;
  high_downtime_flag: boolean;
}

export interface DowntimeIntel {
  id: string;
  machine_id: string;
  work_order_id?: string;
  downtime_class: DowntimeClass;
  downtime_subclass?: string;
  reason_code?: string | null;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  repeat_occurrence: boolean;
  maintenance_escalated: boolean;
  cost_impact?: number;
  root_cause?: string;
  units_lost?: number;
  notes?: string;
  machine_name?: string;
}

export interface MachineCostAttribution {
  machine_id: string;
  machine_code: string;
  runtime_hours: number;
  setup_hours: number;
  hourly_cost_rate_used?: number | null;
  energy_cost_per_hour_used?: number | null;
  runtime_cost?: number | null;
  setup_cost?: number | null;
  energy_cost?: number | null;
  total_cost?: number | null;
  source_runtime_log_ids: string[];
  unavailable_runtime_log_ids: string[];
  overlapping_runtime_log_ids: string[];
}

export interface LaborCostAttribution {
  labor_log_id: string;
  operator_id: string;
  approved_flag: boolean;
  duration_minutes?: number | null;
  overtime_minutes?: number | null;
  cost_rate_per_hour?: number | null;
  direct_cost?: number | null;
  overtime_cost?: number | null;
  included: boolean;
  exclusion_reason?: string | null;
}

export interface CostContribution {
  production_order_id: string;
  machine_runtime_hours: number;
  machine_setup_hours: number;
  machine_cost_runtime?: number | null;
  machine_cost_setup?: number | null;
  machine_cost_energy?: number | null;
  machine_cost_total?: number | null;
  labor_direct_hours: number;
  labor_overtime_hours: number;
  labor_cost_direct?: number | null;
  labor_cost_overtime?: number | null;
  labor_cost_total?: number | null;
  total_cost?: number | null;
  attribution_complete: boolean;
  machine_attributions: MachineCostAttribution[];
  labor_attributions: LaborCostAttribution[];
  unavailable_runtime_log_ids: string[];
  overlapping_runtime_log_ids: string[];
  unapproved_labor_log_ids: string[];
  unpriced_labor_log_ids: string[];
  overlapping_labor_log_ids: string[];
  cost_unit_note: string;
  data_notes: string[];
  variance_pct?: number;
}

export interface MOAIRec {
  id: string;
  agent_type: MOAIAgentType;
  status: MOAIRecStatus;
  machine_id?: string;
  operator_id?: string;
  title: string;
  description: string;
  severity: string;
  confidence_score?: number;
  estimated_impact?: string;
  actioned_at?: string;
}

export interface MODashboard {
  total_machines: number;
  machines_active: number;
  machines_maintenance: number;
  total_operators: number;
  total_teams: number;
  expiring_certs: number;
  avg_oee_today?: number;
  total_downtime_today_min: number;
  pending_ai_recs: number;
  recent_downtime: DowntimeIntel[];
  ai_recommendations: MOAIRec[];
}

// ── Label / Color Maps ────────────────────────────────────────────────────────

export const MACHINE_STATUS_COLORS: Record<MachineStatus, string> = {
  ACTIVE: "bg-green-100 text-green-700",
  MAINTENANCE: "bg-orange-100 text-orange-700",
  INACTIVE: "bg-gray-100 text-gray-600",
  RETIRED: "bg-red-100 text-red-600",
};

export const CERT_STATUS_COLORS: Record<CertStatus, string> = {
  VALID: "bg-green-100 text-green-700",
  EXPIRING_SOON: "bg-yellow-100 text-yellow-700",
  EXPIRED: "bg-red-100 text-red-700",
  PENDING: "bg-blue-100 text-blue-700",
  BLOCKED: "bg-red-200 text-red-900",
};

export const ACTIVITY_COLORS: Record<RuntimeActivity, string> = {
  SETUP: "bg-blue-400",
  RUNNING: "bg-green-500",
  PAUSED: "bg-yellow-400",
  IDLE: "bg-gray-300",
  DOWNTIME: "bg-red-500",
  CLEANUP: "bg-cyan-400",
  CHANGEOVER: "bg-purple-400",
  MAINTENANCE: "bg-orange-500",
  QC_WAIT: "bg-indigo-400",
};

export const DOWNTIME_CLASS_LABELS: Partial<Record<DowntimeClass, string>> = {
  MECHANICAL_BREAKDOWN: "Mechanical",
  ELECTRICAL_ISSUE: "Electrical",
  PNEUMATIC_ISSUE: "Pneumatic",
  MATERIAL_SHORTAGE: "Material Shortage",
  OPERATOR_UNAVAILABLE: "No Operator",
  CHANGEOVER_DELAY: "Changeover Delay",
  CLEANING_DELAY: "Cleaning Delay",
  SPEED_LOSS: "Speed Loss",
  MICRO_STOP: "Micro-Stop",
  UTILITY_ISSUE: "Utility",
  OTHER: "Other",
};

export const AI_AGENT_LABELS: Record<MOAIAgentType, string> = {
  PERFORMANCE_ANOMALY: "Performance Anomaly",
  PRODUCTIVITY_OPTIMIZER: "Productivity Optimizer",
  COST_VARIANCE: "Cost Variance",
};

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

// ── API Client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/machine-ops";

export const moApi = {
  getDashboard: () => apiClient.get<MODashboard>(`${BASE}/dashboard`).then((r) => r.data),

  // Machines
  listMachines: (params?: Record<string, string>) => apiClient.get<Machine[]>(`${BASE}/machines`, { params }).then((r) => r.data),
  getMachine: (id: string) => apiClient.get<Machine>(`${BASE}/machines/${id}`).then((r) => r.data),
  createMachine: (d: Partial<Machine>) => apiClient.post<Machine>(`${BASE}/machines`, d).then((r) => r.data),
  updateMachine: (id: string, d: Partial<Machine>) => apiClient.patch<Machine>(`${BASE}/machines/${id}`, d).then((r) => r.data),
  getMachineRuntime: (id: string, params?: Record<string, string>) => apiClient.get<RuntimeLog[]>(`${BASE}/machines/${id}/runtime`, { params }).then((r) => r.data),
  getMachineRuntimeKpis: (id: string, params?: Record<string, string>) => apiClient.get<MachineRuntimeKpis>(`${BASE}/machines/${id}/runtime-kpis`, { params }).then((r) => r.data),
  getPerformanceAnomalies: (params?: Record<string, string>) => apiClient.get<PerformanceAnomalyReport>(`${BASE}/performance/anomalies`, { params }).then((r) => r.data),
  getDowntimeProductionCorrelations: (params?: Record<string, string>) => apiClient.get<DowntimeProductionCorrelationReport>(`${BASE}/performance/downtime-correlations`, { params }).then((r) => r.data),
  getMachinePerformance: (id: string, params?: Record<string, string>) => apiClient.get<PerformanceSnapshot[]>(`${BASE}/machines/${id}/performance`, { params }).then((r) => r.data),
  computePerformance: (id: string, snapshot_date?: string) => apiClient.post<PerformanceSnapshot>(`${BASE}/machines/${id}/performance/compute`, {}, { params: snapshot_date ? { snapshot_date } : {} }).then((r) => r.data),

  // Operators
  listOperators: () => apiClient.get<OperatorProfile[]>(`${BASE}/operators`).then((r) => r.data),
  getOperator: (id: string) => apiClient.get<OperatorProfile>(`${BASE}/operators/${id}`).then((r) => r.data),
  createOperator: (d: Partial<OperatorProfile>) => apiClient.post<OperatorProfile>(`${BASE}/operators`, d).then((r) => r.data),
  getOperatorPerformance: (id: string) => apiClient.get<LaborTimeLog[]>(`${BASE}/operators/${id}/performance`).then((r) => r.data),
  getOperatorProductivity: (id: string, params?: Record<string, string>) => apiClient.get<OperatorProductivity>(`${BASE}/operators/${id}/productivity`, { params }).then((r) => r.data),
  getShiftTeamComparisons: (params?: Record<string, string>) => apiClient.get<ShiftTeamComparisons>(`${BASE}/performance/shift-team-comparisons`, { params }).then((r) => r.data),

  // Teams
  listTeams: () => apiClient.get<ProductionTeam[]>(`${BASE}/teams`).then((r) => r.data),
  createTeam: (d: Partial<ProductionTeam>) => apiClient.post<ProductionTeam>(`${BASE}/teams`, d).then((r) => r.data),
  getTeam: (id: string) => apiClient.get<ProductionTeam>(`${BASE}/teams/${id}`).then((r) => r.data),
  addTeamMember: (teamId: string, d: object) => apiClient.post<TeamMember>(`${BASE}/teams/${teamId}/members`, d).then((r) => r.data),

  // Skills
  listSkills: (params?: Record<string, string>) => apiClient.get<SkillCert[]>(`${BASE}/operators/skills`, { params }).then((r) => r.data),
  createSkill: (d: Partial<SkillCert>) => apiClient.post<SkillCert>(`${BASE}/operators/skills`, d).then((r) => r.data),
  refreshCertStatuses: () => apiClient.post<{ updated: number }>(`${BASE}/operators/skills/refresh-statuses`, {}).then((r) => r.data),

  // Assignments
  validateAssignment: (d: object) => apiClient.post<AssignmentValidateResult>(`${BASE}/assignments/validate`, d).then((r) => r.data),
  createAssignment: (d: object) => apiClient.post<WorkOrderAssignment>(`${BASE}/assignments`, d).then((r) => r.data),
  getAssignment: (workOrderId: string) => apiClient.get<WorkOrderAssignment>(`${BASE}/assignments/${workOrderId}`).then((r) => r.data),
  getAssignmentHistory: (workOrderId: string) => apiClient.get<AssignmentHistory[]>(`${BASE}/assignments/${workOrderId}/history`).then((r) => r.data),

  // Runtime
  logRuntime: (d: Partial<RuntimeLog>) => apiClient.post<RuntimeLog>(`${BASE}/runtime`, d).then((r) => r.data),
  listRuntime: (params?: Record<string, string>) => apiClient.get<RuntimeLog[]>(`${BASE}/runtime`, { params }).then((r) => r.data),

  // Labor
  logLabor: (d: Partial<LaborTimeLog>) => apiClient.post<LaborTimeLog>(`${BASE}/labor`, d).then((r) => r.data),
  listLabor: (params?: Record<string, string>) => apiClient.get<LaborTimeLog[]>(`${BASE}/labor`, { params }).then((r) => r.data),
  approveLabor: (id: string) => apiClient.post<LaborTimeLog>(`${BASE}/labor/${id}/approve`, {}).then((r) => r.data),

  // Downtime
  listDowntimeReasonCodes: () => apiClient.get<DowntimeReasonCode[]>(`${BASE}/downtime/reason-codes`).then((r) => r.data),
  logDowntime: (d: Partial<DowntimeIntel>) => apiClient.post<DowntimeIntel>(`${BASE}/downtime`, d).then((r) => r.data),
  listDowntime: (params?: Record<string, string>) => apiClient.get<DowntimeIntel[]>(`${BASE}/downtime`, { params }).then((r) => r.data),
  getDowntimeIntelligence: () => apiClient.get<DowntimeIntel[]>(`${BASE}/downtime/intelligence`).then((r) => r.data),

  // Performance
  listPerformance: (params?: Record<string, string>) => apiClient.get<PerformanceSnapshot[]>(`${BASE}/performance`, { params }).then((r) => r.data),

  // Costing
  getCosting: (orderId: string) => apiClient.get<CostContribution>(`${BASE}/costing/${orderId}`).then((r) => r.data),

  // AI
  runAI: () => apiClient.post<MOAIRec[]>(`${BASE}/ai/run`, {}).then((r) => r.data),
  listAIRecs: (params?: Record<string, string>) => apiClient.get<MOAIRec[]>(`${BASE}/ai/recommendations`, { params }).then((r) => r.data),
  actionAIRec: (id: string, status: MOAIRecStatus, notes?: string) => apiClient.post<MOAIRec>(`${BASE}/ai/recommendations/${id}/action`, { status, notes }).then((r) => r.data),
};
