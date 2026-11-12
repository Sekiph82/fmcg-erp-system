"use client";
// Public hosted lead form (no login). Embed on any website with:
// <iframe src="https://<erp-host>/forms/<slug>" width="100%" height="640" style="border:0"></iframe>
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface PublicForm { slug: string; title: string; intro: string | null; consent_text: string | null; require_consent: boolean }

const UTM = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"] as const;

export default function PublicLeadForm() {
  const { slug } = useParams<{ slug: string }>();
  const [form, setForm] = useState<PublicForm | null>(null);
  const [state, setState] = useState<"loading" | "missing" | "ready" | "sending" | "sent">("loading");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/lead-forms/${encodeURIComponent(slug)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error();
        setForm(await r.json());
        setState("ready");
      })
      .catch(() => setState("missing"));
  }, [slug]);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const data = new FormData(e.currentTarget);
    const params = new URLSearchParams(window.location.search);
    const body: Record<string, unknown> = {
      company_name: data.get("company_name"), contact_person_name: data.get("contact_person_name") || null,
      contact_email: data.get("contact_email") || null, contact_phone: data.get("contact_phone") || null,
      message: data.get("message") || null, consent: data.get("consent") === "on", website: data.get("website") || null,
      referrer: document.referrer || null, landing_page: (params.get("page") || window.location.href).slice(0, 500),
    };
    for (const k of UTM) body[k] = params.get(k);
    setState("sending");
    const r = await fetch(`${API_ORIGIN}/api/v1/public/lead-forms/${encodeURIComponent(slug)}/submit`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).catch(() => null);
    if (r && r.status === 202) {
      setMessage((await r.json()).message);
      setState("sent");
      return;
    }
    const detail = r ? await r.json().then((j) => j.detail).catch(() => null) : null;
    setError(r?.status === 429 ? "Too many submissions; please try again later."
      : typeof detail === "string" ? detail : "Please check the fields and try again.");
    setState("ready");
  }

  if (state === "loading") return <main className="p-6 text-sm text-gray-500">Loading…</main>;
  if (state === "missing" || !form) return <main className="p-6 text-sm text-gray-600">This form is not available.</main>;
  if (state === "sent") return <main className="p-6 max-w-lg mx-auto"><p role="status" className="text-gray-800">{message}</p></main>;

  const input = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white text-gray-900";
  return (
    <main className="p-6 max-w-lg mx-auto bg-white text-gray-900 min-h-screen">
      <h1 className="text-xl font-bold mb-1">{form.title}</h1>
      {form.intro && <p className="text-sm text-gray-600 mb-4">{form.intro}</p>}
      <form aria-label={form.title} onSubmit={submit} className="space-y-3">
        <label className="block text-sm">Company *<input name="company_name" required maxLength={200} className={input} /></label>
        <label className="block text-sm">Your name<input name="contact_person_name" maxLength={200} className={input} /></label>
        <label className="block text-sm">E-mail<input name="contact_email" type="email" maxLength={200} className={input} /></label>
        <label className="block text-sm">Phone<input name="contact_phone" type="tel" maxLength={50} className={input} /></label>
        <label className="block text-sm">Message<textarea name="message" maxLength={2000} rows={4} className={input} /></label>
        {/* honeypot: hidden from people and screen readers, bots fill it */}
        <div aria-hidden="true" style={{ position: "absolute", left: "-10000px" }}>
          <label>Website<input name="website" tabIndex={-1} autoComplete="off" /></label>
        </div>
        {form.consent_text && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" name="consent" required={form.require_consent} className="mt-1" />
            <span>{form.consent_text}</span>
          </label>
        )}
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <button type="submit" disabled={state === "sending"} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
          {state === "sending" ? "Sending…" : "Send"}
        </button>
      </form>
    </main>
  );
}
