const BASE = "/api/v1/helpdesk";

export type TicketStatus   = "OPEN" | "IN_PROGRESS" | "ESCALATED" | "RESOLVED" | "CLOSED";
export type TicketCategory = "QUALITY" | "DELIVERY" | "BILLING" | "PRODUCT" | "OTHER";
export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type TicketSource   = "PHONE" | "EMAIL" | "PORTAL" | "WHATSAPP" | "MANUAL";

export interface TicketComment {
  id: string;
  ticket_id: string;
  body: string;
  is_internal: boolean;
  created_by_id: string | null;
  created_by_name: string | null;
  created_at: string;
}

export interface Ticket {
  id: string;
  ticket_no: string;
  customer_id: string | null;
  customer_name: string | null;
  customer_code: string | null;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  source: TicketSource;
  subject: string;
  description: string | null;
  lot_id: string | null;
  lot_number: string | null;
  sla_hours: number;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  resolution_notes: string | null;
  customer_satisfaction: number | null;
  assigned_to_id: string | null;
  assigned_to_name: string | null;
  created_by_id: string | null;
  created_at: string;
  sla_breached: boolean;
  comments: TicketComment[];
}

export interface HelpdeskDashboard {
  total_tickets: number;
  open_count: number;
  in_progress_count: number;
  escalated_count: number;
  resolved_count: number;
  closed_count: number;
  sla_breached_count: number;
  avg_resolution_hours: number | null;
  by_category: Record<TicketCategory, number>;
  by_priority: Record<TicketPriority, number>;
}

export interface TicketCreate {
  customer_id?: string;
  category: TicketCategory;
  priority: TicketPriority;
  source: TicketSource;
  subject: string;
  description?: string;
  lot_id?: string;
  sla_hours?: number;
}

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(url, { credentials: "include", ...opts });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail ?? r.statusText);
  }
  return r.json();
}

const json = (body: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const helpdeskApi = {
  list: (p?: { status?: TicketStatus; category?: TicketCategory; priority?: TicketPriority }) => {
    const q = new URLSearchParams();
    if (p?.status)   q.set("status", p.status);
    if (p?.category) q.set("category", p.category);
    if (p?.priority) q.set("priority", p.priority);
    return req<Ticket[]>(`${BASE}/?${q}`);
  },
  dashboard: () => req<HelpdeskDashboard>(`${BASE}/dashboard`),
  get: (id: string) => req<Ticket>(`${BASE}/${id}`),
  create: (body: TicketCreate) => req<Ticket>(BASE + "/", json(body)),
  assign: (id: string, user_id: string) => req<Ticket>(`${BASE}/${id}/assign`, json({ user_id })),
  escalate: (id: string) => req<Ticket>(`${BASE}/${id}/escalate`, { method: "POST" }),
  resolve: (id: string, resolution_notes?: string) =>
    req<Ticket>(`${BASE}/${id}/resolve`, json({ resolution_notes })),
  close: (id: string, customer_satisfaction?: number) =>
    req<Ticket>(`${BASE}/${id}/close`, json({ customer_satisfaction })),
  reopen: (id: string) => req<Ticket>(`${BASE}/${id}/reopen`, { method: "POST" }),
  addComment: (id: string, body: string, is_internal: boolean) =>
    req<Ticket>(`${BASE}/${id}/comments`, json({ body, is_internal })),
};

export const STATUS_COLOR: Record<TicketStatus, string> = {
  OPEN:        "bg-blue-100 text-blue-700",
  IN_PROGRESS: "bg-yellow-100 text-yellow-700",
  ESCALATED:   "bg-orange-100 text-orange-700",
  RESOLVED:    "bg-green-100 text-green-700",
  CLOSED:      "bg-gray-100 text-gray-500",
};

export const PRIORITY_COLOR: Record<TicketPriority, string> = {
  LOW:      "bg-gray-100 text-gray-600",
  MEDIUM:   "bg-blue-100 text-blue-600",
  HIGH:     "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

export function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-KE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
