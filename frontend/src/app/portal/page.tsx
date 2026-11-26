"use client";
// Distributor / customer portal: catalog + cart (server prices), my orders, invoices & statement, claims. Mobile-first.
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import {
  ps, post, PortalError,
  type PortalMe, type CatalogItem, type PortalOrder, type PortalOrderDetail, type PortalStatement, type PortalClaim, type OrderTracking, type PaymentOptions,
} from "@/lib/portalSelf";
import { MESSAGES, useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Tab = "order" | "promotions" | "orders" | "statement" | "claims" | "support" | "feedback" | "points";
interface ShopPromotion { code: string; name: string; valid_from: string; valid_to: string; only_for_you: boolean; offers: string[] }
type Cart = Record<string, { item: CatalogItem; qty: number }>;
type T = ReturnType<typeof useI18n>["t"];
const CLAIM_TYPES = ["SHORTAGE_CLAIM", "DAMAGE_CLAIM", "RETURN_REQUEST", "DELIVERY_DISCREPANCY", "PRICING_DISPUTE", "PRODUCT_COMPLAINT"];
const newRef = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const tomorrow = () => new Date(Date.now() + 86400000).toISOString().slice(0, 10);
/** Translated label for an API enum value (portal.<group>.<VALUE>); unknown values are shown as received. */
const label = (t: T, group: string, value: string, fallback = value) =>
  `portal.${group}.${value}` in MESSAGES.en ? t(`portal.${group}.${value}`) : fallback;
const TABS: Tab[] = ["order", "promotions", "orders", "statement", "claims", "support", "feedback", "points"];

export default function PartnerPortal() {
  const router = useRouter();
  const { t, err } = useI18n();
  const [me, setMe] = useState<PortalMe | null>(null);
  const [tab, setTab] = useState<Tab>("order");
  // the HTTP status of the failed request; the message is translated at render time (server text is English)
  const [error, setError] = useState<{ status?: number } | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const fail = useCallback((e: unknown) => {
    if (e instanceof PortalError && e.status === 401) { router.replace("/portal/login"); return; }
    setError({ status: e instanceof PortalError ? e.status : undefined });
  }, [router]);

  useEffect(() => { ps<PortalMe>("/me").then(setMe).catch(fail); }, [fail]);
  // M47 review fix: a signed-in shop user verifies this browser's analytics id as their own (only with marketing consent;
  // the server checks consent again). Only verified identities drive form shortening and web-event workflows.
  useEffect(() => {
    try {
      const c = JSON.parse(localStorage.getItem("povu_consent_v1") || "null");
      const visitor = localStorage.getItem("povu_vid");
      if (c?.marketing && visitor) ps("/web-identity", { method: "POST", body: JSON.stringify({ visitor }), headers: { "Content-Type": "application/json" } }).catch(() => {});
    } catch { /* storage blocked */ }
  }, []);

  async function signOut() {
    await post("/auth/logout").catch(() => undefined);
    router.replace("/portal/login");
  }

  if (!me) return <main className="p-6 text-sm text-gray-500">{error ? err(error.status) : t("common.loading")}</main>;
  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-indigo-700 text-white px-4 py-3 flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold truncate">{me.customer_name ?? me.account_code}</p>
          <p className="text-xs text-indigo-200 truncate">{me.full_name} · {label(t, "role", me.role)}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3 shrink-0">
          <LanguageSwitcher />
          <button onClick={signOut} className="text-sm underline">{t("common.signOut")}</button>
        </div>
      </header>
      <nav aria-label={t("portal.nav.label")} className="grid grid-cols-3 md:flex md:flex-wrap bg-white border-b text-sm">
        {TABS.map((k) => (
          <button key={k} onClick={() => { setTab(k); setError(null); setInfo(null); }} aria-current={tab === k ? "page" : undefined}
            className={`min-w-0 break-words px-2 md:px-4 py-3 leading-tight md:whitespace-nowrap ${tab === k ? "border-b-2 border-indigo-600 font-semibold text-indigo-700" : "text-gray-600"}`}>{t(`portal.tab.${k}`)}</button>
        ))}
      </nav>
      <div className="max-w-4xl mx-auto p-4 space-y-4">
        {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{err(error.status)}</p>}
        {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}
        {!me.linked ? <p className="rounded-lg p-4 bg-amber-50 border border-amber-200 text-amber-800 text-sm">{t("portal.notLinked")}</p> : (<>
          {tab === "order" && <OrderTab me={me} fail={fail} onPlaced={(no) => { setInfo(t("portal.orderPlaced", { no })); setError(null); }} />}
          {tab === "promotions" && <PromotionsTab fail={fail} />}
          {tab === "orders" && <OrdersTab me={me} fail={fail} />}
          {tab === "statement" && <StatementTab me={me} fail={fail} />}
          {tab === "claims" && <ClaimsTab me={me} fail={fail} onDone={(no) => setInfo(t("portal.claimSubmitted", { no }))} />}
          {tab === "support" && <SupportTab fail={fail} onDone={(msg) => setInfo(msg)} />}
          {tab === "feedback" && <FeedbackTab fail={fail} onDone={(msg) => setInfo(msg)} />}
          {tab === "points" && <PointsTab fail={fail} />}
        </>)}
      </div>
    </main>
  );
}

function OrderTab({ me, fail, onPlaced }: { me: PortalMe; fail: (e: unknown) => void; onPlaced: (no: string) => void }) {
  const { t, f } = useI18n();
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [cart, setCart] = useState<Cart>(() => {
    try { return JSON.parse(sessionStorage.getItem("portal-cart") ?? "{}") as Cart; } catch { return {}; }
  });
  const [delivery, setDelivery] = useState(tomorrow());
  const [notes, setNotes] = useState("");
  const [ref, setRef] = useState(newRef);
  const [busy, setBusy] = useState(false);
  const [payOpts, setPayOpts] = useState<PaymentOptions | null>(null);
  const [pay, setPay] = useState("");
  useEffect(() => { ps<PaymentOptions>("/payment-options").then((o) => { setPayOpts(o); setPay(o.default); }).catch(fail); }, [fail]);

  useEffect(() => {
    const tm = setTimeout(() => {
      ps<{ items: CatalogItem[] }>(`/catalog?search=${encodeURIComponent(search)}`).then((r) => setItems(r.items)).catch(fail);
    }, 250);
    return () => clearTimeout(tm);
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
      const r = await post<{ order_no: string; promotions?: string[] }>("/orders", {
        client_ref: ref, requested_delivery_date: delivery, notes: notes || null, payment_method: pay || null,
        lines: lines.map((l) => ({ product_id: l.item.product_id, quantity: String(l.qty) })),
      });
      setCart({}); setNotes(""); setRef(newRef());
      onPlaced(r.promotions?.length ? t("portal.orderPlacedPromos", { no: r.order_no, list: r.promotions.join("; ") }) : r.order_no);
    } catch (e) { fail(e); } finally { setBusy(false); }
  }

  return (
    <div className="grid md:grid-cols-[1fr_320px] gap-4">
      <section aria-label={t("portal.catalog.label")} className="min-w-0 bg-white rounded-xl border p-3 space-y-2">
        <input aria-label={t("portal.catalog.search")} placeholder={t("portal.catalog.searchPlaceholder")} value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm" maxLength={100} />
        {items.length === 0 ? <p className="text-sm text-gray-400 p-2">{t("portal.catalog.empty")}</p> : (
          <ul className="divide-y">{items.map((i) => (
            <li key={i.product_id} className="py-2 flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{i.name}</p>
                <p className="text-xs text-gray-500 break-words">{i.sku} · {i.uom}{i.units_per_carton > 1 ? ` · ${t("portal.catalog.perCarton", { n: i.units_per_carton })}` : ""} · {f.money(i.unit_price, me.currency)}</p>
              </div>
              <input type="number" min={0} step={1} inputMode="numeric" aria-label={t("portal.catalog.qtyOf", { name: i.name })} disabled={!me.can_order}
                value={cart[i.product_id]?.qty ?? ""} onChange={(e) => setQty(i, Math.max(0, Number(e.target.value) || 0))}
                className="w-20 border rounded-lg px-2 py-1.5 text-sm text-right" />
            </li>))}</ul>)}
      </section>
      <aside aria-label={t("portal.cart.label")} className="min-w-0 bg-white rounded-xl border p-3 space-y-3 h-fit md:sticky md:top-4">
        <h2 className="font-semibold">{t("portal.cart.title", { n: lines.length })}</h2>
        {!me.can_order && <p className="text-xs text-amber-700">{t("portal.cart.viewOnly")}</p>}
        {lines.map((l) => <p key={l.item.product_id} className="text-sm flex justify-between gap-2"><span className="truncate">{l.qty} × {l.item.name}</span><span className="shrink-0">{f.money(l.item.unit_price == null ? null : l.item.unit_price * l.qty, me.currency)}</span></p>)}
        {me.can_view_prices && <p className="text-sm font-semibold flex justify-between gap-2 border-t pt-2"><span className="min-w-0">{t("portal.cart.totalExTax")}</span><span className="shrink-0">{f.money(total, me.currency)}</span></p>}
        <label className="block text-xs text-gray-600">{t("portal.cart.delivery")}
          <input type="date" min={new Date().toISOString().slice(0, 10)} value={delivery} onChange={(e) => setDelivery(e.target.value)} className="mt-1 w-full border rounded-lg px-2 py-1.5 text-sm" />
        </label>
        {payOpts && (
          <label className="block text-xs text-gray-600">{t("portal.cart.payment")}
            <select value={pay} onChange={(e) => setPay(e.target.value)} className="mt-1 w-full border rounded-lg px-2 py-1.5 text-sm">
              {payOpts.allowed.map((m) => <option key={m} value={m}>{PAY_TEXT[m]?.(payOpts, t) ?? m}</option>)}
            </select>
          </label>)}
        <textarea aria-label={t("portal.cart.notes")} placeholder={t("portal.cart.notesPlaceholder")} maxLength={1000} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full border rounded-lg px-2 py-1.5 text-sm" />
        <button onClick={place} disabled={busy || !me.can_order || lines.length === 0}
          className="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium disabled:opacity-50">{busy ? t("portal.sending") : t("portal.cart.place")}</button>
        <p className="text-xs text-gray-400">{t("portal.cart.note")}</p>
      </aside>
    </div>
  );
}

const PAY_TEXT: Record<string, (o: PaymentOptions, t: T) => string> = {
  cash: (_o, t) => t("portal.pay.cash"),
  mpesa: (o, t) => (o.prepaid ? t("portal.pay.mpesaPrepaid") : t("portal.pay.mpesa")),
  credit: (o, t) => t("portal.pay.credit", { days: o.terms_days }),
};

/** Promotions for this shop. List prices are the same for every shop; promotions are applied on top and shown on the invoice. */
function PromotionsTab({ fail }: { fail: (e: unknown) => void }) {
  const { t, f } = useI18n();
  const [rows, setRows] = useState<ShopPromotion[] | null>(null);
  useEffect(() => { ps<ShopPromotion[]>("/promotions").then(setRows).catch(fail); }, [fail]);
  if (rows === null) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (rows.length === 0) return <p className="bg-white rounded-xl border p-4 text-sm text-gray-500">{t("portal.promo.empty")}</p>;
  return (
    <section aria-label={t("portal.tab.promotions")} className="bg-white rounded-xl border overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500"><tr>
          <th className="px-3 py-2 text-left">{t("portal.promo.col.name")}</th><th className="px-3 py-2 text-left">{t("portal.promo.col.offers")}</th><th className="px-3 py-2 text-left">{t("portal.promo.col.valid")}</th>
        </tr></thead>
        <tbody>{rows.map((p) => (
          <tr key={p.code} className="border-t align-top">
            <td className="px-3 py-2 font-medium">{p.name}{p.only_for_you && <span className="ml-2 text-xs text-indigo-700">{t("portal.promo.justForYou")}</span>}</td>
            <td className="px-3 py-2">{p.offers.map((o) => <div key={o}>{o}</div>)}</td>
            <td className="px-3 py-2 whitespace-nowrap">{f.date(p.valid_from)} – {f.date(p.valid_to)}</td>
          </tr>))}
        </tbody>
      </table>
      <p className="px-3 py-2 text-xs text-gray-500">{t("portal.promo.note")}</p>
    </section>
  );
}

function OrdersTab({ me, fail }: { me: PortalMe; fail: (e: unknown) => void }) {
  const { t, f } = useI18n();
  const [rows, setRows] = useState<PortalOrder[] | null>(null);
  const [open, setOpen] = useState<PortalOrderDetail | null>(null);
  const [payMsg, setPayMsg] = useState<string | null>(null);
  async function payMpesa(id: string) {
    setPayMsg(null);
    try {
      const r = await post<{ amount: number; phone_hint: string }>(`/orders/${id}/pay-mpesa`, {});
      setPayMsg(t("portal.orders.mpesaSent", { amount: f.money(r.amount, me.currency), phone: r.phone_hint }));
    } catch (e) { fail(e); }
  }
  useEffect(() => { ps<PortalOrder[]>("/orders").then(setRows).catch(fail); }, [fail]);

  function reorder(d: PortalOrderDetail) {
    const cart: Cart = {};
    for (const l of d.lines) cart[l.product_id] = { item: { product_id: l.product_id, sku: l.sku, name: l.product_name, uom: l.unit, units_per_carton: 1, unit_price: l.unit_price }, qty: l.ordered_quantity };
    try { sessionStorage.setItem("portal-cart", JSON.stringify(cart)); } catch { /* ignore */ }
    window.location.reload();  // opens "New order" with the cart filled; current prices apply when placed
  }

  if (!rows) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (rows.length === 0) return <p className="text-sm text-gray-500">{t("portal.orders.empty")}</p>;
  return (
    <div className="space-y-2">
      {rows.map((o) => (
        <div key={o.id} className="bg-white rounded-xl border p-3">
          <button className="w-full text-left flex justify-between gap-2" aria-expanded={open?.id === o.id}
            onClick={() => open?.id === o.id ? setOpen(null) : ps<PortalOrderDetail>(`/orders/${o.id}`).then(setOpen).catch(fail)}>
            <span className="min-w-0 break-words"><span className="font-medium">{o.order_no}</span><span className="block text-xs text-gray-500">{f.date(o.order_date)} · {t("portal.orders.deliver", { date: f.date(o.requested_delivery_date) })}</span></span>
            <span className="min-w-0 max-w-[50%] text-right text-sm break-words"><span className="block">{label(t, "status", o.status.replace(/^.*\./, ""), o.status)}</span><span className="text-xs text-gray-500">{f.money(o.total, o.currency)}</span></span>
          </button>
          {open?.id === o.id && (
            <div className="mt-2 border-t pt-2 text-sm space-y-1">
              {open.tracking && <Tracking t={open.tracking} />}
              {open.lines.map((l) => <p key={l.product_id} className="flex justify-between gap-2"><span className="min-w-0 break-words">{l.ordered_quantity} × {l.product_name}</span><span className="shrink-0 text-gray-500">{t("portal.orders.shipped", { n: l.shipped_quantity })}</span></p>)}
              {open.shipments.map((s) => { const v = s.status.replace(/^.*\./, ""); return <p key={s.id} className="text-xs text-gray-600">{t("portal.orders.shipment", { no: s.shipment_no, status: label(t, "shipment", v), date: f.date(s.scheduled_date) })}</p>; })}
              {open.invoices.map((i) => <p key={i.id} className="text-xs text-gray-600">{t("portal.orders.invoice", { no: i.invoice_no, amount: f.money(i.total_amount, o.currency) })}</p>)}
              {me.can_order && open.status !== "CANCELLED" && open.payment_status !== "paid" && (open.tracking?.stage ?? "") !== "delivered" && open.payment_method === "mpesa" && (
                <button onClick={() => payMpesa(open.id)} className="block w-full py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium">{t("portal.orders.payMpesa")}</button>)}
              {payMsg && <p role="status" className="text-xs text-emerald-700">{payMsg}</p>}
              {me.can_order && <button onClick={() => reorder(open)} className="text-xs underline text-indigo-700">{t("portal.orders.again")}</button>}
            </div>)}
        </div>))}
    </div>
  );
}

function Tracking({ t: tr }: { t: OrderTracking }) {
  const { t, f } = useI18n();
  if (tr.stage === "cancelled") return <p className="text-sm font-medium text-red-700">{t("portal.track.cancelled")}</p>;
  const at = tr.stages.indexOf(tr.stage);
  return (
    <div className="pb-2" data-testid="order-tracking">
      <ol className="flex items-start gap-1" aria-label={t("portal.track.progress")}>
        {tr.stages.map((s, i) => (
          <li key={s} className="flex-1 min-w-0 text-center" aria-current={i === at ? "step" : undefined}>
            <span className={`block h-1.5 rounded-full ${i <= at ? "bg-emerald-500" : "bg-gray-200"}`} />
            <span className={`block mt-1 text-[11px] leading-tight break-words ${i === at ? "font-semibold text-gray-900" : "text-gray-500"}`}>{label(t, "stage", s)}</span>
          </li>))}
      </ol>
      <p className="mt-2 text-sm text-gray-800" role="status">
        {tr.stage === "delivered" ? (tr.delivered_at ? t("portal.track.deliveredAt", { time: f.time(tr.delivered_at) }) : t("portal.track.delivered"))
          : tr.eta ? (tr.stops_before
            ? t(tr.stops_before > 1 ? "portal.track.etaStops_other" : "portal.track.etaStops_one", { time: f.time(tr.eta), n: tr.stops_before })
            : t("portal.track.eta", { time: f.time(tr.eta) }))
          : tr.eta_date ? t("portal.track.planned", { date: f.date(tr.eta_date) }) : null}
      </p>
    </div>
  );
}

function StatementTab({ me, fail }: { me: PortalMe; fail: (e: unknown) => void }) {
  const { t, f } = useI18n();
  const [st, setSt] = useState<PortalStatement | null>(null);
  useEffect(() => { ps<PortalStatement>("/statement").then(setSt).catch(fail); }, [fail]);
  if (!st) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 text-center">
        {([["portal.st.invoiced", st.total_invoiced], ["portal.st.paid", st.total_paid], ["portal.st.balance", st.outstanding_balance]] as [string, number][]).map(([k, v]) => (
          <div key={k} className="min-w-0 bg-white rounded-xl border p-3 break-words"><p className="text-xs text-gray-500">{t(k)}</p><p className="font-semibold text-sm">{f.money(v, me.currency)}</p></div>))}
      </div>
      <div className="bg-white rounded-xl border overflow-x-auto">
        <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th className="p-2">{t("portal.st.col.invoice")}</th><th>{t("common.date")}</th><th>{t("portal.st.col.due")}</th><th>{t("common.total")}</th><th>{t("portal.st.col.open")}</th></tr></thead>
          <tbody>{st.invoices.map((i) => <tr key={i.id} className="border-t"><td className="p-2">{i.invoice_no}</td><td>{f.date(i.invoice_date)}</td><td>{f.date(i.due_date)}</td><td>{f.money(i.total_amount, i.currency)}</td><td>{f.money(i.outstanding, i.currency)}</td></tr>)}</tbody>
        </table>
        {st.invoices.length === 0 && <p className="p-3 text-sm text-gray-500">{t("portal.st.empty")}</p>}
      </div>
    </div>
  );
}

function ClaimsTab({ me, fail, onDone }: { me: PortalMe; fail: (e: unknown) => void; onDone: (no: string) => void }) {
  const { t } = useI18n();
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
        <form onSubmit={submit} aria-label={t("portal.claim.form")} className="bg-white rounded-xl border p-3 grid gap-2 sm:grid-cols-2">
          <select aria-label={t("portal.claim.type")} value={form.claim_type} onChange={(e) => setForm({ ...form, claim_type: e.target.value })} className="min-w-0 border rounded-lg px-2 py-1.5 text-sm">
            {CLAIM_TYPES.map((ct) => <option key={ct} value={ct}>{label(t, "claimType", ct, ct.replace(/_/g, " ").toLowerCase())}</option>)}
          </select>
          <select aria-label={t("portal.claim.order")} value={form.linked_order_id} onChange={(e) => setForm({ ...form, linked_order_id: e.target.value })} className="min-w-0 border rounded-lg px-2 py-1.5 text-sm">
            <option value="">{t("portal.claim.noOrder")}</option>
            {orders.map((o) => <option key={o.id} value={o.id}>{o.order_no}</option>)}
          </select>
          <textarea aria-label={t("portal.claim.what")} required maxLength={2000} rows={2} placeholder={t("portal.claim.what")} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="sm:col-span-2 border rounded-lg px-2 py-1.5 text-sm" />
          <button className="sm:col-start-2 py-2 rounded-lg bg-indigo-600 text-white text-sm">{t("portal.claim.submit")}</button>
        </form>)}
      {rows.length === 0 ? <p className="text-sm text-gray-500">{t("portal.claim.empty")}</p> : rows.map((c) => (
        <div key={c.id} className="bg-white rounded-xl border p-3 text-sm">
          <p className="flex justify-between gap-2"><span className="min-w-0 break-words font-medium">{c.claim_no}</span><span className="min-w-0 text-right break-words">{label(t, "claimStatus", c.status, c.status.replace(/_/g, " ").toLowerCase())}</span></p>
          <p className="text-gray-600 break-words">{c.reason}</p>
          {c.resolution_notes && <p className="text-xs text-emerald-700">{t("portal.resolution", { text: c.resolution_notes })}</p>}
        </div>))}
    </div>
  );
}

interface Ticket { id: string; ticket_no: string; category: string; status: string; subject: string; created_at: string | null; resolution_notes: string | null; rating?: number | null;
  description?: string; thread?: { body: string; from_us: boolean; at: string | null }[];
  attachments?: { id: string; file_name: string; size: number; from_customer: boolean; downloadable: boolean; scan_status: string }[] }

function SupportTab({ fail, onDone }: { fail: (e: unknown) => void; onDone: (msg: string) => void }) {
  const { t, f } = useI18n();
  const [rows, setRows] = useState<Ticket[]>([]);
  const [open, setOpen] = useState<Ticket | null>(null);
  const [form, setForm] = useState({ category: "DELIVERY", subject: "", description: "" });
  const [reply, setReply] = useState("");
  const [uploading, setUploading] = useState(false);
  const [rateNote, setRateNote] = useState("");
  const load = useCallback(() => { ps<Ticket[]>("/tickets").then(setRows).catch(fail); }, [fail]);
  useEffect(load, [load]);
  const show = (id: string) => ps<Ticket>(`/tickets/${id}`).then(setOpen).catch(fail);

  return (
    <div className="space-y-3">
      <form aria-label={t("portal.ticket.form")} className="bg-white rounded-xl border p-3 grid gap-2 sm:grid-cols-2" onSubmit={async (e) => {
        e.preventDefault();
        try { const r = await post<{ ticket_no: string }>("/tickets", form); setForm({ ...form, subject: "", description: "" }); onDone(t("portal.ticketOpened", { no: r.ticket_no })); load(); }
        catch (err) { fail(err); }
      }}>
        <select aria-label={t("portal.ticket.topic")} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="min-w-0 border rounded-lg px-2 py-1.5 text-sm">
          {["DELIVERY", "BILLING", "QUALITY", "PRODUCT", "OTHER"].map((c) => <option key={c} value={c}>{label(t, "topic", c, c.toLowerCase())}</option>)}
        </select>
        <input aria-label={t("portal.ticket.subject")} required minLength={3} maxLength={200} placeholder={t("portal.ticket.subject")} value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="min-w-0 border rounded-lg px-2 py-1.5 text-sm" />
        <textarea aria-label={t("portal.ticket.describe")} required minLength={3} maxLength={4000} rows={3} placeholder={t("portal.ticket.describe")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="sm:col-span-2 border rounded-lg px-2 py-1.5 text-sm" />
        <button className="sm:col-start-2 py-2 rounded-lg bg-indigo-600 text-white text-sm">{t("portal.ticket.open")}</button>
      </form>
      {rows.length === 0 ? <p className="text-sm text-gray-500">{t("portal.ticket.empty")}</p> : rows.map((tk) => (
        <div key={tk.id} className="bg-white rounded-xl border p-3 text-sm">
          <button className="w-full text-left flex justify-between gap-2" aria-expanded={open?.id === tk.id} onClick={() => open?.id === tk.id ? setOpen(null) : show(tk.id)}>
            <span className="min-w-0 break-words"><span className="font-medium">{tk.subject}</span><span className="block text-xs text-gray-500">{tk.ticket_no} · {label(t, "topic", tk.category, tk.category.toLowerCase())}</span></span>
            <span className="min-w-0 max-w-[40%] text-right text-xs break-words">{label(t, "ticketStatus", tk.status, tk.status.replace(/_/g, " ").toLowerCase())}</span>
          </button>
          {open?.id === tk.id && (
            <div className="mt-2 border-t pt-2 space-y-2">
              <p className="text-gray-700 whitespace-pre-line break-words">{open.description}</p>
              {(open.thread ?? []).map((m, i) => <p key={i} className={`rounded-lg p-2 whitespace-pre-line break-words ${m.from_us ? "bg-indigo-50" : "bg-gray-50"}`}><span className="block text-xs text-gray-500">{m.from_us ? t("portal.ticket.ourTeam") : t("portal.ticket.you")}{m.at ? ` · ${f.dateTime(m.at)}` : ""}</span>{m.body}</p>)}
              {(open.attachments ?? []).length > 0 && (
                <ul aria-label={t("portal.ticket.files")} className="text-xs space-y-1">
                  {(open.attachments ?? []).map((a) => (
                    <li key={a.id} className="flex flex-wrap gap-2 items-center">
                      <span>📎</span>
                      {a.downloadable
                        ? <a className="text-indigo-700 underline break-all" href={`${API_ORIGIN}/api/v1/portal-self/tickets/${open.id}/attachments/${a.id}`}>{a.file_name}</a>
                        : <span className="break-all">{a.file_name}</span>}
                      <span className="text-gray-500">{a.from_customer ? t("portal.ticket.you") : t("portal.ticket.ourTeam")} · {t("portal.ticket.size", { size: f.number(Math.max(1, Math.round(a.size / 1024))) })}{a.downloadable ? "" : ` · ${t("portal.ticket.checking")}`}</span>
                    </li>
                  ))}
                </ul>
              )}
              {open.resolution_notes && <p className="text-xs text-emerald-700">{t("portal.resolution", { text: open.resolution_notes })}</p>}
              {(open.status === "RESOLVED" || open.status === "CLOSED") && (open.rating
                ? <p className="text-xs text-gray-600">{t("portal.ticket.yourRating", { stars: "★".repeat(open.rating) + "☆".repeat(5 - open.rating) })}</p>
                : <div role="group" aria-label={t("portal.ticket.rateGroup")} className="rounded-lg bg-amber-50 p-2 space-y-1.5">
                    <p className="text-xs font-medium text-amber-900">{t("portal.ticket.rateQ")}</p>
                    <input aria-label={t("portal.commentOptional")} placeholder={t("portal.commentOptional")} value={rateNote} onChange={(e) => setRateNote(e.target.value)} className="w-full border rounded-lg px-2 py-1 text-xs" />
                    <div className="flex flex-wrap gap-1">{[1, 2, 3, 4, 5].map((n) => (
                      <button key={n} aria-label={t("portal.ticket.stars", { n })} onClick={async () => { try { await post(`/tickets/${open.id}/rate`, { score: n, comment: rateNote || null }); setRateNote(""); onDone(t("portal.ratingThanks")); show(open.id); } catch (e) { fail(e); } }}
                        className="w-9 h-9 rounded-lg border bg-white text-sm leading-none">{n}★</button>))}</div>
                  </div>)}
              {open.status !== "CLOSED" && (
                <label className="text-xs text-indigo-700 inline-flex items-center gap-1 cursor-pointer">
                  <input type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.docx,.xlsx" disabled={uploading}
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (!file) return;
                      setUploading(true);
                      try { const fd = new FormData(); fd.append("file", file); await ps(`/tickets/${open.id}/attachments`, { method: "POST", body: fd }); show(open.id); }
                      catch (err) { fail(err); } finally { setUploading(false); }
                    }} />
                  {uploading ? t("portal.ticket.uploading") : t("portal.ticket.addFile")}
                </label>)}
              {open.status !== "CLOSED" && (
                <div className="flex gap-2"><input aria-label={t("portal.ticket.reply")} placeholder={t("portal.ticket.replyPlaceholder")} value={reply} onChange={(e) => setReply(e.target.value)} className="flex-1 min-w-0 border rounded-lg px-2 py-1.5" />
                  <button disabled={!reply.trim()} onClick={async () => { try { await post(`/tickets/${open.id}/reply`, { body: reply }); setReply(""); show(open.id); load(); } catch (e) { fail(e); } }} className="shrink-0 px-3 rounded-lg bg-indigo-600 text-white disabled:opacity-50">{t("common.send")}</button></div>)}
            </div>)}
        </div>))}
    </div>
  );
}


// ── Feedback (NPS) and loyalty points (M40.S01.T001) ─────────────────────────
interface OpenSurvey { survey_id: string; so_id: string | null; order_no: string | null; question: string; follow_up: string | null }

function ScoreScale({ value, onChange }: { value: number | null; onChange: (n: number) => void }) {
  const { t } = useI18n();
  return (
    <div role="radiogroup" aria-label={t("portal.fb.scale")} className="grid grid-cols-11 gap-1">
      {Array.from({ length: 11 }, (_, n) => (
        <button key={n} type="button" role="radio" aria-checked={value === n} onClick={() => onChange(n)}
          className={`py-2 rounded text-sm border ${value === n ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-700"}`}>{n}</button>
      ))}
      <span className="col-span-5 text-[11px] text-gray-500">{t("portal.fb.notLikely")}</span><span className="col-span-6 text-right text-[11px] text-gray-500">{t("portal.fb.veryLikely")}</span>
    </div>
  );
}

function FeedbackTab({ fail, onDone }: { fail: (e: unknown) => void; onDone: (msg: string) => void }) {
  const { t } = useI18n();
  const [rows, setRows] = useState<OpenSurvey[] | null>(null);
  const [score, setScore] = useState<Record<string, number>>({});
  const [comment, setComment] = useState<Record<string, string>>({});
  const load = useCallback(() => { ps<OpenSurvey[]>("/feedback").then(setRows).catch(fail); }, [fail]);
  useEffect(load, [load]);
  const key = (r: OpenSurvey) => `${r.survey_id}:${r.so_id ?? ""}`;
  if (!rows) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (!rows.length) return <p className="text-sm text-gray-500">{t("portal.fb.empty")}</p>;
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <form key={key(r)} aria-label={r.question} className="bg-white rounded-xl border p-3 space-y-2" onSubmit={async (e) => {
          e.preventDefault();
          if (score[key(r)] === undefined) return;
          try { await post("/feedback", { survey_id: r.survey_id, so_id: r.so_id, score: score[key(r)], comment: comment[key(r)] || null }); onDone(t("portal.feedbackThanks")); load(); }
          catch (err) { fail(err); }
        }}>
          <p className="text-sm font-medium">{r.question}</p>
          {r.order_no && <p className="text-xs text-gray-500">{t("portal.fb.order", { no: r.order_no })}</p>}
          <ScoreScale value={score[key(r)] ?? null} onChange={(n) => setScore({ ...score, [key(r)]: n })} />
          <textarea aria-label={t("portal.commentOptional")} maxLength={2000} rows={2} placeholder={r.follow_up ?? t("portal.fb.placeholder")}
            value={comment[key(r)] ?? ""} onChange={(e) => setComment({ ...comment, [key(r)]: e.target.value })} className="w-full border rounded-lg px-2 py-1.5 text-sm" />
          <button disabled={score[key(r)] === undefined} className="w-full py-2 rounded-lg bg-indigo-600 text-white text-sm disabled:opacity-50">{t("common.send")}</button>
        </form>
      ))}
    </div>
  );
}

interface Points { enrolled: boolean; balance?: number; lifetime?: number; tier?: string | null;
  next_tier?: { name: string; points_needed: number } | null; history?: { at: string; type: string; points: number; balance_after: number; description: string | null }[] }

function PointsTab({ fail }: { fail: (e: unknown) => void }) {
  const { t, f } = useI18n();
  const [p, setP] = useState<Points | null>(null);
  useEffect(() => { ps<Points>("/loyalty").then(setP).catch(fail); }, [fail]);
  if (!p) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (!p.enrolled) return <p className="text-sm text-gray-600 bg-white rounded-xl border p-4">{t("portal.pts.notEnrolled")}</p>;
  return (
    <div className="space-y-3">
      <div className="bg-white rounded-xl border p-4 grid grid-cols-2 gap-2 text-sm">
        <div className="min-w-0"><p className="text-xs text-gray-500">{t("portal.pts.points")}</p><p className="text-2xl font-bold text-indigo-700 break-words">{f.number(p.balance)}</p></div>
        <div className="min-w-0"><p className="text-xs text-gray-500">{t("portal.pts.level")}</p><p className="text-lg font-semibold break-words">{p.tier ?? "—"}</p></div>
        {p.next_tier && <p className="col-span-2 text-xs text-gray-600">{t("portal.pts.next", { n: f.number(p.next_tier.points_needed), tier: p.next_tier.name })}</p>}
      </div>
      <div className="bg-white rounded-xl border divide-y text-sm">
        {(p.history ?? []).length === 0 ? <p className="p-3 text-gray-500">{t("portal.pts.empty")}</p> : p.history!.map((h, i) => (
          <div key={i} className="p-3 flex justify-between gap-2">
            <span className="min-w-0 break-words"><span className="block">{h.description ?? label(t, "pts.type", h.type, h.type.toLowerCase())}</span><span className="text-xs text-gray-500">{h.at ? f.date(h.at) : ""}</span></span>
            <span className={`shrink-0 font-semibold ${h.points >= 0 ? "text-emerald-700" : "text-red-700"}`}>{h.points > 0 ? "+" : ""}{f.number(h.points)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
