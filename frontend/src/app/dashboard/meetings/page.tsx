"use client";

import { ConnectedAccounts } from "@/components/ConnectedAccounts";
import { CalendarSubscriptionsPanel } from "@/components/meetings/CalendarSubscriptionsPanel";
import { RecurringSeriesPanel } from "@/components/meetings/RecurringSeriesPanel";
import { BookingPagesPanel } from "@/components/BookingPagesPanel";
import { EntityPicker } from "@/components/EntityPicker";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { MeetingRecap } from "@/components/sales/MeetingRecap";

interface Meeting {
  id: string;
  title: string;
  platform: string;
  meeting_url?: string;
  host_name?: string;
  customer_name?: string;
  scheduled_at: string;
  local_start?: string;
  time_zone?: string;
  can_change?: boolean;
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
  jitsi: "🎥",
  in_person: "🤝",
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

const BROWSER_TZ = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"; } catch { return "Africa/Nairobi"; } })();
const ZONES = Array.from(new Set(["Africa/Nairobi", BROWSER_TZ, "Africa/Kampala", "Africa/Dar_es_Salaam", "Europe/London", "Europe/Istanbul", "Asia/Dubai", "UTC"]));

const BLANK = {
  title: "", platform: "jitsi", meeting_url: "",
  customer_id: "", start: "", time_zone: "Africa/Nairobi", duration_minutes: "60",
  agenda: "", attendees: "",
};

function errorText(e: unknown, fallback: string) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) {
    const d = detail as { detail: string; conflict?: { title: string; scheduled_at: string } };
    return d.conflict ? `${d.detail} (${d.conflict.title}, ${new Date(d.conflict.scheduled_at).toLocaleString()})` : d.detail;
  }
  if (Array.isArray(detail)) return detail.map((x) => (x as { msg?: string }).msg).join("; ");
  return fallback;
}

const INVITE_TEXT: Record<string, string> = {
  SENT: "Invitations e-mailed from your mailbox.",
  NO_MAILBOX: "Saved. Invitations were not sent: connect your mailbox under Communication → Email.",
  NO_ATTENDEES: "Saved.",
  NOT_REQUESTED: "Saved.",
};

function CalendarConflicts() {
  // M43.S01.T003/T004: calendar edits the two-way sync did not apply (ERP version kept)
  const [rows, setRows] = useState<{ meeting_id: string; title: string; scheduled_at: string; conflict: string }[]>([]);
  useEffect(() => {
    apiClient.get("/api/v1/meetings/calendar-conflicts").then((r) => setRows(r.data)).catch(() => setRows([]));
  }, []);
  if (!rows.length) return null;
  return (
    <div className="border border-amber-200 bg-amber-50 rounded-lg p-3 text-xs space-y-1">
      <div className="font-semibold text-amber-900">Calendar sync needs your attention</div>
      {rows.map((r) => (
        <div key={r.meeting_id} className="text-amber-900">
          {r.title} ({new Date(r.scheduled_at).toLocaleString()}): {r.conflict}
        </div>
      ))}
    </div>
  );
}

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
  const [recapId, setRecapId] = useState<string | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [editOutcome, setEditOutcome] = useState("");
  const [info, setInfo] = useState("");
  const [feedUrl, setFeedUrl] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, s] = await Promise.all([
        apiClient.get<Meeting[]>("/api/v1/meetings/", { params: filterStatus ? { status: filterStatus } : {} }),
        apiClient.get<Stats>("/api/v1/meetings/stats"),
      ]);
      setMeetings(m.data); setStats(s.data);
    } finally { setLoading(false); }
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.title || !form.start) { setError("Title and date required"); return; }
    setSaving(true); setError("");
    try {
      const r = await apiClient.post<{ invites: string }>("/api/v1/meetings/", {
        title: form.title,
        platform: form.platform,
        meeting_url: form.meeting_url || null,
        customer_id: form.customer_id || null,
        start: form.start,            // wall time in the chosen zone; the server stores UTC
        time_zone: form.time_zone,
        duration_minutes: parseInt(form.duration_minutes) || 60,
        agenda: form.agenda || null,
        attendees: form.attendees.split(",").map((x) => x.trim()).filter(Boolean).map((email) => ({ email })),
      });
      setInfo(INVITE_TEXT[r.data.invites] ?? `Saved. ${r.data.invites}`);
      setShowCreate(false); setForm({ ...BLANK }); await load();
    } catch (e) { setError(errorText(e, "Failed to create meeting")); }
    finally { setSaving(false); }
  };

  const calendarLink = async (revoke: boolean) => {
    setError("");
    try {
      if (revoke) { await apiClient.delete("/api/v1/meetings/calendar-feed"); setFeedUrl(""); setInfo("Calendar link revoked."); }
      else { const r = await apiClient.post<{ url: string }>("/api/v1/meetings/calendar-feed"); setFeedUrl(r.data.url); }
    } catch (e) { setError(errorText(e, "Request failed")); }
  };

  const markComplete = async (id: string) => {
    try {
      await apiClient.patch(`/api/v1/meetings/${id}`, {
        status: "COMPLETED",
        notes: editNotes || null,
        outcome: editOutcome || null,
      });
      setEditId(null); setEditNotes(""); setEditOutcome("");
      await load();
    } catch (e) { setError(errorText(e, "Update failed")); }
  };

  const cancel = async (id: string) => {
    if (!confirm("Cancel this meeting? Invitees get a calendar cancellation.")) return;
    try {
      const r = await apiClient.delete<{ invites: string }>(`/api/v1/meetings/${id}`);
      setInfo(r.data.invites === "SENT" ? "Cancelled; invitees were notified." : "Cancelled.");
      await load();
    } catch (e) { setError(errorText(e, "Cancel failed")); }
  };

  return (
    <div className="p-6 space-y-5">
      <ConnectedAccounts purposes={["calendar"]} />
      <CalendarSubscriptionsPanel />
      <RecurringSeriesPanel />
      <CalendarConflicts />
      <BookingPagesPanel />
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Video Meetings</h1>
          <p className="text-xs text-gray-500 mt-0.5">Book customer meetings without double booking; invitees get a calendar invitation from your mailbox.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => calendarLink(false)}
            className="rounded border px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
            My calendar link
          </button>
          <button onClick={() => { setShowCreate(true); setError(""); }}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Schedule Meeting
          </button>
        </div>
      </div>
      {!showCreate && error && <p role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
      {info && <p role="status" className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">{info}</p>}
      {feedUrl && (
        <div className="text-sm bg-white border rounded px-3 py-2 space-y-1">
          <p>Add this link in Google Calendar (Other calendars → From URL) or Outlook (Add calendar → Subscribe from web). Keep it private; making a new one turns this one off.</p>
          <input readOnly value={feedUrl} onFocus={(e) => e.currentTarget.select()} className="w-full border rounded px-2 py-1 text-xs font-mono" aria-label="Calendar link" />
          <button onClick={() => calendarLink(true)} className="text-xs text-red-600 underline">Turn this link off</button>
        </div>
      )}

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
                      <span>{new Date(m.scheduled_at).toLocaleString()}{m.time_zone && m.time_zone !== BROWSER_TZ ? ` (booked as ${m.local_start?.slice(11, 16)} ${m.time_zone})` : ""}</span>
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
                  {m.status === "SCHEDULED" && m.can_change && (
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
                  <button onClick={() => setRecapId(recapId === m.id ? null : m.id)}
                    className="rounded border px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50">
                    Brief &amp; recap
                  </button>
                  {m.recording_url && (
                    <a href={m.recording_url} target="_blank" rel="noreferrer"
                      className="rounded border px-3 py-1.5 text-xs text-purple-600 hover:bg-purple-50 border-purple-200">
                      Recording
                    </a>
                  )}
                </div>
              </div>

              {recapId === m.id && <MeetingRecap meetingId={m.id} canChange={!!m.can_change} />}

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
                  placeholder="POVU AllClean listing review"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Platform</label>
                  <select value={form.platform} onChange={e => setForm(f => ({ ...f, platform: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                    <option value="jitsi">🎥 Jitsi (link created for you)</option>
                    <option value="in_person">🤝 In person</option>
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
                  <input type="datetime-local" value={form.start}
                    onChange={e => setForm(f => ({ ...f, start: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Time zone of that time</label>
                  <select value={form.time_zone} onChange={e => setForm(f => ({ ...f, time_zone: e.target.value }))}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
                    {ZONES.map((z) => <option key={z} value={z}>{z}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Invitees (e-mails, comma separated)</label>
                  <input type="text" value={form.attendees}
                    onChange={e => setForm(f => ({ ...f, attendees: e.target.value }))}
                    placeholder="buyer@duka.co.ke, rep@povu.co.ke"
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Meeting URL (optional)</label>
                  <input type="text" value={form.meeting_url}
                    onChange={e => setForm(f => ({ ...f, meeting_url: e.target.value }))}
                    placeholder={form.platform === "jitsi" ? "Leave empty: a Jitsi link is created" : "Paste the Google Meet / Zoom / Teams link"}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Customer (optional)</label>
                  <EntityPicker kind="customer" label="Customer" value={form.customer_id}
                    onChange={id => setForm(f => ({ ...f, customer_id: id }))} />
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
