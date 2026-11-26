"use client";

import { useState } from "react";
import { CPQPanel } from "@/components/sales/CPQPanel";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  quoteApi, Quotation, QuoteStatus, QuoteCreate, QuoteLineCreate,
  STATUS_COLORS, fmtCcy, fmtDate,
} from "@/lib/quotations";
import { salesApi, Customer } from "@/lib/sales";
import { productsApi, Product } from "@/lib/products";
import { Button } from "@/components/ui/Button";
import { tx } from "@/lib/i18n/core";

// ── KPI card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <span className="text-2xl font-bold text-gray-900">{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: QuoteStatus }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLORS[status]}`}>
      {status}
    </span>
  );
}

function ViewOnlyBadge({ reason }: { reason?: string | null }) {
  return (
    <span
      title={reason ?? tx("You can view this record but cannot modify it in this scope.")}
      className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"
    >
      {tx("View only")}
    </span>
  );
}

// ── Line editor ───────────────────────────────────────────────────────────────

interface LineEditorProps {
  lines: QuoteLineCreate[];
  products: Product[];
  onChange: (lines: QuoteLineCreate[]) => void;
}

function LineEditor({ lines, products, onChange }: LineEditorProps) {
  const add = () =>
    onChange([...lines, { line_no: lines.length + 1, product_id: "", qty: 1, unit: "PCS", unit_price: 0, discount_pct: 0, tax_rate: 16 }]);
  const remove = (i: number) => onChange(lines.filter((_, idx) => idx !== i).map((l, idx) => ({ ...l, line_no: idx + 1 })));
  const update = (i: number, field: keyof QuoteLineCreate, v: string | number) => {
    const next = lines.map((l, idx) => idx === i ? { ...l, [field]: v } : l);
    onChange(next);
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">{tx("Line Items")}</span>
        <button onClick={add} className="text-xs text-blue-600 hover:underline">{tx("+ Add line")}</button>
      </div>
      {lines.length === 0 && <p className="text-xs text-gray-400">{tx("No lines yet. Add a product.")}</p>}
      {lines.map((l, i) => {
        const prod = products.find(p => p.id === l.product_id);
        const lineTotal = l.qty * l.unit_price * (1 - l.discount_pct / 100) * (1 + l.tax_rate / 100);
        return (
          <div key={i} className="border rounded p-2 space-y-2 bg-gray-50">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-500">{tx("Product")}</label>
                <select
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={l.product_id ?? ""}
                  onChange={e => {
                    const p = products.find(pr => pr.id === e.target.value);
                    const next = { ...l, product_id: e.target.value, unit_price: p ? (p.selling_price ?? 0) : l.unit_price };
                    onChange(lines.map((ll, idx) => idx === i ? next : ll));
                  }}
                >
                  <option value="">{tx("— select product —")}</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">{tx("Description (optional)")}</label>
                <input
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={l.description ?? ""}
                  onChange={e => update(i, "description", e.target.value)}
                  placeholder={tx("Free text override")}
                />
              </div>
            </div>
            <div className="grid grid-cols-5 gap-2">
              <div>
                <label className="text-xs text-gray-500">{tx("Qty")}</label>
                <input type="number" min={0} step={0.001} className="w-full border rounded px-2 py-1 text-sm" value={l.qty}
                  onChange={e => update(i, "qty", parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">{tx("Unit")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm" value={l.unit}
                  onChange={e => update(i, "unit", e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">{tx("Unit Price")}</label>
                <input type="number" min={0} step={0.01} className="w-full border rounded px-2 py-1 text-sm" value={l.unit_price}
                  onChange={e => update(i, "unit_price", parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">{tx("Disc %")}</label>
                <input type="number" min={0} max={100} step={0.01} className="w-full border rounded px-2 py-1 text-sm" value={l.discount_pct}
                  onChange={e => update(i, "discount_pct", parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">{tx("Tax %")}</label>
                <input type="number" min={0} max={100} step={0.01} className="w-full border rounded px-2 py-1 text-sm" value={l.tax_rate}
                  onChange={e => update(i, "tax_rate", parseFloat(e.target.value) || 0)} />
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">{tx("Line total:")} <strong>{lineTotal.toFixed(2)}</strong></span>
              <button onClick={() => remove(i)} className="text-xs text-red-500 hover:underline">{tx("Remove")}</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Create modal ──────────────────────────────────────────────────────────────

function CreateModal({ customers, products, onClose, editing }: {
  customers: Customer[];
  products: Product[];
  onClose: () => void;
  editing?: Quotation;   // a draft being changed (e.g. after its discount was rejected)
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<QuoteCreate>(editing ? {
    customer_id: editing.customer_id,
    quote_date: editing.quote_date,
    valid_until: editing.valid_until ?? "",
    currency: editing.currency,
    discount_pct: Number(editing.discount_pct),
    notes: editing.notes ?? "",
    lines: editing.lines.map((l) => ({
      line_no: l.line_no, product_id: l.product_id ?? undefined, description: l.description ?? undefined,
      qty: Number(l.qty), unit: l.unit, unit_price: Number(l.unit_price), discount_pct: Number(l.discount_pct), tax_rate: Number(l.tax_rate),
    })),
  } : {
    customer_id: "",
    quote_date: new Date().toISOString().slice(0, 10),
    valid_until: "",
    currency: "KES",
    discount_pct: 0,
    notes: "",
    lines: [],
  });

  const mut = useMutation({
    mutationFn: () => {
      const { customer_id: _c, quote_date: _d, ...rest } = form;
      return editing
        ? quoteApi.update(editing.id, { ...rest, valid_until: form.valid_until || undefined })
        : quoteApi.create({ ...form, valid_until: form.valid_until || undefined });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["quotes"] }); onClose(); },
  });

  const totalGrand = form.lines.reduce((s, l) =>
    s + l.qty * l.unit_price * (1 - l.discount_pct / 100) * (1 + l.tax_rate / 100), 0
  ) * (1 - form.discount_pct / 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">{editing ? tx("Edit {quote_no}", { quote_no: editing.quote_no }) : tx("New Quotation")}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700">{tx("Customer *")}</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1" disabled={!!editing}
              value={form.customer_id} onChange={e => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">{tx("— select —")}</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">{tx("Currency")}</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })}>
              {["KES", "USD", "EUR", "GBP"].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">{tx("Quote Date *")}</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.quote_date} onChange={e => setForm({ ...form, quote_date: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">{tx("Valid Until")}</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.valid_until ?? ""} onChange={e => setForm({ ...form, valid_until: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">{tx("Overall Discount %")}</label>
            <input type="number" min={0} max={100} step={0.01} className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.discount_pct} onChange={e => setForm({ ...form, discount_pct: parseFloat(e.target.value) || 0 })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">{tx("Notes")}</label>
            <input className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.notes ?? ""} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>

        <LineEditor lines={form.lines} products={products} onChange={lines => setForm({ ...form, lines })} />

        <div className="flex justify-between items-center pt-2 border-t">
          <div className="text-sm text-gray-600">
            {tx("Estimated Grand Total:")} <strong className="text-gray-900">{fmtCcy(totalGrand, form.currency)}</strong>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>{tx("Cancel")}</Button>
            <Button onClick={() => mut.mutate()} disabled={!form.customer_id || mut.isPending}>
              {mut.isPending ? tx("Saving…") : editing ? tx("Save changes") : tx("Create Quote")}
            </Button>
          </div>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Reject modal ──────────────────────────────────────────────────────────────

function RejectModal({ quote, onClose }: { quote: Quotation; onClose: () => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const mut = useMutation({
    mutationFn: () => quoteApi.reject(quote.id, reason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["quotes"] }); onClose(); },
  });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-80 space-y-4 shadow-xl">
        <h3 className="font-semibold text-gray-800">{tx("Reject Quote")} {quote.quote_no}</h3>
        <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3}
          placeholder={tx("Reason for rejection (optional)")} value={reason} onChange={e => setReason(e.target.value)} />
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>{tx("Cancel")}</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending} className="bg-red-600 hover:bg-red-700">
            {mut.isPending ? tx("Rejecting…") : tx("Reject")}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Row actions ───────────────────────────────────────────────────────────────

function SharePanel({ quote, onClose }: { quote: Quotation; onClose: () => void }) {
  const qc = useQueryClient();
  const [days, setDays] = useState(14);
  const [label, setLabel] = useState("");
  const [password, setPassword] = useState("");
  const [newUrl, setNewUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const links = useQuery({ queryKey: ["share-links", quote.id], queryFn: () => quoteApi.shareLinks(quote.id) });
  const signed = useQuery({ queryKey: ["quote-decision", quote.id], queryFn: () => quoteApi.decision(quote.id) });
  const refresh = () => qc.invalidateQueries({ queryKey: ["share-links", quote.id] });
  const create = useMutation({
    mutationFn: () => quoteApi.createShareLink(quote.id, { expires_in_days: days, label: label || undefined, password: password || undefined }),
    onSuccess: (r) => { setNewUrl(r.url); setErr(null); refresh(); },
    onError: (e: Error) => setErr(e.message),
  });
  const revoke = useMutation({ mutationFn: (id: string) => quoteApi.revokeShareLink(id), onSuccess: refresh, onError: (e: Error) => setErr(e.message) });
  const when = (v: string | null) => (v ? new Date(v).toLocaleString() : "—");
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-5 space-y-3 max-h-full overflow-y-auto">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold">{tx("Share")} {quote.quote_no}</h2>
          <button onClick={onClose} className="text-gray-400 text-xl" aria-label={tx("Close")}>×</button>
        </div>
        {signed.data?.decision && (
          <p role="status" className={`text-sm rounded p-2 border ${signed.data.unchanged_since_signing ? "border-emerald-300" : "border-red-400"}`}>
            {signed.data.decision === "ACCEPTED" ? tx("Accepted") : tx("Declined")} {tx("online by")} {signed.data.signer_name} ({signed.data.signer_email}{signed.data.email_verified_at ? tx(", e-mail verified by code") : tx(", e-mail not verified")}{tx(") on")} {when(signed.data.decided_at ?? null)}{tx(", ref")} {signed.data.reference}.
            {signed.data.reason ? tx(" Reason: {reason}.", { reason: signed.data.reason }) : ""}{" "}
            {signed.data.unchanged_since_signing ? tx("Content unchanged since signing.") : tx("WARNING: the quotation content changed after signing.")}
          </p>
        )}
        <p className="text-xs text-gray-500">{tx("The customer opens the quotation without signing in and sees prices, lines and customer notes only (never internal notes). You see when it was opened; no IP address is stored.")}</p>
        <div className="flex flex-wrap gap-2 items-center">
          <input aria-label={tx("Who is it for")} placeholder={tx("Who is it for (optional)")} value={label} onChange={(e) => setLabel(e.target.value)} className="border rounded px-2 py-1.5 text-sm flex-1 min-w-[10rem]" />
          <select aria-label={tx("Valid for")} value={days} onChange={(e) => setDays(Number(e.target.value))} className="border rounded px-2 py-1.5 text-sm">
            {[3, 7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{d} {tx("days")}</option>)}
          </select>
          <input aria-label={tx("Password (optional)")} type="password" placeholder={tx("Password (optional)")} value={password} onChange={(e) => setPassword(e.target.value)} className="border rounded px-2 py-1.5 text-sm w-40" />
          <button disabled={create.isPending} onClick={() => create.mutate()} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded">{tx("Create link")}</button>
        </div>
        <CPQPanel key={`${quote.id}:${quote.approval_status ?? ""}:${quote.discount_approved_at ?? ""}:${quote.grand_total ?? ""}`} quoteId={quote.id} status={quote.status} onChanged={() => qc.invalidateQueries({ queryKey: ["quotes"] })} />
        {newUrl && (
          <div className="space-y-1">
            <p className="text-xs text-emerald-700">{tx("Copy it now; it is shown only once.")}</p>
            <input readOnly value={newUrl} onFocus={(e) => e.currentTarget.select()} aria-label={tx("Share link")} className="w-full border rounded px-2 py-1 text-xs font-mono" />
          </div>
        )}
        {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr className="text-left text-gray-500"><th className="py-1">{tx("For")}</th><th>{tx("State")}</th><th>{tx("Views")}</th><th>{tx("Last opened")}</th><th>{tx("Expires")}</th><th /></tr></thead>
            <tbody>
              {(links.data ?? []).map((l) => (
                <tr key={l.id} className="border-t">
                  <td className="py-1.5">{l.label ?? "—"}</td><td>{l.state}</td><td>{l.views}</td><td>{when(l.last_viewed_at)}</td>
                  <td>{new Date(l.expires_at).toLocaleDateString()}</td>
                  <td>{l.state === "ACTIVE" && <button onClick={() => revoke.mutate(l.id)} className="text-red-600 underline">{tx("Turn off")}</button>}</td>
                </tr>
              ))}
              {links.data && links.data.length === 0 && <tr><td colSpan={6} className="py-2 text-gray-400">{tx("No links yet.")}</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function QuoteActions({ quote, onReject, onEdit }: { quote: Quotation; onReject: () => void; onEdit: () => void }) {
  const qc = useQueryClient();
  const useQuoteMutation = (fn: () => Promise<unknown>) =>
    useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ["quotes"] }) });

  const sendM = useQuoteMutation(() => quoteApi.send(quote.id));
  const acceptM = useQuoteMutation(() => quoteApi.accept(quote.id));
  const expireM = useQuoteMutation(() => quoteApi.expire(quote.id));
  const reviseM = useQuoteMutation(() => quoteApi.revise(quote.id));
  const convertM = useQuoteMutation(() => quoteApi.convert(quote.id));
  const discountM = useMutation({
    mutationFn: (v: { approve: boolean; reason?: string }) => quoteApi.decideDiscount(quote.id, v.approve, v.reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quotes"] }),
  });
  const failed = [sendM, acceptM, expireM, reviseM, convertM, discountM].find((m) => m.isError)?.error as Error | undefined;
  const discountWaiting = quote.approval_status === "PENDING_DISCOUNT";
  const discountRejected = quote.approval_status === "DISCOUNT_REJECTED";

  const busy = sendM.isPending || acceptM.isPending || expireM.isPending || reviseM.isPending || convertM.isPending || discountM.isPending;
  const access = quote.access;
  const [sharing, setSharing] = useState(false);

  if (access?.view_only) {
    return <ViewOnlyBadge reason={access.reason} />;
  }

  return (
    <div className="flex flex-wrap gap-1">
      {discountWaiting && <span className="text-xs px-2 py-1 rounded bg-amber-50 text-amber-800">{tx("Discount waiting for approval")}</span>}
      {discountRejected && <span className="text-xs px-2 py-1 rounded bg-red-50 text-red-700">{tx("Discount rejected — change it")}</span>}
      {quote.approval_status === "DISCOUNT_APPROVED" && <span className="text-xs px-2 py-1 rounded bg-green-50 text-green-700">{tx("Discount approved")}</span>}
      {access?.can_discount_approve && (
        <>
          <button disabled={busy} onClick={() => discountM.mutate({ approve: true })}
            className="text-xs px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700">{tx("Approve discount")}</button>
          <button disabled={busy} onClick={() => { const reason = window.prompt(tx("Why is the discount rejected?")); if (reason?.trim()) discountM.mutate({ approve: false, reason }); }}
            className="text-xs px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700">{tx("Reject discount")}</button>
        </>
      )}
      {quote.status === "DRAFT" && (access?.can_edit ?? true) && (
        <button disabled={busy} onClick={onEdit}
          className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 hover:bg-gray-200">{tx("Edit")}</button>
      )}
      {quote.status === "DRAFT" && !discountWaiting && !discountRejected && (access?.can_edit ?? true) && (
        <button disabled={busy} onClick={() => sendM.mutate()}
          className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100">{tx("Send")}</button>
      )}
      {quote.status === "SENT" && (access?.can_approve ?? true) && (
        <>
          <button disabled={busy} onClick={() => acceptM.mutate()}
            className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100">{tx("Accept")}</button>
          <button disabled={busy} onClick={onReject}
            className="text-xs px-2 py-1 rounded bg-red-50 text-red-700 hover:bg-red-100">{tx("Reject")}</button>
        </>
      )}
      {quote.status === "ACCEPTED" && (access?.can_convert ?? true) && (
        <button disabled={busy} onClick={() => convertM.mutate()}
          className="text-xs px-2 py-1 rounded bg-purple-50 text-purple-700 hover:bg-purple-100">{tx("Convert to SO")}</button>
      )}
      {(quote.status === "DRAFT" || quote.status === "SENT") && (access?.can_cancel ?? true) && (
        <button disabled={busy} onClick={() => expireM.mutate()}
          className="text-xs px-2 py-1 rounded bg-yellow-50 text-yellow-700 hover:bg-yellow-100">{tx("Expire")}</button>
      )}
      {quote.status !== "CONVERTED" && quote.status !== "DRAFT" && (access?.can_edit ?? true) && (
        <button disabled={busy} onClick={() => reviseM.mutate()}
          className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 hover:bg-gray-200">{tx("Revise")}</button>
      )}
      {access && !access.view_only && !(access.can_edit || access.can_approve || access.can_convert || access.can_cancel) && (
        <ViewOnlyBadge reason={access.reason} />
      )}
      {failed && <span role="alert" className="text-xs text-red-700 w-full">{failed.message}</span>}
      {(convertM.isSuccess) && (
        <span className="text-xs text-purple-700">{tx("SO created")}</span>
      )}
      {["DRAFT", "SENT", "ACCEPTED"].includes(quote.status) && (
        <button onClick={() => setSharing(true)}
          className="text-xs px-2 py-1 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100">{tx("Share")}</button>
      )}
      {sharing && <SharePanel quote={quote} onClose={() => setSharing(false)} />}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function QuotesPage() {
  const [statusFilter, setStatusFilter] = useState<QuoteStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<Quotation | null>(null);
  const [editTarget, setEditTarget] = useState<Quotation | null>(null);

  const { data: dash } = useQuery({ queryKey: ["quotes", "dashboard"], queryFn: quoteApi.dashboard });
  const { data: quotes = [], isLoading } = useQuery({
    queryKey: ["quotes", statusFilter],
    queryFn: () => quoteApi.list(statusFilter ? { status: statusFilter } : undefined),
  });
  const { data: customers = [] } = useQuery({ queryKey: ["customers"], queryFn: () => salesApi.listCustomers() });
  const { data: products = [] } = useQuery({ queryKey: ["products-all"], queryFn: () => productsApi.list() });

  const statuses: QuoteStatus[] = ["DRAFT", "SENT", "ACCEPTED", "REJECTED", "EXPIRED", "CONVERTED"];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Quotations")}</h1>
          <p className="text-sm text-gray-500">{tx("Manage commercial quotes before converting to Sales Orders")}</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>{tx("+ New Quote")}</Button>
      </div>

      {/* KPI cards */}
      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <KpiCard label={tx("Total Quotes")} value={dash.total_quotes} />
          <KpiCard label={tx("Draft")} value={dash.draft_count} />
          <KpiCard label={tx("Sent")} value={dash.sent_count} />
          <KpiCard label={tx("Accepted")} value={dash.accepted_count} />
          <KpiCard label={tx("Rejected")} value={dash.rejected_count} />
          <KpiCard label={tx("Win Rate")} value={dash.win_rate_pct != null ? `${dash.win_rate_pct}%` : "—"} />
          <KpiCard label={tx("Pipeline")} value={fmtCcy(dash.total_pipeline)} sub="SENT quotes" />
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setStatusFilter("")}
          className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${statusFilter === "" ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"}`}
        >
          {tx("All")}
        </button>
        {statuses.map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${statusFilter === s ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"}`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{tx("Loading quotes…")}</div>
        ) : quotes.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{tx("No quotes found. Create your first quotation.")}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {[tx("Quote No"), tx("Version"), tx("Customer"), tx("Date"), tx("Valid Until"), tx("Status"), tx("Grand Total"), tx("Actions")].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {quotes.map(q => (
                  <tr key={q.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono font-medium text-gray-900">{q.quote_no}</td>
                    <td className="px-4 py-3 text-gray-500">{tx("v")}{q.version}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{q.customer_name ?? "—"}</div>
                      <div className="text-xs text-gray-400">{q.customer_code}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{fmtDate(q.quote_date)}</td>
                    <td className="px-4 py-3 text-gray-600">{fmtDate(q.valid_until)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <StatusBadge status={q.status} />
                        {q.access?.view_only && <ViewOnlyBadge reason={q.access.reason} />}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-semibold text-gray-900 text-right">
                      {fmtCcy(q.grand_total, q.currency)}
                    </td>
                    <td className="px-4 py-3">
                      <QuoteActions quote={q} onReject={() => setRejectTarget(q)} onEdit={() => setEditTarget(q)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {editTarget && (
        <CreateModal customers={customers} products={products} editing={editTarget} onClose={() => setEditTarget(null)} />
      )}
      {showCreate && (
        <CreateModal customers={customers} products={products} onClose={() => setShowCreate(false)} />
      )}
      {rejectTarget && (
        <RejectModal quote={rejectTarget} onClose={() => setRejectTarget(null)} />
      )}
    </div>
  );
}
