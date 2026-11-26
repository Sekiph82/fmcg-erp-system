"use client";
// M45.S01.T021 payment links on an invoice: create (URL shown once), status, attempts, revoke.
// M48.S01.T010 card payments: Pesapal hosted checkout per link, status refresh, refund request + second-person
// decision, reconciliation (collection / ledger / credit), provider set-up with disabled reasons.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Card = { id: string; status: string; settlement: string; simulated: boolean; amount: string; currency: string; redirect_url: string | null; status_description: string | null };
type Link = { id: string; status: string; settled_amount: string; expires_at: string; currency: string; allow_partial: boolean;
  attempts: { amount: string; status: string; receipt: string | null; simulated: boolean }[]; card_payments: Card[] };
type Cfg = { mode: string; disabled_reasons: string[]; environment: string | null; ipn_registered: boolean; live_requested: boolean; live_active: boolean; consumer_key_set: boolean };
type RecRow = Card & { tracking_id: string | null; confirmation_code: string | null; payment_method: string | null; notifications: number;
  collection: { no: string; status: string; amount: string; posted: boolean } | null;
  refund: { id: string; amount: string; status: string; reason: string; message: string | null; journal_entry_id: string | null } | null };
type Rec = { invoice_no: string; total: string; paid: string; status: string; currency: string;
  credit: { limit: string | null; outstanding: string; available: string | null; over_limit: boolean; note: string }; card_payments: RecRow[] };

const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const low = (s: string) => s.toLowerCase().replace(/_/g, " ");

export function PaymentLinks({ invoiceId, open }: { invoiceId: string; open: boolean }) {
  const [links, setLinks] = useState<Link[]>([]);
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [rec, setRec] = useState<Rec | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [checkout, setCheckout] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [refund, setRefund] = useState<{ id: string; amount: string; reason: string } | null>(null);
  const [setup, setSetup] = useState<{ environment: string; consumer_key: string; consumer_secret: string; base_url?: string } | null>(null);

  const load = useCallback(() => {
    apiClient.get("/api/v1/payment-links", { params: { invoice_id: invoiceId } }).then((r) => setLinks(r.data)).catch(() => setLinks([]));
    apiClient.get("/api/v1/payment-links/card/config").then((r) => setCfg(r.data)).catch(() => setCfg(null));
    apiClient.get("/api/v1/payment-links/reconciliation", { params: { invoice_id: invoiceId } }).then((r) => setRec(r.data)).catch(() => setRec(null));
  }, [invoiceId]);
  useEffect(() => { load(); }, [load]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setMsg(null);
    try { await fn(); } catch (e) { setMsg(err(e)); } finally { setBusy(false); load(); }
  };
  const create = () => act(async () => { const r = await apiClient.post("/api/v1/payment-links", { invoice_id: invoiceId, days: 14, allow_partial: true }); setUrl(r.data.url); });
  const revoke = (id: string) => act(() => apiClient.post(`/api/v1/payment-links/${id}/revoke`));
  const card = (l: Link) => act(async () => {
    const amount = amounts[l.id]?.trim();
    const r = await apiClient.post(`/api/v1/payment-links/${l.id}/card`, amount ? { amount } : {});
    setCheckout(r.data.redirect_url);
  });
  const refresh = (id: string) => act(() => apiClient.post(`/api/v1/payment-links/card-payments/${id}/refresh`));
  const askRefund = () => refund && act(async () => {
    await apiClient.post(`/api/v1/payment-links/card-payments/${refund.id}/refund`, { amount: refund.amount, reason: refund.reason });
    setRefund(null);
  });
  const decide = (rid: string, d: "approve" | "reject") => act(async () => {
    const r = await apiClient.post(`/api/v1/payment-links/card-refunds/${rid}/${d}`);
    if (r.data.message) setMsg(`Provider: ${r.data.message}`);
  });
  const saveSetup = () => setup && act(async () => {
    await apiClient.put("/api/v1/payment-links/card/config", { ...setup, base_url: setup.base_url?.trim() || null }); setSetup(null);
  });
  const cfgAction = (a: string) => act(() => apiClient.post(`/api/v1/payment-links/card/config/${a}`));

  const cardOff = !cfg || cfg.mode === "NOT_CONFIGURED" || cfg.mode === "BLOCKED";
  const cardReason = (l: Link) => l.status !== "ACTIVE" ? "The link is not open for payment." :
    cardOff ? (cfg?.disabled_reasons.join(" ") || "Card payments are not set up.") : "";

  return (
    <div className="bg-white rounded-lg border">
      <div className="px-6 py-4 border-b flex justify-between items-center"><h2 className="font-semibold text-gray-900">Payment links</h2>
        {open && <button className="text-sm border rounded px-3 py-1 disabled:opacity-50" disabled={busy} onClick={create}>Create payment link</button>}</div>
      <div className="px-6 py-3 space-y-2 text-sm">
        {msg && <p role="alert" className="text-red-600 text-xs">{msg}</p>}
        {url && <p className="text-xs break-all bg-amber-50 border rounded p-2">Send this to the customer (shown once): <b>{url}</b> <button className="underline" onClick={() => navigator.clipboard?.writeText(url)}>copy</button></p>}
        {checkout && <p className="text-xs break-all bg-blue-50 border rounded p-2">Hosted card checkout (the card is typed on Pesapal&apos;s page, never here): <a className="underline" href={checkout} target="_blank" rel="noopener noreferrer">{checkout}</a> <button className="underline" onClick={() => navigator.clipboard?.writeText(checkout)}>copy</button></p>}

        <div className="text-xs border rounded p-2 bg-gray-50">
          <b>Card payments (Pesapal):</b> {cfg ? low(cfg.mode) : "unknown"}{cfg?.environment ? ` · ${low(cfg.environment)}` : ""}
          {cfg?.disabled_reasons.map((r) => <div key={r} className="text-gray-600">• {r}</div>)}
          <div className="flex flex-wrap gap-2 mt-1">
            <button className="underline" onClick={() => setSetup(setup ? null : { environment: "SANDBOX", consumer_key: "", consumer_secret: "" })}>{setup ? "Close set-up" : "Set up provider"}</button>
            <button className="underline disabled:opacity-40" disabled={busy || !cfg?.consumer_key_set} title={cfg?.consumer_key_set ? "" : "Save credentials first."} onClick={() => cfgAction("register-ipn")}>Register IPN URL</button>
            <button className="underline disabled:opacity-40" disabled={busy || cfg?.environment !== "LIVE" || !cfg?.ipn_registered || cfg?.live_active} title={cfg?.environment !== "LIVE" ? "Needs LIVE credentials." : ""} onClick={() => cfgAction("request-live")}>Request live</button>
            <button className="underline disabled:opacity-40" disabled={busy || !cfg?.live_requested || cfg?.live_active} title={cfg?.live_requested ? "A different finance approver must approve." : "Nobody has requested live payments."} onClick={() => cfgAction("approve-live")}>Approve live</button>
          </div>
          {setup && <div className="mt-2 grid gap-1 sm:grid-cols-4">
            <select aria-label="Environment" className="border rounded px-1" value={setup.environment} onChange={(e) => setSetup({ ...setup, environment: e.target.value })}><option value="SANDBOX">Sandbox</option><option value="LIVE">Live</option></select>
            <input aria-label="Consumer key" className="border rounded px-1" placeholder="Consumer key" value={setup.consumer_key} onChange={(e) => setSetup({ ...setup, consumer_key: e.target.value })} />
            <input aria-label="Consumer secret" type="password" autoComplete="off" className="border rounded px-1" placeholder="Consumer secret" value={setup.consumer_secret} onChange={(e) => setSetup({ ...setup, consumer_secret: e.target.value })} />
            <input aria-label="API URL override" className="border rounded px-1 sm:col-span-4" placeholder="API URL override (optional; local simulator only, never in live egress)" value={setup.base_url ?? ""} onChange={(e) => setSetup({ ...setup, base_url: e.target.value })} />
            <button className="border rounded px-2 disabled:opacity-40" disabled={busy || setup.consumer_key.length < 8 || setup.consumer_secret.length < 8} onClick={saveSetup}>Save (encrypted)</button>
          </div>}
        </div>

        {links.length === 0 ? <p className="text-xs text-gray-500">No links yet.</p> : links.map((l) => <div key={l.id} className="text-xs border-t pt-1">
          <b>{low(l.status)}</b> · settled {l.settled_amount} {l.currency} · until {new Date(l.expires_at).toLocaleDateString()}
          {l.status === "ACTIVE" && <button className="ml-2 text-red-600 underline" onClick={() => revoke(l.id)}>Cancel link</button>}
          {l.attempts.map((a, i) => <div key={i} className="text-gray-600">M-Pesa {a.amount} · {a.status.toLowerCase()}{a.receipt ? ` · ${a.receipt}` : ""}{a.simulated ? " · simulated" : ""}</div>)}
          {open && <div className="flex flex-wrap items-center gap-2 mt-1">
            <input aria-label="Card amount" inputMode="decimal" className="border rounded px-1 w-28" placeholder={l.allow_partial ? "Amount (blank = all)" : "Full amount"} disabled={!l.allow_partial}
              value={amounts[l.id] ?? ""} onChange={(e) => setAmounts({ ...amounts, [l.id]: e.target.value })} />
            <button className="border rounded px-2 disabled:opacity-40" disabled={busy || !!cardReason(l)} title={cardReason(l)} onClick={() => card(l)}>Card checkout link</button>
            {cardReason(l) && <span className="text-gray-500">{cardReason(l)}</span>}
          </div>}
          {l.card_payments.map((p) => <div key={p.id} className="text-gray-600">Card {p.amount} {p.currency} · {low(p.status)} · {low(p.settlement)}{p.simulated ? " · test" : ""}
            {p.status_description ? ` · ${p.status_description}` : ""}
            <button className="ml-2 underline disabled:opacity-40" disabled={busy} onClick={() => refresh(p.id)}>Refresh status</button>
            {p.status === "COMPLETED" && <button className="ml-2 underline" onClick={() => setRefund({ id: p.id, amount: p.amount, reason: "" })}>Request refund</button>}
          </div>)}
        </div>)}

        {refund && <div className="text-xs border rounded p-2 bg-amber-50 flex flex-wrap gap-2 items-center">
          Refund (one per payment; a second finance person approves):
          <input aria-label="Refund amount" inputMode="decimal" className="border rounded px-1 w-24" value={refund.amount} onChange={(e) => setRefund({ ...refund, amount: e.target.value })} />
          <input aria-label="Refund reason" className="border rounded px-1 flex-1 min-w-[10rem]" placeholder="Reason" value={refund.reason} onChange={(e) => setRefund({ ...refund, reason: e.target.value })} />
          <button className="border rounded px-2 disabled:opacity-40" disabled={busy || refund.reason.trim().length < 3} title={refund.reason.trim().length < 3 ? "Give a reason." : ""} onClick={askRefund}>Send for approval</button>
          <button className="underline" onClick={() => setRefund(null)}>Cancel</button>
        </div>}

        {rec && rec.card_payments.length > 0 && <div className="text-xs border rounded p-2">
          <b>Card reconciliation</b> · invoice {rec.invoice_no}: paid {rec.paid} of {rec.total} {rec.currency} ({low(rec.status)})
          <div className="text-gray-600">Credit: limit {rec.credit.limit ?? "none"} · outstanding {rec.credit.outstanding}{rec.credit.available !== null ? ` · available ${rec.credit.available}` : ""}{rec.credit.over_limit ? " · OVER LIMIT" : ""}. {rec.credit.note}</div>
          <div className="overflow-x-auto"><table className="min-w-full mt-1">
            <thead><tr className="text-left text-gray-500"><th className="pr-2">Amount</th><th className="pr-2">Provider</th><th className="pr-2">Settlement</th><th className="pr-2">Collection / ledger</th><th className="pr-2">Refund</th></tr></thead>
            <tbody>{rec.card_payments.map((p) => <tr key={p.id} className="border-t align-top">
              <td className="pr-2">{p.amount} {p.currency}{p.simulated ? " (test)" : ""}</td>
              <td className="pr-2">{low(p.status)}{p.confirmation_code ? ` · ${p.confirmation_code}` : ""}{p.payment_method ? ` · ${p.payment_method}` : ""} · {p.notifications} notices</td>
              <td className="pr-2">{low(p.settlement)}</td>
              <td className="pr-2">{p.collection ? `${p.collection.no} · ${low(p.collection.status)} · ${p.collection.posted ? "posted" : "awaiting finance"}` : "—"}</td>
              <td className="pr-2">{p.refund ? <>{p.refund.amount} · {low(p.refund.status)}{p.refund.journal_entry_id ? " · booked" : ""}{p.refund.message ? ` · ${p.refund.message}` : ""}
                {p.refund.status === "REQUESTED" && <span className="ml-1"><button className="underline" disabled={busy} onClick={() => decide(p.refund!.id, "approve")}>Approve</button> <button className="underline text-red-600" disabled={busy} onClick={() => decide(p.refund!.id, "reject")}>Reject</button></span>}</> : "—"}</td>
            </tr>)}</tbody></table></div>
        </div>}
        <p className="text-xs text-gray-500">M-Pesa and card payments arrive as collections that finance confirms into the ledger; test payments never do.</p>
      </div>
    </div>
  );
}
