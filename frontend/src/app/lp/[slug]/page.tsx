"use client";
// Public landing page (M36.S05.T002): the server picks this browser's variant (always the same one) and the
// form goes through the lead-form rules (consent, spam protection).
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface LP { slug: string; variant: string; headline: string; body: string | null; cta_label: string; consent_text: string | null; require_consent: boolean }

function visitorId(): string {
  try {
    const k = "povu.lp.visitor"; let v = localStorage.getItem(k);
    if (!v) { v = (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}-x`).replace(/[^A-Za-z0-9-]/g, ""); localStorage.setItem(k, v); }
    return v;
  } catch { return `${Date.now()}-anon-${Math.random().toString(36).slice(2)}`; }
}

export default function LandingPage() {
  const { slug } = useParams<{ slug: string }>();
  const [lp, setLp] = useState<LP | null>(null);
  const [missing, setMissing] = useState(false);
  const [f, setF] = useState({ company_name: "", contact_person_name: "", contact_email: "", contact_phone: "", message: "", consent: false, website: "" });
  const [state, setState] = useState<"form" | "sent">("form");
  const [error, setError] = useState<string | null>(null);
  const [visitor] = useState(visitorId);
  const base = `${API_ORIGIN}/api/v1/public/lp/${encodeURIComponent(slug)}`;

  useEffect(() => {
    fetch(`${base}?visitor=${encodeURIComponent(visitor)}`).then(async (r) => { if (r.ok) setLp(await r.json()); else setMissing(true); }).catch(() => setMissing(true));
  }, [base, visitor]);

  async function send(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    const q = new URLSearchParams(window.location.search);
    const lead = { ...f, contact_email: f.contact_email || null, contact_phone: f.contact_phone || null, contact_person_name: f.contact_person_name || null,
      message: f.message || null, website: f.website || null, utm_source: q.get("utm_source"), utm_medium: q.get("utm_medium"), utm_campaign: q.get("utm_campaign"),
      referrer: document.referrer || null };
    const r = await fetch(`${base}/convert`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ visitor, lead }) }).catch(() => null);
    if (r?.ok) setState("sent");
    else setError(r?.status === 422 ? "Please accept the consent statement and check the fields." : r?.status === 429 ? "Too many submissions; please try later." : "Could not send; please try again.");
  }

  if (missing) return <main className="min-h-screen bg-white p-6 text-gray-600">This page is not available.</main>;
  if (!lp) return <main className="min-h-screen bg-white p-6 text-gray-400">Loading…</main>;
  const input = "w-full border rounded-lg px-3 py-2 text-sm";
  return (
    <main className="min-h-screen bg-white text-gray-900">
      <div className="max-w-xl mx-auto p-5 space-y-5">
        <p className="font-bold text-indigo-700">POVU</p>
        <h1 className="text-3xl font-bold leading-tight">{lp.headline}</h1>
        {lp.body && <p className="text-gray-700 whitespace-pre-line">{lp.body}</p>}
        {state === "sent" ? <p className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-emerald-800">Thank you — we will be in touch.</p> : (
          <form onSubmit={send} className="space-y-3 border rounded-xl p-4">
            <input aria-label="Shop or company name" required placeholder="Shop / company name" value={f.company_name} onChange={(e) => setF({ ...f, company_name: e.target.value })} className={input} />
            <input aria-label="Your name" placeholder="Your name" value={f.contact_person_name} onChange={(e) => setF({ ...f, contact_person_name: e.target.value })} className={input} />
            <input aria-label="E-mail" type="email" placeholder="E-mail" value={f.contact_email} onChange={(e) => setF({ ...f, contact_email: e.target.value })} className={input} />
            <input aria-label="Phone" placeholder="Phone" value={f.contact_phone} onChange={(e) => setF({ ...f, contact_phone: e.target.value })} className={input} />
            <textarea aria-label="Message" placeholder="Message (optional)" rows={3} value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} className={input} />
            <input tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" value={f.website} onChange={(e) => setF({ ...f, website: e.target.value })} />
            {lp.consent_text && <label className="flex gap-2 text-xs text-gray-600"><input type="checkbox" checked={f.consent} onChange={(e) => setF({ ...f, consent: e.target.checked })} />{lp.consent_text}</label>}
            {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
            <button className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium">{lp.cta_label}</button>
          </form>)}
      </div>
    </main>
  );
}
