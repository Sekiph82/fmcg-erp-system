import apiClient from "@/lib/api";

export type MachineStatus = "ACTIVE" | "MAINTENANCE" | "INACTIVE" | "RETIRED";
export type MachineFamily = "FILLING" | "MIXING" | "PACKAGING" | "LABELING" | "PALLETIZING" | "CONVEYOR" | "WEIGHING" | "INSPECTION" | "UTILITY" | "OTHER";
export type SkillLevel = "TRAINEE" | "BASIC" | "INTERMEDIATE" | "ADVANCED" | "EXPERT";
export type CertStatus = "VALID" | "EXPIRING_SOON" | "EXPIRED" | "PENDING" | "BLOCKED";
export type RuntimeActivity = "SETUP" | "RUNNING" | "PAUSED" | "IDLE" | "DOWNTIME" | "CLEANUP" | "CHANGEOVER" | "MAINTENANCE" | "QC_WAIT";
export type DowntimeClass = "MECHANICAL_BREAKDOWN" | "ELECTRICAL_ISSUE" | "PNEUMATIC_ISSUE" | "MATERIAL_SHORTAGE" | "PACKAGING_SHORTAGE" | "OPERATOR_UNAVAILABLE" | "QC_WAITING" | "CHANGEOVER_DELAY" | "CLEANING_DELAY" | "MAINTENANCE_INTERVENTION" | "SPEED_LOSS" | "MICRO_STOP" | "PLANNED_STOP" | "UNPLANNED_STOP" | "UTILITY_ISSUE" | "OTHER";
export type LaborActivity = "SETUP" | "RUN" | "CLEANUP" | "DOWNTIME_SUPPORT" | "QC_SUPPORT" | "REWORK" | "MAINTENANCE_ASSIST" | "CHANGEOVER";
export type MOAIAgentType = "PERFORMANCE_ANOMALY" | "PRODUCTIVITY_OPTIMIZER" | "COST_VARIANCE";
export type MOAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "APPLIED";

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
  machine_name?: string;
  operator_name?: string;
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
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  repeat_occurrence: boolean;
  maintenance_escalated: boolean;
  cost_impact?: number;
  root_cause?: string;
  machine_name?: string;
}

export interface CostContribution {
  production_order_id: string;
  machine_runtime_hours: number;
  machine_setup_hours: number;
  machine_cost_runtime: number;
  machine_cost_setup: number;
  machine_cost_energy: number;
  machine_cost_total: number;
  labor_direct_hours: number;
  labor_overtime_hours: number;
  labor_cost_direct: number;
  labor_cost_overtime: number;
  labor_cost_total: number;
  total_cost: number;
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

const BASE = "/machine-ops";

export const moApi = {
  getDashboard: () => apiClient.get<MODashboard>(`${BASE}/dashboard`),

  // Machines
  listMachines: (params?: Record<string, string>) => apiClient.get<Machine[]>(`${BASE}/machines`, { params }),
  getMachine: (id: string) => apiClient.get<Machine>(`${BASE}/machines/${id}`),
  createMachine: (d: Partial<Machine>) => apiClient.post<Machine>(`${BASE}/machines`, d),
  updateMachine: (id: string, d: Partial<Machine>) => apiClient.patch<Machine>(`${BASE}/machines/${id}`, d),
  getMachineRuntime: (id: string, params?: Record<string, string>) => apiClient.get<RuntimeLog[]>(`${BASE}/machines/${id}/runtime`, { params }),
  getMachinePerformance: (id: string, params?: Record<string, string>) => apiClient.get<PerformanceSnapshot[]>(`${BASE}/machines/${id}/performance`, { params }),
  computePerformance: (id: string, snapshot_date?: string) => apiClient.post<PerformanceSnapshot>(`${BASE}/machines/${id}/performance/compute`, {}, { params: snapshot_date ? { snapshot_date } : {} }),

  // Operators
  listOperators: () => apiClient.get<OperatorProfile[]>(`${BASE}/operators`),
  getOperator: (id: string) => apiClient.get<OperatorProfile>(`${BASE}/operators/${id}`),
  createOperator: (d: Partial<OperatorProfile>) => apiClient.post<OperatorProfile>(`${BASE}/operators`, d),
  getOperatorPerformance: (id: string) => apiClient.get<LaborTimeLog[]>(`${BASE}/operators/${id}/performance`),

  // Teams
  listTeams: () => apiClient.get<ProductionTeam[]>(`${BASE}/teams`),
  createTeam: (d: Partial<ProductionTeam>) => apiClient.post<ProductionTeam>(`${BASE}/teams`, d),
  getTeam: (id: string) => apiClient.get<ProductionTeam>(`${BASE}/teams/${id}`),
  addTeamMember: (teamId: string, d: object) => apiClient.post<TeamMember>(`${BASE}/teams/${teamId}/members`, d),

  // Skills
  listSkills: (params?: Record<string, string>) => apiClient.get<SkillCert[]>(`${BASE}/operators/skills`, { params }),
  createSkill: (d: Partial<SkillCert>) => apiClient.post<SkillCert>(`${BASE}/operators/skills`, d),
  refreshCertStatuses: () => apiClient.post<{ updated: number }>(`${BASE}/operators/skills/refresh-statuses`, {}),

  // Assignments
  validateAssignment: (d: object) => apiClient.post<AssignmentValidateResult>(`${BASE}/assignments/validate`, d),
  createAssignment: (d: object) => apiClient.post<WorkOrderAssignment>(`${BASE}/assignments`, d),
  getAssignment: (workOrderId: string) => apiClient.get<WorkOrderAssignment>(`${BASE}/assignments/${workOrderId}`),
  getAssignmentHistory: (workOrderId: string) => apiClient.get<AssignmentHistory[]>(`${BASE}/assignments/${workOrderId}/history`),

  // Runtime
  logRuntime: (d: Partial<RuntimeLog>) => apiClient.post<RuntimeLog>(`${BASE}/runtime`, d),
  listRuntime: (params?: Record<string, string>) => apiClient.get<RuntimeLog[]>(`${BASE}/runtime`, { params }),

  // Labor
  logLabor: (d: Partial<LaborTimeLog>) => apiClient.post<LaborTimeLog>(`${BASE}/labor`, d),
  listLabor: (params?: Record<string, string>) => apiClient.get<LaborTimeLog[]>(`${BASE}/labor`, { params }),
  approveLabor: (id: string) => apiClient.post<LaborTimeLog>(`${BASE}/labor/${id}/approve`, {}),

  // Downtime
  logDowntime: (d: Partial<DowntimeIntel>) => apiClient.post<DowntimeIntel>(`${BASE}/downtime`, d),
  listDowntime: (params?: Record<string, string>) => apiClient.get<DowntimeIntel[]>(`${BASE}/downtime`, { params }),
  getDowntimeIntelligence: () => apiClient.get<DowntimeIntel[]>(`${BASE}/downtime/intelligence`),

  // Performance
  listPerformance: (params?: Record<string, string>) => apiClient.get<PerformanceSnapshot[]>(`${BASE}/performance`, { params }),

  // Costing
  getCosting: (orderId: string) => apiClient.get<CostContribution>(`${BASE}/costing/${orderId}`),

  // AI
  runAI: () => apiClient.post<MOAIRec[]>(`${BASE}/ai/run`, {}),
  listAIRecs: (params?: Record<string, string>) => apiClient.get<MOAIRec[]>(`${BASE}/ai/recommendations`, { params }),
  actionAIRec: (id: string, status: MOAIRecStatus, notes?: string) => apiClient.post<MOAIRec>(`${BASE}/ai/recommendations/${id}/action`, { status, notes }),
};
