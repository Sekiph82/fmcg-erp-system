"use client";
import { useEffect, useState } from "react";
import { calendarApi, CalendarEvent, ResourceBooking, CalendarResource, EVENT_BADGE } from "@/lib/calendar";

export default function CalendarDashboard() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [bookings, setBookings] = useState<ResourceBooking[]>([]);
  const [resources, setResources] = useState<CalendarResource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const now = new Date();
    const weekEnd = new Date(now);
    weekEnd.setDate(weekEnd.getDate() + 7);
    Promise.all([
      calendarApi.listEvents({ start: now.toISOString(), end: weekEnd.toISOString() }),
      calendarApi.listBookings(),
      calendarApi.listResources(),
    ]).then(([e, b, r]) => {
      setEvents(e);
      setBookings(b);
      setResources(r);
    }).finally(() => setLoading(false));
  }, []);

  const next24h = events.filter(e => {
    const s = new Date(e.start_datetime);
    const now = new Date();
    const h24 = new Date(now.getTime() + 86400000);
    return s >= now && s <= h24 && e.status === "scheduled";
  });

  const pendingBookings = bookings.filter(b => b.status === "reserved");
  const activeResources = resources.filter(r => r.status === "active");

  const stats = [
    { label: "Events This Week", value: events.length, color: "text-blue-600" },
    { label: "Upcoming (24h)", value: next24h.length, color: "text-purple-600" },
    { label: "Pending Bookings", value: pendingBookings.length, color: "text-orange-600" },
    { label: "Active Resources", value: activeResources.length, color: "text-green-600" },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Calendar & Resource Scheduling</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{loading ? "—" : s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="bg-white border rounded-lg shadow-sm">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800 text-sm">Upcoming Events (Next 7 Days)</h2>
          </div>
          {loading ? <p className="p-4 text-sm text-gray-500">Loading…</p> :
            events.length === 0 ? <p className="p-4 text-sm text-gray-400 text-center py-8">No upcoming events.</p> : (
              <div className="divide-y max-h-72 overflow-y-auto">
                {events.slice(0, 10).map(e => (
                  <div key={e.event_id} className="px-4 py-2.5 flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-gray-800 truncate">{e.event_title}</p>
                        <span className={`text-xs rounded-full px-2 py-0.5 ${EVENT_BADGE[e.event_type]}`}>{e.event_type}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {new Date(e.start_datetime).toLocaleString()} — {e.location ?? "No location"}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
        </div>

        <div className="bg-white border rounded-lg shadow-sm">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800 text-sm">Resources</h2>
          </div>
          {loading ? <p className="p-4 text-sm text-gray-500">Loading…</p> : (
            <div className="divide-y max-h-72 overflow-y-auto">
              {resources.map(r => (
                <div key={r.resource_id} className="px-4 py-2.5 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{r.name}</p>
                    <p className="text-xs text-gray-500 capitalize">{r.resource_type} · {r.location ?? "No location"}</p>
                  </div>
                  <span className={`text-xs rounded-full px-2 py-0.5 ${
                    r.status === "active" ? "bg-green-100 text-green-700" :
                    r.status === "maintenance" ? "bg-orange-100 text-orange-700" :
                    "bg-gray-100 text-gray-500"}`}>
                    {r.status}
                  </span>
                </div>
              ))}
              {resources.length === 0 && <p className="p-4 text-sm text-gray-400 text-center py-8">No resources configured.</p>}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { href: "/dashboard/calendar/view", label: "Calendar View", icon: "📅" },
          { href: "/dashboard/calendar/new-event", label: "New Event", icon: "➕" },
          { href: "/dashboard/calendar/resources", label: "Resources", icon: "🏠" },
          { href: "/dashboard/calendar/availability", label: "Check Availability", icon: "✅" },
        ].map(l => (
          <a key={l.href} href={l.href}
            className="bg-white border rounded-lg p-4 shadow-sm hover:bg-gray-50 text-center">
            <div className="text-2xl mb-1">{l.icon}</div>
            <p className="text-sm font-medium text-gray-700">{l.label}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
