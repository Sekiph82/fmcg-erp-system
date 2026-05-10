"use client";
import { useCallback, useEffect, useState } from "react";
import { calendarApi, CalendarEvent, EventType, EventStatus, EVENT_BADGE, STATUS_BADGE } from "@/lib/calendar";

const EVENT_TYPES: EventType[] = ["meeting", "task", "booking", "production", "maintenance", "other"];
const STATUSES: EventStatus[] = ["scheduled", "completed", "cancelled"];

export default function EventsPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const load = useCallback(() =>
    calendarApi.listEvents({
      event_type: filterType || undefined,
      status: filterStatus || undefined,
    }).then(setEvents).finally(() => setLoading(false)), [filterType, filterStatus]);

  useEffect(() => { load(); }, [load]);

  const cancel = async (id: string) => {
    if (!confirm("Cancel this event?")) return;
    await calendarApi.cancelEvent(id);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Events</h1>
        <a href="/dashboard/calendar/new-event"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Event
        </a>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={filterType} onChange={e => setFilterType(e.target.value)}>
          <option value="">All Types</option>
          {EVENT_TYPES.map(t => <option key={t} value={t} className="capitalize">{t}</option>)}
        </select>
        <select className="border rounded px-2 py-1 text-sm" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s} className="capitalize">{s}</option>)}
        </select>
      </div>

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Title", "Type", "Start", "End", "Location", "Status", "Participants", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {events.map(e => (
                <tr key={e.event_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{e.event_title}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${EVENT_BADGE[e.event_type]}`}>{e.event_type}</span>
                  </td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{new Date(e.start_datetime).toLocaleString()}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">{new Date(e.end_datetime).toLocaleString()}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{e.location ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[e.status]}`}>{e.status}</span>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{e.participants.length}</td>
                  <td className="px-4 py-2">
                    {e.status === "scheduled" && (
                      <button onClick={() => cancel(e.event_id)} className="text-xs text-red-500 hover:underline">Cancel</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {events.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No events found.</p>}
        </div>
      )}
    </div>
  );
}
