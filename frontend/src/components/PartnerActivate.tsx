"use client";
// One-time set-password link (invitation or forgotten password), shared by the distributor and supplier portals.
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { partnerFetch, PortalError } from "@/lib/portalSelf";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

function Activate({ base, loginPath }: { base: "portal-self" | "supplier-self"; loginPath: string }) {
  const { t, err } = useI18n();
  const fromUrl = useSearchParams().get("token") ?? "";
  // keep the one-time token in memory only: drop it from the address bar/history and never send it as a referrer
  const [token] = useState(fromUrl);
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "referrer";
    meta.content = "no-referrer";
    document.head.appendChild(meta);
    if (fromUrl) window.history.replaceState(window.history.state, "", window.location.pathname);
    return () => { meta.remove(); };
  }, [fromUrl]);
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pw !== pw2) { setMsg({ ok: false, text: t("portal.act.mismatch") }); return; }
    try {
      await partnerFetch<{ detail: string }>(base, "/auth/activate", { method: "POST", body: JSON.stringify({ token, new_password: pw }) });
      setMsg({ ok: true, text: t("portal.act.done") });
    } catch (ex) {
      const status = ex instanceof PortalError ? ex.status : undefined;
      setMsg({ ok: false, text: status === 400 ? t("portal.act.invalid") : err(status) });
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} aria-label={t("portal.act.form")} className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h1 className="min-w-0 break-words text-xl font-bold text-gray-900">{t("portal.act.title")}</h1>
          <LanguageSwitcher />
        </div>
        {msg && <p role={msg.ok ? "status" : "alert"} className={`rounded-lg p-3 text-sm border ${msg.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-700"}`}>{msg.text}</p>}
        {msg?.ok ? <Link href={loginPath} className="block text-center py-2.5 rounded-lg bg-indigo-600 text-white">{t("portal.act.goSignIn")}</Link> : (<>
          {!token && <p className="text-sm text-red-700">{t("portal.act.noToken")}</p>}
          <label className="block text-sm">{t("portal.act.new")}
            <input type="password" required minLength={10} autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} className="mt-1 w-full border rounded-lg px-3 py-2" />
          </label>
          <label className="block text-sm">{t("portal.act.repeat")}
            <input type="password" required minLength={10} autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} className="mt-1 w-full border rounded-lg px-3 py-2" />
          </label>
          <button disabled={!token} className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium disabled:opacity-50">{t("portal.act.form")}</button>
        </>)}
      </form>
    </main>
  );
}

export function PartnerActivate(props: { base: "portal-self" | "supplier-self"; loginPath: string }) {
  return <Suspense><Activate {...props} /></Suspense>;
}
