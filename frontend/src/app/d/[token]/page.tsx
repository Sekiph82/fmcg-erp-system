"use client";
// Public shared quotation (no login, M36.S03.T001). The view is recorded by this page after it renders,
// not by opening the URL, so mail scanners that pre-fetch links do not count as views.
// M36.S04.T003: the customer can accept or decline with a typed-name electronic signature.
// M41.S01.T002: first a one-time code is e-mailed to an address on file for the customer; the signer types it.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

interface Line { description: string; sku: string | null; qty: string; unit: string; unit_price: string | null; discount_pct: string; tax_rate: string; line_total: string | null }
interface Doc {
  number: string; version: number; status: string; customer: string | null; quote_date: string; valid_until: string | null;
  currency: string; discount_pct: string; total_amount: string | null; tax_amount: string | null; grand_total: string | null;
  notes: string | null; lines: Line[]; link_expires_at: string; document_hash: string; can_decide: boolean;
  decision?: { decision: "ACCEPTED" | "DECLINED"; signer_name: string; decided_at: string; reference: string };
}

export default function SharedDocumentPage() {
  const { t, f, err } = useI18n();
  const money = (v: string | null, c: string) => f.money(v, c);
  const day = (v: string) => f.date(`${v}T00:00:00`);   // a calendar date, not an instant
  const token = String(useParams().token ?? "");
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sign, setSign] = useState({ name: "", email: "", agree: false, reason: "", code: "" });
  const [codeMsg, setCodeMsg] = useState<string | null>(null);
  const [declining, setDeclining] = useState(false);
  const [busy, setBusy] = useState(false);
  const [signErr, setSignErr] = useState<string | null>(null);
  const url = `${API_ORIGIN}/api/v1/public/documents/${encodeURIComponent(token)}`;

  async function decide(decision: "ACCEPTED" | "DECLINED") {
    if (!doc) return;
    setBusy(true); setSignErr(null);
    try {
      const r = await fetch(`${url}/decision`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, signer_name: sign.name, signer_email: sign.email, agree: sign.agree,
                               document_hash: doc.document_hash, reason: sign.reason || null, code: sign.code.trim() }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setSignErr(err(r.status));
        return;
      }
      setDoc({ ...doc, can_decide: false, decision: { decision, signer_name: sign.name, decided_at: j.decided_at, reference: j.reference } });
    } catch { setSignErr(err()); } finally { setBusy(false); }
  }

  async function sendCode() {
    setBusy(true); setSignErr(null); setCodeMsg(null);
    try {
      const r = await fetch(`${url}/signer-code`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ signer_email: sign.email }),
      });
      if (!r.ok) { setSignErr(err(r.status)); return; }
      setCodeMsg(t("docs.quote.codeSent"));
    } catch { setSignErr(err()); } finally { setBusy(false); }
  }

  useEffect(() => {
    fetch(url)
      .then(async (r) => {
        if (!r.ok) { setError(t("docs.quote.notAvailable")); return; }
        setDoc(await r.json());
        fetch(`${url}/view`, { method: "POST" }).catch(() => undefined);
      })
      .catch(() => setError(err()));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per link, not per language
  }, [url]);

  return (
    <main className="min-h-screen bg-white text-gray-900 p-4 sm:p-8">
      <div className="max-w-3xl mx-auto space-y-5">
        <div className="flex justify-end"><LanguageSwitcher /></div>
        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : !doc ? <p className="text-sm text-gray-500">{t("common.loading")}</p> : (
          <>
            <header className="flex flex-wrap justify-between gap-2 border-b pb-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">{t("docs.quote.label")}</p>
                <h1 className="text-xl font-bold">{doc.number}{doc.version > 1 ? ` ${t("docs.quote.version", { n: doc.version })}` : ""}</h1>
                {doc.customer && <p className="text-sm text-gray-600">{t("docs.quote.for", { customer: doc.customer })}</p>}
              </div>
              <div className="text-sm text-gray-600 sm:text-right">
                <p>{t("docs.quote.date", { date: day(doc.quote_date) })}</p>
                {doc.valid_until && <p>{t("docs.quote.validUntil", { date: day(doc.valid_until) })}</p>}
              </div>
            </header>
            <ul className="sm:hidden divide-y border-y text-sm">
              {doc.lines.map((l, i) => (
                <li key={i} className="py-2">
                  <p className="font-medium">{l.description}{l.sku && <span className="ml-1 text-xs text-gray-500">{l.sku}</span>}</p>
                  <p className="flex justify-between text-gray-600">
                    <span>{l.qty} {l.unit} × {money(l.unit_price, doc.currency)}{Number(l.discount_pct) > 0 ? ` −${l.discount_pct}%` : ""}</span>
                    <span className="font-medium text-gray-900">{money(l.line_total, doc.currency)}</span>
                  </p>
                </li>
              ))}
            </ul>
            <div className="hidden sm:block">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-gray-500 border-b"><th className="py-2">{t("docs.quote.item")}</th><th className="text-right">{t("docs.quote.qty")}</th><th className="text-right">{t("docs.quote.unitPrice")}</th><th className="text-right hidden sm:table-cell">{t("docs.quote.discPct")}</th><th className="text-right">{t("docs.quote.total")}</th></tr></thead>
                <tbody>
                  {doc.lines.map((l, i) => (
                    <tr key={i} className="border-b">
                      <td className="py-2 pr-2 min-w-[9rem]">{l.description}{l.sku && <span className="block text-xs text-gray-500">{l.sku}</span>}</td>
                      <td className="text-right whitespace-nowrap">{l.qty} {l.unit}</td>
                      <td className="text-right whitespace-nowrap pl-2">{money(l.unit_price, doc.currency)}{Number(l.discount_pct) > 0 && <span className="block text-xs text-gray-500 sm:hidden">−{l.discount_pct}%</span>}</td>
                      <td className="text-right hidden sm:table-cell">{l.discount_pct}</td>
                      <td className="text-right whitespace-nowrap pl-2">{money(l.line_total, doc.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-sm space-y-1 sm:w-72 sm:ml-auto">
              {Number(doc.discount_pct) > 0 && <p className="flex justify-between"><span>{t("docs.quote.overallDiscount")}</span><span>{doc.discount_pct}%</span></p>}
              <p className="flex justify-between"><span>{t("docs.quote.subtotal")}</span><span>{money(doc.total_amount, doc.currency)}</span></p>
              <p className="flex justify-between"><span>{t("docs.quote.tax")}</span><span>{money(doc.tax_amount, doc.currency)}</span></p>
              <p className="flex justify-between font-bold text-base border-t pt-1"><span>{t("docs.quote.total")}</span><span>{money(doc.grand_total, doc.currency)}</span></p>
            </div>
            {doc.notes && <p className="text-sm whitespace-pre-wrap border-t pt-3">{doc.notes}</p>}
            {doc.decision ? (
              <p role="status" className={`rounded-lg p-3 text-sm border ${doc.decision.decision === "ACCEPTED" ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-gray-50 border-gray-200"}`}>
                {t(doc.decision.decision === "ACCEPTED" ? "docs.quote.accepted" : "docs.quote.declined",
                   { name: doc.decision.signer_name, when: f.dateTime(doc.decision.decided_at), ref: doc.decision.reference })}
                {doc.decision.decision === "ACCEPTED" && ` ${t("docs.quote.willConfirm")}`}
              </p>
            ) : doc.can_decide && (
              <section aria-label={t("docs.quote.yourDecision")} className="border rounded-lg p-4 space-y-3">
                <h2 className="font-semibold">{t("docs.quote.yourDecision")}</h2>
                <div className="grid sm:grid-cols-2 gap-2">
                  <input aria-label={t("docs.quote.fullName")} placeholder={t("docs.quote.fullName")} value={sign.name} onChange={(e) => setSign({ ...sign, name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                  <input aria-label={t("docs.quote.email")} type="email" placeholder={t("docs.quote.email")} value={sign.email} onChange={(e) => setSign({ ...sign, email: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button type="button" disabled={busy || !sign.email.includes("@")} onClick={sendCode}
                    className="px-3 py-2 rounded border text-sm disabled:opacity-50">{t("docs.quote.sendCode")}</button>
                  <input aria-label={t("docs.quote.codeLabel")} inputMode="numeric" maxLength={6} placeholder={t("docs.quote.codePlaceholder")} value={sign.code}
                    onChange={(e) => setSign({ ...sign, code: e.target.value.replace(/[^0-9]/g, "") })} className="border rounded px-3 py-2 text-sm w-32" />
                  <span className="text-xs text-gray-500">{t("docs.quote.emailHint")}</span>
                </div>
                {codeMsg && <p role="status" className="text-sm text-emerald-800">{codeMsg}</p>}
                {declining && <textarea aria-label={t("docs.quote.reason")} placeholder={t("docs.quote.reason")} rows={2} value={sign.reason} onChange={(e) => setSign({ ...sign, reason: e.target.value })} className="w-full border rounded px-3 py-2 text-sm" />}
                <label className="flex gap-2 text-sm items-start">
                  <input type="checkbox" className="mt-1" checked={sign.agree} onChange={(e) => setSign({ ...sign, agree: e.target.checked })} />
                  <span>{t(declining ? "docs.quote.agreeDecline" : "docs.quote.agreeAccept", { number: doc.number, customer: doc.customer ?? t("docs.quote.myBusiness") })}</span>
                </label>
                {signErr && <p role="alert" className="text-sm text-red-700">{signErr}</p>}
                <div className="flex flex-wrap gap-2">
                  {!declining ? (
                    <>
                      <button disabled={busy || !sign.agree || sign.name.trim().length < 2 || !sign.email.includes("@") || sign.code.length !== 6} onClick={() => decide("ACCEPTED")}
                        className="px-4 py-2 rounded bg-emerald-600 text-white text-sm disabled:opacity-50">{t("docs.quote.accept")}</button>
                      <button onClick={() => setDeclining(true)} className="px-4 py-2 rounded border text-sm">{t("docs.quote.declineStart")}</button>
                    </>
                  ) : (
                    <>
                      <button disabled={busy || !sign.agree || sign.name.trim().length < 2 || !sign.email.includes("@") || sign.code.length !== 6} onClick={() => decide("DECLINED")}
                        className="px-4 py-2 rounded bg-gray-700 text-white text-sm disabled:opacity-50">{t("docs.quote.decline")}</button>
                      <button onClick={() => setDeclining(false)} className="px-4 py-2 rounded border text-sm">{t("common.back")}</button>
                    </>
                  )}
                </div>
              </section>
            )}
            <p className="text-xs text-gray-400">{t("docs.quote.linkUntil", { date: f.date(doc.link_expires_at) })}</p>
          </>
        )}
      </div>
    </main>
  );
}
