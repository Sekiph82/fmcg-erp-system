import { apiClient } from "./api";

export type PlanType = "abc" | "random" | "location" | "item" | "frequency";
export type PlanStatus = "draft" | "active" | "paused" | "completed";
export type TaskStatus = "pending" | "in_progress" | "completed" | "approved" | "rejected";
export type ABCClass = "A" | "B" | "C";
export type AdjustmentStatus = "pending" | "approved" | "rejected" | "posted";

export interface CycleCountPlan {
  id: string;
  plan_code: string;
  name: string;
  warehouse_id: string;
  plan_type: PlanType;
  status: PlanStatus;
  frequency_days?: number;
  abc_classes?: string;
  variance_tolerance_pct: number;
  auto_approve_within_tolerance: boolean;
  start_date?: string;
  end_date?: string;
  notes?: string;
  created_at: string;
}

export interface CycleCountTask {
  id: string;
  task_no: string;
  plan_id: string;
  warehouse_id: string;
  location_id?: string;
  product_id?: string;
  material_id?: string;
  abc_class?: ABCClass;
  scheduled_date: string;
  assigned_to_id?: string;
  status: TaskStatus;
  completed_at?: string;
  notes?: string;
  created_at: string;
}

export interface CountEntry {
  id: string;
  task_id: string;
  product_id?: string;
  material_id?: string;
  lot_id?: string;
  location_id?: string;
  system_qty: number;
  counted_qty: number;
  variance_qty: number;
  variance_pct?: number;
  unit_cost?: number;
  variance_value?: number;
  unit: string;
  within_tolerance: boolean;
  root_cause?: string;
  counted_at?: string;
  created_at: string;
}

export interface CountAdjustment {
  id: string;
  entry_id: string;
  status: AdjustmentStatus;
  adjustment_qty: number;
  adjustment_value?: number;
  approved_by_id?: string;
  approved_at?: string;
  rejection_reason?: string;
  posted_flag: boolean;
  stock_movement_ref?: string;
  created_at: string;
}

export interface ABCClassification {
  id: string;
  warehouse_id: string;
  product_id?: string;
  material_id?: string;
  abc_class: ABCClass;
  stock_value?: number;
  annual_movements?: number;
  classification_date: string;
  count_frequency_days?: number;
}

export interface Dashboard {
  total_plans: number;
  active_plans: number;
  tasks_today: number;
  tasks_overdue: number;
  tasks_pending: number;
  tasks_completed_today: number;
  accuracy_pct_7d: number;
  open_variances: number;
  pending_adjustments: number;
  recent_variances: Array<Record<string, unknown>>;
}

const BASE = "/api/v1/cycle-count";

export async function getDashboard(): Promise<Dashboard> {
  return (await apiClient.get<Dashboard>(`${BASE}/dashboard`)).data;
}

// Plans
export async function listPlans(params?: { warehouse_id?: string; status?: PlanStatus }): Promise<CycleCountPlan[]> {
  return (await apiClient.get<CycleCountPlan[]>(`${BASE}/plans`, { params })).data;
}
export async function createPlan(data: Partial<CycleCountPlan>): Promise<CycleCountPlan> {
  return (await apiClient.post<CycleCountPlan>(`${BASE}/plans`, data)).data;
}
export async function updatePlan(id: string, data: Partial<CycleCountPlan>): Promise<CycleCountPlan> {
  return (await apiClient.patch<CycleCountPlan>(`${BASE}/plans/${id}`, data)).data;
}
export async function generateTasks(planId: string, targetDate?: string): Promise<{ generated: number }> {
  return (await apiClient.post(`${BASE}/plans/${planId}/generate-tasks`, null, { params: { target_date: targetDate } })).data;
}

// Tasks
export async function listTasks(params?: {
  plan_id?: string; status?: TaskStatus; scheduled_date?: string; warehouse_id?: string;
}): Promise<CycleCountTask[]> {
  return (await apiClient.get<CycleCountTask[]>(`${BASE}/tasks`, { params })).data;
}
export async function createTask(data: Partial<CycleCountTask>): Promise<CycleCountTask> {
  return (await apiClient.post<CycleCountTask>(`${BASE}/tasks`, data)).data;
}
export async function updateTask(id: string, data: Partial<CycleCountTask>): Promise<CycleCountTask> {
  return (await apiClient.patch<CycleCountTask>(`${BASE}/tasks/${id}`, data)).data;
}

// Count entries
export async function listEntries(params?: { task_id?: string; within_tolerance?: boolean }): Promise<CountEntry[]> {
  return (await apiClient.get<CountEntry[]>(`${BASE}/entries`, { params })).data;
}
export async function createEntry(data: {
  task_id: string; counted_qty: number; unit?: string;
  product_id?: string; material_id?: string; lot_id?: string; location_id?: string;
  unit_cost?: number; root_cause?: string;
}): Promise<CountEntry> {
  return (await apiClient.post<CountEntry>(`${BASE}/entries`, data)).data;
}

// Adjustments
export async function listAdjustments(params?: { status?: AdjustmentStatus }): Promise<CountAdjustment[]> {
  return (await apiClient.get<CountAdjustment[]>(`${BASE}/adjustments`, { params })).data;
}
export async function approveAdjustments(entry_ids: string[], notes?: string): Promise<{ approved: number }> {
  return (await apiClient.post(`${BASE}/adjustments/approve`, { entry_ids, notes })).data;
}
export async function rejectAdjustments(entry_ids: string[], rejection_reason: string): Promise<{ rejected: number }> {
  return (await apiClient.post(`${BASE}/adjustments/reject`, { entry_ids, rejection_reason })).data;
}

// ABC
export async function listABC(params?: { warehouse_id?: string; abc_class?: ABCClass }): Promise<ABCClassification[]> {
  return (await apiClient.get<ABCClassification[]>(`${BASE}/abc`, { params })).data;
}
export async function runABCClassification(warehouse_id: string): Promise<{ classified: number }> {
  return (await apiClient.post(`${BASE}/abc/classify`, null, { params: { warehouse_id } })).data;
}

// Reports
export async function getAccuracyReport(days = 30): Promise<unknown> {
  return (await apiClient.get(`${BASE}/reports/accuracy`, { params: { days } })).data;
}
export async function getVarianceReport(days = 30): Promise<unknown[]> {
  return (await apiClient.get(`${BASE}/reports/variance`, { params: { days } })).data;
}
export async function getCompletionReport(days = 30): Promise<unknown> {
  return (await apiClient.get(`${BASE}/reports/completion`, { params: { days } })).data;
}

// AI
export async function getVarianceAnalyzer(): Promise<unknown> {
  return (await apiClient.get(`${BASE}/ai/variance-analyzer`)).data;
}
export async function getCountOptimizer(): Promise<unknown> {
  return (await apiClient.get(`${BASE}/ai/count-optimizer`)).data;
}

// Helpers
export const PLAN_STATUS_BADGE: Record<PlanStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  active: "bg-green-100 text-green-800",
  paused: "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-800",
};

export const TASK_STATUS_BADGE: Record<TaskStatus, string> = {
  pending: "bg-gray-100 text-gray-600",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  approved: "bg-indigo-100 text-indigo-800",
  rejected: "bg-red-100 text-red-700",
};

export const ABC_BADGE: Record<ABCClass, string> = {
  A: "bg-red-100 text-red-800",
  B: "bg-amber-100 text-amber-800",
  C: "bg-gray-100 text-gray-600",
};
