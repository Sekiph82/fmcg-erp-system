"use client";
// M45.S01.T014 CPQ panel for one quotation: price book, promotions, multi-step approval, readiness, contract.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Approvals = { discount_pct: string; complete: boolean; levels: { level: number; above_pct: number; permission: string; approved_by: string | null }[] };
type Ready = { ready: boolean; credit: { limit: string | null; open_invoices: string; after_order: string; ok: boolean }; stock: { line_no: number; needed: string; available: string; ok: boolean }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export function CPQPanel({ quoteId, status, onChanged }: { quoteId: string; status: string; onChanged?: () => void }) {
  const [appr, setAppr] = useState<Approvals | null>(null);
  const [ready, setReady] = useState<Ready | null>(null);
  const [promos, setPromos] = useState<{ applied: { scheme_name: string; benefit: string }[] } | null>(null);
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get(`/api/v1/cpq/quotes/${quoteId}/approvals`).then((r) => setAppr(r.data)).catch(() => setAppr(null));
    apiClient.get(`/api/v1/cpq/quotes/${quoteId}/readiness`).then((r) => setReady(r.data)).catch(() => setReady(null));
    apiClient.get("/api/v1/cpq/templates").then((r) => setTemplates(r.data.contract)).catch(() => setTemplates([]));
  }, [quoteId]);
  useEffect(() => { load(); }, [load]);
  const act = (p: Promise<unknown>, ok: string) => p.then(() => { setMsg(ok); load(); onChanged?.(); }).catch((e) => setMsg(err(e)));
  const draft = status === "DRAFT";
  return (
    <div className="border rounded p-3 bg-white space-y-2 text-xs">
      <h3 className="font-semibold text-sm">Pricing &amp; approval</h3>
      {msg && <p role="status">{msg}</p>}
      {draft && <div className="flex flex-wrap gap-2">
        <button className="border rounded px-2 py-1" onClick={() => act(apiClient.post(`/api/v1/cpq/quotes/${quoteId}/price-book`), "Prices taken from the customer's price book.")}>Use price book</button>
        <button className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/cpq/quotes/${quoteId}/promotions`).then((r) => setPromos(r.data)).catch((e) => setMsg(err(e)))}>Check promotions</button>
        {promos && promos.applied.length > 0 && <button className="border rounded px-2 py-1" onClick={() => act(apiClient.post(`/api/v1/cpq/quotes/${quoteId}/promotions?apply=true`), "Promotions applied.")}>Apply promotions</button>}</div>}
      {promos && <p>{promos.applied.length === 0 ? "No promotion applies." : promos.applied.map((a) => `${a.scheme_name} (benefit ${a.benefit})`).join("; ")}</p>}
      {appr && <div><p>Discount {appr.discount_pct}% · {appr.levels.length === 0 ? "no extra approval needed" : appr.complete ? "all approval levels done" : "approval needed"}</p>
        <ul>{appr.levels.map((l) => <li key={l.level}>Level {l.level} (over {l.above_pct}%, {l.permission}): {l.approved_by ?? "waiting"}</li>)}</ul>
        {!appr.complete && <button className="border rounded px-2 py-1" onClick={() => act(apiClient.post(`/api/v1/cpq/quotes/${quoteId}/approvals`), "Approved.")}>Approve next level</button>}</div>}
      {ready && <p>Credit: {ready.credit.ok ? "OK" : "over limit"} (open {ready.credit.open_invoices}, after this {ready.credit.after_order}{ready.credit.limit ? ` of ${ready.credit.limit}` : ""}) · Stock: {ready.stock.every((s) => s.ok) ? "available" : `short on ${ready.stock.filter((s) => !s.ok).map((s) => `line ${s.line_no}`).join(", ")}`}</p>}
      {["ACCEPTED", "CONVERTED"].includes(status) && templates.length > 0 && <div className="flex gap-2 items-center">Contract:
        {templates.map((t) => <button key={t.id} className="border rounded px-2 py-1" onClick={() => act(apiClient.post(`/api/v1/cpq/quotes/${quoteId}/contract`, { template_id: t.id }), "Contract created.")}>{t.name}</button>)}</div>}
    </div>
  );
}
