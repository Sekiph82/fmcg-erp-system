"use client";
import { useEffect, useState } from "react";
import {
  recruitmentApi, Offer, JobRequisition,
  OFFER_STATUS_COLOR, OfferStatus, fmtCurrency,
} from "@/lib/recruitment";

export default function OffersPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [respondTarget, setRespondTarget] = useState<string | null>(null);
  const [form, setForm] = useState({
    candidate_id: "", requisition_id: "", offer_date: new Date().toISOString().slice(0, 10),
    salary_offer: "", currency: "KES", joining_date: "", employment_type: "full_time",
    expiry_date: "", notes: "",
  });
  const [respond, setRespond] = useState({ status: "accepted" as OfferStatus, rejection_reason: "", joining_date: "" });
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [o, r] = await Promise.all([recruitmentApi.listOffers(), recruitmentApi.listRequisitions()]);
    setOffers(o); setReqs(r);
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    await recruitmentApi.createOffer({ ...form, salary_offer: Number(form.salary_offer) });
    await load(); setShowForm(false);
    setMsg("Offer created"); setTimeout(() => setMsg(""), 2000);
  };

  const handleSend = async (id: string) => {
    await recruitmentApi.sendOffer(id);
    await load(); setMsg("Offer sent"); setTimeout(() => setMsg(""), 2000);
  };

  const handleRespond = async () => {
    if (!respondTarget) return;
    await recruitmentApi.respondToOffer(respondTarget, {
      status: respond.status,
      rejection_reason: respond.rejection_reason || undefined,
      joining_date: respond.joining_date || undefined,
    });
    setRespondTarget(null); await load();
  };

  const reqName = (id: string) => {
    const r = reqs.find((r) => r.requisition_id === id);
    return r ? `${r.requisition_code} — ${r.job_title}` : id.slice(-8);
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Offer Management</h1>
        <button onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          {showForm ? "Cancel" : "+ New Offer"}
        </button>
      </div>

      {msg && <div className="bg-green-50 text-green-700 text-sm px-4 py-2 rounded">{msg}</div>}

      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Candidate ID</label>
              <input value={form.candidate_id} onChange={(e) => setForm({ ...form, candidate_id: e.target.value })}
                className="w-full border rounded p-2 text-sm" placeholder="UUID" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Requisition</label>
              <select value={form.requisition_id} onChange={(e) => setForm({ ...form, requisition_id: e.target.value })}
                className="w-full border rounded p-2 text-sm">
                <option value="">Select…</option>
                {reqs.map((r) => <option key={r.requisition_id} value={r.requisition_id}>{r.requisition_code} — {r.job_title}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Salary Offer (KES)</label>
              <input type="number" value={form.salary_offer} onChange={(e) => setForm({ ...form, salary_offer: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Offer Date</label>
              <input type="date" value={form.offer_date} onChange={(e) => setForm({ ...form, offer_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Expiry Date</label>
              <input type="date" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Joining Date</label>
              <input type="date" value={form.joining_date} onChange={(e) => setForm({ ...form, joining_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <button onClick={handleCreate} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Create Offer
          </button>
        </div>
      )}

      {respondTarget && (
        <div className="bg-white border rounded-xl p-5 space-y-3 border-green-200">
          <h2 className="text-sm font-semibold">Record Candidate Response</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Decision</label>
              <select value={respond.status}
                onChange={(e) => setRespond({ ...respond, status: e.target.value as OfferStatus })}
                className="w-full border rounded p-2 text-sm">
                {["accepted", "rejected", "negotiating"].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Joining Date (if accepted)</label>
              <input type="date" value={respond.joining_date}
                onChange={(e) => setRespond({ ...respond, joining_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Rejection Reason</label>
              <input value={respond.rejection_reason}
                onChange={(e) => setRespond({ ...respond, rejection_reason: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleRespond} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">
              Save Response
            </button>
            <button onClick={() => setRespondTarget(null)} className="border px-4 py-2 rounded text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Offer Code</th>
              <th className="px-4 py-3 text-left">Requisition</th>
              <th className="px-4 py-3 text-right">Salary</th>
              <th className="px-4 py-3 text-left">Joining</th>
              <th className="px-4 py-3 text-left">Expiry</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {offers.map((o) => (
              <tr key={o.offer_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{o.offer_code}</td>
                <td className="px-4 py-3 text-xs">{reqName(o.requisition_id)}</td>
                <td className="px-4 py-3 text-right font-semibold">{fmtCurrency(o.salary_offer, o.currency)}</td>
                <td className="px-4 py-3">{o.joining_date || "—"}</td>
                <td className="px-4 py-3">{o.expiry_date || "—"}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${OFFER_STATUS_COLOR[o.status]}`}>{o.status}</span>
                </td>
                <td className="px-4 py-3 space-x-2">
                  {o.status === "draft" && (
                    <button onClick={() => handleSend(o.offer_id)} className="text-xs text-blue-600 hover:underline">Send</button>
                  )}
                  {o.status === "sent" && (
                    <button onClick={() => setRespondTarget(o.offer_id)} className="text-xs text-green-600 hover:underline">Record Response</button>
                  )}
                </td>
              </tr>
            ))}
            {offers.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No offers</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
