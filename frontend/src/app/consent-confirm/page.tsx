"use client";
// M48.S01.T022 public double opt-in page (no login). Opening the link changes nothing (mail scanners prefetch links);
// the visitor confirms with the button.
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

type State = { email?: string; subscribed?: boolean; pending?: boolean; blocked?: boolean; error?: string };
const INVALID = "This confirmation link is not valid or has expired.";

function ConsentConfirm() {
  const token = useSearchParams().get("t") ?? "";
  const [state, setState] = useState<State | null>(null);
  const [busy, setBusy] = useState(false);
  const url = `${API_ORIGIN}/api/v1/public/consent-confirm?t=${encodeURIComponent(token)}`;

  useEffect(() => {
    fetch(url)
      .then(async (r) => setState(r.ok ? await r.json() : { error: INVALID }))
      .catch(() => setState({ error: "Please try again later." }));
  }, [url]);

  async function confirm() {
    setBusy(true);
    const r = await fetch(url, { method: "POST" }).catch(() => null);
    setState(r && r.ok ? await r.json() : { error: r && r.status === 404 ? INVALID : "Please try again later." });
    setBusy(false);
  }

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-md mx-auto space-y-4">
        <h1 className="text-xl font-bold">Confirm your subscription</h1>
        {!state ? <p className="text-sm text-gray-500">Loading…</p> : state.error ? (
          <p role="alert" className="text-sm text-red-700">{state.error}</p>
        ) : state.subscribed ? (
          <p role="status" className="text-sm">Thank you. {state.email} will receive POVU product e-mails. Every e-mail has an unsubscribe link.</p>
        ) : state.blocked ? (
          <p role="status" className="text-sm">{state.email} has unsubscribed or cannot receive our e-mails, so nothing was changed. Contact us if you want to subscribe again.</p>
        ) : state.pending ? (
          <>
            <p className="text-sm">Send POVU product e-mails to {state.email}?</p>
            <button onClick={confirm} disabled={busy} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm disabled:opacity-50">
              {busy ? "Confirming…" : "Confirm"}
            </button>
          </>
        ) : (
          <p role="alert" className="text-sm text-red-700">{INVALID}</p>
        )}
      </div>
    </main>
  );
}

export default function ConsentConfirmPage() {
  return <Suspense fallback={null}><ConsentConfirm /></Suspense>;
}
