"use client";
// Public payment link (M45.S01.T021): no login; the token in the link is the only credential.
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Page = { invoice_no: string; customer: string | null; currency: string; amount_due: string; status: string; allow_partial: boolean; expires_at: string;
  providers: { mpesa: string; card: string }; receipts: { receipt: string | null; amount: string; test: boolean }[] };

export default function PayPage() {
  const { t, f, err } = useI18n();
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/pay/${encodeURIComponent(token)}`;
  const [p, setP] = useState<Page | null>(null);
  const [gone, setGone] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const load = useCallback(() => fetch(url).then(async (r) => {
    const j = await r.json().catch(() => ({}));
    if (!r.ok) setGone(r.status === 404 ? t("public.pay.invalid") : err(r.status)); else { setP(j); setAmount(j.amount_due); }
  }).catch(() => setGone(err(0))), [url]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  const pay = async () => {
    setMsg(null);
    const r = await fetch(`${url}/mpesa`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, amount: amount || null }) }).catch(() => null);
    const j = r?.ok ? await r.json().catch(() => ({})) : {};
    setMsg(r?.ok ? (j.simulated ? t("public.pay.startedSimulated") : t("public.pay.started")) : err(r?.status));
    if (r?.ok) setTimeout(load, 5000);
  };
  const payCard = async () => {
    setMsg(null);
    const r = await fetch(`${url}/card`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount: amount || null, email: email || null, phone: phone || null }) }).catch(() => null);
    const j = r?.ok ? await r.json().catch(() => ({})) : {};
    if (r?.ok && j.redirect_url) window.location.href = j.redirect_url; else setMsg(err(r?.status));
  };
  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border shadow-sm p-5 space-y-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-lg font-semibold break-words min-w-0">{t("public.pay.title")}</h1><LanguageSwitcher /></div>
        {gone ? <p className="text-red-600">{gone}</p> : !p ? <p className="text-gray-500">{t("common.loading")}</p> : <>
          <p className="break-words">{t("public.pay.invoice")} <b>{p.invoice_no}</b>{p.customer ? ` · ${p.customer}` : ""}</p>
          {p.status === "ACTIVE" ? <>
            <p className="text-2xl font-bold break-words">{f.money(p.amount_due, p.currency)}</p>
            <p className="text-xs text-gray-500 break-words">{t("public.pay.validUntil", { date: f.date(p.expires_at) })} M-Pesa: {p.providers.mpesa === "LIVE" ? t("public.pay.providerLive") : t("public.pay.providerSimulated")}. {t("public.pay.card")}: {p.providers.card === "LIVE" ? t("public.pay.providerLive") : p.providers.card === "SIMULATED" ? t("public.pay.providerSimulated") : t("public.pay.providerNotConfigured")}.</p>
            <label className="block text-xs">{t("public.pay.phone")}<input aria-label={t("public.pay.phone")} inputMode="tel" className="border rounded px-2 py-2 w-full" placeholder="07XX XXX XXX" value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
            {p.allow_partial && <label className="block text-xs">{t("common.amount")}<input aria-label={t("common.amount")} inputMode="decimal" className="border rounded px-2 py-2 w-full" value={amount} onChange={(e) => setAmount(e.target.value)} /></label>}
            <button className="w-full bg-green-600 text-white rounded py-2 font-semibold disabled:opacity-50" disabled={phone.length < 9} onClick={pay}>{t("public.pay.payMpesa")}</button>
            {(p.providers.card === "LIVE" || p.providers.card === "SIMULATED") && <>
              <label className="block text-xs">{t("public.pay.cardEmail")}<input aria-label={t("public.pay.cardEmail")} type="email" className="border rounded px-2 py-2 w-full" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
              <button className="w-full bg-blue-600 text-white rounded py-2 font-semibold disabled:opacity-50" disabled={!email && phone.length < 9} onClick={payCard}>{t("public.pay.payCard")}</button>
            </>}
          </> : <p className="text-green-700 font-semibold">{p.status === "PAID" ? t("public.pay.paid") : p.status === "TEST_PAID" ? t("public.pay.testPaid") : t("public.pay.closed")}</p>}
          {msg && <p role="status" className="text-xs">{msg}</p>}
          {p.receipts.length > 0 && <div className="text-xs"><b>{t("public.pay.receipts")}</b>{p.receipts.map((r, i) => <div key={i}>{r.receipt ?? "—"} · {f.money(r.amount, p.currency)}{r.test ? ` (${t("public.pay.test")})` : ""}</div>)}</div>}
        </>}
      </div>
    </main>
  );
}
