"use client";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface Meeting {
  id: string;
  title: string;
  platform: string;
  meeting_url?: string;
  host_name?: string;
  customer_name?: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  agenda?: string;
  notes?: string;
  recording_url?: string;
  outcome?: string;
}

interface Stats {
  total: number;
  scheduled: number;
  completed: number;
  upcoming: Meeting[];
}

const PLATFORM_ICONS: Record<string, string> = {
  google_meet: "🟢",
  zoom: "🔵",
  teams: "💜",
  other: "📹",
};

const STATUS_COLORS: Record<string, string> = {
  SCHEDULED: "bg-blue-100 text-blue-700",
  COMPLETED: "bg-green-100 text-green-700",
  CANCELLED: "bg-gray-100 text-gray-500",
  NO_SHOW: "bg-red-100 text-red-600",
};

const BLANK = {
  title: "", platform: "google_meet", meeting_url: "",
  customer_id: "", scheduled_at: "", duration_minutes: "60",
  agenda: "",
};

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...BLANK });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [editOutcome, setEditOutcome] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [m, s] = await Promise.all([
        apiClient.get<Meeting[]>("/api/v1/meetings/", { params: filterStatus ? { status: filterStatus } : {} }),
        apiClient.get<Stats>("/api/v1/meetings/stats"),
      ]);
      setMeetings(m.data); setStats(s.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filterStatus]);

  const create = async () => {
    if (!form.title || !form.scheduled_at) { setError("Title and date required"); return; }
    setSaving(true); setError("");
    try {
      await apiClient.post("/api/v1/meetings/", {
        title: form.title,
        platform: form.platform,
        meeting_url: form.meeting_url || null,
        customer_id: form.customer_id || null,
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        duration_minutes: parseInt(form.duration_minutes) || 60,
        agenda: form.agenda || null,
      });
      setShowCreate(false); setForm({ ...BLANK }); await load();
    } catch { setError("Failed to create meeting"); }
    finally { setSaving(false); }
  };

  const markComplete = async (id: string) => {
    await apiClient.patch(`/api/v1/meetings/${id}`, {
      status: "COMPLETED",
      notes: editNotes || null,
      outcome: editOutcome || null,
    });
    setEditId(null); setEditNotes(""); setEditOutcome("");
    await load();
  };

  const cancel = async (id: string) => {
    if (!confirm("Cancel this meeting?")) return;
    await apiClient.delete(`/api/v1/meetings/${id}`);
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Video Meetings</h1>
          <p className="text-xs text-gray-500 mt-0.5">Schedule and track Google Meet, Zoom, and Teams meetings.</p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Schedule Meeting
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Total Meetings", value: stats.total, color: "text-gray-700" },
            { label: "Scheduled", value: stats.scheduled, color: "text-blue-600" },
            { label: "Completed", value: stats.completed, color: "text-green-600" },
          ].map(s => (
            <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {stats?.upcoming && stats.upcoming.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p className="text-xs font-semibold text-blue-700 mb-2">Upcoming Meetings</p>
          <div className="space-y-2">
            {stats.upcoming.map(m => (
              <div key={m.id} className="flex items-center gap-3 bg-white rounded-lg border px-3 py-2">
                <span className="text-lg">{PLATFORM_ICONS[m.platform] ?? "📹"}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">{m.title}</p>
                  <p className="text-xs text-gray-500">{new Date(m.scheduled_at).toLocaleString()}</p>
                </div>
                {m.meeting_url && (
                  <a href={m.meeting_url} target="_blank" rel="noreferrer"
                    className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700">
                    Join
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {["", "SCHEDULED", "COMPLETED", "CANCELLED"].map(s => (
          <button key={s}
            onClick={() => setFilterStatus(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}>
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : meetings.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📹</p>
          <p className="text-sm">No meetings found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {meetings.map(m => (
            <div key={m.id} className="bg-white border rounded-xl p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <span className="text-xl flex-shrink-0">{PLATFORM_ICONS[m.platform] ?? "📹"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-gray-800">{m.title}</p>
                      <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[m.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {m.status}
                      </span>
                    </div>
                    <div className="flex gap-3 text-xs text-gray-500 mt-0.5 flex-wrap">
                      <span>{new Date(m.scheduled_at).toLocaleString()}</span>
                      <span>{m.duration_minutes}min</span>
                      {m.customer_name && <span>with {m.customer_name}</span>}
                      {m.host_name && <span>by {m.host_name}</span>}
                    </div>
                    {m.agenda && <p className="text-xs text-gray-600 mt-1 line-clamp-2">{m.agenda}</p>}
                    {m.outcome && (
                      <p className="text-xs text-green-700 mt-1">Outcome: {m.outcome}</p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0 flex-wrap">
                  {m.meeting_url && m.status === "SCHEDULED" && (
                    <a href={m.meeting_url} target="_blank" rel="noreferrer"
                      className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700">
                      Join
                    </a>
                  )}
                  {m.status === "SCHEDULED" && (
                    <>
                      <button onClick={() => { setEditId(m.id); setEditNotes(m.notes ?? ""); setEditOutcome(m.outcome ?? ""); }}
                        className="rounded border px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50 border-blue-200">
                        Complete
                      </button>
                      <button onClick={() => cancel(m.id)}
                        className="rounded border px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 border-red-200">
                        Cancel
                      </button>
                    </>
                  )}
                  {m.recording_url && (
                    <a href={m.recording_url} target="_blank" rel="noreferrer"
                      className="rounded border px-3 py-1.5 text-xs text-purple-600 hover:bg-purple-50 border-purple-200">
                      Recording
                    </a>
                  )}
                </div>
              </div>

              {editId === m.id && (
                <div className="mt-3 border-t pt-3 space-y-2">
                  <textarea value={editNotes} onChange={e => setEditNotes(e.target.value)}
                    rows={2} placeholder="Meeting notes…"
                    className="w-full border rounded px-3 py-2 text-xs focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                  />
                  <input type="text" value={editOutcome} onChange={e => setEditOutcome(e.target.value)}
                    placeholder="Meeting outcome…"
                    className="w-full border rounded px-3 py-2 text-xs focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                  <div className="flex gap-2">
                    <button onClick={() => markComplete(m.id)}
                      className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700">
                      Save & Complete
                    </button>
                    <button onClick={() => setEditId(null)}
                      className="rounded border px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Schedule Meeting</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
                <input type="text" value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="Q3 Review with Distributor"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Platform</label>
                  <select value={form.platform} onChange={e => setForm(f => ({ ...f, platform: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                    <option value="google_meet">🟢 Google Meet</option>
                    <option value="zoom">🔵 Zoom</option>
                    <option value="teams">💜 MS Teams</option>
                    <option value="other">📹 Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Duration (min)</label>
                  <input type="number" value={form.duration_minutes}
                    onChange={e => setForm(f => ({ ...f, duration_minutes: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Date & Time *</label>
                  <input type="datetime-local" value={form.scheduled_at}
                    onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Meeting URL (optional)</label>
                  <input type="text" value={form.meeting_url}
                    onChange={e => setForm(f => ({ ...f, meeting_url: e.target.value }))}
                    placeholder="Paste meeting link here"
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Customer ID (UUID, optional)</label>
                  <input type="text" value={form.customer_id}
                    onChange={e => setForm(f => ({ ...f, customer_id: e.target.value }))}
                    placeholder="UUID"
                    className="w-full border rounded px-3 py-2 text-sm font-mono focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Agenda</label>
                  <textarea value={form.agenda}
                    onChange={e => setForm(f => ({ ...f, agenda: e.target.value }))}
                    rows={3} placeholder="Meeting agenda…"
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={create} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Creating…" : "Schedule Meeting"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
