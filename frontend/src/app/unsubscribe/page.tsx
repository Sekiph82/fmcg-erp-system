"use client";
// Public unsubscribe page (no login). Opening the link changes nothing (mail scanners prefetch links);
// the visitor confirms with the button.
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

function Unsubscribe() {
  const { t } = useI18n();
  const token = useSearchParams().get("t") ?? "";
  const [state, setState] = useState<{ email?: string; unsubscribed?: boolean; error?: string } | null>(null);

  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/unsubscribe?t=${encodeURIComponent(token)}`)
      .then(async (r) => setState(r.ok ? await r.json() : { error: "public.unsub.invalid" }))
      .catch(() => setState({ error: "public.mail.retry" }));
  }, [token]);

  const [tracking, setTracking] = useState<string | null>(null);
  async function stopTracking() {   // M43.S01.T006: keep receiving e-mail, but without open/click tracking
    const r = await fetch(`${API_ORIGIN}/api/v1/public/t/optout?t=${encodeURIComponent(token)}`, { method: "POST" }).catch(() => null);
    setTracking(r && r.ok ? "public.unsub.trackingDone" : "public.mail.retry");
  }

  async function confirm() {
    const r = await fetch(`${API_ORIGIN}/api/v1/public/unsubscribe?t=${encodeURIComponent(token)}`, { method: "POST" }).catch(() => null);
    setState(r && r.ok ? await r.json() : { error: "public.mail.retry" });
  }

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-md mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-xl font-bold">{t("public.unsub.title")}</h1><LanguageSwitcher /></div>
        {!state ? <p className="text-sm text-gray-500">{t("public.mail.loading")}</p> : state.error ? (
          <p role="alert" className="text-sm text-red-700">{t(state.error)}</p>
        ) : state.unsubscribed ? (
          <p role="status" className="text-sm">{t("public.unsub.done", { email: state.email ?? "" })}</p>
        ) : (
          <>
            <p className="text-sm">{t("public.unsub.ask", { email: state.email ?? "" })}</p>
            <button onClick={confirm} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">{t("public.unsub.button")}</button>
            <div className="pt-2 border-t">
              <p className="text-sm">{t("public.unsub.trackingAsk")}</p>
              <button onClick={stopTracking} className="mt-1 px-4 py-2 border rounded-lg text-sm">{t("public.unsub.trackingButton")}</button>
              {tracking && <p role="status" className="text-sm mt-1">{t(tracking)}</p>}
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
