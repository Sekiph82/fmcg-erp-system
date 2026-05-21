"use client";
import { useEffect, useState } from "react";
import { calendarApi, CalendarResource, EventType, RecurrenceFrequency } from "@/lib/calendar";

const EVENT_TYPES: EventType[] = ["meeting", "task", "booking", "production", "maintenance", "other"];
const FREQS: RecurrenceFrequency[] = ["daily", "weekly", "monthly", "custom"];

function fmt(d: Date): string {
  return d.toISOString().slice(0, 16);
}

export default function NewEventPage() {
  const [step, setStep] = useState(1);
  const [resources, setResources] = useState<CalendarResource[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const now = new Date();
  const later = new Date(now.getTime() + 3600000);

  const [form, setForm] = useState({
    event_title: "",
    event_type: "meeting" as EventType,
    start_datetime: fmt(now),
    end_datetime: fmt(later),
    all_day_flag: false,
    location: "",
    description: "",
    created_by: "",
  });

  const [participants, setParticipants] = useState<{ name: string; email: string; role: string }[]>([]);
  const [newP, setNewP] = useState({ name: "", email: "", role: "attendee" });

  const [selectedResources, setSelectedResources] = useState<string[]>([]);

  const [useRecurrence, setUseRecurrence] = useState(false);
  const [recurrence, setRecurrence] = useState({
    frequency: "weekly" as RecurrenceFrequency,
    interval: 1,
    end_date: "",
  });

  useEffect(() => { calendarApi.listResources().then(setResources); }, []);

  const toggleResource = (id: string) => {
    setSelectedResources(prev =>
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    );
  };

  const addParticipant = () => {
    if (!newP.name && !newP.email) return;
    setParticipants(prev => [...prev, newP]);
    setNewP({ name: "", email: "", role: "attendee" });
  };

  const submit = async () => {
    setError("");
    setSubmitting(true);
    try {
      await calendarApi.createEvent({
        ...form,
        start_datetime: new Date(form.start_datetime).toISOString(),
        end_datetime: new Date(form.end_datetime).toISOString(),
        participants: participants.map(p => ({
          participant_name: p.name, participant_email: p.email, role: p.role,
        })),
        resource_ids: selectedResources,
        recurrence: useRecurrence ? {
          frequency: recurrence.frequency,
          interval: Number(recurrence.interval),
          end_date: recurrence.end_date ? new Date(recurrence.end_date).toISOString() : undefined,
        } : undefined,
      });
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create event");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) return (
    <div className="p-6 text-center">
      <p className="text-green-600 font-semibold text-lg mb-2">Event created!</p>
      <div className="flex justify-center gap-3">
        <a href="/dashboard/calendar/events" className="text-sm text-blue-600 hover:underline">View Events</a>
        <button onClick={() => { setDone(false); setStep(1); }} className="text-sm text-gray-600 hover:underline">Create Another</button>
      </div>
    </div>
  );

  const steps = ["Basic Info", "Participants", "Resources", "Recurrence"];

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <h1 className="text-xl font-bold text-gray-900">New Event</h1>

      <div className="flex gap-1">
        {steps.map((s, i) => (
          <div key={s} className={`flex-1 text-center text-xs py-1 rounded font-medium ${i + 1 === step ? "bg-blue-600 text-white" : i + 1 < step ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
            {i + 1}. {s}
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <div><label className="text-xs text-gray-500">Title *</label>
            <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.event_title}
              onChange={e => setForm({ ...form, event_title: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-gray-500">Type</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.event_type}
                onChange={e => setForm({ ...form, event_type: e.target.value as EventType })}>
                {EVENT_TYPES.map(t => <option key={t} value={t} className="capitalize">{t}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Organizer</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" placeholder="Your name"
                value={form.created_by} onChange={e => setForm({ ...form, created_by: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Start *</label>
              <input type="datetime-local" className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.start_datetime}
                onChange={e => setForm({ ...form, start_datetime: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">End *</label>
              <input type="datetime-local" className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.end_datetime}
                onChange={e => setForm({ ...form, end_datetime: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Location</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" placeholder="Room, address, or online link"
                value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Description</label>
              <textarea className="w-full border rounded px-2 py-1.5 text-sm mt-1 h-20" value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })} /></div>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold text-gray-800 text-sm">Add Participants</h2>
          <div className="grid grid-cols-3 gap-2">
            <input className="border rounded px-2 py-1.5 text-sm" placeholder="Name"
              value={newP.name} onChange={e => setNewP({ ...newP, name: e.target.value })} />
            <input className="border rounded px-2 py-1.5 text-sm" placeholder="Email"
              value={newP.email} onChange={e => setNewP({ ...newP, email: e.target.value })} />
            <div className="flex gap-1">
              <select className="flex-1 border rounded px-2 py-1.5 text-sm" value={newP.role}
                onChange={e => setNewP({ ...newP, role: e.target.value })}>
                {["organizer", "attendee", "optional"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              <button onClick={addParticipant} className="rounded bg-gray-800 px-2 text-white text-sm">+</button>
            </div>
          </div>
          {participants.length > 0 && (
            <div className="divide-y border rounded">
              {participants.map((p, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                  <span>{p.name || p.email} <span className="text-xs text-gray-400">({p.role})</span></span>
                  <button onClick={() => setParticipants(prev => prev.filter((_, j) => j !== i))}
                    className="text-red-400 text-xs hover:underline">Remove</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {step === 3 && (
        <div className="bg-white border rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-gray-800 text-sm">Book Resources (optional)</h2>
          {resources.filter(r => r.status === "active").map(r => (
            <label key={r.resource_id} className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-gray-50">
              <input type="checkbox" checked={selectedResources.includes(r.resource_id)}
                onChange={() => toggleResource(r.resource_id)} />
              <div>
                <p className="text-sm font-medium text-gray-800">{r.name}</p>
                <p className="text-xs text-gray-500 capitalize">{r.resource_type} · Cap: {r.capacity} · {r.location ?? "No location"}</p>
              </div>
            </label>
          ))}
          {resources.length === 0 && <p className="text-sm text-gray-400">No active resources configured.</p>}
        </div>
      )}

      {step === 4 && (
        <div className="bg-white border rounded-lg p-5 space-y-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={useRecurrence} onChange={e => setUseRecurrence(e.target.checked)} />
            <span className="text-sm font-medium text-gray-800">Make this a recurring event</span>
          </label>
          {useRecurrence && (
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-gray-500">Frequency</label>
                <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={recurrence.frequency}
                  onChange={e => setRecurrence({ ...recurrence, frequency: e.target.value as RecurrenceFrequency })}>
                  {FREQS.map(f => <option key={f} value={f}>{f}</option>)}
                </select></div>
              <div><label className="text-xs text-gray-500">Interval (every N)</label>
                <input type="number" min={1} className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                  value={recurrence.interval} onChange={e => setRecurrence({ ...recurrence, interval: Number(e.target.value) })} /></div>
              <div className="col-span-2"><label className="text-xs text-gray-500">End Date (optional)</label>
                <input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                  value={recurrence.end_date} onChange={e => setRecurrence({ ...recurrence, end_date: e.target.value })} /></div>
            </div>
          )}

          <div className="bg-gray-50 border rounded p-3 text-sm space-y-1">
            <p><span className="font-medium">Title:</span> {form.event_title}</p>
            <p><span className="font-medium">Start:</span> {form.start_datetime}</p>
            <p><span className="font-medium">End:</span> {form.end_datetime}</p>
            <p><span className="font-medium">Participants:</span> {participants.length}</p>
            <p><span className="font-medium">Resources:</span> {selectedResources.length}</p>
            <p><span className="font-medium">Recurring:</span> {useRecurrence ? `Yes (${recurrence.frequency})` : "No"}</p>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex justify-between">
        <button onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}
          className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40">Back</button>
        {step < 4
          ? <button onClick={() => setStep(s => s + 1)} disabled={!form.event_title}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">Next</button>
          : <button onClick={submit} disabled={submitting}
              className="rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50">
              {submitting ? "Creating…" : "Create Event"}
            </button>
        }
      </div>
    </div>
  );
}
