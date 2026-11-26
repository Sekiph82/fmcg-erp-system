"use client";
// M43.S01.T008/T009: provider status, my answering phone, power dialer, IVR menus, call transcripts.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Caps { provider: string | null; configured: boolean; power_dialer: boolean; ivr: boolean; recording: boolean;
  voicemail_drop: boolean; voicemail_drop_reason: string; transcription: boolean; transcription_engine: string }
interface Item { phone: string; label: string | null; state: string; call_id: string | null }
interface Dialer { id: string; name: string; status: string; items: Item[] }
interface Ivr { id: string; name: string; phone_number: string; greeting_text: string; record_calls: boolean;
  options: { digit: string; label: string; user_ids: string[]; phone_numbers: string[] }[] }

const detail = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : fb;
};

export function VoicePanel() {
  const [caps, setCaps] = useState<Caps | null>(null);
  const [phone, setPhone] = useState({ phone_number: "", available: true });
  const [dialers, setDialers] = useState<Dialer[]>([]);
  const [ivrs, setIvrs] = useState<Ivr[]>([]);
  const [list, setList] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    apiClient.get("/api/v1/calls/capabilities").then((r) => setCaps(r.data)).catch(() => setCaps(null));
    apiClient.get("/api/v1/calls/me/phone").then((r) => setPhone({ phone_number: r.data.phone_number ?? "", available: r.data.available }));
    apiClient.get("/api/v1/calls/dialer").then((r) => setDialers(r.data)).catch(() => setDialers([]));
    apiClient.get("/api/v1/calls/ivr").then((r) => setIvrs(r.data)).catch(() => setIvrs([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function run(fn: () => Promise<unknown>, ok?: string) {
    try { await fn(); if (ok) setMsg(ok); load(); } catch (e) { setMsg(detail(e, "That did not work.")); }
  }
  async function next(d: Dialer) {
    try {
      const r = (await apiClient.post(`/api/v1/calls/dialer/${d.id}/next`)).data;
      if (r.call?.dial) window.location.href = r.call.dial;
      else if (r.call) setMsg(tx("Your phone will ring; answer it to be connected."));
      else setMsg(tx("The list is finished."));
      load();
    } catch (e) { setMsg(detail(e, "Could not start the next call.")); }
  }
  const box = "border rounded-lg bg-white p-3 space-y-2";
  return (
    <div className="grid lg:grid-cols-3 gap-3">
      <div className={box}>
        <div className="text-sm font-semibold">{tx("Calling")}</div>
        {caps && (
          <p className="text-xs text-gray-600">
            {caps.configured ? tx("Calls go through {provider}: your phone rings first, then the customer.", { provider: caps.provider }) :
              tx("No voice provider is set up: calls use your phone's dialler and you record the outcome.")}
            {" "}{tx("Transcription:")} {caps.transcription ? caps.transcription_engine : tx("off")}.
            {!caps.voicemail_drop && <> {tx("Voicemail drop: not available (")}{caps.voicemail_drop_reason})</>}
          </p>
        )}
        <form className="flex flex-wrap gap-2 items-end" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.put("/api/v1/calls/me/phone", phone), "Saved."); }}>
          <label className="text-xs">{tx("My answering phone")}<input className="border rounded px-2 py-1 text-sm block" value={phone.phone_number}
            placeholder="+2547…" onChange={(e) => setPhone({ ...phone, phone_number: e.target.value })} /></label>
          <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={phone.available}
            onChange={(e) => setPhone({ ...phone, available: e.target.checked })} /> {tx("Available for team calls")}</label>
          <button className="text-xs bg-indigo-600 text-white rounded px-2 py-1">{tx("Save")}</button>
        </form>
      </div>
      <div className={box}>
        <div className="text-sm font-semibold">{tx("Power dialer")}</div>
        <form className="space-y-1" onSubmit={(e) => {
          e.preventDefault();
          const items = list.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => { const [p, ...rest] = l.split(","); return { phone: p.trim(), label: rest.join(",").trim() || null }; });
          run(() => apiClient.post("/api/v1/calls/dialer", { name: `Call list ${new Date().toLocaleDateString()}`, items }), "Call list created.");
          setList("");
        }}>
          <textarea aria-label={tx("Numbers, one per line")} rows={3} className="border rounded w-full text-xs p-1" placeholder={tx("+254700000001, POVU Synthetic Outlet\n+254700000002")} value={list} onChange={(e) => setList(e.target.value)} />
          <button className="text-xs border rounded px-2 py-1" disabled={!list.trim()}>{tx("Create call list")}</button>
        </form>
        {dialers.filter((d) => d.status !== "DONE").map((d) => {
          const calling = d.items.find((i) => i.state === "CALLING");
          const left = d.items.filter((i) => i.state === "PENDING").length;
          return (
            <div key={d.id} className="text-xs border rounded p-2 space-y-1">
              <div className="flex justify-between"><span>{d.name}</span><span>{left} {tx("left ·")} {d.status}</span></div>
              {calling ? (
                <div className="flex flex-wrap gap-1 items-center">{tx("On call:")} {calling.label || calling.phone}
                  {["ANSWERED", "NO_ANSWER", "BUSY", "VOICEMAIL", "FAILED"].map((o) => (
                    <button key={o} className="border rounded px-1" onClick={() => run(() => apiClient.post(`/api/v1/calls/dialer/${d.id}/outcome`, null, { params: { outcome: o } }))}>{o.replace("_", " ")}</button>
                  ))}
                </div>
              ) : (
                <div className="flex gap-2">
                  <button className="bg-green-600 text-white rounded px-2 py-0.5" disabled={d.status !== "ACTIVE" || !left} onClick={() => next(d)}>{tx("Call next")}</button>
                  <button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/calls/dialer/${d.id}/pause`))}>{d.status === "PAUSED" ? tx("Resume") : tx("Pause")}</button>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className={box}>
        <div className="text-sm font-semibold">{tx("Phone menus (IVR)")}</div>
        {!caps?.ivr && <p className="text-xs text-gray-500">{tx("Active once a voice provider and number are set up; menus can be prepared now.")}</p>}
        {ivrs.map((m) => (
          <div key={m.id} className="text-xs border rounded p-2">
            <div className="font-medium">{m.name} · {m.phone_number}{m.record_calls && tx(" · recorded with consent")}</div>
            <div className="text-gray-600">{m.greeting_text}</div>
            <ul className="list-disc ml-4">{m.options.map((o) => <li key={o.digit}>{o.digit}: {o.label} ({o.user_ids.length + o.phone_numbers.length} {tx("target")}{o.user_ids.length + o.phone_numbers.length === 1 ? "" : tx("s")})</li>)}</ul>
          </div>
        ))}
        <IvrForm onSaved={() => { setMsg(tx("Menu saved.")); load(); }} onError={(t) => setMsg(t)} />
      </div>
      {msg && <p role="status" className="text-xs text-gray-700 lg:col-span-3">{msg}</p>}
    </div>
  );
}

function IvrForm({ onSaved, onError }: { onSaved: () => void; onError: (t: string) => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", phone_number: "", greeting_text: "Welcome to POVU.", options: "1, Sales, +254700000001\n2, Support, +254700000002", record_calls: false, consent_text: "" });
  if (!open) return <button className="text-xs text-indigo-600 underline" onClick={() => setOpen(true)}>{tx("+ Menu")}</button>;
  async function save(e: React.FormEvent) {
    e.preventDefault();
    const options = f.options.split("\n").map((l) => l.split(",").map((x) => x.trim())).filter((p) => p[0])
      .map(([digit, label, ...nums]) => ({ digit, label, user_ids: [], phone_numbers: nums.filter(Boolean) }));
    try { await apiClient.post("/api/v1/calls/ivr", { ...f, options, consent_text: f.consent_text || null }); setOpen(false); onSaved(); }
    catch (x) { onError(detail(x, "Check the menu (only CRM managers can change it).")); }
  }
  const i = "border rounded px-2 py-1 text-xs w-full";
  return (
    <form onSubmit={save} className="space-y-1">
      <input className={i} required placeholder={tx("Name")} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
      <input className={i} required placeholder={tx("Provider number +254…")} value={f.phone_number} onChange={(e) => setF({ ...f, phone_number: e.target.value })} />
      <input className={i} required placeholder={tx("Greeting")} value={f.greeting_text} onChange={(e) => setF({ ...f, greeting_text: e.target.value })} />
      <textarea className={i} rows={3} aria-label={tx("Options: digit, label, numbers")} value={f.options} onChange={(e) => setF({ ...f, options: e.target.value })} />
      <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={f.record_calls} onChange={(e) => setF({ ...f, record_calls: e.target.checked })} /> {tx("Record calls")}</label>
      {f.record_calls && <input className={i} required placeholder={tx("Consent announcement")} value={f.consent_text} onChange={(e) => setF({ ...f, consent_text: e.target.value })} />}
      <div className="flex gap-2"><button className="text-xs bg-indigo-600 text-white rounded px-2 py-1">{tx("Save menu")}</button>
        <button type="button" className="text-xs" onClick={() => setOpen(false)}>{tx("Close")}</button></div>
    </form>
  );
}

export function CallTranscript({ callId }: { callId: string }) {
  const [t, setT] = useState<{ status: string | null; language?: string; segments: { start: number | null; speaker: string | null; text: string }[];
    recap: { next_steps: string[]; questions: string[]; objections: string[] } | null } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => { apiClient.get(`/api/v1/calls/logs/${callId}/transcript`).then((r) => setT(r.data)).catch(() => setT(null)); }, [callId]);
  useEffect(() => { load(); }, [load]);
  const act = async (path: string, ok: string) => {
    try { await apiClient.post(`/api/v1/calls/logs/${callId}/${path}`); setMsg(ok); load(); } catch (e) { setMsg(detail(e, "Not possible.")); }
  };
  return (
    <div className="text-xs space-y-1">
      <div className="flex gap-2">
        <button className="underline" onClick={() => act("transcribe", "Transcription queued.")}>{tx("Transcribe")}</button>
        <button className="underline text-red-600" onClick={() => { if (confirm(tx("Customer withdrew consent? The recording, transcript and coaching notes are deleted."))) act("withdraw-consent", "Recording and transcript deleted."); }}>{tx("Consent withdrawn")}</button>
        {t?.status && <span className="text-gray-500">{tx("Transcript:")} {t.status}</span>}
      </div>
      {msg && <p role="status">{msg}</p>}
      {t?.segments.map((s, i) => <p key={i}>{s.start !== null && <span className="text-gray-400">{s.start.toFixed(0)}{tx("s")} </span>}{s.speaker && <b>{s.speaker}: </b>}{s.text}</p>)}
      {t?.recap && (t.recap.next_steps.length + t.recap.questions.length > 0) && (
        <div className="border-t pt-1"><b>{tx("Recap (quoted)")}</b>
          {t.recap.next_steps.map((q, i) => <p key={`n${i}`}>{tx("Next step: “")}{q}”</p>)}
          {t.recap.questions.map((q, i) => <p key={`q${i}`}>{tx("Question: “")}{q}”</p>)}
        </div>
      )}
    </div>
  );
}

// M43.S01.T017 coaching playlists: managers clip consented transcript segments; agents see only their own calls' clips.
export function CoachingPanel() {
  const [lists, setLists] = useState<{ id: string; name: string; clips: { id: string; call_id: string; start_s: number; end_s: number; note: string | null;
    segments: { start: number; speaker: string | null; text: string }[] }[] }[]>([]);
  const [name, setName] = useState("");
  const [clip, setClip] = useState({ playlist_id: "", call_id: "", start_s: 0, end_s: 30, note: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => { apiClient.get("/api/v1/calls/playlists").then((r) => setLists(r.data)).catch(() => setLists([])); }, []);
  useEffect(() => { load(); }, [load]);
  const run = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); setMsg(ok); load(); } catch (e) { setMsg(detail(e, "Managers only.")); } };
  return (
    <div className="border rounded-lg bg-white p-3 space-y-2 text-xs">
      <div className="text-sm font-semibold">{tx("Coaching playlists")}</div>
      {lists.length === 0 && <p className="text-gray-500">{tx("No coaching clips you can see.")}</p>}
      {lists.map((p) => (
        <details key={p.id} className="border rounded p-2"><summary className="cursor-pointer font-medium">{p.name} ({p.clips.length})</summary>
          {p.clips.map((c) => (
            <div key={c.id} className="border-t pt-1 mt-1">
              <div className="text-gray-500">{tx("Call")} {c.call_id.slice(0, 8)} · {c.start_s}{tx("s–")}{c.end_s}{tx("s")}{c.note ? ` · ${c.note}` : ""}
                <button className="ml-2 text-red-600" onClick={() => run(() => apiClient.delete(`/api/v1/calls/playlists/${p.id}/clips/${c.id}`), "Clip removed.")}>×</button></div>
              {c.segments.map((s, i) => <p key={i}>{s.speaker && <b>{s.speaker}: </b>}{s.text}</p>)}
            </div>))}
        </details>))}
      <form className="flex gap-1" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post("/api/v1/calls/playlists", { name }), "Playlist created."); setName(""); }}>
        <input required className="border rounded px-2 py-1 flex-1" placeholder={tx("New playlist (managers)")} value={name} onChange={(e) => setName(e.target.value)} />
        <button className="border rounded px-2">{tx("Create")}</button></form>
      <form className="grid grid-cols-2 gap-1" onSubmit={(e) => { e.preventDefault();
        run(() => apiClient.post(`/api/v1/calls/playlists/${clip.playlist_id}/clips`, { call_id: clip.call_id, start_s: clip.start_s, end_s: clip.end_s, note: clip.note || null }), "Clip added."); }}>
        <select required className="border rounded px-1 col-span-2" value={clip.playlist_id} onChange={(e) => setClip({ ...clip, playlist_id: e.target.value })}>
          <option value="">{tx("Playlist…")}</option>{lists.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
        <input required className="border rounded px-1 col-span-2" placeholder={tx("Call id (consented, transcribed)")} value={clip.call_id} onChange={(e) => setClip({ ...clip, call_id: e.target.value })} />
        <label>{tx("From (s)")}<input type="number" min={0} className="border rounded px-1 w-full" value={clip.start_s} onChange={(e) => setClip({ ...clip, start_s: +e.target.value })} /></label>
        <label>{tx("To (s)")}<input type="number" min={1} className="border rounded px-1 w-full" value={clip.end_s} onChange={(e) => setClip({ ...clip, end_s: +e.target.value })} /></label>
        <input className="border rounded px-1 col-span-2" placeholder={tx("Coaching note")} value={clip.note} onChange={(e) => setClip({ ...clip, note: e.target.value })} />
        <button className="border rounded px-2 py-1 col-span-2">{tx("Add clip")}</button></form>
      {msg && <p role="status">{msg}</p>}
    </div>
  );
}
