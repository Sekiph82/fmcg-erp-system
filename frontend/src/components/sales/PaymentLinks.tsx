"use client";
// M45.S01.T021 payment links on an invoice: create (URL shown once), status, attempts, revoke.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Link = { id: string; status: string; settled_amount: string; expires_at: string; attempts: { amount: string; status: string; receipt: string | null; simulated: boolean }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export function PaymentLinks({ invoiceId, open }: { invoiceId: string; open: boolean }) {
  const [links, setLinks] = useState<Link[]>([]);
  const [url, setUrl] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/payment-links", { params: { invoice_id: invoiceId } }).then((r) => setLinks(r.data)).catch(() => setLinks([])), [invoiceId]);
  useEffect(() => { load(); }, [load]);
  const create = () => apiClient.post("/api/v1/payment-links", { invoice_id: invoiceId, days: 14, allow_partial: true }).then((r) => { setUrl(r.data.url); load(); }).catch((e) => setMsg(err(e)));
  const revoke = (id: string) => apiClient.post(`/api/v1/payment-links/${id}/revoke`).then(load).catch((e) => setMsg(err(e)));
  return (
    <div className="bg-white rounded-lg border">
      <div className="px-6 py-4 border-b flex justify-between items-center"><h2 className="font-semibold text-gray-900">Payment links</h2>
        {open && <button className="text-sm border rounded px-3 py-1" onClick={create}>Create payment link</button>}</div>
      <div className="px-6 py-3 space-y-2 text-sm">
        {msg && <p className="text-red-600 text-xs">{msg}</p>}
        {url && <p className="text-xs break-all bg-amber-50 border rounded p-2">Send this to the customer (shown once): <b>{url}</b> <button className="underline" onClick={() => navigator.clipboard?.writeText(url)}>copy</button></p>}
        {links.length === 0 ? <p className="text-xs text-gray-500">No links yet.</p> : links.map((l) => <div key={l.id} className="text-xs border-t pt-1">
          <b>{l.status.toLowerCase().replace("_", " ")}</b> · settled {l.settled_amount} · until {new Date(l.expires_at).toLocaleDateString()}
          {l.status === "ACTIVE" && <button className="ml-2 text-red-600 underline" onClick={() => revoke(l.id)}>Cancel link</button>}
          {l.attempts.map((a, i) => <div key={i} className="text-gray-600">{a.amount} · {a.status.toLowerCase()}{a.receipt ? ` · ${a.receipt}` : ""}{a.simulated ? " · simulated" : ""}</div>)}</div>)}
        <p className="text-xs text-gray-500">Real M-Pesa payments arrive as collections that finance confirms; card payments are not activated yet.</p>
      </div>
    </div>
  );
}
