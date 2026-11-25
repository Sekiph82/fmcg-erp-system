"use client";
// Public unsubscribe page (no login). Opening the link changes nothing (mail scanners prefetch links);
// the visitor confirms with the button.
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

function Unsubscribe() {
  const token = useSearchParams().get("t") ?? "";
  const [state, setState] = useState<{ email?: string; unsubscribed?: boolean; error?: string } | null>(null);

  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/unsubscribe?t=${encodeURIComponent(token)}`)
      .then(async (r) => setState(r.ok ? await r.json() : { error: "This unsubscribe link is not valid." }))
      .catch(() => setState({ error: "Please try again later." }));
  }, [token]);

  const [tracking, setTracking] = useState<string | null>(null);
  async function stopTracking() {   // M43.S01.T006: keep receiving e-mail, but without open/click tracking
    const r = await fetch(`${API_ORIGIN}/api/v1/public/t/optout?t=${encodeURIComponent(token)}`, { method: "POST" }).catch(() => null);
    setTracking(r && r.ok ? "We will no longer track whether you open or click our e-mails." : "Please try again later.");
  }

  async function confirm() {
    const r = await fetch(`${API_ORIGIN}/api/v1/public/unsubscribe?t=${encodeURIComponent(token)}`, { method: "POST" }).catch(() => null);
    setState(r && r.ok ? await r.json() : { error: "Please try again later." });
  }

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-md mx-auto space-y-4">
        <h1 className="text-xl font-bold">E-mail preferences</h1>
        {!state ? <p className="text-sm text-gray-500">Loading…</p> : state.error ? (
          <p role="alert" className="text-sm text-red-700">{state.error}</p>
        ) : state.unsubscribed ? (
          <p role="status" className="text-sm">{state.email} will no longer receive these e-mails.</p>
        ) : (
          <>
            <p className="text-sm">Stop sending marketing and follow-up e-mails to {state.email}?</p>
            <button onClick={confirm} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Unsubscribe</button>
            <div className="pt-2 border-t">
              <p className="text-sm">Or keep receiving e-mails but stop open and click tracking:</p>
              <button onClick={stopTracking} className="mt-1 px-4 py-2 border rounded-lg text-sm">Stop tracking</button>
              {tracking && <p role="status" className="text-sm mt-1">{tracking}</p>}
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default function UnsubscribePage() {
  return <Suspense fallback={null}><Unsubscribe /></Suspense>;
}
