"use client";
import { useEffect, useState } from "react";
import { essApi, ESSRequest, ESSRequestType, REQUEST_STATUS_COLOR } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";
const REQ_TYPES: ESSRequestType[] = ["leave", "expense", "profile_update", "document", "certificate", "payslip", "other"];
const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function RequestTrackerPage() {
  const [requests, setRequests] = useState<ESSRequest[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ request_type: "other" as ESSRequestType, subject: "", description: "", attachment_ref: "" });
  const [msg, setMsg] = useState("");

  const load = () => essApi.listRequests({ employee_id: DEMO_EMPLOYEE }).then(setRequests).catch(console.error);
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    const req = await essApi.createRequest({ ...form, employee_id: DEMO_EMPLOYEE });
    await essApi.submitRequest(req.request_id);
    await load(); setShowForm(false); setMsg("Request submitted"); setTimeout(() => setMsg(""), 2500);
  };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">My Requests</h1>
          <p className="text-slate-500 text-sm mt-0.5">{requests.length} requests</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showForm ? "Cancel" : "+ New Request"}
        </button>
      </div>

      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      {showForm && (
        <div className="glow-card p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Request Type</label>
              <select value={form.request_type} onChange={(e) => setForm({ ...form, request_type: e.target.value as ESSRequestType })} className={selectCls}>
                {REQ_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
              </select>
            </div>
            <div><label className={labelCls}>Subject</label><input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className={inputCls} /></div>
            <div className="col-span-2"><label className={labelCls}>Description</label><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className={inputCls} /></div>
          </div>
          <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Submit Request</button>
        </div>
      )}

      <div className="glass-table">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Ref", "Type", "Subject", "Date", "Status", "HR Notes"].map((h) => (
              <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {requests.map((r) => (
              <tr key={r.request_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.request_no}</td>
                <td className="px-4 py-3 text-slate-400 capitalize text-xs">{r.request_type.replace("_", " ")}</td>
                <td className="px-4 py-3 text-white">{r.subject}</td>
                <td className="px-4 py-3 text-slate-400">{r.request_date}</td>
                <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${REQUEST_STATUS_COLOR[r.status]}`}>{r.status.replace("_", " ")}</span></td>
                <td className="px-4 py-3 text-slate-600 text-xs">{r.hr_notes || "—"}</td>
              </tr>
            ))}
            {requests.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-600">No requests</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
