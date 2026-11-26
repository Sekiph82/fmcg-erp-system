"use client";

// M49.S01.T001: recurring meetings. Create a series (repeat rule + time zone), then change or cancel one occurrence,
// this and following, or all of them. One invitation per change; the host's Google / Outlook calendar holds one
// recurring event with exceptions. Double bookings are refused by the server with the clashing meeting named.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface Attendee { email: string; name?: string; response?: string }
interface Series {
  id: string; title: string; time_zone: string; start_local: string; duration_minutes: number; rrule: string;
  status: string; attendees: Attendee[]; sequence: number; meeting_url?: string | null; agenda?: string | null;
}
interface Occurrence {
  date: string; meeting_id: string; status: string; is_exception: boolean; local_start: string; duration_minutes: number;
  title: string; attendees: Attendee[];
}
interface Detail extends Series { occurrences: Occurrence[]; can_change: boolean }

const BROWSER_TZ = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"; } catch { return "Africa/Nairobi"; } })();
const ZONES = Array.from(new Set(["Africa/Nairobi", BROWSER_TZ, "Europe/London", "Europe/Istanbul", "America/New_York", "Asia/Dubai", "UTC"]));
const DAYS = [["MO", "Mon"], ["TU", "Tue"], ["WE", "Wed"], ["TH", "Thu"], ["FR", "Fri"], ["SA", "Sat"], ["SU", "Sun"]] as const;
const SCOPES = [["this", "This occurrence only"], ["following", "This and following"], ["all", "All occurrences"]] as const;
type Scope = (typeof SCOPES)[number][0];

function errorText(e: unknown, fallback: string) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) {
    const d = detail as { detail: string; conflicts?: { wanted_start: string; conflicts_with: string }[] };
    return d.conflicts?.length
      ? `${d.detail} ${d.conflicts.map((c) => `${new Date(c.wanted_start).toLocaleString()} clashes with "${c.conflicts_with}"`).join("; ")}`
      : d.detail;
  }
  if (Array.isArray(detail)) return detail.map((x) => (x as { msg?: string }).msg).join("; ");
  return fallback;
}

const INVITE: Record<string, string> = {
  SENT: "Invitation e-mailed once from your mailbox.", ALREADY_SENT: "Invitation already sent for this version.",
  NO_MAILBOX: "Saved. Connect your mailbox (Communication > Email) so invitations can be sent.", NO_ATTENDEES: "Saved.",
  NOT_REQUESTED: "Saved.", ALREADY_CANCELLED: "Already cancelled.",
};
const say = (m: Record<string, string> | string | undefined) => {
  const v = typeof m === "string" ? m : Object.values(m ?? {})[0] ?? "";
  return INVITE[v] ?? v;
};

function buildRule(f: { freq: string; interval: number; days: string[]; ends: string; count: number; until: string }) {
  const parts = [`FREQ=${f.freq}`];
  if (f.interval > 1) parts.push(`INTERVAL=${f.interval}`);
  if (f.freq === "WEEKLY" && f.days.length) parts.push(`BYDAY=${f.days.join(",")}`);
  if (f.ends === "count") parts.push(`COUNT=${f.count}`);
  if (f.ends === "until" && f.until) parts.push(`UNTIL=${f.until.replaceAll("-", "")}`);
  return parts.join(";");
}

const BLANK = { title: "", start: "", time_zone: "Africa/Nairobi", duration: "60", freq: "WEEKLY", interval: 1, days: ["MO"], ends: "count", count: 8, until: "", attendees: "", agenda: "" };

export function RecurringSeriesPanel() {
  const [series, setSeries] = useState<Series[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ ...BLANK });
  const [detail, setDetail] = useState<Detail | null>(null);
  const [edit, setEdit] = useState<{ mode: "edit" | "cancel"; scope: Scope; date: string; title: string; start: string; duration: string } | null>(null);
  const [rsvp, setRsvp] = useState({ email: "", response: "accepted", date: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [fb, setFb] = useState<{ start: string; end: string }[] | null>(null);

  const load = useCallback(async () => {
    try { setSeries((await apiClient.get<Series[]>("/api/v1/meeting-series")).data); } catch { setSeries([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const show = async (id: string) => {
    try { setDetail((await apiClient.get<Detail>(`/api/v1/meeting-series/${id}`)).data); setEdit(null); }
    catch (e) { setMsg({ ok: false, text: errorText(e, "Could not open the series") }); }
  };

  const run = async (fn: () => Promise<string>, then?: () => Promise<void>) => {
    setBusy(true); setMsg(null);
    try { setMsg({ ok: true, text: await fn() }); await load(); if (then) await then(); }
    catch (e) { setMsg({ ok: false, text: errorText(e, "Request failed") }); }
    finally { setBusy(false); }
  };

  const create = () => run(async () => {
    if (!form.title || !form.start) throw new Error("x");
    const r = await apiClient.post<{ id: string; occurrences: number; invites: string; calendar: string }>("/api/v1/meeting-series", {
      title: form.title, start: form.start, time_zone: form.time_zone, duration_minutes: parseInt(form.duration) || 60,
      rrule: buildRule(form), agenda: form.agenda || null,
      attendees: form.attendees.split(",").map((x) => x.trim()).filter(Boolean).map((email) => ({ email })),
    });
    setOpen(false); setForm({ ...BLANK });
    return `Created ${r.data.occurrences} occurrences. ${say(r.data.invites)} Calendar: ${r.data.calendar === "SYNCED" ? "one recurring event written" : r.data.calendar === "NO_CALENDAR" ? "no calendar connected" : r.data.calendar}.`;
  });

  const applyEdit = () => detail && edit && run(async () => {
    const q = { scope: edit.scope, occurrence_date: edit.scope === "all" ? undefined : edit.date };
    if (edit.mode === "cancel") {
      const r = await apiClient.delete<{ invites: Record<string, string> | string }>(`/api/v1/meeting-series/${detail.id}`, {
        params: { scope: edit.scope, occurrence_date: q.occurrence_date },
      });
      return `Cancelled. ${say(r.data.invites as Record<string, string>)}`;
    }
    const body: Record<string, unknown> = { ...q };
    if (edit.title) body.title = edit.title;
    if (edit.start) body.start = edit.start;
    if (edit.duration) body.duration_minutes = parseInt(edit.duration);
    const r = await apiClient.patch<{ invites: Record<string, string> }>(`/api/v1/meeting-series/${detail.id}`, body);
    return `Saved. ${say(r.data.invites)}`;
  }, async () => { if (detail) await show(detail.id); });

  const sendRsvp = () => detail && run(async () => {
    await apiClient.post(`/api/v1/meeting-series/${detail.id}/rsvp`, { email: rsvp.email, response: rsvp.response, occurrence_date: rsvp.date || null });
    return `Recorded ${rsvp.response} for ${rsvp.email}.`;
  }, async () => { await show(detail.id); });

  const freeBusy = () => run(async () => {
    const from = new Date(); const to = new Date(Date.now() + 14 * 864e5);
    const r = await apiClient.get<{ busy: { start: string; end: string }[]; note?: string; provider?: string }>("/api/v1/meeting-series/free-busy", {
      params: { start: from.toISOString(), end: to.toISOString() } });
    setFb(r.data.busy);
    return `Next 14 days: ${r.data.busy.length} busy block(s)${r.data.provider ? ` (ERP + ${r.data.provider} calendar)` : " (ERP only: no calendar connected)"}.${r.data.note ? " " + r.data.note : ""}`;
  });

  const scopeFields = (mode: "edit" | "cancel", o: Occurrence) =>
    setEdit({ mode, scope: "this", date: o.date, title: "", start: "", duration: "" });

  return (
    <div className="border rounded-lg bg-white p-3 space-y-3" data-testid="recurring-series-panel">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <div className="text-sm font-semibold text-gray-800">Recurring meetings</div>
          <p className="text-xs text-gray-500">Repeat rule and time zone, so every occurrence keeps its local time across clock changes.</p>
        </div>
        <div className="flex gap-2">
          <button className="rounded border px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50" disabled={busy} onClick={freeBusy}>My free/busy (14 days)</button>
          <button className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700" onClick={() => setOpen((v) => !v)}>
            {open ? "Close" : "+ Recurring meeting"}
          </button>
        </div>
      </div>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`text-xs rounded px-2 py-1 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      {fb && (
        <div className="text-xs text-gray-700 border rounded p-2 max-h-32 overflow-auto">
          {fb.length ? fb.map((b, i) => <div key={i}>{new Date(b.start).toLocaleString()} to {new Date(b.end).toLocaleTimeString()}</div>) : "Nothing busy."}
        </div>
      )}

      {open && (
        <div className="border rounded p-3 space-y-2 text-sm">
          <div className="grid sm:grid-cols-2 gap-2">
            <label className="text-xs">Title<input className="w-full border rounded px-2 py-1" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="POVU AllClean 1 L range review" /></label>
            <label className="text-xs">First occurrence (local time)<input type="datetime-local" className="w-full border rounded px-2 py-1" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} /></label>
            <label className="text-xs">Time zone<select className="w-full border rounded px-2 py-1" value={form.time_zone} onChange={(e) => setForm({ ...form, time_zone: e.target.value })}>{ZONES.map((z) => <option key={z}>{z}</option>)}</select></label>
            <label className="text-xs">Duration (minutes)<input type="number" min={5} max={480} className="w-full border rounded px-2 py-1" value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} /></label>
            <label className="text-xs">Repeats<select className="w-full border rounded px-2 py-1" value={form.freq} onChange={(e) => setForm({ ...form, freq: e.target.value })}>
              <option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="MONTHLY">Monthly (same day)</option><option value="YEARLY">Yearly</option></select></label>
            <label className="text-xs">Every N<input type="number" min={1} max={99} className="w-full border rounded px-2 py-1" value={form.interval} onChange={(e) => setForm({ ...form, interval: parseInt(e.target.value) || 1 })} /></label>
          </div>
          {form.freq === "WEEKLY" && (
            <div className="flex gap-2 flex-wrap text-xs">{DAYS.map(([c, n]) => (
              <label key={c} className="flex items-center gap-1"><input type="checkbox" checked={form.days.includes(c)}
                onChange={(e) => setForm({ ...form, days: e.target.checked ? [...form.days, c] : form.days.filter((d) => d !== c) })} />{n}</label>))}</div>
          )}
          <div className="flex gap-3 items-center flex-wrap text-xs">
            <label>Ends <select className="border rounded px-2 py-1" value={form.ends} onChange={(e) => setForm({ ...form, ends: e.target.value })}>
              <option value="count">after N occurrences</option><option value="until">on a date</option><option value="never">never (next 12 months created)</option></select></label>
            {form.ends === "count" && <input type="number" min={1} max={400} className="border rounded px-2 py-1 w-24" value={form.count} onChange={(e) => setForm({ ...form, count: parseInt(e.target.value) || 1 })} />}
            {form.ends === "until" && <input type="date" className="border rounded px-2 py-1" value={form.until} onChange={(e) => setForm({ ...form, until: e.target.value })} />}
            <code className="text-gray-500">{buildRule(form)}</code>
          </div>
          <label className="text-xs block">Invitees (comma separated e-mails)<input className="w-full border rounded px-2 py-1" value={form.attendees} onChange={(e) => setForm({ ...form, attendees: e.target.value })} placeholder="buyer@example.com" /></label>
          <button className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" disabled={busy || !form.title || !form.start} onClick={create}>Create series</button>
          {(!form.title || !form.start) && <span className="text-xs text-gray-500 ml-2">Title and first occurrence are required.</span>}
        </div>
      )}

      <div className="divide-y text-xs">
        {series.length === 0 && <div className="py-2 text-gray-500">No recurring meetings yet.</div>}
        {series.map((s) => (
          <div key={s.id} className="py-2 flex items-center justify-between gap-2 flex-wrap">
            <div><span className="font-medium text-gray-900">{s.title}</span> <span className={`px-1.5 py-0.5 rounded ${s.status === "ACTIVE" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"}`}>{s.status}</span>
              <div className="text-gray-500">{s.rrule} · {s.time_zone} · {s.duration_minutes} min · {s.attendees.length} invitee(s)</div></div>
            <button className="text-indigo-600 hover:underline" onClick={() => show(s.id)}>{detail?.id === s.id ? "Refresh" : "Open"}</button>
          </div>
        ))}
      </div>

      {detail && (
        <div className="border rounded p-3 space-y-2 text-xs">
          <div className="flex justify-between"><div className="font-semibold text-sm">{detail.title}</div><button className="text-gray-500 hover:underline" onClick={() => { setDetail(null); setEdit(null); }}>Close</button></div>
          <div className="max-h-56 overflow-auto border rounded">
            {detail.occurrences.map((o) => (
              <div key={o.date} className="flex items-center justify-between gap-2 px-2 py-1 border-b last:border-0">
                <div className={o.status === "CANCELLED" ? "line-through text-gray-400" : ""}>
                  {new Date(o.local_start).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} {o.is_exception && <span className="text-amber-700">(changed)</span>}
                  <span className="text-gray-500"> · {o.title}</span>
                  {o.attendees.map((a) => a.response && <span key={a.email} className="ml-1 text-gray-500">[{a.email.split("@")[0]}: {a.response}]</span>)}
                </div>
                {detail.can_change && o.status === "SCHEDULED" && detail.status === "ACTIVE" && (
                  <span className="flex gap-2 shrink-0">
                    <button className="text-indigo-600 hover:underline" onClick={() => scopeFields("edit", o)}>Edit</button>
                    <button className="text-red-600 hover:underline" onClick={() => scopeFields("cancel", o)}>Cancel</button>
                  </span>)}
              </div>))}
          </div>
          {edit && (
            <div className="border rounded p-2 space-y-2 bg-gray-50" role="dialog" aria-label="Which events to change">
              <div className="font-medium">{edit.mode === "edit" ? "Edit" : "Cancel"} {edit.date}: which occurrences?</div>
              {SCOPES.map(([v, l]) => (
                <label key={v} className="flex items-center gap-2"><input type="radio" name="scope" checked={edit.scope === v} onChange={() => setEdit({ ...edit, scope: v })} />{l}</label>))}
              {edit.mode === "edit" && (
                <div className="grid sm:grid-cols-3 gap-2">
                  <input className="border rounded px-2 py-1" placeholder="New title" value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} />
                  <input type="datetime-local" className="border rounded px-2 py-1" title={edit.scope === "this" ? "New date and time" : "New time of day (date part ignored)"} value={edit.start} onChange={(e) => setEdit({ ...edit, start: e.target.value })} />
                  <input type="number" className="border rounded px-2 py-1" placeholder="Duration min" value={edit.duration} onChange={(e) => setEdit({ ...edit, duration: e.target.value })} />
                </div>)}
              <div className="flex gap-2">
                <button className={`rounded px-3 py-1 text-white disabled:opacity-50 ${edit.mode === "cancel" ? "bg-red-600" : "bg-blue-600"}`} disabled={busy || (edit.mode === "edit" && !edit.title && !edit.start && !edit.duration)} onClick={applyEdit}>
                  {edit.mode === "cancel" ? "Cancel selected" : "Save changes"}</button>
                <button className="rounded border px-3 py-1" onClick={() => setEdit(null)}>Keep as is</button>
                {edit.mode === "edit" && !edit.title && !edit.start && !edit.duration && <span className="text-gray-500 self-center">Change at least one field.</span>}
              </div>
            </div>)}
          {detail.can_change && detail.attendees.length > 0 && detail.status === "ACTIVE" && (
            <div className="flex gap-2 flex-wrap items-center">
              <span className="text-gray-600">Record an answer:</span>
              <select className="border rounded px-2 py-1" value={rsvp.email} onChange={(e) => setRsvp({ ...rsvp, email: e.target.value })}>
                <option value="">Invitee</option>{detail.attendees.map((a) => <option key={a.email}>{a.email}</option>)}</select>
              <select className="border rounded px-2 py-1" value={rsvp.response} onChange={(e) => setRsvp({ ...rsvp, response: e.target.value })}>
                <option value="accepted">Accepted</option><option value="declined">Declined</option><option value="tentative">Tentative</option></select>
              <select className="border rounded px-2 py-1" value={rsvp.date} onChange={(e) => setRsvp({ ...rsvp, date: e.target.value })}>
                <option value="">All future occurrences</option>{detail.occurrences.filter((o) => o.status === "SCHEDULED").map((o) => <option key={o.date} value={o.date}>{o.date}</option>)}</select>
              <button className="rounded border px-2 py-1 disabled:opacity-50" disabled={busy || !rsvp.email} onClick={sendRsvp}>Record</button>
            </div>)}
          {detail.can_change && detail.status === "ACTIVE" && (
            <button className="text-red-600 hover:underline" onClick={() => setEdit({ mode: "cancel", scope: "all", date: detail.occurrences.find((o) => o.status === "SCHEDULED")?.date ?? "", title: "", start: "", duration: "" })}>Cancel the whole series...</button>)}
        </div>
      )}
    </div>
  );
}
