"use client";
// Public shared quotation (no login, M36.S03.T001). The view is recorded by this page after it renders,
// not by opening the URL, so mail scanners that pre-fetch links do not count as views.
// M36.S04.T003: the customer can accept or decline with a typed-name electronic signature.
// M41.S01.T002: first a one-time code is e-mailed to an address on file for the customer; the signer types it.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface Line { description: string; sku: string | null; qty: string; unit: string; unit_price: string | null; discount_pct: string; tax_rate: string; line_total: string | null }
interface Doc {
  number: string; version: number; status: string; customer: string | null; quote_date: string; valid_until: string | null;
  currency: string; discount_pct: string; total_amount: string | null; tax_amount: string | null; grand_total: string | null;
  notes: string | null; lines: Line[]; link_expires_at: string; document_hash: string; can_decide: boolean;
  decision?: { decision: "ACCEPTED" | "DECLINED"; signer_name: string; decided_at: string; reference: string };
}

const money = (v: string | null, c: string) => (v == null ? "—" : `${c} ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`);

export default function SharedDocumentPage() {
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
        const d = j.detail;
        setSignErr(typeof d === "string" ? d : Array.isArray(d) ? "Please check your name and e-mail address." : "Please try again later.");
        return;
      }
      setDoc({ ...doc, can_decide: false, decision: { decision, signer_name: sign.name, decided_at: j.decided_at, reference: j.reference } });
    } catch { setSignErr("Please try again later."); } finally { setBusy(false); }
  }

  async function sendCode() {
    setBusy(true); setSignErr(null); setCodeMsg(null);
    try {
      const r = await fetch(`${url}/signer-code`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ signer_email: sign.email }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setSignErr(typeof j.detail === "string" ? j.detail : "Please check your e-mail address."); return; }
      setCodeMsg(j.message);
    } catch { setSignErr("Please try again later."); } finally { setBusy(false); }
  }

  useEffect(() => {
    fetch(url)
      .then(async (r) => {
        if (!r.ok) { setError("This link is not available. Ask your POVU contact for a new one."); return; }
        setDoc(await r.json());
        fetch(`${url}/view`, { method: "POST" }).catch(() => undefined);
      })
      .catch(() => setError("Please try again later."));
  }, [url]);

  return (
    <main className="min-h-screen bg-white text-gray-900 p-4 sm:p-8">
      <div className="max-w-3xl mx-auto space-y-5">
        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : !doc ? <p className="text-sm text-gray-500">Loading…</p> : (
          <>
            <header className="flex flex-wrap justify-between gap-2 border-b pb-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">Quotation</p>
                <h1 className="text-xl font-bold">{doc.number}{doc.version > 1 ? ` (v${doc.version})` : ""}</h1>
                {doc.customer && <p className="text-sm text-gray-600">For {doc.customer}</p>}
              </div>
              <div className="text-sm text-gray-600 sm:text-right">
                <p>Date: {doc.quote_date}</p>
                {doc.valid_until && <p>Valid until: {doc.valid_until}</p>}
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
                <thead><tr className="text-left text-xs text-gray-500 border-b"><th className="py-2">Item</th><th className="text-right">Qty</th><th className="text-right">Unit price</th><th className="text-right hidden sm:table-cell">Disc %</th><th className="text-right">Total</th></tr></thead>
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
              {Number(doc.discount_pct) > 0 && <p className="flex justify-between"><span>Overall discount</span><span>{doc.discount_pct}%</span></p>}
              <p className="flex justify-between"><span>Subtotal</span><span>{money(doc.total_amount, doc.currency)}</span></p>
              <p className="flex justify-between"><span>Tax</span><span>{money(doc.tax_amount, doc.currency)}</span></p>
              <p className="flex justify-between font-bold text-base border-t pt-1"><span>Total</span><span>{money(doc.grand_total, doc.currency)}</span></p>
            </div>
            {doc.notes && <p className="text-sm whitespace-pre-wrap border-t pt-3">{doc.notes}</p>}
            {doc.decision ? (
              <p role="status" className={`rounded-lg p-3 text-sm border ${doc.decision.decision === "ACCEPTED" ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-gray-50 border-gray-200"}`}>
                {doc.decision.decision === "ACCEPTED" ? "Accepted" : "Declined"} by {doc.decision.signer_name} on {new Date(doc.decision.decided_at).toLocaleString()}. Reference {doc.decision.reference}.
                {doc.decision.decision === "ACCEPTED" && " Your POVU representative will confirm the order."}
              </p>
            ) : doc.can_decide && (
              <section aria-label="Your decision" className="border rounded-lg p-4 space-y-3">
                <h2 className="font-semibold">Your decision</h2>
                <div className="grid sm:grid-cols-2 gap-2">
                  <input aria-label="Your full name" placeholder="Your full name" value={sign.name} onChange={(e) => setSign({ ...sign, name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                  <input aria-label="Your e-mail" type="email" placeholder="Your e-mail" value={sign.email} onChange={(e) => setSign({ ...sign, email: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button type="button" disabled={busy || !sign.email.includes("@")} onClick={sendCode}
                    className="px-3 py-2 rounded border text-sm disabled:opacity-50">E-mail me a code</button>
                  <input aria-label="Code from the e-mail" inputMode="numeric" maxLength={6} placeholder="6-digit code" value={sign.code}
                    onChange={(e) => setSign({ ...sign, code: e.target.value.replace(/[^0-9]/g, "") })} className="border rounded px-3 py-2 text-sm w-32" />
                  <span className="text-xs text-gray-500">Use the e-mail address your company gave POVU.</span>
                </div>
                {codeMsg && <p role="status" className="text-sm text-emerald-800">{codeMsg}</p>}
                {declining && <textarea aria-label="Reason (optional)" placeholder="Reason (optional)" rows={2} value={sign.reason} onChange={(e) => setSign({ ...sign, reason: e.target.value })} className="w-full border rounded px-3 py-2 text-sm" />}
                <label className="flex gap-2 text-sm items-start">
                  <input type="checkbox" className="mt-1" checked={sign.agree} onChange={(e) => setSign({ ...sign, agree: e.target.checked })} />
                  <span>I {declining ? "decline" : "accept"} quotation {doc.number} as shown above on behalf of {doc.customer ?? "my business"}, and I agree that typing my name, confirmed with the code sent to my e-mail, is my electronic signature.</span>
                </label>
                {signErr && <p role="alert" className="text-sm text-red-700">{signErr}</p>}
                <div className="flex flex-wrap gap-2">
                  {!declining ? (
                    <>
                      <button disabled={busy || !sign.agree || sign.name.trim().length < 2 || !sign.email.includes("@") || sign.code.length !== 6} onClick={() => decide("ACCEPTED")}
                        className="px-4 py-2 rounded bg-emerald-600 text-white text-sm disabled:opacity-50">Accept quotation</button>
                      <button onClick={() => setDeclining(true)} className="px-4 py-2 rounded border text-sm">Decline…</button>
                    </>
                  ) : (
                    <>
                      <button disabled={busy || !sign.agree || sign.name.trim().length < 2 || !sign.email.includes("@") || sign.code.length !== 6} onClick={() => decide("DECLINED")}
                        className="px-4 py-2 rounded bg-gray-700 text-white text-sm disabled:opacity-50">Decline quotation</button>
                      <button onClick={() => setDeclining(false)} className="px-4 py-2 rounded border text-sm">Back</button>
                    </>
                  )}
                </div>
              </section>
            )}
            <p className="text-xs text-gray-400">This private link works until {new Date(doc.link_expires_at).toLocaleDateString()}.</p>
          </>
        )}
      </div>
    </main>
  );
}
