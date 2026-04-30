"use client";
import { useEffect, useState } from "react";
import { trainingApi, TrainingSession, TrainingProgram, SessionStatus, SESSION_STATUS_COLOR } from "@/lib/training";

export default function TrainingSessionsPage() {
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [programs, setPrograms] = useState<TrainingProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [upcomingOnly, setUpcomingOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    training_id: "", session_date: "", end_date: "", location: "",
    trainer_name: "", capacity: "", notes: "",
  });

  const load = () =>
    Promise.all([
      trainingApi.listSessions({ upcoming_only: upcomingOnly }),
      trainingApi.listPrograms({ active_only: true }),
    ]).then(([s, p]) => { setSessions(s); setPrograms(p); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, [upcomingOnly]);

  const submit = async () => {
    await trainingApi.createSession({
      training_id: form.training_id,
      session_date: form.session_date,
      end_date: form.end_date || undefined,
      location: form.location || undefined,
      trainer_name: form.trainer_name || undefined,
      capacity: form.capacity ? Number(form.capacity) : undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  const complete = async (id: string) => {
    await trainingApi.completeSession(id);
    load();
  };

  const updateStatus = async (id: string, status: SessionStatus) => {
    await trainingApi.updateSession(id, { status });
    load();
  };

  // Group by month
  const byMonth: Record<string, TrainingSession[]> = {};
  for (const s of sessions) {
    const month = s.session_date.slice(0, 7);
    byMonth[month] = byMonth[month] ?? [];
    byMonth[month].push(s);
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Training Sessions & Calendar</h1>
        <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Schedule Session
        </button>
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input type="checkbox" checked={upcomingOnly} onChange={(e) => setUpcomingOnly(e.target.checked)} />
        Upcoming sessions only
      </label>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Schedule Training Session</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Training Program *</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.training_id}
                onChange={(e) => setForm({ ...form, training_id: e.target.value })}>
                <option value="">Select program…</option>
                {programs.map(p => <option key={p.training_id} value={p.training_id}>{p.training_name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Session Date *</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.session_date} onChange={(e) => setForm({ ...form, session_date: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">End Date</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Location</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Trainer Name</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.trainer_name} onChange={(e) => setForm({ ...form, trainer_name: e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Capacity</label>
              <input type="number" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Schedule</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-6">
          {Object.entries(byMonth).sort().map(([month, sess]) => (
            <div key={month}>
              <h2 className="text-sm font-semibold text-gray-600 mb-2 uppercase tracking-wide">
                {new Date(month + "-01").toLocaleDateString("en-GB", { month: "long", year: "numeric" })}
              </h2>
              <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {["Program","Date","Location","Trainer","Capacity","Enrolled","Status","Actions"].map(h=>(
                        <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {sess.map(s => (
                      <tr key={s.session_id} className="hover:bg-gray-50">
                        <td className="px-3 py-2 font-medium text-gray-800">{s.training_name ?? s.training_id}</td>
                        <td className="px-3 py-2 text-gray-600">{s.session_date}{s.end_date ? ` → ${s.end_date}` : ""}</td>
                        <td className="px-3 py-2 text-gray-600">{s.location ?? "—"}</td>
                        <td className="px-3 py-2 text-gray-600">{s.trainer_name ?? "—"}</td>
                        <td className="px-3 py-2 text-center">{s.capacity ?? "—"}</td>
                        <td className="px-3 py-2 text-center">{s.enrolled_count}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${SESSION_STATUS_COLOR[s.status]}`}>
                            {s.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 flex gap-2">
                          {s.status === "planned" && (
                            <button onClick={() => complete(s.session_id)} className="text-xs text-green-600 hover:underline">Complete</button>
                          )}
                          {s.status === "planned" && (
                            <button onClick={() => updateStatus(s.session_id, "cancelled")} className="text-xs text-red-500 hover:underline">Cancel</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          {sessions.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No sessions scheduled.</p>}
        </div>
      )}
    </div>
  );
}
