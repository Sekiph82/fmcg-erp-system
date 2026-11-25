"use client";
// M43.S01.T015 contacts: people linked to customers, deals, tickets, quotes and orders; lifecycle stage + history.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";

interface Contact { id: string; full_name: string; email: string | null; phone: string | null; job_title: string | null;
  lifecycle_stage: string | null }
interface Detail extends Contact { associations: { id: string; object_type: string; object_id: string; label: string }[];
  lifecycle_history: { from: string | null; to: string; source: string; reason: string | null; changed_at: string }[] }

const STAGES = ["SUBSCRIBER", "LEAD", "MQL", "SQL", "OPPORTUNITY", "CUSTOMER", "EVANGELIST", "OTHER"];
const LABELS = ["primary", "billing", "decision_maker", "buyer", "influencer", "champion", "user", "blocker", "finance", "technical", "other"];
const err = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : (d as { message?: string })?.message ?? fb;
};

export default function CRMContactsPage() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Contact[]>([]);
  const [open, setOpen] = useState<Detail | null>(null);
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", job_title: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [assoc, setAssoc] = useState({ object_type: "customer", object_id: "", label: "primary" });
  const load = useCallback(() => {
    apiClient.get("/api/v1/crm-contacts", { params: { q: q || undefined } }).then((r) => setRows(r.data)).catch(() => setRows([]));
  }, [q]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);
  const show = async (id: string) => { try { setOpen((await apiClient.get(`/api/v1/crm-contacts/${id}`)).data); } catch { setOpen(null); } };

  return (
    <div className="p-4 grid lg:grid-cols-2 gap-4">
      <section className="space-y-2">
        <div className="flex gap-2 items-center">
          <h2 className="text-lg font-semibold">Contacts</h2>
          <input aria-label="Search contacts" className="border rounded px-2 py-1 text-sm flex-1" placeholder="Search name, e-mail, phone…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <form className="grid grid-cols-2 gap-1 text-xs border rounded p-2 bg-white" onSubmit={async (e) => {
          e.preventDefault();
          try { const r = await apiClient.post("/api/v1/crm-contacts", { ...form, email: form.email || null }); setForm({ full_name: "", email: "", phone: "", job_title: "" }); load(); show(r.data.id); setMsg(null); }
          catch (x) { setMsg(err(x, "Could not add the contact.")); }
        }}>
          <input required className="border rounded px-2 py-1" placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          <input type="email" className="border rounded px-2 py-1" placeholder="E-mail" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="border rounded px-2 py-1" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <input className="border rounded px-2 py-1" placeholder="Job title" value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
          <button className="col-span-2 bg-indigo-600 text-white rounded py-1">Add contact</button>
        </form>
        {msg && <p role="alert" className="text-xs text-red-600">{msg}</p>}
        <ul className="divide-y border rounded bg-white">
          {rows.map((c) => (
            <li key={c.id}><button className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50" onClick={() => show(c.id)}>
              <span className="font-medium">{c.full_name}</span> <span className="text-gray-500 text-xs">{c.email ?? c.phone ?? ""} · {c.lifecycle_stage ?? "—"}</span>
            </button></li>
          ))}
          {rows.length === 0 && <li className="px-3 py-2 text-xs text-gray-500">No contacts.</li>}
        </ul>
      </section>
      {open && (
        <section className="border rounded bg-white p-3 space-y-3 text-sm">
          <div><div className="font-semibold">{open.full_name}</div><div className="text-xs text-gray-500">{open.job_title} {open.email} {open.phone}</div></div>
          <label className="text-xs">Lifecycle stage
            <select className="ml-2 border rounded px-2 py-1" value={open.lifecycle_stage ?? ""} onChange={async (e) => {
              const stage = e.target.value;
              const back = STAGES.indexOf(stage) < STAGES.indexOf(open.lifecycle_stage ?? "SUBSCRIBER");
              const reason = back ? prompt("Why move this contact back?") : null;
              if (back && !reason) return;
              try { await apiClient.put(`/api/v1/crm-contacts/${open.id}/lifecycle`, { stage, reason }); show(open.id); load(); } catch (x) { setMsg(err(x, "Not allowed.")); }
            }}>{STAGES.map((s) => <option key={s}>{s}</option>)}</select></label>
          <div>
            <div className="text-xs font-semibold mb-1">Linked to</div>
            {open.associations.map((a) => (
              <div key={a.id} className="flex justify-between text-xs border-b py-1"><span>{a.object_type} · {a.label}</span>
                <button className="text-red-600" onClick={async () => { await apiClient.delete(`/api/v1/crm-contacts/${open.id}/associations/${a.id}`).catch(() => null); show(open.id); }}>Remove</button></div>
            ))}
            <div className="flex flex-wrap gap-1 mt-2 text-xs items-end">
              <select className="border rounded px-1 py-1" value={assoc.object_type} onChange={(e) => setAssoc({ ...assoc, object_type: e.target.value, object_id: "" })}>
                {["customer", "crm_record", "sales_order"].map((t) => <option key={t}>{t}</option>)}</select>
              <div className="min-w-[12rem] flex-1"><EntityPicker kind={assoc.object_type as "customer"} value={assoc.object_id} onChange={(id) => setAssoc({ ...assoc, object_id: id })} /></div>
              <select className="border rounded px-1 py-1" value={assoc.label} onChange={(e) => setAssoc({ ...assoc, label: e.target.value })}>
                {LABELS.map((l) => <option key={l}>{l}</option>)}</select>
              <button className="border rounded px-2 py-1" disabled={!assoc.object_id} onClick={async () => {
                try { await apiClient.post(`/api/v1/crm-contacts/${open.id}/associations`, assoc); show(open.id); } catch (x) { setMsg(err(x, "Could not link.")); }
              }}>Link</button>
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold mb-1">Lifecycle history</div>
            {open.lifecycle_history.map((h, i) => <div key={i} className="text-xs text-gray-600">{new Date(h.changed_at).toLocaleString()}: {h.from ?? "—"} → {h.to} ({h.source}{h.reason ? `: ${h.reason}` : ""})</div>)}
          </div>
        </section>
      )}
    </div>
  );
}
