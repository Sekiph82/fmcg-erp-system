"use client";
// M43.S01.T005: staff side of public booking pages (own page; team round-robin pages for CRM managers).
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";

interface BookingPage {
  id: string; slug: string; title: string; description: string | null; duration_minutes: number; buffer_before: number;
  buffer_after: number; min_notice_hours: number; max_days_ahead: number; time_zone: string; open_time: string;
  close_time: string; weekdays: number[]; host_ids: string[]; routing: string; platform: string;
  consent_text: string | null; is_active: boolean; public_url: string;
}
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const BLANK = { slug: "", title: "", description: "", duration_minutes: 30, buffer_before: 0, buffer_after: 10,
  min_notice_hours: 4, max_days_ahead: 30, time_zone: "Africa/Nairobi", open_time: "08:00", close_time: "17:00",
  weekdays: [0, 1, 2, 3, 4], host_ids: [] as string[], routing: "round_robin", platform: "jitsi",
  consent_text: "I agree that POVU stores my name and e-mail to arrange this meeting.", is_active: true };

export function BookingPagesPanel() {
  const qc = useQueryClient();
  const [form, setForm] = useState<typeof BLANK | null>(null);
  const [editId, setEditId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const { data: pages = [] } = useQuery<BookingPage[]>({
    queryKey: ["booking-pages"], queryFn: async () => (await apiClient.get("/api/v1/booking-pages")).data,
  });
  const save = useMutation({
    mutationFn: async (body: typeof BLANK) => editId
      ? apiClient.put(`/api/v1/booking-pages/${editId}`, body) : apiClient.post("/api/v1/booking-pages", body),
    onSuccess: () => { setForm(null); setEditId(null); setErr(null); qc.invalidateQueries({ queryKey: ["booking-pages"] }); },
    onError: (e: unknown) => {
      const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setErr(typeof d === "string" ? d : "Check the fields.");
    },
  });
  const f = "border rounded px-2 py-1 text-sm w-full";
  const set = (k: keyof typeof BLANK, v: unknown) => setForm((x) => (x ? { ...x, [k]: v } : x));

  return (
    <div className="border rounded-lg bg-white p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-800">Booking pages</span>
        <button className="text-xs text-indigo-600 hover:underline" onClick={() => { setForm({ ...BLANK }); setEditId(null); }}>+ New page</button>
      </div>
      {pages.length === 0 && !form && <p className="text-xs text-gray-500">Share a link where customers pick a free time themselves.</p>}
      {pages.map((p) => (
        <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 text-xs border rounded p-2">
          <div>
            <div className="font-medium">{p.title} {!p.is_active && <span className="text-gray-500">(off)</span>}</div>
            <a className="text-indigo-600 break-all" href={p.public_url} target="_blank" rel="noreferrer">{p.public_url}</a>
            <div className="text-gray-500">{p.duration_minutes} min · {p.host_ids.length > 1 ? `${p.host_ids.length} hosts, ${p.routing.replace("_", " ")}` : "you"}</div>
          </div>
          <div className="flex gap-2">
            <button className="text-gray-700 hover:underline" onClick={() => navigator.clipboard?.writeText(p.public_url)}>Copy link</button>
            <button className="text-indigo-600 hover:underline" onClick={() => { setEditId(p.id); setForm({ ...BLANK, ...p, description: p.description ?? "", consent_text: p.consent_text ?? "" }); }}>Edit</button>
          </div>
        </div>
      ))}
      {form && (
        <form className="grid sm:grid-cols-2 gap-2 border-t pt-2" onSubmit={(e) => { e.preventDefault(); save.mutate(form); }}>
          <label className="text-xs">Title<input className={f} required value={form.title} onChange={(e) => set("title", e.target.value)} /></label>
          <label className="text-xs">Address (/book/…)<input className={f} required pattern="[a-z0-9][a-z0-9-]*" value={form.slug} onChange={(e) => set("slug", e.target.value.toLowerCase())} /></label>
          <label className="text-xs sm:col-span-2">Description<textarea className={f} value={form.description ?? ""} onChange={(e) => set("description", e.target.value)} /></label>
          <label className="text-xs">Minutes<input type="number" min={5} max={480} className={f} value={form.duration_minutes} onChange={(e) => set("duration_minutes", +e.target.value)} /></label>
          <label className="text-xs">Time zone<input className={f} value={form.time_zone} onChange={(e) => set("time_zone", e.target.value)} /></label>
          <label className="text-xs">Opens<input type="time" className={f} value={form.open_time} onChange={(e) => set("open_time", e.target.value)} /></label>
          <label className="text-xs">Closes<input type="time" className={f} value={form.close_time} onChange={(e) => set("close_time", e.target.value)} /></label>
          <label className="text-xs">Buffer after (min)<input type="number" min={0} max={240} className={f} value={form.buffer_after} onChange={(e) => set("buffer_after", +e.target.value)} /></label>
          <label className="text-xs">Notice (hours)<input type="number" min={0} max={720} className={f} value={form.min_notice_hours} onChange={(e) => set("min_notice_hours", +e.target.value)} /></label>
          <fieldset className="text-xs sm:col-span-2 flex flex-wrap gap-2"><legend className="mb-1">Days</legend>
            {DAYS.map((d, i) => (
              <label key={d} className="flex items-center gap-1"><input type="checkbox" checked={form.weekdays.includes(i)}
                onChange={(e) => set("weekdays", e.target.checked ? [...form.weekdays, i] : form.weekdays.filter((x) => x !== i))} />{d}</label>
            ))}
          </fieldset>
          <div className="text-xs sm:col-span-2 space-y-1">
            <div>Hosts (none = only you; team pages need CRM manager rights)</div>
            <div className="flex flex-wrap gap-1">{form.host_ids.map((h) => (
              <span key={h} className="bg-gray-100 rounded px-2 py-0.5">{h.slice(0, 8)}…
                <button type="button" aria-label="Remove host" className="ml-1 text-red-600" onClick={() => set("host_ids", form.host_ids.filter((x) => x !== h))}>×</button></span>
            ))}</div>
            <EntityPicker kind="user" value="" placeholder="Add a host…"
                          onChange={(id) => { if (id && !form.host_ids.includes(String(id))) set("host_ids", [...form.host_ids, String(id)]); }} />
          </div>
          <label className="text-xs">Routing<select className={f} value={form.routing} onChange={(e) => set("routing", e.target.value)}>
            <option value="round_robin">Round robin</option><option value="first_available">First available</option></select></label>
          <label className="text-xs">Meeting link<select className={f} value={form.platform} onChange={(e) => set("platform", e.target.value)}>
            <option value="jitsi">Jitsi (automatic)</option><option value="google_meet">Google Meet (connected calendar)</option>
            <option value="teams">Teams (connected calendar)</option></select></label>
          <label className="text-xs sm:col-span-2">Consent statement<input className={f} value={form.consent_text ?? ""} onChange={(e) => set("consent_text", e.target.value)} /></label>
          <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} /> Page is live</label>
          {err && <p className="text-xs text-red-600 sm:col-span-2" role="alert">{err}</p>}
          <div className="flex gap-2 sm:col-span-2">
            <button className="bg-indigo-600 text-white rounded px-3 py-1 text-sm" disabled={save.isPending}>Save</button>
            <button type="button" className="text-sm text-gray-600" onClick={() => setForm(null)}>Close</button>
          </div>
        </form>
      )}
    </div>
  );
}
