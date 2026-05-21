"use client";
import { useEffect, useState } from "react";
import { calendarApi, CalendarEvent, EVENT_COLOR } from "@/lib/calendar";

type ViewMode = "week" | "month" | "day";

const HOUR_HEIGHT = 48;
const DAY_START = 8;
const DAY_END = 20;
const HOURS = Array.from({ length: DAY_END - DAY_START }, (_, i) => i + DAY_START);
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getMondayOfWeek(d: Date): Date {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(d.getFullYear(), d.getMonth(), diff, 0, 0, 0);
}

function getWeekDays(monday: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
}

function getMonthDays(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startPad = (first.getDay() + 6) % 7;
  const days: (Date | null)[] = Array(startPad).fill(null);
  for (let d = 1; d <= last.getDate(); d++) days.push(new Date(year, month, d));
  while (days.length % 7 !== 0) days.push(null);
  return days;
}

function eventTopPct(event: CalendarEvent): number {
  const s = new Date(event.start_datetime);
  return ((s.getHours() - DAY_START) * 60 + s.getMinutes()) / 60 * HOUR_HEIGHT;
}

function eventHeightPx(event: CalendarEvent): number {
  const s = new Date(event.start_datetime);
  const e = new Date(event.end_datetime);
  const mins = (e.getTime() - s.getTime()) / 60000;
  return Math.max((mins / 60) * HOUR_HEIGHT, 20);
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
}

export default function CalendarViewPage() {
  const [view, setView] = useState<ViewMode>("week");
  const [anchor, setAnchor] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<CalendarEvent | null>(null);

  const monday = getMondayOfWeek(view === "week" ? anchor : new Date(anchor.getFullYear(), anchor.getMonth(), 1));
  const weekDays = getWeekDays(monday);
  const monthDays = getMonthDays(anchor.getFullYear(), anchor.getMonth());

  useEffect(() => {
    setLoading(true);
    let start: Date, end: Date;
    if (view === "week") {
      start = monday;
      end = new Date(monday);
      end.setDate(monday.getDate() + 7);
    } else if (view === "month") {
      start = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
      end = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);
    } else {
      start = new Date(anchor);
      start.setHours(0, 0, 0, 0);
      end = new Date(anchor);
      end.setHours(23, 59, 59, 999);
    }
    calendarApi.listEvents({ start: start.toISOString(), end: end.toISOString() })
      .then(setEvents).finally(() => setLoading(false));
  }, [view, anchor]);

  const navigate = (dir: number) => {
    const d = new Date(anchor);
    if (view === "week") d.setDate(d.getDate() + dir * 7);
    else if (view === "month") d.setMonth(d.getMonth() + dir);
    else d.setDate(d.getDate() + dir);
    setAnchor(d);
  };

  const title = view === "week"
    ? `${monday.toLocaleDateString("en-GB", { day: "numeric", month: "short" })} – ${weekDays[6].toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`
    : view === "month"
    ? anchor.toLocaleDateString("en-GB", { month: "long", year: "numeric" })
    : anchor.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Calendar</h1>
        <div className="flex items-center gap-2">
          <div className="flex rounded border overflow-hidden text-sm">
            {(["day", "week", "month"] as ViewMode[]).map(v => (
              <button key={v} onClick={() => setView(v)}
                className={`px-3 py-1 capitalize ${view === v ? "bg-gray-800 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
                {v}
              </button>
            ))}
          </div>
          <button onClick={() => navigate(-1)} className="rounded border px-2 py-1 text-sm hover:bg-gray-50">‹</button>
          <button onClick={() => setAnchor(new Date())} className="rounded border px-2 py-1 text-sm hover:bg-gray-50">Today</button>
          <button onClick={() => navigate(1)} className="rounded border px-2 py-1 text-sm hover:bg-gray-50">›</button>
          <a href="/dashboard/calendar/new-event"
            className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700">+ Event</a>
        </div>
      </div>

      <p className="text-sm font-medium text-gray-700">{title}</p>

      {loading && <p className="text-sm text-gray-500 py-8 text-center">Loading…</p>}

      {!loading && view === "week" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="grid grid-cols-8 border-b bg-gray-50">
            <div className="px-2 py-2 text-xs text-gray-400" />
            {weekDays.map((d, i) => {
              const today = isSameDay(d, new Date());
              return (
                <div key={i} className={`px-2 py-2 text-xs font-semibold text-center border-l ${today ? "text-blue-600" : "text-gray-600"}`}>
                  <div>{DAYS[i]}</div>
                  <div className={`text-base ${today ? "bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center mx-auto" : ""}`}>
                    {d.getDate()}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="grid grid-cols-8 overflow-y-auto" style={{ maxHeight: "70vh" }}>
            <div>
              {HOURS.map(h => (
                <div key={h} style={{ height: HOUR_HEIGHT }} className="border-b px-2 text-xs text-gray-400 pt-1">
                  {h}:00
                </div>
              ))}
            </div>
            {weekDays.map((day, di) => {
              const dayEvents = events.filter(e => isSameDay(new Date(e.start_datetime), day));
              return (
                <div key={di} className="border-l relative" style={{ height: HOURS.length * HOUR_HEIGHT }}>
                  {HOURS.map(h => (
                    <div key={h} style={{ height: HOUR_HEIGHT }} className="border-b border-gray-100" />
                  ))}
                  {dayEvents.map(e => {
                    const top = eventTopPct(e);
                    const height = eventHeightPx(e);
                    const color = EVENT_COLOR[e.event_type];
                    return (
                      <div key={e.event_id}
                        style={{ position: "absolute", top, height, left: 2, right: 2 }}
                        className={`${color} text-white text-xs rounded px-1 py-0.5 overflow-hidden cursor-pointer hover:opacity-90 z-10`}
                        onClick={() => setSelected(e)}>
                        <p className="font-semibold truncate">{e.event_title}</p>
                        <p className="opacity-80">{new Date(e.start_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!loading && view === "month" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="grid grid-cols-7 bg-gray-50 border-b">
            {DAYS.map(d => (
              <div key={d} className="py-2 text-xs font-semibold text-center text-gray-600">{d}</div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {monthDays.map((day, i) => {
              if (!day) return <div key={i} className="h-24 border-b border-r bg-gray-50" />;
              const today = isSameDay(day, new Date());
              const dayEvs = events.filter(e => isSameDay(new Date(e.start_datetime), day));
              return (
                <div key={i} className={`h-24 border-b border-r p-1 ${today ? "bg-blue-50" : ""}`}>
                  <p className={`text-xs font-medium mb-1 ${today ? "text-blue-600" : "text-gray-700"}`}>{day.getDate()}</p>
                  {dayEvs.slice(0, 3).map(e => (
                    <div key={e.event_id}
                      className={`text-xs rounded px-1 py-0.5 mb-0.5 truncate cursor-pointer text-white ${EVENT_COLOR[e.event_type]}`}
                      onClick={() => setSelected(e)}>
                      {e.event_title}
                    </div>
                  ))}
                  {dayEvs.length > 3 && <p className="text-xs text-gray-400">+{dayEvs.length - 3} more</p>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!loading && view === "day" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="grid grid-cols-[64px_1fr] overflow-y-auto" style={{ maxHeight: "70vh" }}>
            <div>
              {HOURS.map(h => (
                <div key={h} style={{ height: HOUR_HEIGHT }} className="border-b px-2 text-xs text-gray-400 pt-1">
                  {h}:00
                </div>
              ))}
            </div>
            <div className="border-l relative" style={{ height: HOURS.length * HOUR_HEIGHT }}>
              {HOURS.map(h => (
                <div key={h} style={{ height: HOUR_HEIGHT }} className="border-b border-gray-100" />
              ))}
              {events.filter(e => isSameDay(new Date(e.start_datetime), anchor)).map(e => {
                const top = eventTopPct(e);
                const height = eventHeightPx(e);
                return (
                  <div key={e.event_id}
                    style={{ position: "absolute", top, height, left: 4, right: 4 }}
                    className={`${EVENT_COLOR[e.event_type]} text-white rounded px-2 py-1 overflow-hidden cursor-pointer hover:opacity-90`}
                    onClick={() => setSelected(e)}>
                    <p className="font-semibold text-sm">{e.event_title}</p>
                    <p className="text-xs opacity-80">
                      {new Date(e.start_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} –{" "}
                      {new Date(e.end_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                    {e.location && <p className="text-xs opacity-70">{e.location}</p>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
            <div className="flex items-start justify-between mb-3">
              <h2 className="font-bold text-gray-900">{selected.event_title}</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-1.5 text-sm text-gray-600">
              <p><span className="font-medium">Type:</span> {selected.event_type}</p>
              <p><span className="font-medium">Status:</span> {selected.status}</p>
              <p><span className="font-medium">Start:</span> {new Date(selected.start_datetime).toLocaleString()}</p>
              <p><span className="font-medium">End:</span> {new Date(selected.end_datetime).toLocaleString()}</p>
              {selected.location && <p><span className="font-medium">Location:</span> {selected.location}</p>}
              {selected.description && <p><span className="font-medium">Description:</span> {selected.description}</p>}
              {selected.participants.length > 0 && (
                <p><span className="font-medium">Participants:</span> {selected.participants.map(p => p.participant_name || p.participant_email).join(", ")}</p>
              )}
            </div>
            <div className="flex justify-end mt-4">
              <button onClick={() => setSelected(null)} className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
