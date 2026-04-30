"use client";
import { useEffect, useState } from "react";
import { recruitmentApi, Offer, JobRequisition, OFFER_STATUS_COLOR, OfferStatus, fmtCurrency } from "@/lib/recruitment";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function OffersPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [respondTarget, setRespondTarget] = useState<string | null>(null);
  const [form, setForm] = useState({ candidate_id: "", requisition_id: "", offer_date: new Date().toISOString().slice(0, 10), salary_offer: "", currency: "KES", joining_date: "", employment_type: "full_time", expiry_date: "", notes: "" });
  const [respond, setRespond] = useState({ status: "accepted" as OfferStatus, rejection_reason: "", joining_date: "" });
  const [msg, setMsg] = useState("");

  const load = async () => { const [o, r] = await Promise.all([recruitmentApi.listOffers(), recruitmentApi.listRequisitions()]); setOffers(o); setReqs(r); };
  useEffect(() => { load(); }, []);

  const handleCreate = async () => { await recruitmentApi.createOffer({ ...form, salary_offer: Number(form.salary_offer) }); await load(); setShowForm(false); setMsg("Offer created"); setTimeout(() => setMsg(""), 2000); };
  const handleSend = async (id: string) => { await recruitmentApi.sendOffer(id); await load(); setMsg("Offer sent"); setTimeout(() => setMsg(""), 2000); };
  const handleRespond = async () => { if (!respondTarget) return; await recruitmentApi.respondToOffer(respondTarget, { status: respond.status, rejection_reason: respond.rejection_reason || undefined, joining_date: respond.joining_date || undefined }); setRespondTarget(null); await load(); };

  const reqName = (id: string) => { const r = reqs.find((r) => r.requisition_id === id); return r ? `${r.requisition_code} — ${r.job_title}` : id.slice(-8); };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Offer Management</h1>
          <p className="text-slate-500 text-sm mt-0.5">{offers.length} offers</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showForm ? "Cancel" : "+ New Offer"}
        </button>
      </div>

      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      {showForm && (
        <div className="glow-card p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Candidate ID</label><input value={form.candidate_id} onChange={(e) => setForm({ ...form, candidate_id: e.target.value })} placeholder="UUID" className={inputCls} /></div>
            <div><label className={labelCls}>Requisition</label>
              <select value={form.requisition_id} onChange={(e) => setForm({ ...form, requisition_id: e.target.value })} className={selectCls}>
                <option value="">Select…</option>
                {reqs.map((r) => <option key={r.requisition_id} value={r.requisition_id}>{r.requisition_code} — {r.job_title}</option>)}
              </select>
            </div>
            <div><label className={labelCls}>Salary Offer (KES)</label><input type="number" value={form.salary_offer} onChange={(e) => setForm({ ...form, salary_offer: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Offer Date</label><input type="date" value={form.offer_date} onChange={(e) => setForm({ ...form, offer_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Expiry Date</label><input type="date" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Joining Date</label><input type="date" value={form.joining_date} onChange={(e) => setForm({ ...form, joining_date: e.target.value })} className={inputCls} /></div>
          </div>
          <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Create Offer</button>
        </div>
      )}

      {respondTarget && (
        <div className="glow-card border-emerald-500/20 p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Record Candidate Response</h2>
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Decision</label>
              <select value={respond.status} onChange={(e) => setRespond({ ...respond, status: e.target.value as OfferStatus })} className={selectCls}>
                {["accepted", "rejected", "negotiating"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div><label className={labelCls}>Joining Date (if accepted)</label><input type="date" value={respond.joining_date} onChange={(e) => setRespond({ ...respond, joining_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Rejection Reason</label><input value={respond.rejection_reason} onChange={(e) => setRespond({ ...respond, rejection_reason: e.target.value })} className={inputCls} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleRespond} className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm">Save Response</button>
            <button onClick={() => setRespondTarget(null)} className="px-4 py-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="glass-table">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Offer Code", "Requisition", "Salary", "Joining", "Expiry", "Status", "Actions"].map((h) => (
              <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Salary" ? "text-right" : "text-left"}`}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {offers.map((o) => (
              <tr key={o.offer_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs text-slate-400">{o.offer_code}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{reqName(o.requisition_id)}</td>
                <td className="px-4 py-3 text-right text-emerald-400 font-semibold">{fmtCurrency(o.salary_offer, o.currency)}</td>
                <td className="px-4 py-3 text-slate-400">{o.joining_date || "—"}</td>
                <td className="px-4 py-3 text-slate-400">{o.expiry_date || "—"}</td>
                <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${OFFER_STATUS_COLOR[o.status]}`}>{o.status}</span></td>
                <td className="px-4 py-3 space-x-3">
                  {o.status === "draft" && <button onClick={() => handleSend(o.offer_id)} className="text-xs text-blue-400 hover:text-blue-300">Send</button>}
                  {o.status === "sent" && <button onClick={() => setRespondTarget(o.offer_id)} className="text-xs text-emerald-400 hover:text-emerald-300">Record Response</button>}
                </td>
              </tr>
            ))}
            {offers.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No offers</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
