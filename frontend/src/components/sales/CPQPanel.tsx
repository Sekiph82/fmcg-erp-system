"use client";
// M45.S01.T014 CPQ panel for one quotation: price book, promotions, multi-step approval, readiness, contract.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { ProviderSignaturePanel } from "@/components/esign/ProviderSignature";

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
      {/* M48.S01.T009 DocuSign / Adobe Acrobat Sign for the approved (sent) quotation */}
      <ProviderSignaturePanel sourceType="QUOTATION" sourceId={quoteId} sourceStatus={status} />
    </div>
  );
}

// M47.S01.T009 quote draft from a deal: proposed lines (re-order of the last order, prices from the price book);
// the rep edits quantities and saves a DRAFT quotation. Nothing is sent.
type DraftLine = { product_id: string; product: string | null; qty: string; unit: string; tax_rate: string; unit_price: string | null; price_source: string; source: string };
export function QuoteDraftFromDeal({ recordId }: { recordId: string }) {
  const [d, setD] = useState<{ engine: string; lines: DraftLine[]; note: string } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { setD(null); setMsg(null); }, [recordId]);
  const propose = () => apiClient.post(`/api/v1/cpq/deals/${recordId}/quote-draft`).then((r) => setD(r.data)).catch((e) => setMsg(err(e)));
  const save = () => d && apiClient.post(`/api/v1/cpq/deals/${recordId}/quote-draft/save`, {
    lines: d.lines.map((l) => ({ product_id: l.product_id, qty: Number(l.qty), unit: l.unit, tax_rate: Number(l.tax_rate) })),
  }).then((r) => { setMsg(`Draft quotation ${r.data.quote_no} saved (DRAFT; approvals apply, nothing sent).`); setD(null); }).catch((e) => setMsg(err(e)));
  return (
    <div className="border rounded p-2 bg-white space-y-1 text-xs">
      <div className="flex items-center gap-2"><b>Quote draft</b><button className="border rounded px-2" onClick={propose}>Propose lines</button></div>
      {msg && <p role="status">{msg}</p>}
      {d && <>
        <p className="text-gray-500">{d.note} Engine: {d.engine}.</p>
        <table className="w-full"><tbody>{d.lines.map((l, i) => (
          <tr key={l.product_id} className="border-t"><td>{l.product ?? l.product_id}</td>
            <td><input aria-label="Quantity" type="number" min="0" step="any" className="border rounded w-20 px-1" value={l.qty}
              onChange={(e) => setD({ ...d, lines: d.lines.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)) })} /></td>
            <td>{l.unit_price ?? "—"}</td><td className="text-gray-500">{l.price_source}; {l.source}</td></tr>))}</tbody></table>
        {d.lines.length > 0 && <button className="border rounded px-2 py-1" onClick={save}>Save as draft quotation</button>}
      </>}
    </div>
  );
}

// M47.S01.T009 contract import: CSV (+ PDFs matched by the attachment column), dry run first.
export function ContractImport() {
  const [csv, setCsv] = useState<File | null>(null);
  const [pdfs, setPdfs] = useState<FileList | null>(null);
  const [res, setRes] = useState<{ dry_run: boolean; total_rows: number; valid_rows: number; errors: { row: number; message: string }[]; attachments_stored: { contract_code: string }[] } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const run = (dry: boolean) => {
    if (!csv) return;
    const f = new FormData();
    f.append("file", csv);
    Array.from(pdfs ?? []).forEach((p) => f.append("attachments", p));
    f.append("dry_run", String(dry));
    apiClient.post("/api/v1/bulk-import/contracts/import-with-files", f).then((r) => { setRes(r.data); setMsg(null); }).catch((e) => setMsg(err(e)));
  };
  return (
    <div className="border rounded p-2 bg-white space-y-1 text-xs">
      <b>Import contracts</b>
      <p className="text-gray-500">CSV: contract_code, customer_code, start_date, end_date, value, currency, auto_renew, renewal_notice_days, attachment (PDF file name).</p>
      <label className="block">CSV <input type="file" accept=".csv" onChange={(e) => setCsv(e.target.files?.[0] ?? null)} /></label>
      <label className="block">PDFs <input type="file" accept=".pdf" multiple onChange={(e) => setPdfs(e.target.files)} /></label>
      <div className="flex gap-2"><button className="border rounded px-2" disabled={!csv} onClick={() => run(true)}>Dry run</button>
        <button className="border rounded px-2" disabled={!csv || !res?.dry_run} onClick={() => run(false)}>Import valid rows</button></div>
      {msg && <p role="status">{msg}</p>}
      {res && <div><p>{res.dry_run ? "Dry run" : "Imported"}: {res.valid_rows} of {res.total_rows} rows valid{res.attachments_stored?.length ? `, ${res.attachments_stored.length} PDF(s) stored` : ""}.</p>
        <ul className="text-red-600">{res.errors.map((e, i) => <li key={i}>Row {e.row}: {e.message}</li>)}</ul></div>}
    </div>
  );
}
