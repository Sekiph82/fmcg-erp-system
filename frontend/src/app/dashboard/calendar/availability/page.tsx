"use client";
import { useEffect, useState } from "react";
import { calendarApi, CalendarResource, AvailabilitySlot } from "@/lib/calendar";

export default function AvailabilityPage() {
  const [resources, setResources] = useState<CalendarResource[]>([]);
  const [selectedResources, setSelectedResources] = useState<string[]>([]);
  const [duration, setDuration] = useState(60);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const [checkResource, setCheckResource] = useState("");
  const [checkStart, setCheckStart] = useState("");
  const [checkEnd, setCheckEnd] = useState("");
  const [checkResult, setCheckResult] = useState<{ available: boolean; conflicts: number } | null>(null);

  useEffect(() => { calendarApi.listResources().then(setResources); }, []);

  const toggle = (id: string) => setSelectedResources(prev =>
    prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
  );

  const findSlots = async () => {
    if (selectedResources.length === 0) { alert("Select at least one resource"); return; }
    setLoading(true);
    setSearched(true);
    try {
      const result = await calendarApi.getAvailableSlots({
        resource_ids: selectedResources,
        duration_minutes: duration,
        date,
        max_slots: 8,
      });
      setSlots(result);
    } finally {
      setLoading(false);
    }
  };

  const checkSpecific = async () => {
    if (!checkResource || !checkStart || !checkEnd) { alert("Fill all fields"); return; }
    const result = await calendarApi.checkAvailability({
      resource_id: checkResource,
      start_datetime: new Date(checkStart).toISOString(),
      end_datetime: new Date(checkEnd).toISOString(),
    });
    setCheckResult(result);
  };

  const fmt = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const fmtDate = (iso: string) => new Date(iso).toLocaleDateString();

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-xl font-bold text-gray-900">Availability Checker</h1>

      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
        <h2 className="font-semibold text-gray-800">Find Available Slots</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Date</label>
            <input type="date" className="w-full border rounded px-2 py-1.5 text-sm"
              value={date} onChange={e => setDate(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Duration (minutes)</label>
            <input type="number" min={15} step={15} className="w-full border rounded px-2 py-1.5 text-sm"
              value={duration} onChange={e => setDuration(Number(e.target.value))} />
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-2">Select Resources *</label>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
            {resources.filter(r => r.status === "active").map(r => (
              <label key={r.resource_id} className="flex items-center gap-2 p-2 border rounded cursor-pointer hover:bg-gray-50">
                <input type="checkbox" checked={selectedResources.includes(r.resource_id)}
                  onChange={() => toggle(r.resource_id)} />
                <div>
                  <p className="text-sm font-medium text-gray-800">{r.name}</p>
                  <p className="text-xs text-gray-400 capitalize">{r.resource_type}</p>
                </div>
              </label>
            ))}
          </div>
          {resources.length === 0 && <p className="text-sm text-gray-400">No active resources.</p>}
        </div>
        <button onClick={findSlots} disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Searching…" : "Find Available Slots"}
        </button>
      </div>

      {searched && !loading && (
        <div className="bg-white border rounded-lg p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-3">
            Available Slots on {new Date(date).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}
          </h2>
          {slots.length === 0
            ? <p className="text-sm text-gray-400 text-center py-8">No available slots found for the selected duration and resources.</p>
            : (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {slots.map((s, i) => (
                  <div key={i} className="border border-green-200 bg-green-50 rounded-lg p-3 text-center cursor-pointer hover:bg-green-100">
                    <p className="text-sm font-semibold text-green-800">{fmt(s.start)} – {fmt(s.end)}</p>
                    <p className="text-xs text-green-600 mt-0.5">{fmtDate(s.start)}</p>
                    <p className="text-xs text-green-500 mt-1">{duration} min · All resources free</p>
                  </div>
                ))}
              </div>
            )
          }
        </div>
      )}

      <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
        <h2 className="font-semibold text-gray-800">Check Specific Slot</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <div className="col-span-2 md:col-span-1">
            <label className="text-xs text-gray-500 block mb-1">Resource</label>
            <select className="w-full border rounded px-2 py-1.5 text-sm" value={checkResource}
              onChange={e => { setCheckResource(e.target.value); setCheckResult(null); }}>
              <option value="">Select resource…</option>
              {resources.map(r => <option key={r.resource_id} value={r.resource_id}>{r.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Start</label>
            <input type="datetime-local" className="w-full border rounded px-2 py-1.5 text-sm"
              value={checkStart} onChange={e => { setCheckStart(e.target.value); setCheckResult(null); }} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">End</label>
            <input type="datetime-local" className="w-full border rounded px-2 py-1.5 text-sm"
              value={checkEnd} onChange={e => { setCheckEnd(e.target.value); setCheckResult(null); }} />
          </div>
        </div>
        <button onClick={checkSpecific}
          className="rounded border border-blue-300 px-4 py-1.5 text-sm text-blue-600 hover:bg-blue-50">
          Check Availability
        </button>
        {checkResult && (
          <div className={`flex items-center gap-2 text-sm font-medium p-3 rounded ${checkResult.available ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            <span className="text-lg">{checkResult.available ? "✓" : "✗"}</span>
            {checkResult.available
              ? "Resource is available for this time slot."
              : `Resource is NOT available — ${checkResult.conflicts} conflict(s) detected.`}
          </div>
        )}
      </div>
    </div>
  );
}
