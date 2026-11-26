"use client";
// M48.S01.T022 public double opt-in page (no login). Opening the link changes nothing (mail scanners prefetch links);
// the visitor confirms with the button.
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type State = { email?: string; subscribed?: boolean; pending?: boolean; blocked?: boolean; error?: string };

function ConsentConfirm() {
  const { t } = useI18n();
  const token = useSearchParams().get("t") ?? "";
  const [state, setState] = useState<State | null>(null);
  const [busy, setBusy] = useState(false);
  const url = `${API_ORIGIN}/api/v1/public/consent-confirm?t=${encodeURIComponent(token)}`;

  useEffect(() => {
    fetch(url)
      .then(async (r) => setState(r.ok ? await r.json() : { error: "public.consent.invalid" }))
      .catch(() => setState({ error: "public.mail.retry" }));
  }, [url]);

  async function confirm() {
    setBusy(true);
    const r = await fetch(url, { method: "POST" }).catch(() => null);
    setState(r && r.ok ? await r.json() : { error: r && r.status === 404 ? "public.consent.invalid" : "public.mail.retry" });
    setBusy(false);
  }

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-md mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-xl font-bold">{t("public.consent.title")}</h1><LanguageSwitcher /></div>
        {!state ? <p className="text-sm text-gray-500">{t("public.mail.loading")}</p> : state.error ? (
          <p role="alert" className="text-sm text-red-700">{t(state.error)}</p>
        ) : state.subscribed ? (
          <p role="status" className="text-sm">{t("public.consent.done", { email: state.email ?? "" })}</p>
        ) : state.blocked ? (
          <p role="status" className="text-sm">{t("public.consent.blocked", { email: state.email ?? "" })}</p>
        ) : state.pending ? (
          <>
            <p className="text-sm">{t("public.consent.ask", { email: state.email ?? "" })}</p>
            <button onClick={confirm} disabled={busy} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm disabled:opacity-50">
              {busy ? t("public.consent.busy") : t("public.consent.button")}
            </button>
          </>
        ) : (
          <p role="alert" className="text-sm text-red-700">{t("public.consent.invalid")}</p>
        )}
      </div>
    </main>
  );
}

export default function ConsentConfirmPage() {
  return <Suspense fallback={null}><ConsentConfirm /></Suspense>;
}
