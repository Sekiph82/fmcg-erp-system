"use client";
// Warehouse floor (M38.S06): pickers and putaway operators work task by task by scanning the bin and the item.
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { ScanInput } from "@/components/ScanInput";
import { tx } from "@/lib/i18n/core";

interface PickTask { id: string; task_no: string; product_name: string | null; lot_number: string | null; from_location_code: string | null;
  requested_qty: string; unit: string; status: string; assignee_name: string | null; warehouse_name: string | null; wave_no: string | null;
  parcel_invoice_no?: string | null }
interface PutTask { id: string; task_no: string; product_name: string | null; product_sku: string | null; material_name: string | null;
  lot_number: string | null; quantity: string; suggested_location_code: string | null; status: string; warehouse_name: string | null }

interface ParcelInvoice { invoice_no: string; invoice_date: string; currency: string; customer: string | null; subtotal: number;
  tax_amount: number; total_amount: number; lines: { description: string | null; quantity: number; unit_price: number; discount_pct: number; line_total: number }[] }

const esc = (v: unknown) => String(v ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));

/** Paper copy for the parcel of a marketplace order (invoice cut when the payment arrived). */
async function printParcelInvoice(taskId: string) {
  const inv = await call<ParcelInvoice>(`/picking/tasks/${taskId}/parcel-invoice`);
  const w = window.open("", "_blank");
  if (!w) throw new Error(tx("Allow pop-ups to print the invoice."));
  const rows = inv.lines.map((l) => `<tr><td>${esc(l.description)}</td><td>${l.quantity}</td><td>${l.unit_price.toFixed(2)}</td><td>${l.discount_pct ? (l.discount_pct * 100).toFixed(1) + "%" : ""}</td><td>${l.line_total.toFixed(2)}</td></tr>`).join("");
  w.document.write(`<html><head><title>${esc(inv.invoice_no)}</title><style>body{font-family:sans-serif;font-size:12px}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #ccc;padding:4px;text-align:left}</style></head><body>
<h2>Invoice ${esc(inv.invoice_no)}</h2><p>${esc(inv.customer)} · ${esc(inv.invoice_date)}</p>
<table><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Discount</th><th>Total</th></tr>${rows}</table>
<p>Subtotal ${esc(inv.currency)} ${inv.subtotal.toFixed(2)} · Tax ${inv.tax_amount.toFixed(2)} · <b>Total ${esc(inv.currency)} ${inv.total_amount.toFixed(2)}</b></p></body></html>`);
  w.document.close();
  w.print();
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(`/api/v1/wms${path}`, { ...init, headers: { "Content-Type": "application/json" } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) { const d = (body as { detail?: unknown }).detail; throw new Error(typeof d === "string" ? d : tx("Request failed")); }
  return body as T;
}
const box = "bg-white rounded-xl border p-3";
const btn = "px-3 py-2 rounded-lg text-sm font-medium disabled:opacity-50";

export default function WarehouseFloor() {
  const [tab, setTab] = useState<"pick" | "put">("pick");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  return (
    <main className="max-w-xl mx-auto p-3 space-y-3">
      <h1 className="text-lg font-bold">{tx("Warehouse floor")}</h1>
      <div className="flex gap-1" role="tablist">
        {([["pick", "Picking"], ["put", tx("Put away")]] as const).map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => { setTab(k); setMsg(null); }}
            className={`${btn} flex-1 ${tab === k ? "bg-indigo-600 text-white" : "bg-gray-100"}`}>{l}</button>))}
      </div>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`rounded-lg p-3 text-sm border ${msg.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-700"}`}>{msg.text}</p>}
      {tab === "pick" ? <Picking say={(ok, text) => setMsg({ ok, text })} /> : <Putaway say={(ok, text) => setMsg({ ok, text })} />}
    </main>
  );
}

function Picking({ say }: { say: (ok: boolean, t: string) => void }) {
  const [tasks, setTasks] = useState<PickTask[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [scan, setScan] = useState({ location: "", item: "", qty: "", reason: "" });
  const load = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([call<PickTask[]>("/picking/tasks?status=PENDING"), call<PickTask[]>("/picking/tasks?status=IN_PROGRESS")]);
      setTasks([...b, ...a]);
    } catch (e) { say(false, (e as Error).message); }
  }, [say]);
  useEffect(() => { load(); }, [load]);
  const t = tasks.find((x) => x.id === open);
  async function confirm() {
    if (!t) return;
    try {
      await call(`/picking/tasks/${t.id}/scan-confirm`, { method: "POST", body: JSON.stringify({ location_code: scan.location, item_code: scan.item, picked_qty: scan.qty || t.requested_qty, short_reason: scan.reason || null }) });
      say(true, `${t.task_no} picked.`); setOpen(null); setScan({ location: "", item: "", qty: "", reason: "" }); load();
    } catch (e) { say(false, (e as Error).message); }
  }
  if (tasks.length === 0) return <p className={box + " text-sm text-gray-500"}>{tx("No open picking tasks.")}</p>;
  return (<div className="space-y-2">{tasks.map((x) => (
    <div key={x.id} className={box}>
      <button className="w-full text-left flex justify-between gap-2" aria-expanded={open === x.id} onClick={() => { setOpen(open === x.id ? null : x.id); setScan({ location: "", item: "", qty: "", reason: "" }); }}>
        <span><span className="font-medium">{x.from_location_code ?? "—"} · {x.product_name}</span><span className="block text-xs text-gray-500">{x.task_no}{x.wave_no ? tx(" · wave {wave_no}", { wave_no: x.wave_no }) : ""}{x.lot_number ? tx(" · lot {lot_number}", { lot_number: x.lot_number }) : ""}</span>
          {x.parcel_invoice_no && <span className="block text-xs font-semibold text-amber-700">{tx("Put a paper copy of invoice")} {x.parcel_invoice_no} {tx("in the parcel")}{" "}
            <span role="button" tabIndex={0} className="underline" onClick={(e) => { e.stopPropagation(); printParcelInvoice(x.id).catch((err) => say(false, (err as Error).message)); }}>{tx("Print")}</span></span>}</span>
        <span className="text-right text-sm font-semibold">{Number(x.requested_qty)} {x.unit}<span className="block text-xs font-normal text-gray-500">{x.assignee_name ?? tx("unassigned")}</span></span>
      </button>
      {open === x.id && (
        <div className="mt-2 border-t pt-2 space-y-2">
          <ScanInput id={`loc-${x.id}`} label={tx("1. Scan bin {from_location_code}", { from_location_code: x.from_location_code ?? "" })} onScan={(c) => setScan((s) => ({ ...s, location: c }))} />
          {scan.location && <p className="text-xs text-gray-600">{tx("Bin:")} {scan.location}</p>}
          <ScanInput id={`item-${x.id}`} label={tx("2. Scan item")} onScan={(c) => setScan((s) => ({ ...s, item: c }))} />
          {scan.item && <p className="text-xs text-gray-600">{tx("Item:")} {scan.item}</p>}
          <label className="block text-xs text-gray-600">{tx("3. Quantity picked")}
            <input inputMode="decimal" aria-label={tx("Quantity picked")} placeholder={String(Number(x.requested_qty))} value={scan.qty} onChange={(e) => setScan({ ...scan, qty: e.target.value })} className="mt-1 w-full border rounded-lg px-2 py-2 text-sm" /></label>
          {scan.qty !== "" && Number(scan.qty) < Number(x.requested_qty) && (
            <input aria-label={tx("Short pick reason")} placeholder={tx("Why less? (e.g. bin empty)")} value={scan.reason} onChange={(e) => setScan({ ...scan, reason: e.target.value })} className="w-full border rounded-lg px-2 py-2 text-sm" />)}
          <button onClick={confirm} disabled={!scan.location || !scan.item} className={`${btn} w-full bg-emerald-600 text-white`}>{tx("Confirm pick")}</button>
        </div>)}
    </div>))}</div>);
}

function Putaway({ say }: { say: (ok: boolean, t: string) => void }) {
  const [tasks, setTasks] = useState<PutTask[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [scan, setScan] = useState({ item: "", location: "", reason: "" });
  const load = useCallback(async () => {
    try { setTasks(await call<PutTask[]>("/putaway/tasks?status=PENDING")); } catch (e) { say(false, (e as Error).message); }
  }, [say]);
  useEffect(() => { load(); }, [load]);
  async function done(t: PutTask) {
    try {
      const r = await call<{ actual_location_code: string }>(`/putaway/tasks/${t.id}/scan-execute`, { method: "POST", body: JSON.stringify({ item_code: scan.item, location_code: scan.location, override_reason: scan.reason || null }) });
      say(true, `${t.task_no} put away in ${r.actual_location_code}.`); setOpen(null); setScan({ item: "", location: "", reason: "" }); load();
    } catch (e) { say(false, (e as Error).message); }
  }
  if (tasks.length === 0) return <p className={box + " text-sm text-gray-500"}>{tx("No open putaway tasks.")}</p>;
  return (<div className="space-y-2">{tasks.map((t) => {
    const offSuggestion = !!scan.location && !!t.suggested_location_code && scan.location.toUpperCase() !== t.suggested_location_code.toUpperCase();
    return (
      <div key={t.id} className={box}>
        <button className="w-full text-left flex justify-between gap-2" aria-expanded={open === t.id} onClick={() => { setOpen(open === t.id ? null : t.id); setScan({ item: "", location: "", reason: "" }); }}>
          <span><span className="font-medium">{t.product_name ?? t.material_name}</span><span className="block text-xs text-gray-500">{t.task_no}{t.lot_number ? tx(" · lot {lot_number}", { lot_number: t.lot_number }) : ""} {tx("· to")} {t.suggested_location_code ?? tx("any bin")}</span></span>
          <span className="text-sm font-semibold">{Number(t.quantity)}</span>
        </button>
        {open === t.id && (
          <div className="mt-2 border-t pt-2 space-y-2">
            <ScanInput id={`pitem-${t.id}`} label={tx("1. Scan item")} onScan={(c) => setScan((s) => ({ ...s, item: c }))} />
            {scan.item && <p className="text-xs text-gray-600">{tx("Item:")} {scan.item}</p>}
            <ScanInput id={`ploc-${t.id}`} label={tx("2. Scan bin {suggested_location_code}", { suggested_location_code: t.suggested_location_code ?? "" })} onScan={(c) => setScan((s) => ({ ...s, location: c }))} />
            {scan.location && <p className="text-xs text-gray-600">{tx("Bin:")} {scan.location}</p>}
            {offSuggestion && <input aria-label={tx("Reason for another bin")} placeholder={tx("Why a different bin?")} value={scan.reason} onChange={(e) => setScan({ ...scan, reason: e.target.value })} className="w-full border rounded-lg px-2 py-2 text-sm" />}
            <button onClick={() => done(t)} disabled={!scan.item || !scan.location} className={`${btn} w-full bg-emerald-600 text-white`}>{tx("Confirm put away")}</button>
          </div>)}
      </div>);
  })}</div>);
}
