"use client";
// Distributor / customer portal: catalog + cart (server prices), my orders, invoices & statement, claims. Mobile-first.
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ps, post, money, statusText, PortalError,
  type PortalMe, type CatalogItem, type PortalOrder, type PortalOrderDetail, type PortalStatement, type PortalClaim,
} from "@/lib/portalSelf";

type Tab = "order" | "orders" | "statement" | "claims";
type Cart = Record<string, { item: CatalogItem; qty: number }>;
const CLAIM_TYPES = ["SHORTAGE_CLAIM", "DAMAGE_CLAIM", "RETURN_REQUEST", "DELIVERY_DISCREPANCY", "PRICING_DISPUTE", "PRODUCT_COMPLAINT"];
const newRef = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const tomorrow = () => new Date(Date.now() + 86400000).toISOString().slice(0, 10);

export default function PartnerPortal() {
  const router = useRouter();
  const [me, setMe] = useState<PortalMe | null>(null);
  const [tab, setTab] = useState<Tab>("order");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const fail = useCallback((e: unknown) => {
    if (e instanceof PortalError && e.status === 401) { router.replace("/portal/login"); return; }
    setError((e as Error).message);
  }, [router]);

  useEffect(() => { ps<PortalMe>("/me").then(setMe).catch(fail); }, [fail]);

  async function signOut() {
    await post("/auth/logout").catch(() => undefined);
    router.replace("/portal/login");
  }

  if (!me) return <main className="p-6 text-sm text-gray-500">{error ?? "Loading…"}</main>;
  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-indigo-700 text-white px-4 py-3 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold truncate">{me.customer_name ?? me.account_code}</p>
          <p className="text-xs text-indigo-200 truncate">{me.full_name} · {me.role}</p>
        </div>
        <button onClick={signOut} className="text-sm underline shrink-0">Sign out</button>
      </header>
      <nav aria-label="Portal sections" className="flex overflow-x-auto bg-white border-b text-sm">
        {([["order", "New order"], ["orders", "My orders"], ["statement", "Invoices & statement"], ["claims", "Claims"]] as [Tab, string][]).map(([k, label]) => (
          <button key={k} onClick={() => { setTab(k); setError(null); setInfo(null); }} aria-current={tab === k ? "page" : undefined}
            className={`px-4 py-3 whitespace-nowrap ${tab === k ? "border-b-2 border-indigo-600 font-semibold text-indigo-700" : "text-gray-600"}`}>{label}</button>
        ))}
      </nav>
      <div className="max-w-4xl mx-auto p-4 space-y-4">
        {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
        {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}
        {!me.linked ? <p className="rounded-lg p-4 bg-amber-50 border border-amber-200 text-amber-800 text-sm">Your account is not linked to a customer yet. Please contact your sales representative.</p> : (<>
          {tab === "order" && <OrderTab me={me} fail={fail} onPlaced={(no) => { setInfo(`Order ${no} received. Our sales team will confirm it.`); setError(null); }} />}
          {tab === "orders" && <OrdersTab me={me} fail={fail} />}
          {tab === "statement" && <StatementTab me={me} fail={fail} />}
          {tab === "claims" && <ClaimsTab me={me} fail={fail} onDone={(no) => setInfo(`Claim ${no} submitted.`)} />}
        </>)}
      </div>
    </main>
  );
}

function OrderTab({ me, fail, onPlaced }: { me: PortalMe; fail: (e: unknown) => void; onPlaced: (no: string) => void }) {
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [cart, setCart] = useState<Cart>(() => {
    try { return JSON.parse(sessionStorage.getItem("portal-cart") ?? "{}") as Cart; } catch { return {}; }
  });
  const [delivery, setDelivery] = useState(tomorrow());
  const [notes, setNotes] = useState("");
  const [ref, setRef] = useState(newRef);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      ps<{ items: CatalogItem[] }>(`/catalog?search=${encodeURIComponent(search)}`).then((r) => setItems(r.items)).catch(fail);
    }, 250);
    return () => clearTimeout(t);
  }, [search, fail]);
  useEffect(() => { try { sessionStorage.setItem("portal-cart", JSON.stringify(cart)); } catch { /* private mode */ } }, [cart]);

  const setQty = (item: CatalogItem, qty: number) => setCart((c) => {
    const next = { ...c };
    if (qty > 0) next[item.product_id] = { item, qty }; else delete next[item.product_id];
    return next;
  });
  const lines = Object.values(cart);
  const total = useMemo(() => lines.reduce((s, l) => s + (l.item.unit_price ?? 0) * l.qty, 0), [lines]);

  async function place() {
    setBusy(true);
    try {
      const r = await post<{ order_no: string }>("/orders", {
        client_ref: ref, requested_delivery_date: delivery, notes: notes || null,
        lines: lines.map((l) => ({ product_id: l.item.product_id, quantity: String(l.qty) })),
      });
      setCart({}); setNotes(""); setRef(newRef());
      onPlaced(r.order_no);
    } catch (e) { fail(e); } finally { setBusy(false); }
  }

  return (
    <div className="grid md:grid-cols-[1fr_320px] gap-4">
      <section aria-label="Catalog" className="bg-white rounded-xl border p-3 space-y-2">
        <input aria-label="Search products" placeholder="Search product or SKU…" value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm" maxLength={100} />
        {items.length === 0 ? <p className="text-sm text-gray-400 p-2">No products found.</p> : (
          <ul className="divide-y">{items.map((i) => (
            <li key={i.product_id} className="py-2 flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{i.name}</p>
                <p className="text-xs text-gray-500">{i.sku} · {i.uom}{i.units_per_carton > 1 ? ` · ${i.units_per_carton}/carton` : ""} · {money(i.unit_price, me.currency)}</p>
              </div>
              <input type="number" min={0} step={1} inputMode="numeric" aria-label={`Quantity of ${i.name}`} disabled={!me.can_order}
                value={cart[i.product_id]?.qty ?? ""} onChange={(e) => setQty(i, Math.max(0, Number(e.target.value) || 0))}
                className="w-20 border rounded-lg px-2 py-1.5 text-sm text-right" />
            </li>))}</ul>)}
      </section>
      <aside aria-label="Cart" className="bg-white rounded-xl border p-3 space-y-3 h-fit md:sticky md:top-4">
        <h2 className="font-semibold">Cart ({lines.length})</h2>
        {!me.can_order && <p className="text-xs text-amber-700">Your role can view but not place orders.</p>}
        {lines.map((l) => <p key={l.item.product_id} className="text-sm flex justify-between gap-2"><span className="truncate">{l.qty} × {l.item.name}</span><span>{money(l.item.unit_price == null ? null : l.item.unit_price * l.qty, me.currency)}</span></p>)}
        {me.can_view_prices && <p className="text-sm font-semibold flex justify-between border-t pt-2"><span>Total (excl. tax)</span><span>{money(total, me.currency)}</span></p>}
        <label className="block text-xs text-gray-600">Delivery date
          <input type="date" min={new Date().toISOString().slice(0, 10)} value={delivery} onChange={(e) => setDelivery(e.target.value)} className="mt-1 w-full border rounded-lg px-2 py-1.5 text-sm" />
        </label>
        <textarea aria-label="Order notes" placeholder="Notes (delivery gate, contact…)" maxLength={1000} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full border rounded-lg px-2 py-1.5 text-sm" />
        <button onClick={place} disabled={busy || !me.can_order || lines.length === 0}
          className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium disabled:opacity-50">{busy ? "Sending…" : "Place order"}</button>
        <p className="text-xs text-gray-400">Prices are confirmed by our system; the order is confirmed by our sales team (credit check).</p>
      </aside>
    </div>
  );
}

function OrdersTab({ me, fail }: { me: PortalMe; fail: (e: unknown) => void }) {
  const [rows, setRows] = useState<PortalOrder[] | null>(null);
  const [open, setOpen] = useState<PortalOrderDetail | null>(null);
  useEffect(() => { ps<PortalOrder[]>("/orders").then(setRows).catch(fail); }, [fail]);

  function reorder(d: PortalOrderDetail) {
    const cart: Cart = {};
    for (const l of d.lines) cart[l.product_id] = { item: { product_id: l.product_id, sku: l.sku, name: l.product_name, uom: l.unit, units_per_carton: 1, unit_price: l.unit_price }, qty: l.ordered_quantity };
    try { sessionStorage.setItem("portal-cart", JSON.stringify(cart)); } catch { /* ignore */ }
    window.location.reload();  // opens "New order" with the cart filled; current prices apply when placed
  }

  if (!rows) return <p className="text-sm text-gray-500">Loading…</p>;
  if (rows.length === 0) return <p className="text-sm text-gray-500">No orders yet.</p>;
  return (
    <div className="space-y-2">
      {rows.map((o) => (
        <div key={o.id} className="bg-white rounded-xl border p-3">
          <button className="w-full text-left flex justify-between gap-2" aria-expanded={open?.id === o.id}
            onClick={() => open?.id === o.id ? setOpen(null) : ps<PortalOrderDetail>(`/orders/${o.id}`).then(setOpen).catch(fail)}>
            <span><span className="font-medium">{o.order_no}</span><span className="block text-xs text-gray-500">{o.order_date} · deliver {o.requested_delivery_date}</span></span>
            <span className="text-right text-sm"><span className="block">{statusText(o.status)}</span><span className="text-xs text-gray-500">{money(o.total, o.currency)}</span></span>
          </button>
          {open?.id === o.id && (
            <div className="mt-2 border-t pt-2 text-sm space-y-1">
              {open.lines.map((l) => <p key={l.product_id} className="flex justify-between"><span>{l.ordered_quantity} × {l.product_name}</span><span className="text-gray-500">shipped {l.shipped_quantity}</span></p>)}
              {open.shipments.map((s) => <p key={s.id} className="text-xs text-gray-600">Shipment {s.shipment_no}: {s.status.replace(/^.*\./, "")} ({s.scheduled_date})</p>)}
              {open.invoices.map((i) => <p key={i.id} className="text-xs text-gray-600">Invoice {i.invoice_no}: {money(i.total_amount, o.currency)}</p>)}
              {me.can_order && <button onClick={() => reorder(open)} className="text-xs underline text-indigo-700">Order again</button>}
            </div>)}
        </div>))}
    </div>
  );
}

function StatementTab({ me, fail }: { me: PortalMe; fail: (e: unknown) => void }) {
  const [st, setSt] = useState<PortalStatement | null>(null);
  useEffect(() => { ps<PortalStatement>("/statement").then(setSt).catch(fail); }, [fail]);
  if (!st) return <p className="text-sm text-gray-500">Loading…</p>;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 text-center">
        {([["Invoiced", st.total_invoiced], ["Paid", st.total_paid], ["Balance", st.outstanding_balance]] as [string, number][]).map(([k, v]) => (
          <div key={k} className="bg-white rounded-xl border p-3"><p className="text-xs text-gray-500">{k}</p><p className="font-semibold text-sm">{money(v, me.currency)}</p></div>))}
      </div>
      <div className="bg-white rounded-xl border overflow-x-auto">
        <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th className="p-2">Invoice</th><th>Date</th><th>Due</th><th>Total</th><th>Open</th></tr></thead>
          <tbody>{st.invoices.map((i) => <tr key={i.id} className="border-t"><td className="p-2">{i.invoice_no}</td><td>{i.invoice_date}</td><td>{i.due_date}</td><td>{money(i.total_amount, i.currency)}</td><td>{money(i.outstanding, i.currency)}</td></tr>)}</tbody>
        </table>
        {st.invoices.length === 0 && <p className="p-3 text-sm text-gray-500">No invoices yet.</p>}
      </div>
    </div>
  );
}

function ClaimsTab({ me, fail, onDone }: { me: PortalMe; fail: (e: unknown) => void; onDone: (no: string) => void }) {
  const [rows, setRows] = useState<PortalClaim[]>([]);
  const [orders, setOrders] = useState<PortalOrder[]>([]);
  const [form, setForm] = useState({ claim_type: CLAIM_TYPES[0], linked_order_id: "", reason: "" });
  const load = useCallback(() => { ps<PortalClaim[]>("/claims").then(setRows).catch(fail); ps<PortalOrder[]>("/orders").then(setOrders).catch(fail); }, [fail]);
  useEffect(load, [load]);
  const canClaim = ["OWNER", "BUYER", "LOGISTICS"].includes(me.role);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await post<{ claim_no: string }>("/claims", { ...form, linked_order_id: form.linked_order_id || null });
      setForm({ ...form, reason: "" }); onDone(r.claim_no); load();
    } catch (err) { fail(err); }
  }

  return (
    <div className="space-y-3">
      {canClaim && (
        <form onSubmit={submit} aria-label="New claim" className="bg-white rounded-xl border p-3 grid gap-2 sm:grid-cols-2">
          <select aria-label="Claim type" value={form.claim_type} onChange={(e) => setForm({ ...form, claim_type: e.target.value })} className="border rounded-lg px-2 py-1.5 text-sm">
            {CLAIM_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ").toLowerCase()}</option>)}
          </select>
          <select aria-label="Related order" value={form.linked_order_id} onChange={(e) => setForm({ ...form, linked_order_id: e.target.value })} className="border rounded-lg px-2 py-1.5 text-sm">
            <option value="">No specific order</option>
            {orders.map((o) => <option key={o.id} value={o.id}>{o.order_no}</option>)}
          </select>
          <textarea aria-label="What happened" required maxLength={2000} rows={2} placeholder="What happened?" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="sm:col-span-2 border rounded-lg px-2 py-1.5 text-sm" />
          <button className="sm:col-start-2 py-2 rounded-lg bg-indigo-600 text-white text-sm">Submit claim</button>
        </form>)}
      {rows.length === 0 ? <p className="text-sm text-gray-500">No claims.</p> : rows.map((c) => (
        <div key={c.id} className="bg-white rounded-xl border p-3 text-sm">
          <p className="flex justify-between"><span className="font-medium">{c.claim_no}</span><span>{c.status.replace(/_/g, " ").toLowerCase()}</span></p>
          <p className="text-gray-600">{c.reason}</p>
          {c.resolution_notes && <p className="text-xs text-emerald-700">Resolution: {c.resolution_notes}</p>}
        </div>))}
    </div>
  );
}
