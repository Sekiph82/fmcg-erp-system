"use client";
// Field app: one mobile screen for reps / moto riders, delivery drivers and field controllers (whatever the login is set up as).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  fx, fpost, newRef, currentPosition, kes, mapsLink,
  type FieldMe, type Today, type Stop, type CatalogItem, type OpenInvoice, type Trip, type TripStop, type AuditRow, type CollectorAccount,
} from "@/lib/field";
import { tx, lx } from "@/lib/i18n/core";

type Tab = "route" | "collect" | "trips" | "audits";
const OUTCOMES: [string, string][] = lx(() => [["NO_ORDER", tx("Visited, no order")], ["ORDERED", "Ordered"], ["CUSTOMER_CLOSED", tx("Shop closed")], ["CREDIT_HOLD", tx("Credit hold")], ["NOT_FOUND", tx("Could not find shop")]]);
const box = "bg-white rounded-xl border p-3";
const btn = "px-3 py-2 rounded-lg text-sm font-medium disabled:opacity-50";
const input = "border rounded-lg px-2 py-2 text-sm w-full";

export default function FieldApp() {
  const [me, setMe] = useState<FieldMe | null>(null);
  const [tab, setTab] = useState<Tab | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const say = useCallback((ok: boolean, text: string) => setMsg({ ok, text }), []);
  const fail = useCallback((e: unknown) => say(false, (e as Error).message), [say]);

  useEffect(() => {
    fx<FieldMe>("/field/me").then((m) => { setMe(m); setTab(m.rep ? "route" : m.is_collector ? "collect" : m.is_driver ? "trips" : m.can_audit ? "audits" : null); }).catch(fail);
  }, [fail]);

  if (!me) return <main className="p-4 text-sm text-gray-500">{msg?.text ?? tx("Loading…")}</main>;
  const tabs: [Tab, string][] = [
    ...(me.rep ? [["route", me.rep.vehicle_type === "MOTORBIKE" ? tx("My route (moto)") : tx("My route")] as [Tab, string]] : []),
    ...(me.is_collector ? [["collect", tx("My collections")] as [Tab, string]] : []),
    ...(me.is_driver ? [["trips", tx("My deliveries")] as [Tab, string]] : []),
    ...(me.can_audit ? [["audits", tx("Outlet audits")] as [Tab, string]] : []),
  ];
  return (
    <main className="min-h-screen bg-gray-50 -m-4 sm:m-0">
      <header className="bg-indigo-700 text-white px-4 py-3 flex items-center justify-between">
        <div><p className="font-semibold">{me.full_name}</p><p className="text-xs text-indigo-200">{me.rep ? `${me.rep.code} · ${me.rep.region ?? ""}` : tx("Field app")}{me.van ? tx(" · van {van_code}", { van_code: me.van.van_code }) : ""}</p></div>
        {me.can_supervise && <Link href="/dashboard/field/supervisor" className="text-sm underline">{tx("Team")}</Link>}
      </header>
      {tabs.length > 1 && (
        <nav aria-label={tx("Field sections")} className="flex flex-wrap md:flex-nowrap bg-white border-b text-sm">
          {tabs.map(([k, l]) => <button key={k} onClick={() => { setTab(k); setMsg(null); }} aria-current={tab === k ? "page" : undefined}
            className={`flex-1 basis-1/3 md:flex-none px-2 md:px-4 py-3 leading-tight md:whitespace-nowrap ${tab === k ? "border-b-2 border-indigo-600 font-semibold text-indigo-700" : "text-gray-600"}`}>{l}</button>)}
        </nav>)}
      <div className="max-w-2xl mx-auto p-3 space-y-3">
        {msg && <p role={msg.ok ? "status" : "alert"} className={`rounded-lg p-3 text-sm border ${msg.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-700"}`}>{msg.text}</p>}
        {tab === null && <p className={box + " text-sm text-gray-600"}>{tx("Your login is not set up for field work yet (sales rep, collector, driver or field controller). Ask your manager.")}{me.can_supervise ? tx(" You can open the Team view.") : ""}</p>}
        {tab === "route" && <RouteTab say={say} fail={fail} />}
        {tab === "collect" && <CollectorTab say={say} fail={fail} />}
        {tab === "trips" && <TripsTab say={say} fail={fail} />}
        {tab === "audits" && <AuditsTab say={say} fail={fail} />}
        {me.van && <Link href="/dashboard/van-sales/pos" className="block text-center text-sm text-indigo-700 underline">{tx("Open van POS (sell from van stock)")}</Link>}
      </div>
    </main>
  );
}

type Say = { say: (ok: boolean, t: string) => void; fail: (e: unknown) => void };

/** Up to `max` photos, added one or several at a time (camera or library), shown as a count with Clear. */
function PhotosInput({ label, files, onChange, max = 10 }: { label: string; files: File[]; onChange: (f: File[]) => void; max?: number }) {
  const [dropped, setDropped] = useState(0);
  return <label className="block text-xs text-gray-600">{label} — {files.length}/{max}
    <input type="file" accept="image/jpeg,image/png" multiple aria-label={label} disabled={files.length >= max}
      onChange={(e) => { const all = [...files, ...Array.from(e.target.files ?? [])]; setDropped(Math.max(0, all.length - max)); onChange(all.slice(0, max)); e.target.value = ""; }}
      className="mt-1 block w-full text-sm" />
    {dropped > 0 && <span className="block text-amber-700">{dropped} {tx("photo(s) not added: at most")} {max}.</span>}
    {files.length > 0 && <button type="button" onClick={() => { onChange([]); setDropped(0); }} className="mt-1 underline">{tx("Clear photos")}</button>}
  </label>;
}

function PhotoInput({ label, onFile }: { label: string; onFile: (f: File | null) => void }) {
  return <label className="block text-xs text-gray-600">{label}
    <input type="file" accept="image/jpeg,image/png" capture="environment" aria-label={label} onChange={(e) => onFile(e.target.files?.[0] ?? null)} className="mt-1 block w-full text-sm" />
  </label>;
}

// ── rep / moto rider ─────────────────────────────────────────────────────────

function RouteTab({ say, fail }: Say) {
  const [day, setDay] = useState<Today | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const load = useCallback(() => fx<Today>("/field/today").then(setDay).catch(fail), [fail]);
  useEffect(() => { load(); }, [load]);
  if (!day) return <p className="text-sm text-gray-500">{tx("Loading…")}</p>;
  const pct = day.target_amount ? Math.min(100, Math.round((100 * day.sold_today) / day.target_amount)) : null;
  return (
    <div className="space-y-2">
      <div className={box + " grid grid-cols-3 text-center text-sm"}>
        <div><p className="text-xs text-gray-500">{tx("Visited")}</p><p className="font-semibold">{day.visited}/{day.stops.length}</p></div>
        <div><p className="text-xs text-gray-500">{tx("Sold today")}</p><p className="font-semibold">{kes(day.sold_today)}</p></div>
        <div><p className="text-xs text-gray-500">{tx("Target")}</p><p className="font-semibold">{day.target_amount ? `${pct}%` : "—"}</p></div>
      </div>
      {day.stops.length === 0 && <p className={box + " text-sm text-gray-500"}>{tx("No outlets on your route. Ask your manager to assign a route.")}</p>}
      {day.stops.map((s) => (
        <div key={s.customer_id} className={box}>
          <button className="w-full text-left flex justify-between gap-2" aria-expanded={open === s.customer_id} onClick={() => setOpen(open === s.customer_id ? null : s.customer_id)}>
            <span className="min-w-0"><span className="font-medium block truncate">{s.sequence}. {s.name}</span><span className="text-xs text-gray-500 block truncate">{s.route}{s.address ? ` · ${s.address}` : ""}</span></span>
            <span className="text-right text-xs shrink-0">{s.visit ? <span className="text-emerald-700">✓ {s.visit.outcome.replace(/_/g, " ").toLowerCase()}</span> : <span className="text-amber-700">{tx("to visit")}</span>}
              {s.open_balance > 0 && <span className="block text-red-700">{tx("owes")} {kes(s.open_balance, s.currency)}</span>}</span>
          </button>
          {open === s.customer_id && <StopPanel stop={s} say={say} fail={fail} reload={load} />}
        </div>))}
    </div>
  );
}

function StopPanel({ stop, say, fail, reload }: Say & { stop: Stop; reload: () => void }) {
  const [mode, setMode] = useState<"visit" | "shelf" | "order" | "collect">(stop.visit ? "order" : "visit");
  const maps = mapsLink(stop.lat, stop.lng, stop.address);
  return (
    <div className="mt-2 border-t pt-2 space-y-2">
      <div className="flex gap-2 text-xs">
        {stop.phone && <a href={`tel:${stop.phone}`} className="underline text-indigo-700">{tx("Call")} {stop.contact ?? ""}</a>}
        {maps && <a href={maps} target="_blank" rel="noreferrer" className="underline text-indigo-700">{tx("Directions")}</a>}
      </div>
      <div className="flex gap-1" role="tablist">
        {(["visit", "shelf", "order", "collect"] as const).map((m) => <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
          className={`${btn} flex-1 ${mode === m ? "bg-indigo-600 text-white" : "bg-gray-100"}`}>{m === "visit" ? tx("Check in") : m === "shelf" ? tx("Shelf") : m === "order" ? tx("Order") : tx("Collect")}</button>)}
      </div>
      {mode === "visit" && <VisitForm stop={stop} say={say} fail={fail} reload={reload} />}
      {mode === "shelf" && (stop.visit ? <ShelfForm stop={stop} say={say} fail={fail} />
        : <p className="text-sm text-gray-600">{tx("Check in first — the shelf check belongs to the visit.")}</p>)}
      {mode === "order" && <OrderForm stop={stop} say={say} fail={fail} reload={reload} />}
      {mode === "collect" && <CollectForm stop={stop} say={say} fail={fail} reload={reload} />}
    </div>
  );
}

function VisitForm({ stop, say, fail, reload }: Say & { stop: Stop; reload: () => void }) {
  const [outcome, setOutcome] = useState("NO_ORDER");
  const [notes, setNotes] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const ref = useRef(newRef());
  async function save() {
    setBusy(true);
    try {
      const gps = await currentPosition();
      const v = await fpost<{ id: string }>("/field/visits", { client_ref: ref.current, customer_id: stop.customer_id, outcome, notes: notes || null, lat: gps?.lat, lng: gps?.lng });
      if (photo) { const fd = new FormData(); fd.append("file", photo); await fpost(`/field/visits/${v.id}/photo`, fd); }
      ref.current = newRef();
      say(true, `Visit to ${stop.name} saved${gps ? " with location" : " (location not available)"}.`);
      reload();
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2">
      <select aria-label={tx("Visit result")} value={outcome} onChange={(e) => setOutcome(e.target.value)} className={input}>{OUTCOMES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
      <input aria-label={tx("Visit notes")} placeholder={tx("Notes (optional)")} maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} className={input} />
      <PhotoInput label={tx("Outlet photo (optional)")} onFile={setPhoto} />
      <button onClick={save} disabled={busy} className={`${btn} w-full bg-indigo-600 text-white`}>{busy ? tx("Saving…") : tx("Save visit")}</button>
    </div>
  );
}

function OrderForm({ stop, say, fail, reload }: Say & { stop: Stop; reload: () => void }) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [search, setSearch] = useState("");
  const [qty, setQty] = useState<Record<string, number>>({});
  const [pay, setPay] = useState("cash");
  const [when, setWhen] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 10));
  const [busy, setBusy] = useState(false);
  const ref = useRef(newRef());
  useEffect(() => {
    const t = setTimeout(() => fx<{ items: CatalogItem[] }>(`/field/catalog?customer_id=${stop.customer_id}&search=${encodeURIComponent(search)}`).then((r) => setItems(r.items)).catch(fail), 250);
    return () => clearTimeout(t);
  }, [search, stop.customer_id, fail]);
  const lines = items.filter((i) => (qty[i.product_id] ?? 0) > 0);
  const total = useMemo(() => lines.reduce((s, i) => s + i.unit_price * qty[i.product_id], 0), [lines, qty]);
  async function place() {
    setBusy(true);
    try {
      const r = await fpost<{ order_no: string }>("/field/orders", { client_ref: ref.current, customer_id: stop.customer_id, requested_delivery_date: when, payment_method: pay,
        visit_id: stop.visit?.id ?? null, lines: lines.map((i) => ({ product_id: i.product_id, quantity: String(qty[i.product_id]) })) });
      ref.current = newRef(); setQty({});
      say(true, `Order ${r.order_no} sent for ${stop.name}.`); reload();
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2">
      <input aria-label={tx("Search products")} placeholder={tx("Search product…")} value={search} onChange={(e) => setSearch(e.target.value)} className={input} />
      <ul className="divide-y max-h-72 overflow-y-auto">{items.map((i) => (
        <li key={i.product_id} className="py-1.5 flex items-center gap-2 text-sm">
          <span className="flex-1 min-w-0"><span className="block truncate">{i.name}</span><span className="text-xs text-gray-500">{kes(i.unit_price, stop.currency)} / {i.uom}</span></span>
          <input type="number" min={0} inputMode="numeric" aria-label={tx("Quantity of {name}", { name: i.name })} value={qty[i.product_id] ?? ""}
            onChange={(e) => setQty({ ...qty, [i.product_id]: Math.max(0, Number(e.target.value) || 0) })} className="w-20 border rounded-lg px-2 py-1.5 text-right" />
        </li>))}</ul>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-gray-600">{tx("Delivery")}<input type="date" value={when} onChange={(e) => setWhen(e.target.value)} className={input} /></label>
        <label className="text-xs text-gray-600">{tx("Payment")}<select value={pay} onChange={(e) => setPay(e.target.value)} className={input}><option value="cash">{tx("Cash")}</option><option value="mpesa">{tx("M-Pesa")}</option><option value="credit">{tx("Credit")}</option></select></label>
      </div>
      <button onClick={place} disabled={busy || lines.length === 0} className={`${btn} w-full bg-indigo-600 text-white`}>{busy ? tx("Sending…") : tx("Send order · {kes}", { kes: kes(total, stop.currency) })}</button>
    </div>
  );
}

// ── cash collector (assigned on dunning cases; no rep link needed) ────────────

function CollectorTab({ say, fail }: Say) {
  const [rows, setRows] = useState<CollectorAccount[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const load = useCallback(() => fx<CollectorAccount[]>("/field/collector/accounts").then(setRows).catch(fail), [fail]);
  useEffect(() => { load(); }, [load]);
  if (!rows) return <p className="text-sm text-gray-500">{tx("Loading…")}</p>;
  return (
    <div className="space-y-2">
      {rows.length === 0 && <p className={box + " text-sm text-gray-500"}>{tx("No accounts to collect from.")}</p>}
      {rows.map((a) => {
        const maps = mapsLink(a.lat, a.lng, a.address);
        return (
          <div key={a.case_id} className={box}>
            <button className="w-full text-left flex justify-between gap-2" aria-expanded={open === a.case_id} onClick={() => setOpen(open === a.case_id ? null : a.case_id)}>
              <span className="min-w-0"><span className="font-medium block truncate">{a.name}</span><span className="text-xs text-gray-500 block truncate">{a.case_no}{a.address ? ` · ${a.address}` : ""}</span></span>
              <span className="text-right text-xs shrink-0"><span className="block text-red-700">{tx("owes")} {kes(a.open_balance, a.currency)}</span>{a.next_action_date && <span className="block text-gray-500">{tx("follow up")} {a.next_action_date}</span>}</span>
            </button>
            {open === a.case_id && <div className="mt-2 border-t pt-2 space-y-2">
              <div className="flex gap-2 text-xs">
                {a.phone && <a href={`tel:${a.phone}`} className="underline text-indigo-700">{tx("Call")} {a.contact ?? ""}</a>}
                {maps && <a href={maps} target="_blank" rel="noreferrer" className="underline text-indigo-700">{tx("Directions")}</a>}
              </div>
              <CollectForm stop={{ customer_id: a.customer_id, name: a.name, phone: a.phone }} say={say} fail={fail} reload={load} />
            </div>}
          </div>);
      })}
    </div>
  );
}

function CollectForm({ stop, say, fail, reload }: Say & { stop: Pick<Stop, "customer_id" | "name" | "phone">; reload: () => void }) {
  const [invoices, setInvoices] = useState<OpenInvoice[]>([]);
  const [form, setForm] = useState({ invoice_id: "", method: "CASH", amount: "", mpesa_code: "", mpesa_phone: stop.phone ?? "", reference: "" });
  const [busy, setBusy] = useState(false);
  const ref = useRef(newRef());
  useEffect(() => { fx<OpenInvoice[]>(`/field/customers/${stop.customer_id}/invoices`).then(setInvoices).catch(fail); }, [stop.customer_id, fail]);
  async function save() {
    setBusy(true);
    try {
      const gps = await currentPosition();
      const r = await fpost<{ collection_no: string }>("/field/collections", { client_ref: ref.current, customer_id: stop.customer_id, invoice_id: form.invoice_id || null,
        method: form.method, amount: form.amount, mpesa_code: form.method === "MPESA" ? form.mpesa_code.toUpperCase() : null,
        mpesa_phone: form.method === "MPESA" && form.mpesa_phone ? form.mpesa_phone : null, reference: form.reference || null, lat: gps?.lat, lng: gps?.lng });
      ref.current = newRef();
      say(true, tx("Collection {collection_no} recorded — give the customer this number as the receipt. Finance confirms it.", { collection_no: r.collection_no })); reload();
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  async function stk() {
    if (!form.invoice_id) return;
    setBusy(true);
    try { await fpost(`/field/invoices/${form.invoice_id}/stk`, { phone: form.mpesa_phone, amount: form.amount }); say(true, "M-Pesa request sent to the customer's phone."); }
    catch (e) { fail(e); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2">
      <select aria-label={tx("Invoice")} value={form.invoice_id} onChange={(e) => { const i = invoices.find((x) => x.id === e.target.value); setForm({ ...form, invoice_id: e.target.value, amount: i ? String(i.outstanding) : form.amount }); }} className={input}>
        <option value="">{tx("Choose the invoice being paid…")}</option>
        {invoices.map((i) => <option key={i.id} value={i.id}>{i.invoice_no} {tx("· due")} {i.due_date} · {kes(i.outstanding, i.currency)}{i.overdue ? tx(" · OVERDUE") : ""}</option>)}
      </select>
      <div className="grid grid-cols-2 gap-2">
        <select aria-label={tx("Payment method")} value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })} className={input}><option value="CASH">{tx("Cash")}</option><option value="MPESA">{tx("M-Pesa")}</option><option value="CHEQUE">{tx("Cheque")}</option></select>
        <input aria-label={tx("Amount")} inputMode="decimal" placeholder={tx("Amount")} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className={input} />
      </div>
      {form.method === "MPESA" && (<div className="grid grid-cols-2 gap-2">
        <input aria-label={tx("M-Pesa code")} placeholder={tx("M-Pesa code e.g. QK12AB34CD")} value={form.mpesa_code} onChange={(e) => setForm({ ...form, mpesa_code: e.target.value })} className={input} />
        <input aria-label={tx("Customer phone")} inputMode="tel" placeholder={tx("Phone 07…")} value={form.mpesa_phone} onChange={(e) => setForm({ ...form, mpesa_phone: e.target.value })} className={input} />
      </div>)}
      {form.method === "CHEQUE" && <input aria-label={tx("Cheque number")} placeholder={tx("Cheque number / bank")} value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} className={input} />}
      {invoices.length === 0 && <p className="text-xs text-gray-500">{tx("No open invoices for this customer.")}</p>}
      <button onClick={save} disabled={busy || !form.amount || !form.invoice_id} className={`${btn} w-full bg-emerald-600 text-white`}>{tx("Record collection")}</button>
      {form.method === "MPESA" && form.invoice_id && <button onClick={stk} disabled={busy || !form.amount || !form.mpesa_phone} className={`${btn} w-full border`}>{tx("Send M-Pesa request to phone")}</button>}
    </div>
  );
}

// ── driver ────────────────────────────────────────────────────────────────────

function TripsTab({ say, fail }: Say) {
  const [trips, setTrips] = useState<Trip[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const load = useCallback(() => fx<Trip[]>("/field/trips").then(setTrips).catch(fail), [fail]);
  useEffect(() => { load(); }, [load]);
  const act = async (path: string, text: string) => { try { await fpost(path, {}); say(true, text); load(); } catch (e) { fail(e); } };
  if (!trips) return <p className="text-sm text-gray-500">{tx("Loading…")}</p>;
  if (trips.length === 0) return <p className={box + " text-sm text-gray-500"}>{tx("No trips assigned for today.")}</p>;
  return (<div className="space-y-3">{trips.map((t) => (
    <div key={t.id} className={box + " space-y-2"}>
      <div className="flex justify-between items-center"><div><p className="font-semibold">{t.trip_no}</p><p className="text-xs text-gray-500">{t.trip_date} · {t.vehicle ?? ""} · {t.status.replace(/_/g, " ").toLowerCase()}</p></div>
        {["PLANNED", "LOADING"].includes(t.status) && <button onClick={() => act(`/field/trips/${t.id}/start`, tx("Trip started."))} className={`${btn} bg-indigo-600 text-white`}>{tx("Start trip")}</button>}
        {t.status === "IN_TRANSIT" && <button onClick={() => act(`/field/trips/${t.id}/finish`, tx("Trip completed."))} className={`${btn} border`}>{tx("Finish trip")}</button>}</div>
      {t.stops.map((s) => (
        <div key={s.id} className="border-t pt-2">
          <button className="w-full text-left flex justify-between" aria-expanded={open === s.id} onClick={() => setOpen(open === s.id ? null : s.id)}>
            <span><span className="font-medium">{s.sequence}. {s.customer}</span><span className="block text-xs text-gray-500">{s.shipment_no} · {s.order_no}</span></span>
            <span className={`text-xs ${s.status === "DELIVERED" ? "text-emerald-700" : s.status === "FAILED" ? "text-red-700" : "text-amber-700"}`}>{s.status.toLowerCase()}</span>
          </button>
          {open === s.id && <DeliveryPanel stop={s} tripActive={t.status === "IN_TRANSIT"} say={say} fail={fail} reload={load} />}
        </div>))}
    </div>))}</div>);
}

function SignaturePad({ onChange }: { onChange: (b: Blob | null) => void }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  useEffect(() => { const c = ref.current!.getContext("2d")!; c.fillStyle = "#fff"; c.fillRect(0, 0, 500, 180); c.lineWidth = 3; c.lineCap = "round"; c.strokeStyle = "#111827"; }, []);
  const pos = (e: React.PointerEvent<HTMLCanvasElement>) => { const r = ref.current!.getBoundingClientRect(); return { x: ((e.clientX - r.left) * 500) / r.width, y: ((e.clientY - r.top) * 180) / r.height }; };
  const done = () => { drawing.current = false; ref.current!.toBlob((b) => onChange(b), "image/png"); };
  const clear = () => { const c = ref.current!.getContext("2d")!; c.fillRect(0, 0, 500, 180); onChange(null); };
  return (<div className="space-y-1">
    <canvas ref={ref} width={500} height={180} aria-label={tx("Customer signature")} className="w-full border-2 border-dashed rounded-lg bg-white touch-none"
      onPointerDown={(e) => { drawing.current = true; const p = pos(e); const c = ref.current!.getContext("2d")!; c.beginPath(); c.moveTo(p.x, p.y); }}
      onPointerMove={(e) => { if (!drawing.current) return; const p = pos(e); const c = ref.current!.getContext("2d")!; c.lineTo(p.x, p.y); c.stroke(); }}
      onPointerUp={done} onPointerLeave={() => { if (drawing.current) done(); }} />
    <button type="button" onClick={clear} className="text-xs underline text-gray-600">{tx("Clear signature")}</button>
  </div>);
}

function DeliveryPanel({ stop, tripActive, say, fail, reload }: Say & { stop: TripStop; tripActive: boolean; reload: () => void }) {
  const [receivedBy, setReceivedBy] = useState("");
  const [sig, setSig] = useState<Blob | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const maps = mapsLink(stop.lat, stop.lng, stop.address);
  async function deliver() {
    setBusy(true);
    try {
      const gps = await currentPosition();
      const fd = new FormData();
      fd.append("received_by", receivedBy);
      if (gps) { fd.append("lat", String(gps.lat)); fd.append("lng", String(gps.lng)); }
      fd.append("signature", sig!, "signature.png");
      for (const p of photos) fd.append("photos", p);
      const r = await fpost<{ id: string | null; duplicate: boolean }>(`/field/trip-orders/${stop.id}/deliver`, fd);
      say(true, r.duplicate ? tx("Delivery to {customer} was already recorded.", { customer: stop.customer }) : `Delivered to ${stop.customer}.`); reload();
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  async function failed() {
    try { await fpost(`/field/trip-orders/${stop.id}/fail`, { reason }); say(true, tx("Marked as not delivered.")); reload(); } catch (e) { fail(e); }
  }
  return (
    <div className="mt-2 space-y-2">
      <div className="flex gap-3 text-xs">{stop.phone && <a href={`tel:${stop.phone}`} className="underline text-indigo-700">{tx("Call")}</a>}{maps && <a href={maps} target="_blank" rel="noreferrer" className="underline text-indigo-700">{tx("Directions")}</a>}</div>
      {stop.status === "FAILED" && <p className="text-xs text-red-700">{tx("Not delivered earlier:")} {stop.failure_reason}{tx(". You can deliver it now if the customer is back.")}</p>}
      {stop.status !== "PENDING" && stop.status !== "FAILED" ? <p className="text-xs text-gray-600">{tx("Delivered.")}</p> : !tripActive ? <p className="text-xs text-amber-700">{tx("Start the trip first.")}</p> : (<>
        <input aria-label={tx("Received by")} placeholder={tx("Name of person receiving")} value={receivedBy} onChange={(e) => setReceivedBy(e.target.value)} className={input} />
        <SignaturePad onChange={setSig} />
        <PhotosInput label={tx("Photos of delivered goods (optional)")} files={photos} onChange={setPhotos} />
        {(receivedBy.trim().length < 2 || !sig) && <p className="text-xs text-amber-700">{tx("To confirm:")} {[receivedBy.trim().length < 2 && "type the name of the person receiving", !sig && "get their signature"].filter(Boolean).join(" and ")}.</p>}
        <button onClick={deliver} disabled={busy || receivedBy.trim().length < 2 || !sig} className={`${btn} w-full bg-emerald-600 text-white`}>{busy ? tx("Saving…") : tx("Confirm delivery")}</button>
        <div className="flex gap-2"><input aria-label={tx("Reason not delivered")} placeholder={tx("Reason not delivered")} value={reason} onChange={(e) => setReason(e.target.value)} className={input} />
          <button onClick={failed} disabled={reason.trim().length < 3} className={`${btn} border shrink-0`}>{tx("Not delivered")}</button></div>
      </>)}
    </div>
  );
}

// ── field controller ──────────────────────────────────────────────────────────

function AuditsTab({ say, fail }: Say) {
  const sentPhotos = useRef(0);
  const [items, setItems] = useState<{ key: string; label: string }[]>([]);
  const [search, setSearch] = useState("");
  const [outlets, setOutlets] = useState<{ customer_id: string; name: string; route: string; rep: string | null }[]>([]);
  const [outlet, setOutlet] = useState<{ customer_id: string; name: string } | null>(null);
  const [ans, setAns] = useState<Record<string, { ok: boolean; note: string }>>({});
  const [notes, setNotes] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [recent, setRecent] = useState<AuditRow[]>([]);
  const [busy, setBusy] = useState(false);
  const ref = useRef(newRef());
  const loadRecent = useCallback(() => fx<AuditRow[]>("/field/audits?days=7").then(setRecent).catch(fail), [fail]);
  useEffect(() => { fx<{ key: string; label: string }[]>("/field/audit-checklist").then((r) => { setItems(r); setAns(Object.fromEntries(r.map((i) => [i.key, { ok: true, note: "" }]))); }).catch(fail); loadRecent(); }, [fail, loadRecent]);
  useEffect(() => {
    if (search.trim().length < 2) { setOutlets([]); return; }
    const t = setTimeout(() => fx<typeof outlets>(`/field/audit-outlets?search=${encodeURIComponent(search)}`).then(setOutlets).catch(fail), 250);
    return () => clearTimeout(t);
  }, [search, fail]);
  async function submit() {
    if (!outlet) return;
    setBusy(true);
    try {
      const gps = await currentPosition();
      const r = await fpost<{ id: string; audit_no: string; score: number }>("/field/audits", { client_ref: ref.current, customer_id: outlet.customer_id, notes: notes || null,
        lat: gps?.lat, lng: gps?.lng, answers: items.map((i) => ({ key: i.key, ok: ans[i.key].ok, note: ans[i.key].note || null })) });
      // a retry replays the same audit (client_ref): send only the photos not uploaded yet
      for (const p of photos.slice(sentPhotos.current)) { const fd = new FormData(); fd.append("file", p); await fpost(`/field/audits/${r.id}/photo`, fd); sentPhotos.current += 1; }
      sentPhotos.current = 0;
      ref.current = newRef(); setOutlet(null); setNotes(""); setPhotos([]); setAns(Object.fromEntries(items.map((i) => [i.key, { ok: true, note: "" }])));
      say(true, tx("Audit {audit_no} saved — score {score}%.", { audit_no: r.audit_no, score: r.score })); loadRecent();
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-3">
      <div className={box + " space-y-2"}>
        {!outlet ? (<>
          <input aria-label={tx("Find outlet")} placeholder={tx("Find outlet by name or code…")} value={search} onChange={(e) => setSearch(e.target.value)} className={input} />
          {outlets.map((o) => <button key={o.customer_id} onClick={() => setOutlet(o)} className="block w-full text-left text-sm border-t py-2"><span className="font-medium">{o.name}</span><span className="block text-xs text-gray-500">{o.route} {tx("· rep")} {o.rep ?? "—"}</span></button>)}
        </>) : (<>
          <p className="font-semibold flex justify-between">{outlet.name}<button onClick={() => setOutlet(null)} className="text-xs underline font-normal">{tx("change")}</button></p>
          {items.map((i) => (
            <div key={i.key} className="border-t pt-2">
              <div className="flex justify-between items-center gap-2 text-sm"><span>{i.label}</span>
                <span className="flex gap-1 shrink-0" role="radiogroup" aria-label={i.label}>
                  {[true, false].map((v) => <button key={String(v)} role="radio" aria-checked={ans[i.key]?.ok === v} onClick={() => setAns({ ...ans, [i.key]: { ...ans[i.key], ok: v } })}
                    className={`${btn} ${ans[i.key]?.ok === v ? (v ? "bg-emerald-600 text-white" : "bg-red-600 text-white") : "bg-gray-100"}`}>{v ? "OK" : tx("Not OK")}</button>)}
                </span></div>
              {ans[i.key] && !ans[i.key].ok && <input aria-label={tx("Note: {label}", { label: i.label })} placeholder={tx("What is wrong?")} value={ans[i.key].note} onChange={(e) => setAns({ ...ans, [i.key]: { ...ans[i.key], note: e.target.value } })} className={input + " mt-1"} />}
            </div>))}
          <textarea aria-label={tx("Audit notes")} placeholder={tx("Notes")} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className={input} />
          <PhotosInput label={tx("Photos (shelf, fridge…)")} files={photos} onChange={setPhotos} />
          <button onClick={submit} disabled={busy} className={`${btn} w-full bg-indigo-600 text-white`}>{busy ? tx("Saving…") : tx("Save audit")}</button>
        </>)}
      </div>
      <div className={box}><h2 className="font-semibold text-sm mb-1">{tx("My audits (7 days)")}</h2>
        {recent.length === 0 ? <p className="text-sm text-gray-500">{tx("None yet.")}</p> : recent.map((a) => (
          <p key={a.id} className="text-sm border-t py-1.5 flex justify-between gap-2"><span className="min-w-0 truncate">{a.outlet}{a.failed.length ? <span className="block text-xs text-red-700 truncate">{a.failed.join(", ")}</span> : null}</span><span className="shrink-0 font-semibold">{a.score}%</span></p>))}
      </div>
    </div>
  );
}


// Merchandiser shelf check (M40.S01.T004): per product facings, out of stock, shelf price, planogram, photo.
interface ShelfLine { product_id: string; name: string; facings: string; out_of_stock: boolean; shelf_price: string; planogram_ok: boolean | null; photo: File | null; saved?: boolean }
function ShelfForm({ stop, say, fail }: Say & { stop: Stop }) {
  const visitId = stop.visit!.id;
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [search, setSearch] = useState("");
  const [lines, setLines] = useState<ShelfLine[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fx<{ product_id: string; product: string; facings: number; out_of_stock: boolean; shelf_price: number | null; planogram_ok: boolean | null }[]>(`/field/visits/${visitId}/shelf`)
      .then((rows) => setLines(rows.map((r) => ({ product_id: r.product_id, name: r.product, facings: String(r.facings), out_of_stock: r.out_of_stock,
        shelf_price: r.shelf_price === null ? "" : String(r.shelf_price), planogram_ok: r.planogram_ok, photo: null, saved: true })))).catch(fail);
  }, [visitId, fail]);
  useEffect(() => {
    const t = setTimeout(() => fx<{ items: CatalogItem[] }>(`/field/catalog?customer_id=${stop.customer_id}&search=${encodeURIComponent(search)}`).then((r) => setItems(r.items)).catch(fail), 250);
    return () => clearTimeout(t);
  }, [search, stop.customer_id, fail]);
  const add = (i: CatalogItem) => { if (!lines.some((l) => l.product_id === i.product_id))
    setLines([...lines, { product_id: i.product_id, name: i.name, facings: "", out_of_stock: false, shelf_price: "", planogram_ok: null, photo: null }]); setSearch(""); };
  const upd = (id: string, patch: Partial<ShelfLine>) => setLines((ls) => ls.map((l) => (l.product_id === id ? { ...l, ...patch } : l)));
  async function save() {
    setBusy(true);
    try {
      const rows = await fx<{ id: string; product_id: string }[]>(`/field/visits/${visitId}/shelf`, { method: "PUT", body: JSON.stringify({ lines: lines.map((l) => ({
        product_id: l.product_id, facings: Number(l.facings) || 0, out_of_stock: l.out_of_stock,
        shelf_price: l.shelf_price === "" ? null : l.shelf_price, planogram_ok: l.planogram_ok })) }) });
      for (const l of lines.filter((x) => x.photo)) {
        const row = rows.find((r) => r.product_id === l.product_id);
        if (row) { const fd = new FormData(); fd.append("file", l.photo!); await fpost(`/field/shelf/${row.id}/photo`, fd); }
      }
      setLines((ls) => ls.map((l) => ({ ...l, photo: null, saved: true })));
      say(true, tx("Shelf check for {name} saved ({length} products).", { name: stop.name, length: lines.length }));
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-2">
      <input aria-label={tx("Add product to shelf check")} placeholder={tx("Add product…")} value={search} onChange={(e) => setSearch(e.target.value)} className={input} />
      {search && <ul className="divide-y max-h-40 overflow-y-auto border rounded-lg">{items.slice(0, 8).map((i) => (
        <li key={i.product_id}><button onClick={() => add(i)} className="w-full text-left px-2 py-1.5 text-sm">{i.name}</button></li>))}</ul>}
      {lines.map((l) => (
        <div key={l.product_id} className="border rounded-lg p-2 space-y-1.5 text-sm">
          <p className="font-medium">{l.name}</p>
          <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={l.out_of_stock} onChange={(e) => upd(l.product_id, { out_of_stock: e.target.checked })} /> {tx("Out of stock on the shelf")}</label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-gray-600">{tx("Facings")}<input type="number" min={0} inputMode="numeric" aria-label={tx("Facings of {name}", { name: l.name })} disabled={l.out_of_stock} value={l.out_of_stock ? "0" : l.facings} onChange={(e) => upd(l.product_id, { facings: e.target.value })} className={input} /></label>
            <label className="text-xs text-gray-600">{tx("Shelf price")}<input type="number" min={0} step="0.01" inputMode="decimal" aria-label={tx("Shelf price of {name}", { name: l.name })} value={l.shelf_price} onChange={(e) => upd(l.product_id, { shelf_price: e.target.value })} className={input} /></label>
          </div>
          <div className="flex gap-2 text-xs" role="radiogroup" aria-label={tx("Planogram for {name}", { name: l.name })}>
            <span className="text-gray-600 self-center">{tx("Planogram:")}</span>
            {([[true, tx("As agreed")], [false, tx("Not as agreed")]] as const).map(([v, t]) => (
              <button key={t} type="button" role="radio" aria-checked={l.planogram_ok === v} onClick={() => upd(l.product_id, { planogram_ok: v })}
                className={`px-2 py-1 rounded border ${l.planogram_ok === v ? (v ? "bg-emerald-600 text-white" : "bg-red-600 text-white") : ""}`}>{t}</button>))}
          </div>
          <PhotoInput label={tx("Shelf photo (optional)")} onFile={(f) => upd(l.product_id, { photo: f })} />
        </div>))}
      <button onClick={save} disabled={busy || lines.length === 0} className={`${btn} w-full bg-indigo-600 text-white`}>{busy ? tx("Saving…") : tx("Save shelf check")}</button>
    </div>
  );
}
