"use client";
// M36.S03.T003 quick capture on a phone: log a call / visit / note on a customer in a few taps.
// Offline: the note waits on this phone (per signed-in user) and is resent with the same id when the
// connection returns; the server stores it once, so a retry never creates a second note.
import { useCallback, useEffect, useRef, useState } from "react";
import { crmApi } from "@/lib/crm_pipeline";
import { useAuth } from "@/context/AuthContext";
import { tx } from "@/lib/i18n/core";

type Pending = { customerId: string; tries: number; body: { channel: string; summary: string; follow_up_date?: string; client_ref: string } };
const keyFor = (userId: string) => `povu.crm.pendingNotes.${userId}`;   // never sent as another user
const MAX_TRIES = 20;
const newRef = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`);
let flushing = false;   // one flush at a time per page

function readQueue(key: string): Pending[] {
  try { return JSON.parse(localStorage.getItem(key) ?? "[]"); } catch { return []; }
}
function writeQueue(key: string, q: Pending[]) {
  try { localStorage.setItem(key, JSON.stringify(q)); } catch { /* storage blocked: the note stays only in memory */ }
}
function update(key: string, fn: (q: Pending[]) => Pending[]) { writeQueue(key, fn(readQueue(key))); }

/** Keep the note for later on no answer, timeouts, rate limits, an expired session or server errors. */
function retryable(e: unknown): boolean {
  const status = (e as { response?: { status?: number } }).response?.status;
  return status === undefined || status === 401 || status === 408 || status === 429 || status >= 500;
}

export function QuickNote({ customerId, onSaved }: { customerId: string; onSaved?: () => void }) {
  const { user } = useAuth();
  const key = user ? keyFor(user.id) : null;
  const [channel, setChannel] = useState("visit");
  const [summary, setSummary] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(0);
  const [busy, setBusy] = useState(false);
  const saved = useRef(onSaved);
  useEffect(() => { saved.current = onSaved; }, [onSaved]);

  const flush = useCallback(async () => {
    if (!key || flushing) return;
    flushing = true;
    let sent = 0;
    try {
      for (const p of readQueue(key)) {
        try {
          await crmApi.addQuickNote(p.customerId, p.body);
          update(key, (q) => q.filter((x) => x.body.client_ref !== p.body.client_ref));
          sent++;
        } catch (e) {
          update(key, (q) => (retryable(e) && p.tries + 1 < MAX_TRIES
            ? q.map((x) => (x.body.client_ref === p.body.client_ref ? { ...x, tries: x.tries + 1 } : x))
            : q.filter((x) => x.body.client_ref !== p.body.client_ref)));   // refused for good (no access, invalid)
        }
      }
    } finally {
      flushing = false;
      setWaiting(readQueue(key).filter((p) => p.customerId === customerId).length);
      if (sent) saved.current?.();
    }
  }, [key, customerId]);

  useEffect(() => {
    flush();
    window.addEventListener("online", flush);
    return () => window.removeEventListener("online", flush);
  }, [flush]);

  async function save() {
    if (!key) return;
    const body = { channel, summary: summary.trim(), follow_up_date: followUp || undefined, client_ref: newRef() };
    setBusy(true); setMsg(null);
    try {
      await crmApi.addQuickNote(customerId, body);
      setSummary(""); setFollowUp(""); setMsg(tx("Saved.")); saved.current?.();
    } catch (e) {
      if (retryable(e)) {
        update(key, (q) => [...q, { customerId, tries: 0, body }]);
        setSummary(""); setFollowUp(""); setWaiting((n) => n + 1);
        setMsg(tx("Not sent yet: saved on this phone and will be sent automatically."));
      } else {
        const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
        setMsg(typeof d === "string" ? d : tx("The note could not be saved."));
      }
    } finally { setBusy(false); }
  }

  return (
    <section aria-label={tx("Quick note")} className="bg-white rounded-xl border p-3 space-y-2">
      <div className="grid grid-cols-4 gap-1">
        {[["visit", "Visit"], ["call", "Call"], ["message", "Message"], ["note", "Note"]].map(([k, v]) => (
          <button key={k} type="button" aria-pressed={channel === k} onClick={() => setChannel(k)}
            className={`py-2.5 rounded-lg text-sm border ${channel === k ? "bg-indigo-600 text-white border-indigo-600 ring-2 ring-indigo-400 font-semibold" : "opacity-80"}`}>{channel === k ? "✓ " : ""}{v}</button>
        ))}
      </div>
      <textarea aria-label={tx("What happened")} rows={3} maxLength={2000} placeholder={tx("What happened? e.g. shelf has 3 cartons left, wants 20 on Friday")}
        value={summary} onChange={(e) => setSummary(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" />
      <div className="flex flex-wrap gap-2 items-center">
        <label className="text-xs text-gray-500 flex items-center gap-1">{tx("Follow up")}
          <input type="date" value={followUp} onChange={(e) => setFollowUp(e.target.value)} className="border rounded-lg px-2 py-1.5 text-sm" />
        </label>
        <button type="button" disabled={busy || summary.trim().length < 2} onClick={save}
          className="ml-auto px-4 py-2.5 rounded-lg bg-indigo-600 text-white text-sm disabled:opacity-50">{tx("Save")}</button>
      </div>
      {msg && <p role="status" className="text-xs text-gray-600">{msg}</p>}
      {waiting > 0 && <p className="text-xs text-amber-700">{waiting} {tx("note(s) waiting for a connection.")}</p>}
    </section>
  );
}
