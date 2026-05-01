"use client";
import { useEffect, useState } from "react";
import { calendarApi, CalendarResource, ResourceBooking, CalendarEvent } from "@/lib/calendar";

type Tab = "utilization" | "events" | "bookings";

export default function CalendarReportsPage() {
  const [tab, setTab] = useState<Tab>("utilization");
  const [resources, setResources] = useState<CalendarResource[]>([]);
  const [bookings, setBookings] = useState<ResourceBooking[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    Promise.all([
      calendarApi.listResources(),
      calendarApi.listBookings({ start: monthStart.toISOString(), end: monthEnd.toISOString() }),
      calendarApi.listEvents({ start: monthStart.toISOString(), end: monthEnd.toISOString() }),
    ]).then(([r, b, e]) => { setResources(r); setBookings(b); setEvents(e); }).finally(() => setLoading(false));
  }, []);

  const resourceUtilization = resources.map(r => {
    const rb = bookings.filter(b => b.resource_id === r.resource_id && b.status !== "cancelled");
    const totalHours = rb.reduce((acc, b) => {
      return acc + (new Date(b.end_datetime).getTime() - new Date(b.start_datetime).getTime()) / 3600000;
    }, 0);
    const availableHours = 160;
    const pct = Math.min(100, Math.round((totalHours / availableHours) * 100));
    return { resource: r, totalHours: Math.round(totalHours), bookingCount: rb.length, pct };
  });

  const eventsByType = events.reduce((acc, e) => {
    acc[e.event_type] = (acc[e.event_type] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const bookingsByStatus = bookings.reduce((acc, b) => {
    acc[b.status] = (acc[b.status] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const tabs: { key: Tab; label: string }[] = [
    { key: "utilization", label: "Resource Utilization" },
    { key: "events", label: "Event Summary" },
    { key: "bookings", label: "Booking Summary" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Calendar Reports</h1>

      <div className="flex border-b">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t.key ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <p className="text-sm text-gray-500 py-8 text-center">Loading…</p> : (
        <>
          {tab === "utilization" && (
            <div className="bg-white border rounded-lg shadow-sm p-5 space-y-4">
              <p className="text-xs text-gray-500">Based on bookings this calendar month (assuming 160h available per resource).</p>
              {resourceUtilization.length === 0 && <p className="text-sm text-gray-400 text-center py-8">No resources.</p>}
              {resourceUtilization.map(({ resource, totalHours, bookingCount, pct }) => (
                <div key={resource.resource_id}>
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <span className="text-sm font-medium text-gray-800">{resource.name}</span>
                      <span className="text-xs text-gray-400 ml-2 capitalize">{resource.resource_type}</span>
                    </div>
                    <span className="text-sm font-semibold text-gray-700">{pct}% ({totalHours}h / {bookingCount} bookings)</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div className={`h-3 rounded-full ${pct >= 80 ? "bg-red-500" : pct >= 50 ? "bg-orange-400" : "bg-blue-500"}`}
                      style={{ width: `${pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "events" && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="bg-white border rounded-lg shadow-sm p-5">
                <h2 className="font-semibold text-gray-800 mb-3 text-sm">Events by Type (This Month)</h2>
                {Object.entries(eventsByType).length === 0
                  ? <p className="text-sm text-gray-400">No events this month.</p>
                  : Object.entries(eventsByType).sort((a, b) => b[1] - a[1]).map(([type, count]) => {
                    const max = Math.max(...Object.values(eventsByType));
                    const pct = Math.round((count / max) * 100);
                    return (
                      <div key={type} className="mb-3">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="capitalize text-gray-700">{type}</span>
                          <span className="font-semibold">{count}</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2">
                          <div className="h-2 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })
                }
              </div>
              <div className="bg-white border rounded-lg shadow-sm p-5">
                <h2 className="font-semibold text-gray-800 mb-3 text-sm">Event Status Summary</h2>
                {[
                  { label: "Scheduled", value: events.filter(e => e.status === "scheduled").length, color: "bg-blue-500" },
                  { label: "Completed", value: events.filter(e => e.status === "completed").length, color: "bg-green-500" },
                  { label: "Cancelled", value: events.filter(e => e.status === "cancelled").length, color: "bg-red-400" },
                ].map(s => (
                  <div key={s.label} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${s.color}`} />
                      <span className="text-sm text-gray-700">{s.label}</span>
                    </div>
                    <span className="font-semibold text-gray-800">{s.value}</span>
                  </div>
                ))}
                <div className="mt-3 pt-3 border-t flex justify-between text-sm font-bold">
                  <span>Total Events</span>
                  <span>{events.length}</span>
                </div>
              </div>
            </div>
          )}

          {tab === "bookings" && (
            <div className="bg-white border rounded-lg shadow-sm p-5">
              <h2 className="font-semibold text-gray-800 mb-4 text-sm">Booking Status Summary (This Month)</h2>
              <div className="grid grid-cols-3 gap-4 mb-6">
                {[
                  { label: "Reserved", value: bookingsByStatus["reserved"] ?? 0, color: "text-yellow-600" },
                  { label: "Confirmed", value: bookingsByStatus["confirmed"] ?? 0, color: "text-green-600" },
                  { label: "Cancelled", value: bookingsByStatus["cancelled"] ?? 0, color: "text-gray-500" },
                ].map(s => (
                  <div key={s.label} className="border rounded-lg p-4 text-center">
                    <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-gray-500 mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Bookings by Resource</h3>
              <div className="space-y-2">
                {resources.map(r => {
                  const count = bookings.filter(b => b.resource_id === r.resource_id).length;
                  return (
                    <div key={r.resource_id} className="flex items-center justify-between py-1.5 border-b last:border-0">
                      <span className="text-sm text-gray-700">{r.name}</span>
                      <span className="text-sm font-semibold text-gray-800">{count} booking{count !== 1 ? "s" : ""}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
