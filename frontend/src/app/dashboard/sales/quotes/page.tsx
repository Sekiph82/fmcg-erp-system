"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  quoteApi, Quotation, QuoteStatus, QuoteCreate, QuoteLineCreate,
  STATUS_COLORS, fmtCcy, fmtDate,
} from "@/lib/quotations";
import { salesApi, Customer } from "@/lib/sales";
import { productsApi, Product } from "@/lib/products";
import { Button } from "@/components/ui/Button";

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
      title={reason ?? "You can view this record but cannot modify it in this scope."}
      className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"
    >
      View only
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
        <span className="text-sm font-medium text-gray-700">Line Items</span>
        <button onClick={add} className="text-xs text-blue-600 hover:underline">+ Add line</button>
      </div>
      {lines.length === 0 && <p className="text-xs text-gray-400">No lines yet. Add a product.</p>}
      {lines.map((l, i) => {
        const prod = products.find(p => p.id === l.product_id);
        const lineTotal = l.qty * l.unit_price * (1 - l.discount_pct / 100) * (1 + l.tax_rate / 100);
        return (
          <div key={i} className="border rounded p-2 space-y-2 bg-gray-50">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-500">Product</label>
                <select
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={l.product_id ?? ""}
                  onChange={e => {
                    const p = products.find(pr => pr.id === e.target.value);
                    const next = { ...l, product_id: e.target.value, unit_price: p ? (p.selling_price ?? 0) : l.unit_price };
                    onChange(lines.map((ll, idx) => idx === i ? next : ll));
                  }}
                >
                  <option value="">— select product —</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">Description (optional)</label>
                <input
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={l.description ?? ""}
                  onChange={e => update(i, "description", e.target.value)}
                  placeholder="Free text override"
                />
              </div>
            </div>
            <div className="grid grid-cols-5 gap-2">
              <div>
                <label className="text-xs text-gray-500">Qty</label>
                <input type="number" min={0} step={0.001} className="w-full border rounded px-2 py-1 text-sm" value={l.qty}
                  onChange={e => update(i, "qty", parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Unit</label>
                <input className="w-full border rounded px-2 py-1 text-sm" value={l.unit}
                  onChange={e => update(i, "unit", e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Unit Price</label>
                <input type="number" min={0} step={0.01} className="w-full border rounded px-2 py-1 text-sm" value={l.unit_price}
                  onChange={e => update(i, "unit_price", parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Disc %</label>
                <input type="number" min={0} max={100} step={0.01} className="w-full border rounded px-2 py-1 text-sm" value={l.discount_pct}
                  onChange={e => update(i, "discount_pct", parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Tax %</label>
                <input type="number" min={0} max={100} step={0.01} className="w-full border rounded px-2 py-1 text-sm" value={l.tax_rate}
                  onChange={e => update(i, "tax_rate", parseFloat(e.target.value) || 0)} />
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">Line total: <strong>{lineTotal.toFixed(2)}</strong></span>
              <button onClick={() => remove(i)} className="text-xs text-red-500 hover:underline">Remove</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Create modal ──────────────────────────────────────────────────────────────

function CreateModal({ customers, products, onClose }: {
  customers: Customer[];
  products: Product[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<QuoteCreate>({
    customer_id: "",
    quote_date: new Date().toISOString().slice(0, 10),
    valid_until: "",
    currency: "KES",
    discount_pct: 0,
    notes: "",
    lines: [],
  });

  const mut = useMutation({
    mutationFn: () => quoteApi.create({ ...form, valid_until: form.valid_until || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["quotes"] }); onClose(); },
  });

  const totalGrand = form.lines.reduce((s, l) =>
    s + l.qty * l.unit_price * (1 - l.discount_pct / 100) * (1 + l.tax_rate / 100), 0
  ) * (1 - form.discount_pct / 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">New Quotation</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700">Customer *</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.customer_id} onChange={e => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">— select —</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Currency</label>
            <select className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })}>
              {["KES", "USD", "EUR", "GBP"].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Quote Date *</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.quote_date} onChange={e => setForm({ ...form, quote_date: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Valid Until</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.valid_until ?? ""} onChange={e => setForm({ ...form, valid_until: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Overall Discount %</label>
            <input type="number" min={0} max={100} step={0.01} className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.discount_pct} onChange={e => setForm({ ...form, discount_pct: parseFloat(e.target.value) || 0 })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Notes</label>
            <input className="w-full border rounded px-3 py-2 text-sm mt-1"
              value={form.notes ?? ""} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>

        <LineEditor lines={form.lines} products={products} onChange={lines => setForm({ ...form, lines })} />

        <div className="flex justify-between items-center pt-2 border-t">
          <div className="text-sm text-gray-600">
            Estimated Grand Total: <strong className="text-gray-900">{fmtCcy(totalGrand, form.currency)}</strong>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button onClick={() => mut.mutate()} disabled={!form.customer_id || mut.isPending}>
              {mut.isPending ? "Creating…" : "Create Quote"}
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
        <h3 className="font-semibold text-gray-800">Reject Quote {quote.quote_no}</h3>
        <textarea className="w-full border rounded px-3 py-2 text-sm" rows={3}
          placeholder="Reason for rejection (optional)" value={reason} onChange={e => setReason(e.target.value)} />
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending} className="bg-red-600 hover:bg-red-700">
            {mut.isPending ? "Rejecting…" : "Reject"}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Row actions ───────────────────────────────────────────────────────────────

function QuoteActions({ quote, onReject }: { quote: Quotation; onReject: () => void }) {
  const qc = useQueryClient();
  const useQuoteMutation = (fn: () => Promise<unknown>) =>
    useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: ["quotes"] }) });

  const sendM = useQuoteMutation(() => quoteApi.send(quote.id));
  const acceptM = useQuoteMutation(() => quoteApi.accept(quote.id));
  const expireM = useQuoteMutation(() => quoteApi.expire(quote.id));
  const reviseM = useQuoteMutation(() => quoteApi.revise(quote.id));
  const convertM = useQuoteMutation(() => quoteApi.convert(quote.id));

  const busy = sendM.isPending || acceptM.isPending || expireM.isPending || reviseM.isPending || convertM.isPending;
  const access = quote.access;

  if (access?.view_only) {
    return <ViewOnlyBadge reason={access.reason} />;
  }

  return (
    <div className="flex flex-wrap gap-1">
      {quote.status === "DRAFT" && (access?.can_edit ?? true) && (
        <button disabled={busy} onClick={() => sendM.mutate()}
          className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100">Send</button>
      )}
      {quote.status === "SENT" && (access?.can_approve ?? true) && (
        <>
          <button disabled={busy} onClick={() => acceptM.mutate()}
            className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100">Accept</button>
          <button disabled={busy} onClick={onReject}
            className="text-xs px-2 py-1 rounded bg-red-50 text-red-700 hover:bg-red-100">Reject</button>
        </>
      )}
      {quote.status === "ACCEPTED" && (access?.can_convert ?? true) && (
        <button disabled={busy} onClick={() => convertM.mutate()}
          className="text-xs px-2 py-1 rounded bg-purple-50 text-purple-700 hover:bg-purple-100">Convert to SO</button>
      )}
      {(quote.status === "DRAFT" || quote.status === "SENT") && (access?.can_cancel ?? true) && (
        <button disabled={busy} onClick={() => expireM.mutate()}
          className="text-xs px-2 py-1 rounded bg-yellow-50 text-yellow-700 hover:bg-yellow-100">Expire</button>
      )}
      {quote.status !== "CONVERTED" && quote.status !== "DRAFT" && (access?.can_edit ?? true) && (
        <button disabled={busy} onClick={() => reviseM.mutate()}
          className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 hover:bg-gray-200">Revise</button>
      )}
      {access && !access.view_only && !(access.can_edit || access.can_approve || access.can_convert || access.can_cancel) && (
        <ViewOnlyBadge reason={access.reason} />
      )}
      {(convertM.isSuccess) && (
        <span className="text-xs text-purple-700">SO created</span>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function QuotesPage() {
  const [statusFilter, setStatusFilter] = useState<QuoteStatus | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<Quotation | null>(null);

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
          <h1 className="text-2xl font-bold text-gray-900">Quotations</h1>
          <p className="text-sm text-gray-500">Manage commercial quotes before converting to Sales Orders</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Quote</Button>
      </div>

      {/* KPI cards */}
      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <KpiCard label="Total Quotes" value={dash.total_quotes} />
          <KpiCard label="Draft" value={dash.draft_count} />
          <KpiCard label="Sent" value={dash.sent_count} />
          <KpiCard label="Accepted" value={dash.accepted_count} />
          <KpiCard label="Rejected" value={dash.rejected_count} />
          <KpiCard label="Win Rate" value={dash.win_rate_pct != null ? `${dash.win_rate_pct}%` : "—"} />
          <KpiCard label="Pipeline" value={fmtCcy(dash.total_pipeline)} sub="SENT quotes" />
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setStatusFilter("")}
          className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${statusFilter === "" ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"}`}
        >
          All
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
          <div className="p-8 text-center text-gray-400">Loading quotes…</div>
        ) : quotes.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No quotes found. Create your first quotation.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Quote No", "Version", "Customer", "Date", "Valid Until", "Status", "Grand Total", "Actions"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {quotes.map(q => (
                  <tr key={q.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono font-medium text-gray-900">{q.quote_no}</td>
                    <td className="px-4 py-3 text-gray-500">v{q.version}</td>
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
                      <QuoteActions quote={q} onReject={() => setRejectTarget(q)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && (
        <CreateModal customers={customers} products={products} onClose={() => setShowCreate(false)} />
      )}
      {rejectTarget && (
        <RejectModal quote={rejectTarget} onClose={() => setRejectTarget(null)} />
      )}
    </div>
  );
}
