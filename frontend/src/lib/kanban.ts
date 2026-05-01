const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/kanban`;

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

export type BoardModuleType = "crm" | "recruitment" | "tasks" | "approvals" | "custom" | "operations" | "projects";
export type BoardVisibility = "private" | "team" | "global";
export type ColumnStageType = "normal" | "final_success" | "final_failure";
export type CardPriority = "low" | "normal" | "high" | "critical";
export type CardStatus = "active" | "blocked" | "done" | "archived";
export type ActivityEventType = "created" | "moved" | "assigned" | "priority_changed" | "commented" | "due_date_set" | "status_changed" | "archived";
export type KBAIAgentType = "workflow_optimizer" | "task_prioritizer";
export type KBAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface KanbanColumn {
  column_id: string;
  board_id: string;
  column_name: string;
  sequence: number;
  stage_type: ColumnStageType;
  color: string;
  wip_limit: number | null;
  description: string | null;
  card_count: number;
  created_at: string;
}

export interface KanbanActivity {
  activity_id: string;
  card_id: string;
  event_type: ActivityEventType;
  actor_id: string | null;
  actor_name: string | null;
  from_value: string | null;
  to_value: string | null;
  note: string | null;
  created_at: string;
}

export interface KanbanComment {
  comment_id: string;
  card_id: string;
  author_id: string | null;
  author_name: string | null;
  body: string;
  created_at: string;
}

export interface KanbanCard {
  card_id: string;
  board_id: string;
  column_id: string;
  card_no: string | null;
  title: string;
  description: string | null;
  reference_type: string | null;
  reference_id: string | null;
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  due_date: string | null;
  priority: CardPriority;
  status: CardStatus;
  tags: string | null;
  position: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  activities: KanbanActivity[];
  comments: KanbanComment[];
}

export interface KanbanBoard {
  board_id: string;
  board_code: string;
  board_name: string;
  module_type: BoardModuleType;
  description: string | null;
  owner_id: string | null;
  owner_name: string | null;
  visibility: BoardVisibility;
  active_flag: boolean;
  created_at: string;
  columns: KanbanColumn[];
}

export interface KanbanDashboard {
  total_boards: number;
  active_boards: number;
  total_cards: number;
  active_cards: number;
  overdue_cards: number;
  blocked_cards: number;
  done_cards: number;
  cards_by_priority: Record<string, number>;
  cards_by_module: { module: string; count: number }[];
  top_assignees: { user: string; count: number }[];
}

export interface KBAIRec {
  rec_id: string;
  agent_type: KBAIAgentType;
  status: KBAIRecStatus;
  title: string;
  body: string;
  board_id: string | null;
  column_id: string | null;
  card_id: string | null;
  score: number | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string;
}

// ── Color / Label Maps ────────────────────────────────────────────────────────

export const PRIORITY_COLOR: Record<CardPriority, string> = {
  low: "bg-gray-100 text-gray-500",
  normal: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export const PRIORITY_BADGE: Record<CardPriority, string> = {
  low: "border-l-gray-300",
  normal: "border-l-blue-400",
  high: "border-l-orange-400",
  critical: "border-l-red-500",
};

export const STATUS_COLOR: Record<CardStatus, string> = {
  active: "bg-green-100 text-green-700",
  blocked: "bg-red-100 text-red-700",
  done: "bg-gray-100 text-gray-600",
  archived: "bg-gray-50 text-gray-400",
};

export const STAGE_COLOR: Record<ColumnStageType, string> = {
  normal: "",
  final_success: "border-t-4 border-t-green-500",
  final_failure: "border-t-4 border-t-red-400",
};

export const MODULE_LABEL: Record<BoardModuleType, string> = {
  crm: "CRM", recruitment: "Recruitment", tasks: "Tasks",
  approvals: "Approvals", custom: "Custom", operations: "Operations", projects: "Projects",
};

export const PRIORITIES: CardPriority[] = ["low", "normal", "high", "critical"];
export const MODULE_TYPES: BoardModuleType[] = ["crm", "recruitment", "tasks", "approvals", "operations", "projects", "custom"];

// ── API ───────────────────────────────────────────────────────────────────────

export const kanbanApi = {
  getDashboard: () => req<KanbanDashboard>("/dashboard"),

  listBoards: (params?: { module_type?: string; active_only?: boolean; owner_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.module_type) q.set("module_type", params.module_type);
    if (params?.active_only) q.set("active_only", "true");
    if (params?.owner_id) q.set("owner_id", params.owner_id);
    return req<KanbanBoard[]>(`/boards?${q}`);
  },
  createBoard: (d: object) => req<KanbanBoard>("/boards", { method: "POST", body: JSON.stringify(d) }),
  getBoard: (id: string) => req<KanbanBoard>(`/boards/${id}`),
  updateBoard: (id: string, d: object) => req<KanbanBoard>(`/boards/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
  seedBoards: () => req<{ created: number }>("/boards/seed-defaults", { method: "POST" }),

  addColumn: (boardId: string, d: object) =>
    req<KanbanColumn>(`/boards/${boardId}/columns`, { method: "POST", body: JSON.stringify(d) }),
  updateColumn: (colId: string, d: object) =>
    req<KanbanColumn>(`/columns/${colId}`, { method: "PATCH", body: JSON.stringify(d) }),
  deleteColumn: (colId: string) => req<void>(`/columns/${colId}`, { method: "DELETE" }),

  createCard: (boardId: string, d: object) =>
    req<KanbanCard>(`/boards/${boardId}/cards`, { method: "POST", body: JSON.stringify(d) }),
  listCards: (params?: {
    board_id?: string; column_id?: string; assigned_user_id?: string;
    priority?: string; status?: string; overdue_only?: boolean;
  }) => {
    const q = new URLSearchParams();
    if (params?.board_id) q.set("board_id", params.board_id);
    if (params?.column_id) q.set("column_id", params.column_id);
    if (params?.assigned_user_id) q.set("assigned_user_id", params.assigned_user_id);
    if (params?.priority) q.set("priority", params.priority);
    if (params?.status) q.set("status", params.status);
    if (params?.overdue_only) q.set("overdue_only", "true");
    return req<KanbanCard[]>(`/cards?${q}`);
  },
  getCard: (id: string) => req<KanbanCard>(`/cards/${id}`),
  updateCard: (id: string, d: object, actor?: string) =>
    req<KanbanCard>(`/cards/${id}${actor ? `?actor=${encodeURIComponent(actor)}` : ""}`, { method: "PATCH", body: JSON.stringify(d) }),
  moveCard: (id: string, d: object) => req<KanbanCard>(`/cards/${id}/move`, { method: "POST", body: JSON.stringify(d) }),
  deleteCard: (id: string) => req<void>(`/cards/${id}`, { method: "DELETE" }),

  addComment: (cardId: string, d: object) =>
    req<KanbanComment>(`/cards/${cardId}/comments`, { method: "POST", body: JSON.stringify(d) }),

  reportBottleneck: (boardId: string) => req<object[]>(`/reports/bottleneck/${boardId}`),
  reportCompletion: (boardId: string) => req<object>(`/reports/completion/${boardId}`),

  runWorkflowOptimizer: () => req<KBAIRec[]>("/ai/run-workflow-optimizer", { method: "POST" }),
  runTaskPrioritizer: () => req<KBAIRec[]>("/ai/run-task-prioritizer", { method: "POST" }),
  listAIRecs: (status?: string) => req<KBAIRec[]>(`/ai/recommendations${status ? `?status=${status}` : ""}`),
  ackAIRec: (id: string, d: object) =>
    req<KBAIRec>(`/ai/recommendations/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
};
