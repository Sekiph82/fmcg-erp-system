const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API}/api/v1/calendar`;

export type EventType = "meeting" | "task" | "booking" | "production" | "maintenance" | "other";
export type EventStatus = "scheduled" | "completed" | "cancelled";
export type ParticipantRole = "organizer" | "attendee" | "optional";
export type ResponseStatus = "pending" | "accepted" | "declined";
export type ResourceType = "employee" | "room" | "vehicle" | "machine" | "external";
export type ResourceStatus = "active" | "inactive" | "maintenance";
export type BookingStatus = "reserved" | "confirmed" | "cancelled";
export type RecurrenceFrequency = "daily" | "weekly" | "monthly" | "custom";
export type CAIAgentType = "schedule_optimizer" | "conflict_resolver";
export type CAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface CalendarResource {
  resource_id: string;
  resource_type: ResourceType;
  name: string;
  capacity: number;
  location?: string;
  description?: string;
  availability_rules: Record<string, unknown>;
  status: ResourceStatus;
  created_at: string;
}

export interface Participant {
  participant_id: string;
  event_id: string;
  user_id?: string;
  participant_name?: string;
  participant_email?: string;
  role: ParticipantRole;
  response_status: ResponseStatus;
}

export interface ResourceBooking {
  booking_id: string;
  event_id?: string;
  resource_id: string;
  start_datetime: string;
  end_datetime: string;
  status: BookingStatus;
  notes?: string;
  booked_by?: string;
  created_at: string;
}

export interface CalendarEvent {
  event_id: string;
  event_title: string;
  event_type: EventType;
  start_datetime: string;
  end_datetime: string;
  all_day_flag: boolean;
  created_by?: string;
  description?: string;
  location?: string;
  status: EventStatus;
  source_module?: string;
  recurrence_id?: string;
  created_at: string;
  participants: Participant[];
  bookings: { booking_id: string; resource_id: string; status: BookingStatus; start_datetime?: string; end_datetime?: string }[];
}

export interface AvailabilitySlot {
  start: string;
  end: string;
}

export interface CAIRec {
  rec_id: string;
  agent_type: CAIAgentType;
  title: string;
  body: string;
  score?: number;
  status: CAIRecStatus;
  rec_metadata: Record<string, unknown>;
  created_at: string;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function qs(params?: Record<string, string | undefined>): string {
  if (!params) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const calendarApi = {
  listResources: (params?: { resource_type?: string; status?: string }) =>
    api<CalendarResource[]>(`/resources${qs(params)}`),
  createResource: (data: object) =>
    api<CalendarResource>("/resources", { method: "POST", body: JSON.stringify(data) }),
  updateResource: (id: string, data: object) =>
    api<CalendarResource>(`/resources/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  listEvents: (params?: { start?: string; end?: string; event_type?: string; status?: string }) =>
    api<CalendarEvent[]>(`/events${qs(params)}`),
  createEvent: (data: object) =>
    api<CalendarEvent>("/events", { method: "POST", body: JSON.stringify(data) }),
  getEvent: (id: string) => api<CalendarEvent>(`/events/${id}`),
  updateEvent: (id: string, data: object) =>
    api<CalendarEvent>(`/events/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  cancelEvent: (id: string) =>
    api<{ ok: boolean }>(`/events/${id}`, { method: "DELETE" }),

  listBookings: (params?: { resource_id?: string; start?: string; end?: string; status?: string }) =>
    api<ResourceBooking[]>(`/bookings${qs(params)}`),
  createBooking: (data: object) =>
    api<ResourceBooking>("/bookings", { method: "POST", body: JSON.stringify(data) }),
  confirmBooking: (id: string) =>
    api<ResourceBooking>(`/bookings/${id}/confirm`, { method: "POST" }),
  cancelBooking: (id: string) =>
    api<{ ok: boolean }>(`/bookings/${id}`, { method: "DELETE" }),

  checkAvailability: (data: object) =>
    api<{ available: boolean; conflicts: number }>("/availability/check", {
      method: "POST", body: JSON.stringify(data),
    }),
  getAvailableSlots: (data: object) =>
    api<AvailabilitySlot[]>("/availability/slots", { method: "POST", body: JSON.stringify(data) }),

  listAIRecs: () => api<CAIRec[]>("/ai/recs"),
  runScheduleOptimizer: () =>
    api<{ generated: number }>("/ai/run/schedule-optimizer", { method: "POST" }),
  runConflictResolver: () =>
    api<{ generated: number }>("/ai/run/conflict-resolver", { method: "POST" }),
  ackAIRec: (id: string, data: { status: CAIRecStatus }) =>
    api<CAIRec>(`/ai/recs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
};

export const EVENT_COLOR: Record<EventType, string> = {
  meeting: "bg-blue-500",
  task: "bg-purple-500",
  booking: "bg-green-500",
  production: "bg-orange-500",
  maintenance: "bg-red-500",
  other: "bg-gray-400",
};

export const EVENT_BADGE: Record<EventType, string> = {
  meeting: "bg-blue-100 text-blue-700",
  task: "bg-purple-100 text-purple-700",
  booking: "bg-green-100 text-green-700",
  production: "bg-orange-100 text-orange-700",
  maintenance: "bg-red-100 text-red-700",
  other: "bg-gray-100 text-gray-600",
};

export const RESOURCE_ICON: Record<ResourceType, string> = {
  employee: "👤",
  room: "🏠",
  vehicle: "🚗",
  machine: "⚙️",
  external: "🌐",
};

export const STATUS_BADGE: Record<EventStatus, string> = {
  scheduled: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};
