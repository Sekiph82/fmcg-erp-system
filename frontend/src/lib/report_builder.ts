const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/reports-builder`;

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? r.statusText);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type ReportVisibility = "private" | "team" | "global";
export type AggregationType = "none" | "sum" | "avg" | "min" | "max" | "count" | "count_distinct";
export type FilterOperator = "eq" | "neq" | "gt" | "lt" | "gte" | "lte" | "between" | "in" | "like" | "is_null" | "is_not_null";
export type LogicalOperator = "and" | "or";
export type SortDirection = "asc" | "desc";
export type ChartType = "table" | "bar" | "line" | "pie" | "kpi" | "area" | "scatter";
export type ScheduleFrequency = "daily" | "weekly" | "monthly" | "custom";
export type ExportFormat = "csv" | "xlsx" | "json";
export type RBAIAgentType = "builder_assistant" | "insight_generator" | "performance_optimizer";
export type RBAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface DataSourceField {
  path: string;
  label: string;
  type: "string" | "number" | "date" | "boolean" | "datetime";
}

export interface DataSource {
  label: string;
  module: string;
  field_count: number;
  fields: DataSourceField[];
}

export interface ReportField {
  report_field_id: string;
  report_id: string;
  field_path: string;
  alias: string | null;
  data_type: string;
  aggregation: AggregationType;
  is_group_by: boolean;
  sort_direction: SortDirection | null;
  sort_order: number | null;
  position: number;
  visible: boolean;
}

export interface ReportFilter {
  filter_id: string;
  report_id: string;
  field_path: string;
  operator: FilterOperator;
  value: string | null;
  value_to: string | null;
  logical_op: LogicalOperator;
  position: number;
}

export interface CalcField {
  calc_id: string;
  report_id: string;
  expression: string;
  alias: string;
  data_type: string;
  description: string | null;
}

export interface Schedule {
  schedule_id: string;
  report_id: string;
  frequency: ScheduleFrequency;
  run_time: string | null;
  recipients: string | null;
  export_format: ExportFormat;
  active_flag: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface Report {
  report_id: string;
  report_code: string;
  report_name: string;
  description: string | null;
  owner_user_id: string | null;
  owner_name: string | null;
  visibility: ReportVisibility;
  data_source: string;
  query_definition: Record<string, unknown> | null;
  active_flag: boolean;
  is_template: boolean;
  run_count: number;
  last_run_at: string | null;
  created_at: string;
  fields: ReportField[];
  filters: ReportFilter[];
  calculated_fields: CalcField[];
  schedules: Schedule[];
}

export interface RunResult {
  report_id: string;
  report_name: string;
  data_source: string;
  columns: { path: string; label: string; type: string }[];
  rows: Record<string, string | null>[];
  total_count: number;
  execution_ms: number;
  page: number;
  page_size: number;
}

export interface Widget {
  widget_id: string;
  dashboard_id: string;
  report_id: string | null;
  widget_title: string | null;
  chart_type: ChartType;
  position: number;
  width: number;
  height: number;
  x_axis_field: string | null;
  y_axis_field: string | null;
  color_field: string | null;
  refresh_interval: number | null;
  config: Record<string, unknown> | null;
  created_at: string;
}

export interface Dashboard {
  dashboard_id: string;
  dashboard_code: string;
  dashboard_name: string;
  description: string | null;
  owner_user_id: string | null;
  visibility: ReportVisibility;
  active_flag: boolean;
  created_at: string;
  widgets: Widget[];
}

export interface RBAIRec {
  rec_id: string;
  agent_type: RBAIAgentType;
  status: RBAIRecStatus;
  title: string;
  body: string;
  report_id: string | null;
  score: number | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Label Maps ────────────────────────────────────────────────────────────────

export const AGG_LABEL: Record<AggregationType, string> = {
  none: "—", sum: "SUM", avg: "AVG", min: "MIN", max: "MAX",
  count: "COUNT", count_distinct: "COUNT DISTINCT",
};

export const OP_LABEL: Record<FilterOperator, string> = {
  eq: "=", neq: "≠", gt: ">", lt: "<", gte: "≥", lte: "≤",
  between: "Between", in: "In list", like: "Contains",
  is_null: "Is empty", is_not_null: "Is not empty",
};

export const CHART_LABEL: Record<ChartType, string> = {
  table: "Table", bar: "Bar Chart", line: "Line Chart",
  pie: "Pie Chart", kpi: "KPI Card", area: "Area Chart", scatter: "Scatter",
};

export const CHART_TYPES: ChartType[] = ["table","bar","line","pie","kpi","area"];
export const FILTER_OPS: FilterOperator[] = ["eq","neq","gt","lt","gte","lte","between","in","like","is_null","is_not_null"];
export const AGG_TYPES: AggregationType[] = ["none","sum","avg","min","max","count","count_distinct"];

// ── API ───────────────────────────────────────────────────────────────────────

export const reportBuilderApi = {
  getCatalog: () => req<Record<string, DataSource>>("/catalog"),
  getDataSource: (id: string) => req<DataSource>(`/catalog/${id}`),

  createReport: (d: object) => req<Report>("/reports", { method: "POST", body: JSON.stringify(d) }),
  listReports: (params?: { data_source?: string; owner?: string; template_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.data_source) q.set("data_source", params.data_source);
    if (params?.owner) q.set("owner", params.owner);
    if (params?.template_only) q.set("template_only", "true");
    return req<Report[]>(`/reports?${q}`);
  },
  getReport: (id: string) => req<Report>(`/reports/${id}`),
  updateReport: (id: string, d: object) => req<Report>(`/reports/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  deleteReport: (id: string) => req<void>(`/reports/${id}`, { method: "DELETE" }),
  cloneReport: (id: string, new_code: string, new_name: string) =>
    req<Report>(`/reports/${id}/clone?new_code=${encodeURIComponent(new_code)}&new_name=${encodeURIComponent(new_name)}`, { method: "POST" }),
  seedTemplates: () => req<{ created: number }>("/reports/seed-templates", { method: "POST" }),

  runReport: (id: string, d: object) => req<RunResult>(`/reports/${id}/run`, { method: "POST", body: JSON.stringify(d) }),
  getExportUrl: (id: string) => `${BASE}/reports/${id}/export`,

  preview: (data_source: string, limit = 5) =>
    req<{ columns: unknown[]; rows: unknown[]; total: number }>(`/preview?data_source=${data_source}&limit=${limit}`, { method: "POST" }),

  createSchedule: (report_id: string, d: object) =>
    req<Schedule>(`/reports/${report_id}/schedule`, { method: "POST", body: JSON.stringify(d) }),
  listSchedules: (report_id?: string) =>
    req<Schedule[]>(`/schedules${report_id ? `?report_id=${report_id}` : ""}`),
  deactivateSchedule: (id: string) => req<void>(`/schedules/${id}`, { method: "DELETE" }),

  createDashboard: (d: object) => req<Dashboard>("/dashboards", { method: "POST", body: JSON.stringify(d) }),
  listDashboards: () => req<Dashboard[]>("/dashboards"),
  getDashboard: (id: string) => req<Dashboard>(`/dashboards/${id}`),
  addWidget: (dashboard_id: string, d: object) =>
    req<Widget>(`/dashboards/${dashboard_id}/widgets`, { method: "POST", body: JSON.stringify(d) }),
  deleteWidget: (id: string) => req<void>(`/widgets/${id}`, { method: "DELETE" }),

  runBuilderAssistant: () => req<RBAIRec[]>("/ai/run-builder-assistant", { method: "POST" }),
  runInsightGenerator: () => req<RBAIRec[]>("/ai/run-insight-generator", { method: "POST" }),
  runPerformanceOptimizer: () => req<RBAIRec[]>("/ai/run-performance-optimizer", { method: "POST" }),
  listAIRecs: (status?: string) => req<RBAIRec[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackAIRec: (id: string, d: object) =>
    req<RBAIRec>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
