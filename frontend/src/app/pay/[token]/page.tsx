"use client";
// Public payment link (M45.S01.T021): no login; the token in the link is the only credential.
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

type Page = { invoice_no: string; customer: string | null; currency: string; amount_due: string; status: string; allow_partial: boolean; expires_at: string;
  providers: { mpesa: string; card: string }; receipts: { receipt: string | null; amount: string; test: boolean }[] };

export default function PayPage() {
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/pay/${encodeURIComponent(token)}`;
  const [p, setP] = useState<Page | null>(null);
  const [gone, setGone] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => fetch(url).then(async (r) => {
    const j = await r.json().catch(() => ({}));
    if (!r.ok) setGone(typeof j.detail === "string" ? j.detail : "This link is not valid."); else { setP(j); setAmount(j.amount_due); }
  }).catch(() => setGone("This link is not valid.")), [url]);
  useEffect(() => { load(); }, [load]);
  const pay = async () => {
    setMsg(null);
    const r = await fetch(`${url}/mpesa`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, amount: amount || null }) }).catch(() => null);
    const j = r ? await r.json().catch(() => ({})) : {};
    setMsg(r?.ok ? j.message : (typeof j.detail === "string" ? j.detail : "Could not start the payment; try again."));
    if (r?.ok) setTimeout(load, 5000);
  };
  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border shadow-sm p-5 space-y-3 text-sm">
        <h1 className="text-lg font-semibold">POVU payment</h1>
        {gone ? <p className="text-red-600">{gone}</p> : !p ? <p className="text-gray-500">Loading…</p> : <>
          <p>Invoice <b>{p.invoice_no}</b>{p.customer ? ` · ${p.customer}` : ""}</p>
          {p.status === "ACTIVE" ? <>
            <p className="text-2xl font-bold">{p.currency} {p.amount_due}</p>
            <p className="text-xs text-gray-500">Link valid until {new Date(p.expires_at).toLocaleDateString()}. M-Pesa: {p.providers.mpesa.toLowerCase()}. Card: {p.providers.card.toLowerCase().replace("_", " ")}.</p>
            <label className="block text-xs">M-Pesa phone<input aria-label="M-Pesa phone" inputMode="tel" className="border rounded px-2 py-2 w-full" placeholder="07XX XXX XXX" value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
            {p.allow_partial && <label className="block text-xs">Amount<input aria-label="Amount" inputMode="decimal" className="border rounded px-2 py-2 w-full" value={amount} onChange={(e) => setAmount(e.target.value)} /></label>}
            <button className="w-full bg-green-600 text-white rounded py-2 font-semibold disabled:opacity-50" disabled={phone.length < 9} onClick={pay}>Pay with M-Pesa</button>
          </> : <p className="text-green-700 font-semibold">{p.status === "PAID" ? "Paid — thank you." : p.status === "TEST_PAID" ? "Test payment completed (simulated, no real money)." : "This link is closed."}</p>}
          {msg && <p role="status" className="text-xs">{msg}</p>}
          {p.receipts.length > 0 && <div className="text-xs"><b>Receipts</b>{p.receipts.map((r, i) => <div key={i}>{r.receipt ?? "—"} · {p.currency} {r.amount}{r.test ? " (test)" : ""}</div>)}</div>}
        </>}
      </div>
    </main>
  );
}
