"use client";
// Supplier portal: purchase orders (confirm / reject / new delivery date), documents (invoices, certificates), payments.
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { partnerFetch, money, PortalError } from "@/lib/portalSelf";

const sp = <T,>(path: string, init: RequestInit = {}) => partnerFetch<T>("supplier-self", path, init);
const spPost = <T,>(path: string, data: unknown) => sp<T>(path, { method: "POST", body: JSON.stringify(data) });

interface Me { full_name: string; role: string; supplier_name: string | null; can_respond: boolean; can_upload: boolean; can_view_payment: boolean }
interface PO { po_id: string; po_number: string; po_date: string; status: string; total_amount: number | null; currency: string; required_date: string; acknowledgment_status: string }
interface PODetail {
  id: string; po_number: string; status: string; currency: string; required_date: string; payment_terms: string | null; total_amount: number | null;
  lines: { line_no: number; item: string; quantity: number; unit: string; unit_price: number | null }[];
  acknowledgment: { status: string; comment: string | null; proposed_eta: string | null } | null;
  eta_history: { revision_no: number; proposed_date: string; status: string; reason: string | null; buyer_notes: string | null }[];
  documents: { id: string; type: string; file_name: string; review_status: string }[];
}
interface Doc { id: string; type: string; file_name: string; linked_po_id: string | null; review_status: string; expiry_date: string | null; uploaded_at: string }
interface Payment { invoice_id: string; invoice_number: string; invoice_date: string | null; total_amount: number | null; paid_amount: number; currency: string; status: string; due_date: string | null }
type Tab = "pos" | "docs" | "payments";
const DOC_TYPES = ["INVOICE", "DELIVERY_NOTE", "PACKING_LIST", "COA", "MSDS", "SPECIFICATION", "COMPLIANCE_CERT", "FOOD_SAFETY_CERT", "HALAL_CERT", "TEST_RESULT", "TAX_DOC", "OTHER"];
const human = (s: string) => s.replace(/_/g, " ").toLowerCase();

export default function SupplierPortal() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>("pos");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const fail = useCallback((e: unknown) => {
    if (e instanceof PortalError && e.status === 401) { router.replace("/supplier/login"); return; }
    setError((e as Error).message);
  }, [router]);
  const ok = (m: string) => { setInfo(m); setError(null); };
  useEffect(() => { sp<Me>("/me").then(setMe).catch(fail); }, [fail]);

  if (!me) return <main className="p-6 text-sm text-gray-500">{error ?? "Loading…"}</main>;
  const tabs: [Tab, string][] = [["pos", "Purchase orders"], ["docs", "Documents"], ...(me.can_view_payment ? [["payments", "Payments"] as [Tab, string]] : [])];
  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-emerald-700 text-white px-4 py-3 flex items-center justify-between gap-2">
        <div className="min-w-0"><p className="font-semibold truncate">{me.supplier_name ?? "Supplier"}</p><p className="text-xs text-emerald-100 truncate">{me.full_name} · {me.role}</p></div>
        <button onClick={async () => { await sp("/auth/logout", { method: "POST" }).catch(() => undefined); router.replace("/supplier/login"); }} className="text-sm underline shrink-0">Sign out</button>
      </header>
      <nav aria-label="Supplier sections" className="flex overflow-x-auto bg-white border-b text-sm">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => { setTab(k); setError(null); setInfo(null); }} aria-current={tab === k ? "page" : undefined}
            className={`px-4 py-3 whitespace-nowrap ${tab === k ? "border-b-2 border-emerald-600 font-semibold text-emerald-700" : "text-gray-600"}`}>{label}</button>))}
      </nav>
      <div className="max-w-4xl mx-auto p-4 space-y-4">
        {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
        {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}
        {tab === "pos" && <POsTab me={me} fail={fail} ok={ok} />}
        {tab === "docs" && <DocsTab me={me} fail={fail} ok={ok} />}
        {tab === "payments" && <PaymentsTab fail={fail} />}
      </div>
    </main>
  );
}

function POsTab({ me, fail, ok }: { me: Me; fail: (e: unknown) => void; ok: (m: string) => void }) {
  const [rows, setRows] = useState<PO[] | null>(null);
  const [open, setOpen] = useState<PODetail | null>(null);
  const [ack, setAck] = useState({ response_status: "ACCEPTED", supplier_comment: "", rejection_reason: "", proposed_eta: "" });
  const [eta, setEta] = useState({ proposed_date: "", supplier_reason: "" });
  const load = useCallback(() => sp<PO[]>("/purchase-orders").then(setRows).catch(fail), [fail]);
  useEffect(() => { load(); }, [load]);
  const show = (id: string) => sp<PODetail>(`/purchase-orders/${id}`).then(setOpen).catch(fail);

  async function respond(id: string) {
    try {
      await spPost(`/purchase-orders/${id}/acknowledge`, { response_status: ack.response_status, supplier_comment: ack.supplier_comment || null,
        rejection_reason: ack.rejection_reason || null, proposed_eta: ack.proposed_eta || null });
      ok("Your response was sent to the buyer."); await load(); await show(id);
    } catch (e) { fail(e); }
  }
  async function reschedule(id: string) {
    try { await spPost(`/purchase-orders/${id}/eta`, eta); ok("New delivery date proposed."); setEta({ proposed_date: "", supplier_reason: "" }); await show(id); }
    catch (e) { fail(e); }
  }

  if (!rows) return <p className="text-sm text-gray-500">Loading…</p>;
  if (rows.length === 0) return <p className="text-sm text-gray-500">No purchase orders.</p>;
  const input = "border rounded-lg px-2 py-1.5 text-sm";
  return (
    <div className="space-y-2">
      {rows.map((p) => (
        <div key={p.po_id} className="bg-white rounded-xl border p-3">
          <button className="w-full text-left flex justify-between gap-2" aria-expanded={open?.id === p.po_id} onClick={() => open?.id === p.po_id ? setOpen(null) : show(p.po_id)}>
            <span><span className="font-medium">{p.po_number}</span><span className="block text-xs text-gray-500">{p.po_date} · deliver by {p.required_date}</span></span>
            <span className="text-right text-sm"><span className="block">{human(p.acknowledgment_status)}</span><span className="text-xs text-gray-500">{money(p.total_amount, p.currency)}</span></span>
          </button>
          {open?.id === p.po_id && (
            <div className="mt-2 border-t pt-2 space-y-3 text-sm">
              <table className="w-full"><tbody>{open.lines.map((l) => <tr key={l.line_no}><td>{l.item}</td><td className="text-right">{l.quantity} {l.unit}</td><td className="text-right text-gray-500">{money(l.unit_price, open.currency)}</td></tr>)}</tbody></table>
              {open.payment_terms && <p className="text-xs text-gray-500">Payment terms: {open.payment_terms}</p>}
              {open.acknowledgment && <p className="text-xs">Your response: <b>{human(open.acknowledgment.status)}</b>{open.acknowledgment.comment ? ` — ${open.acknowledgment.comment}` : ""}</p>}
              {open.eta_history.map((e) => <p key={e.revision_no} className="text-xs text-gray-600">Date proposal #{e.revision_no}: {e.proposed_date} ({human(e.status)}){e.buyer_notes ? ` — buyer: ${e.buyer_notes}` : ""}</p>)}
              {me.can_respond && (<>
                <div className="grid sm:grid-cols-2 gap-2" aria-label="Respond to order">
                  <select aria-label="Response" value={ack.response_status} onChange={(e) => setAck({ ...ack, response_status: e.target.value })} className={input}>
                    <option value="ACCEPTED">Accept</option><option value="ACCEPTED_REVISED_ETA">Accept with another date</option>
                    <option value="PARTIALLY_ACCEPTED">Accept partly</option><option value="REJECTED">Reject</option>
                  </select>
                  {ack.response_status === "ACCEPTED_REVISED_ETA" && <input type="date" aria-label="Date you can deliver" value={ack.proposed_eta} onChange={(e) => setAck({ ...ack, proposed_eta: e.target.value })} className={input} />}
                  {ack.response_status === "REJECTED" && <input aria-label="Reason for rejecting" placeholder="Reason" maxLength={2000} value={ack.rejection_reason} onChange={(e) => setAck({ ...ack, rejection_reason: e.target.value })} className={input} />}
                  <input aria-label="Comment" placeholder="Comment (optional)" maxLength={2000} value={ack.supplier_comment} onChange={(e) => setAck({ ...ack, supplier_comment: e.target.value })} className={`${input} sm:col-span-2`} />
                  <button onClick={() => respond(open.id)} className="sm:col-start-2 py-2 rounded-lg bg-emerald-600 text-white">Send response</button>
                </div>
                <div className="grid sm:grid-cols-[160px_1fr_auto] gap-2" aria-label="Propose new delivery date">
                  <input type="date" aria-label="New delivery date" value={eta.proposed_date} onChange={(e) => setEta({ ...eta, proposed_date: e.target.value })} className={input} />
                  <input aria-label="Reason for new date" placeholder="Reason for the new date" maxLength={2000} value={eta.supplier_reason} onChange={(e) => setEta({ ...eta, supplier_reason: e.target.value })} className={input} />
                  <button onClick={() => reschedule(open.id)} disabled={!eta.proposed_date || eta.supplier_reason.length < 3} className="px-3 py-2 rounded-lg border text-sm disabled:opacity-50">Propose date</button>
                </div>
              </>)}
            </div>)}
        </div>))}
    </div>
  );
}

function DocsTab({ me, fail, ok }: { me: Me; fail: (e: unknown) => void; ok: (m: string) => void }) {
  const [rows, setRows] = useState<Doc[]>([]);
  const [pos, setPos] = useState<PO[]>([]);
  const [form, setForm] = useState({ upload_type: "INVOICE", linked_po_id: "", expiry_date: "" });
  const [file, setFile] = useState<File | null>(null);
  const load = useCallback(() => { sp<Doc[]>("/documents").then(setRows).catch(fail); sp<PO[]>("/purchase-orders").then(setPos).catch(fail); }, [fail]);
  useEffect(load, [load]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const fd = new FormData();
    fd.append("upload_type", form.upload_type);
    if (form.linked_po_id) fd.append("linked_po_id", form.linked_po_id);
    if (form.expiry_date) fd.append("expiry_date", form.expiry_date);
    fd.append("file", file);
    try { await sp("/documents", { method: "POST", body: fd }); ok(`${file.name} uploaded for review.`); setFile(null); (e.target as HTMLFormElement).reset(); load(); }
    catch (err) { fail(err); }
  }
  const input = "border rounded-lg px-2 py-1.5 text-sm";
  return (
    <div className="space-y-3">
      {me.can_upload && (
        <form onSubmit={upload} aria-label="Upload document" className="bg-white rounded-xl border p-3 grid gap-2 sm:grid-cols-2">
          <select aria-label="Document type" value={form.upload_type} onChange={(e) => setForm({ ...form, upload_type: e.target.value })} className={input}>
            {DOC_TYPES.map((t) => <option key={t} value={t}>{human(t)}</option>)}
          </select>
          <select aria-label="Purchase order" value={form.linked_po_id} onChange={(e) => setForm({ ...form, linked_po_id: e.target.value })} className={input}>
            <option value="">Not for a specific order</option>
            {pos.map((p) => <option key={p.po_id} value={p.po_id}>{p.po_number}</option>)}
          </select>
          <label className="text-xs text-gray-600">Valid until (certificates)<input type="date" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} className={`${input} w-full mt-1`} /></label>
          <label className="text-xs text-gray-600">File (PDF, JPG/PNG, Excel, Word)<input type="file" required aria-label="File" accept=".pdf,.png,.jpg,.jpeg,.xlsx,.docx,.csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="w-full mt-1 text-sm" /></label>
          <button className="sm:col-start-2 py-2 rounded-lg bg-emerald-600 text-white text-sm">Upload</button>
        </form>)}
      {rows.length === 0 ? <p className="text-sm text-gray-500">No documents yet.</p> : (
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th className="p-2">File</th><th>Type</th><th>Review</th><th>Valid until</th></tr></thead>
            <tbody>{rows.map((d) => <tr key={d.id} className="border-t"><td className="p-2 break-all">{d.file_name}</td><td>{human(d.type)}</td><td>{human(d.review_status)}</td><td>{d.expiry_date ?? "—"}</td></tr>)}</tbody></table>
        </div>)}
    </div>
  );
}

function PaymentsTab({ fail }: { fail: (e: unknown) => void }) {
  const [rows, setRows] = useState<Payment[] | null>(null);
  useEffect(() => { sp<Payment[]>("/payments").then(setRows).catch(fail); }, [fail]);
  if (!rows) return <p className="text-sm text-gray-500">Loading…</p>;
  if (rows.length === 0) return <p className="text-sm text-gray-500">No invoices registered yet.</p>;
  return (
    <div className="bg-white rounded-xl border overflow-x-auto">
      <table className="w-full text-sm"><thead><tr className="text-left text-xs text-gray-500"><th className="p-2">Invoice</th><th>Date</th><th>Due</th><th>Total</th><th>Paid</th><th>Status</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.invoice_id} className="border-t"><td className="p-2">{r.invoice_number}</td><td>{r.invoice_date}</td><td>{r.due_date}</td><td>{money(r.total_amount, r.currency)}</td><td>{money(r.paid_amount, r.currency)}</td><td>{human(r.status)}</td></tr>)}</tbody></table>
    </div>
  );
}
