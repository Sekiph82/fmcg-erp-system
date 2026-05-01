import { apiClient } from "./api";

const BASE = "/api/v1/calendar";

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

export const calendarApi = {
  listResources: (params?: { resource_type?: string; status?: string }) =>
    apiClient.get<CalendarResource[]>(`${BASE}/resources`, { params }).then(r => r.data),
  createResource: (data: object) =>
    apiClient.post<CalendarResource>(`${BASE}/resources`, data).then(r => r.data),
  updateResource: (id: string, data: object) =>
    apiClient.patch<CalendarResource>(`${BASE}/resources/${id}`, data).then(r => r.data),

  listEvents: (params?: { start?: string; end?: string; event_type?: string; status?: string }) =>
    apiClient.get<CalendarEvent[]>(`${BASE}/events`, { params }).then(r => r.data),
  createEvent: (data: object) =>
    apiClient.post<CalendarEvent>(`${BASE}/events`, data).then(r => r.data),
  getEvent: (id: string) =>
    apiClient.get<CalendarEvent>(`${BASE}/events/${id}`).then(r => r.data),
  updateEvent: (id: string, data: object) =>
    apiClient.patch<CalendarEvent>(`${BASE}/events/${id}`, data).then(r => r.data),
  cancelEvent: (id: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/events/${id}`).then(r => r.data),

  listBookings: (params?: { resource_id?: string; start?: string; end?: string; status?: string }) =>
    apiClient.get<ResourceBooking[]>(`${BASE}/bookings`, { params }).then(r => r.data),
  createBooking: (data: object) =>
    apiClient.post<ResourceBooking>(`${BASE}/bookings`, data).then(r => r.data),
  confirmBooking: (id: string) =>
    apiClient.post<ResourceBooking>(`${BASE}/bookings/${id}/confirm`).then(r => r.data),
  cancelBooking: (id: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/bookings/${id}`).then(r => r.data),

  checkAvailability: (data: object) =>
    apiClient.post<{ available: boolean; conflicts: number }>(`${BASE}/availability/check`, data).then(r => r.data),
  getAvailableSlots: (data: object) =>
    apiClient.post<AvailabilitySlot[]>(`${BASE}/availability/slots`, data).then(r => r.data),

  listAIRecs: () =>
    apiClient.get<CAIRec[]>(`${BASE}/ai/recs`).then(r => r.data),
  runScheduleOptimizer: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/schedule-optimizer`).then(r => r.data),
  runConflictResolver: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/conflict-resolver`).then(r => r.data),
  ackAIRec: (id: string, data: { status: CAIRecStatus }) =>
    apiClient.patch<CAIRec>(`${BASE}/ai/recs/${id}`, data).then(r => r.data),
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
