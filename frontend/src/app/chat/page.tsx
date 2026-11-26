"use client";
// Public website chat (M36.S03.T005): embed with <iframe src="https://<app>/chat" width="360" height="560">.
// The chat token lives only in this tab's sessionStorage and is sent as a header, never in a URL.
import { useCallback, useEffect, useRef, useState } from "react";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

interface Msg { id: string; from: "visitor" | "bot" | "agent"; body: string; at: string }
const BASE = `${API_ORIGIN}/api/v1/public/chat`;
const KEY = "povu.chat";

function load(): { id: string; token: string } | null {
  try { return JSON.parse(sessionStorage.getItem(KEY) ?? "null"); } catch { return null; }
}

export default function WebsiteChat() {
  const { t } = useI18n();
  const [chat, setChat] = useState<{ id: string; token: string } | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [status, setStatus] = useState("BOT");
  const [form, setForm] = useState({ name: "", email: "", consent: false, website: "" });
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  const merge = (more: Msg[]) => setMsgs((m) => { const ids = new Set(m.map((x) => x.id)); return [...m, ...more.filter((x) => !ids.has(x.id))]; });
  const lastAt = useRef<string | null>(null);
  useEffect(() => { lastAt.current = msgs.length ? msgs[msgs.length - 1].at : null; }, [msgs]);
  const poll = useCallback(async (c: { id: string; token: string }) => {
    const after = lastAt.current ? `?after=${encodeURIComponent(lastAt.current)}` : "";   // only new messages
    const r = await fetch(`${BASE}/sessions/${c.id}/messages${after}`, { headers: { "X-Chat-Token": c.token } }).catch(() => null);
    if (r?.ok) { const j = await r.json(); merge(j.messages); setStatus(j.status); }
    else if (r && r.status === 404) { try { sessionStorage.removeItem(KEY); } catch { /* ignore */ } setChat(null); }
  }, []);

  useEffect(() => { const c = load(); if (c) { setChat(c); poll(c); } }, [poll]);
  useEffect(() => {
    if (!chat || status === "CLOSED") return;
    const t = setInterval(() => poll(chat), status === "WAITING" ? 4000 : 15000);
    return () => clearInterval(t);
  }, [chat, status, poll]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function start() {
    setError(null);
    const r = await fetch(`${BASE}/sessions`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: form.name || null, email: form.email || null, consent: form.consent, page_url: document.referrer || null, website: form.website || null }) }).catch(() => null);
    if (!r || !r.ok) { setError(r?.status === 429 ? t("public.chat.tooManyChats") : t("public.chat.unavailable")); return; }
    const j = await r.json();
    const c = { id: j.session_id, token: j.token };
    try { sessionStorage.setItem(KEY, JSON.stringify(c)); } catch { /* chat still works for this page */ }
    setChat(c); setMsgs(j.messages);
  }

  async function send() {
    if (!chat || !text.trim()) return;
    const body = text.trim(); setText(""); setError(null);
    const r = await fetch(`${BASE}/sessions/${chat.id}/messages`, { method: "POST", headers: { "Content-Type": "application/json", "X-Chat-Token": chat.token },
      body: JSON.stringify({ body }) }).catch(() => null);
    if (!r || !r.ok) { setError(r?.status === 429 ? t("public.chat.slowDown") : r?.status === 409 ? t("public.chat.closedError") : t("public.chat.notSent")); setText(body); return; }
    const j = await r.json(); merge(j.messages); setStatus(j.status);
  }

  const bubble = (m: Msg) => m.from === "visitor" ? "bg-indigo-600 text-white ml-auto" : m.from === "agent" ? "bg-emerald-50 border border-emerald-200" : "bg-gray-100";
  return (
    <main className="min-h-screen bg-white text-gray-900 flex flex-col max-w-md mx-auto">
      <header className="p-3 border-b flex flex-wrap items-start justify-between gap-2"><div className="min-w-0"><p className="font-semibold break-words">{t("public.chat.title")}</p><p className="text-xs text-gray-500 break-words">{t("public.chat.subtitle")}</p></div><LanguageSwitcher /></header>
      {!chat ? (
        <form className="p-4 space-y-3" onSubmit={(e) => { e.preventDefault(); start(); }}>
          <input aria-label={t("public.chat.name")} placeholder={t("public.chat.namePlaceholder")} maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
          <input aria-label={t("public.chat.email")} type="email" placeholder={t("public.chat.emailPlaceholder")} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
          {/* honeypot: hidden from people */}
          <input tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
          {form.email && (
            <label className="flex gap-2 text-xs text-gray-600"><input type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} />
              <span className="min-w-0 break-words">{t("public.chat.consent")}</span></label>
          )}
          <button className="w-full py-2.5 rounded-lg bg-indigo-600 text-white text-sm">{t("public.chat.start")}</button>
          <p className="text-xs text-gray-400">{t("public.chat.retention")}</p>
        </form>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto p-3 space-y-2" aria-live="polite">
            {msgs.map((m) => <p key={m.id} className={`max-w-[85%] w-fit rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${bubble(m)}`}>{m.body}</p>)}
            {status === "WAITING" && <p className="text-xs text-gray-400 text-center">{t("public.chat.waiting")}</p>}
            {status === "CLOSED" && <p className="text-xs text-gray-400 text-center">{t("public.chat.ended")}</p>}
            <div ref={end} />
          </div>
          {error && <p role="alert" className="px-3 text-xs text-red-700">{error}</p>}
          {status !== "CLOSED" && (
            <form className="p-3 border-t flex gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
              <input aria-label={t("public.chat.message")} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("public.chat.messagePlaceholder")} className="flex-1 min-w-0 border rounded-lg px-3 py-2 text-sm" />
              <button className="px-4 rounded-lg bg-indigo-600 text-white text-sm">{t("common.send")}</button>
            </form>
          )}
        </>
      )}
    </main>
  );
}
