import { apiClient } from "./api";

// ── Enums ──────────────────────────────────────────────────────────────────────

export type ScenarioStatus = "DRAFT" | "ACTIVE" | "LOCKED" | "ARCHIVED";
export type ScenarioMode = "FINITE" | "INFINITE";
export type OpQueueStatus = "PENDING" | "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "SKIPPED";
export type BottleneckSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type PlanningAgentType = "CAPACITY_OPTIMIZER" | "SEQUENCING_OPTIMIZER" | "DISRUPTION_PREDICTOR";
export type PlanningRecStatus = "PENDING" | "ACCEPTED" | "REJECTED";
export type SimulationStatus = "DRAFT" | "COMPUTED" | "PUBLISHED" | "DISCARDED";

export const PLANNING_VIEW_PERMISSIONS = ["planning.view", "planning.view_all", "planning.view_own_scope"];
export const PLANNING_CREATE_PERMISSIONS = ["planning.create", "planning.create_all", "planning.create_own_scope"];
export const PLANNING_EDIT_PERMISSIONS = ["planning.edit", "planning.edit_all", "planning.edit_own_scope"];
export const PLANNING_CALCULATE_PERMISSIONS = ["planning.calculate", "planning.calculate_all", "planning.calculate_own_scope"];
export const PLANNING_APPROVE_PERMISSIONS = ["planning.approve", "planning.approve_all", "planning.approve_own_scope"];

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ScenarioSummary {
  id: string;
  scenario_no: string;
  scenario_name: string;
  status: ScenarioStatus;
  mode: ScenarioMode;
  horizon_start: string | null;
  horizon_end: string | null;
  total_ops: number;
  scheduled_ops: number;
  bottleneck_count: number;
  calculated_at: string | null;
}

export interface ScenarioOut extends ScenarioSummary {
  description: string | null;
  mps_plan_id: string | null;
  blocked_ops: number;
  avg_utilization_pct: number | null;
  total_changeover_hrs: number | null;
  created_at: string;
}

export interface OpQueueOut {
  id: string;
  op_no: string;
  scenario_id: string;
  mps_line_id: string | null;
  product_id: string | null;
  product_name: string | null;
  product_code: string | null;
  work_center_id: string | null;
  work_center_name: string | null;
  step_name: string | null;
  planned_qty: number;
  rate_per_hour: number | null;
  setup_minutes: number;
  run_minutes: number;
  cleanup_minutes: number;
  changeover_minutes: number;
  total_minutes: number;
  scheduled_start: string | null;
  scheduled_end: string | null;
  priority: number;
  status: OpQueueStatus;
  is_critical_path: boolean;
  block_reason: string | null;
}

export interface LoadSnapshot {
  id: string;
  work_center_id: string;
  work_center_name: string | null;
  slot_date: string;
  available_hours: number;
  allocated_hours: number;
  changeover_hours: number;
  utilization_pct: number;
  is_overloaded: boolean;
  overload_hours: number;
}

export interface CapacityBoardRow {
  work_center_id: string;
  work_center_name: string;
  peak_utilization_pct: number;
  overloaded_days: number;
  total_overload_hrs: number;
  slots: LoadSnapshot[];
}

export interface CapacityBoard {
  rows: CapacityBoardRow[];
  overload_alerts: { work_center: string; date: string; overload_hours: number; utilization_pct: number }[];
  total_ops: number;
  avg_utilization_pct: number;
}

export interface BottleneckOut {
  id: string;
  scenario_id: string;
  work_center_id: string | null;
  work_center_name: string | null;
  severity: BottleneckSeverity;
  peak_utilization_pct: number;
  overloaded_days: number;
  total_overload_hrs: number;
  blocked_op_count: number;
  recommendation: string | null;
  detected_at: string | null;
  is_resolved: boolean;
}

export interface AIRecOut {
  id: string;
  scenario_id: string;
  agent_type: PlanningAgentType;
  status: PlanningRecStatus;
  title: string;
  explanation: string | null;
  impact_summary: string | null;
  confidence_score: number | null;
  affected_op_ids: string[] | null;
  payload: Record<string, unknown> | null;
  actioned_at: string | null;
}

export interface SimulationOut {
  id: string;
  sim_no: string;
  sim_name: string;
  description: string | null;
  scenario_id: string;
  status: SimulationStatus;
  changes: Record<string, unknown>[] | null;
  ops_rescheduled: number | null;
  ops_delayed: number | null;
  utilization_delta: number | null;
  changeover_delta_hrs: number | null;
  throughput_delta_pct: number | null;
  impact_summary: string | null;
  computed_at: string | null;
  published_at: string | null;
}

export interface PlanningDashboard {
  active_scenarios: number;
  total_ops_today: number;
  scheduled_pct: number;
  avg_utilization_pct: number;
  critical_bottlenecks: number;
  pending_ai_recs: number;
  scenarios: ScenarioSummary[];
  top_bottlenecks: BottleneckOut[];
  recent_ai_recs: AIRecOut[];
}

export interface ChangeoverRow {
  id: string;
  work_center_id: string;
  from_family: string;
  to_family: string;
  changeover_minutes: number;
  notes: string | null;
  is_active: boolean;
}

// ── Color / label maps ─────────────────────────────────────────────────────────

export const SCENARIO_STATUS_COLOR: Record<ScenarioStatus, string> = {
  DRAFT:    "bg-gray-100 text-gray-600",
  ACTIVE:   "bg-green-100 text-green-700",
  LOCKED:   "bg-blue-100 text-blue-700",
  ARCHIVED: "bg-yellow-100 text-yellow-700",
};

export const OP_STATUS_COLOR: Record<OpQueueStatus, string> = {
  PENDING:     "bg-gray-100 text-gray-500",
  SCHEDULED:   "bg-green-100 text-green-700",
  IN_PROGRESS: "bg-blue-100 text-blue-700",
  COMPLETED:   "bg-emerald-100 text-emerald-700",
  BLOCKED:     "bg-red-100 text-red-700",
  SKIPPED:     "bg-orange-100 text-orange-600",
};

export const BN_SEVERITY_COLOR: Record<BottleneckSeverity, string> = {
  LOW:      "bg-yellow-100 text-yellow-600",
  MEDIUM:   "bg-orange-100 text-orange-600",
  HIGH:     "bg-red-100 text-red-600",
  CRITICAL: "bg-red-200 text-red-800 font-bold",
};

export const AGENT_LABEL: Record<PlanningAgentType, string> = {
  CAPACITY_OPTIMIZER:   "Capacity Optimizer",
  SEQUENCING_OPTIMIZER: "Sequencing Optimizer",
  DISRUPTION_PREDICTOR: "Disruption Predictor",
};

export const AGENT_COLOR: Record<PlanningAgentType, string> = {
  CAPACITY_OPTIMIZER:   "bg-indigo-100 text-indigo-700",
  SEQUENCING_OPTIMIZER: "bg-purple-100 text-purple-700",
  DISRUPTION_PREDICTOR: "bg-red-100 text-red-700",
};

export function utilColor(pct: number): string {
  if (pct >= 100) return "bg-red-500";
  if (pct >= 85) return "bg-orange-400";
  if (pct >= 60) return "bg-yellow-400";
  return "bg-green-400";
}

export function fmtMins(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${m > 0 ? m + "m" : ""}`.trim() : `${m}m`;
}

// ── API client ─────────────────────────────────────────────────────────────────

export const planningApi = {
  dashboard: () => apiClient.get<PlanningDashboard>("/planning/dashboard").then((r) => r.data),

  // Scenarios
  createScenario: (body: Partial<ScenarioOut>) => apiClient.post<ScenarioOut>("/planning/scenarios", body).then((r) => r.data),
  listScenarios:  (status?: string) => apiClient.get<ScenarioSummary[]>(`/planning/scenarios${status ? `?status=${status}` : ""}`).then((r) => r.data),
  getScenario:    (id: string) => apiClient.get<ScenarioOut>(`/planning/scenarios/${id}`).then((r) => r.data),
  updateScenario: (id: string, body: Partial<ScenarioOut>) => apiClient.patch<ScenarioOut>(`/planning/scenarios/${id}`, body).then((r) => r.data),
  activateScenario: (id: string) => apiClient.post<ScenarioOut>(`/planning/scenarios/${id}/activate`, {}).then((r) => r.data),
  lockScenario:   (id: string) => apiClient.post<ScenarioOut>(`/planning/scenarios/${id}/lock`, {}).then((r) => r.data),

  // Calculate (run scheduling engine)
  calculate: (id: string) => apiClient.post<{ total_ops: number; scheduled: number; blocked: number }>(`/planning/scenarios/${id}/calculate`, {}).then((r) => r.data),

  // Operations
  listOps: (scenarioId: string, status?: string) =>
    apiClient.get<OpQueueOut[]>(`/planning/scenarios/${scenarioId}/operations${status ? `?status=${status}` : ""}`).then((r) => r.data),

  // Capacity board
  capacityBoard: (scenarioId: string) => apiClient.get<CapacityBoard>(`/planning/scenarios/${scenarioId}/capacity`).then((r) => r.data),

  // Bottlenecks
  listBottlenecks: (scenarioId: string) => apiClient.get<BottleneckOut[]>(`/planning/scenarios/${scenarioId}/bottlenecks`).then((r) => r.data),
  resolveBottleneck: (bnId: string) => apiClient.post<BottleneckOut>(`/planning/bottlenecks/${bnId}/resolve`, {}).then((r) => r.data),

  // AI
  runAI:    (scenarioId: string) => apiClient.post<{ total: number }>(`/planning/scenarios/${scenarioId}/run-ai`, {}).then((r) => r.data),
  listAI:   (scenarioId: string) => apiClient.get<AIRecOut[]>(`/planning/scenarios/${scenarioId}/ai-recommendations`).then((r) => r.data),
  actionAI: (recId: string, status: PlanningRecStatus) =>
    apiClient.post<AIRecOut>(`/planning/ai-recommendations/${recId}/action`, { status }).then((r) => r.data),

  // Simulations
  createSim:  (scenarioId: string, body: { sim_name: string; description?: string; changes: Record<string, unknown>[] }) =>
    apiClient.post<SimulationOut>(`/planning/scenarios/${scenarioId}/simulations`, body).then((r) => r.data),
  computeSim: (simId: string) => apiClient.post<SimulationOut>(`/planning/simulations/${simId}/compute`, {}).then((r) => r.data),
  publishSim: (simId: string) => apiClient.post<SimulationOut>(`/planning/simulations/${simId}/publish`, {}).then((r) => r.data),
  listSims:   (scenarioId: string) => apiClient.get<SimulationOut[]>(`/planning/scenarios/${scenarioId}/simulations`).then((r) => r.data),

  // Calendars
  createCalendar: (body: Record<string, unknown>) => apiClient.post("/planning/calendars", body).then((r) => r.data),
  listCalendars:  (wcId?: string) => apiClient.get(`/planning/calendars${wcId ? `?work_center_id=${wcId}` : ""}`).then((r) => r.data),

  // Changeover matrix
  createChangeover: (body: Record<string, unknown>) => apiClient.post("/planning/changeover-matrix", body).then((r) => r.data),
  listChangeover:   (wcId?: string) => apiClient.get<ChangeoverRow[]>(`/planning/changeover-matrix${wcId ? `?work_center_id=${wcId}` : ""}`).then((r) => r.data),
};
