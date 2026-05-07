const BASE = "/api/v1/projects";

export type ProjectStatus    = "PLANNING" | "ACTIVE" | "ON_HOLD" | "COMPLETED" | "CANCELLED";
export type ProjectTaskStatus = "TODO" | "IN_PROGRESS" | "BLOCKED" | "DONE";
export type ProjectPriority  = "LOW" | "MEDIUM" | "HIGH";

export interface Milestone {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  due_date: string;
  is_complete: boolean;
  completed_at: string | null;
  created_at: string;
}

export interface ProjectTask {
  id: string;
  project_id: string;
  milestone_id: string | null;
  parent_task_id: string | null;
  title: string;
  description: string | null;
  status: ProjectTaskStatus;
  priority: ProjectPriority;
  assigned_to_id: string | null;
  assigned_to_name: string | null;
  start_date: string | null;
  due_date: string | null;
  duration_days: number | null;
  estimated_hours: number | null;
  actual_hours: number | null;
  is_critical_path: boolean;
  completed_at: string | null;
  created_at: string;
  depends_on_ids: string[];
}

export interface Project {
  id: string;
  project_no: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  owner_id: string | null;
  owner_name: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: number | null;
  actual_cost: number | null;
  notes: string | null;
  created_at: string;
  task_count: number;
  done_count: number;
  milestone_count: number;
}

export interface ProjectDetail extends Project {
  milestones: Milestone[];
  tasks: ProjectTask[];
}

export interface GanttTask {
  id: string;
  title: string;
  status: ProjectTaskStatus;
  priority: ProjectPriority;
  milestone_id: string | null;
  parent_task_id: string | null;
  start_date: string | null;
  due_date: string | null;
  duration_days: number | null;
  assigned_to_name: string | null;
  is_critical_path: boolean;
  depends_on_ids: string[];
  pct_complete: number;
}

export interface GanttResponse {
  project_id: string;
  project_no: string;
  project_name: string;
  start_date: string | null;
  end_date: string | null;
  milestones: Milestone[];
  tasks: GanttTask[];
}

export interface ProjectDashboard {
  total_projects: number;
  planning_count: number;
  active_count: number;
  on_hold_count: number;
  completed_count: number;
  cancelled_count: number;
  total_tasks: number;
  overdue_tasks: number;
  blocked_tasks: number;
}

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(url, { credentials: "include", ...opts });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail ?? r.statusText);
  }
  return r.json();
}

const json = (body: unknown, method = "POST") => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const projectsApi = {
  list: (status?: ProjectStatus) => {
    const q = status ? `?status=${status}` : "";
    return req<Project[]>(`${BASE}/${q}`);
  },
  dashboard: () => req<ProjectDashboard>(`${BASE}/dashboard`),
  get: (id: string) => req<ProjectDetail>(`${BASE}/${id}`),
  create: (body: { name: string; description?: string; start_date?: string; end_date?: string; budget?: number; notes?: string }) =>
    req<Project>(BASE + "/", json(body)),
  update: (id: string, body: Partial<{ name: string; description: string; status: ProjectStatus; start_date: string; end_date: string; budget: number; notes: string }>) =>
    req<Project>(`${BASE}/${id}`, json(body, "PATCH")),
  delete: (id: string) => fetch(`${BASE}/${id}`, { method: "DELETE", credentials: "include" }),

  gantt: (id: string) => req<GanttResponse>(`${BASE}/${id}/gantt`),

  addMilestone: (pid: string, body: { name: string; due_date: string; description?: string }) =>
    req<Milestone>(`${BASE}/${pid}/milestones`, json(body)),

  addTask: (pid: string, body: Partial<ProjectTask> & { title: string; project_id: string }) =>
    req<ProjectTask>(`${BASE}/${pid}/tasks`, json(body)),
  updateTask: (tid: string, body: Partial<ProjectTask>) =>
    req<ProjectTask>(`${BASE}/tasks/${tid}`, json(body, "PATCH")),
  completeTask: (tid: string) => req<ProjectTask>(`${BASE}/tasks/${tid}/complete`, { method: "POST" }),
  deleteTask: (tid: string) => fetch(`${BASE}/tasks/${tid}`, { method: "DELETE", credentials: "include" }),
};

export const STATUS_COLOR: Record<ProjectStatus, string> = {
  PLANNING:  "bg-gray-100 text-gray-700",
  ACTIVE:    "bg-blue-100 text-blue-700",
  ON_HOLD:   "bg-yellow-100 text-yellow-700",
  COMPLETED: "bg-green-100 text-green-700",
  CANCELLED: "bg-red-100 text-red-700",
};

export const TASK_STATUS_COLOR: Record<ProjectTaskStatus, string> = {
  TODO:        "bg-gray-100 text-gray-600",
  IN_PROGRESS: "bg-blue-100 text-blue-700",
  BLOCKED:     "bg-red-100 text-red-700",
  DONE:        "bg-green-100 text-green-700",
};

export const TASK_BAR_COLOR: Record<ProjectTaskStatus, string> = {
  TODO:        "bg-gray-300",
  IN_PROGRESS: "bg-blue-500",
  BLOCKED:     "bg-red-500",
  DONE:        "bg-green-500",
};

export function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}
