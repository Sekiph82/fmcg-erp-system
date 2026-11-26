"use client";
// A shop asks for an ordering account (M39.S02.T003); sales staff approve it and send a set-password link.
import { useState } from "react";
import Link from "next/link";
import { partnerFetch, PortalError } from "@/lib/portalSelf";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

export default function ShopSignup() {
  const { t, err } = useI18n();
  const [f, setF] = useState({ shop_name: "", contact_name: "", phone: "", email: "", address: "" });
  const [pos, setPos] = useState<{ lat: number; lng: number } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((x) => ({ ...x, [k]: e.target.value }));

  function locate() {
    setError(null);
    navigator.geolocation?.getCurrentPosition(
      (p) => setPos({ lat: Number(p.coords.latitude.toFixed(6)), lng: Number(p.coords.longitude.toFixed(6)) }),
      () => setError(t("portal.su.noLocation")),
      { enableHighAccuracy: true, timeout: 15000 });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await partnerFetch<{ detail: string }>("portal-self", "/auth/signup-request",
        { method: "POST", body: JSON.stringify({ ...f, lat: pos?.lat ?? null, lng: pos?.lng ?? null }) });
      setMsg(t("portal.su.done"));
    } catch (ex) { setError(err(ex instanceof PortalError ? ex.status : undefined)); } finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} aria-label={t("portal.su.form")} className="w-full max-w-sm bg-white rounded-2xl shadow p-6 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0 break-words">
            <h1 className="text-xl font-bold text-gray-900">{t("portal.su.title")}</h1>
            <p className="text-sm text-gray-500">{t("portal.su.intro")}</p>
          </div>
          <LanguageSwitcher />
        </div>
        {msg ? <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{msg}</p> : <>
          {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
          <label className="block text-sm">{t("portal.su.shopName")}<input required minLength={2} maxLength={150} value={f.shop_name} onChange={set("shop_name")} className="mt-1 w-full border rounded-lg px-3 py-2" /></label>
          <label className="block text-sm">{t("portal.su.yourName")}<input required minLength={2} maxLength={150} value={f.contact_name} onChange={set("contact_name")} className="mt-1 w-full border rounded-lg px-3 py-2" /></label>
          <label className="block text-sm">{t("portal.su.phone")}<input required type="tel" inputMode="tel" pattern="\+?[0-9 ]{9,20}" value={f.phone} onChange={set("phone")} placeholder="07…" className="mt-1 w-full border rounded-lg px-3 py-2" /></label>
          <label className="block text-sm">{t("common.email")}<input required type="email" maxLength={200} value={f.email} onChange={set("email")} className="mt-1 w-full border rounded-lg px-3 py-2" /></label>
          <label className="block text-sm">{t("portal.su.address")}<input required minLength={3} maxLength={300} value={f.address} onChange={set("address")} placeholder={t("portal.su.addressPlaceholder")} className="mt-1 w-full border rounded-lg px-3 py-2" /></label>
          <button type="button" onClick={locate} className="w-full py-2 px-2 rounded-lg border text-sm break-words">{pos ? t("portal.su.located", { lat: pos.lat, lng: pos.lng }) : t("portal.su.locate")}</button>
          <button disabled={busy} className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium disabled:opacity-50">{busy ? t("portal.sending") : t("portal.su.send")}</button>
        </>}
        <p className="text-xs text-gray-500"><Link href="/portal/login" className="underline">{t("portal.su.back")}</Link></p>
      </form>
    </main>
  );
}
