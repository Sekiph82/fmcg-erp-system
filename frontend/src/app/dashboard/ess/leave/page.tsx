"use client";
import { useEffect, useState } from "react";
import { essApi, ESSLeaveRequest, ESSLeaveBalance, ESSLeaveType, LEAVE_STATUS_COLOR } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";
const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function LeaveManagementPage() {
  const [requests, setRequests] = useState<ESSLeaveRequest[]>([]);
  const [balances, setBalances] = useState<ESSLeaveBalance[]>([]);
  const [types, setTypes] = useState<ESSLeaveType[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ leave_type_id: "", start_date: "", end_date: "", reason: "", attachment_ref: "" });
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [reqs, bals, lts] = await Promise.all([essApi.listLeaveRequests({ employee_id: DEMO_EMPLOYEE }), essApi.getLeaveBalances(DEMO_EMPLOYEE), essApi.listLeaveTypes()]);
    setRequests(reqs); setBalances(bals); setTypes(lts);
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    const req = await essApi.createLeaveRequest({ ...form, employee_id: DEMO_EMPLOYEE });
    await essApi.submitLeaveRequest(req.leave_request_id);
    await load(); setShowForm(false); setMsg("Leave request submitted"); setTimeout(() => setMsg(""), 2500);
  };
  const handleCancel = async (id: string) => { await essApi.cancelLeave(id, DEMO_EMPLOYEE); await load(); };
  const typeName = (id: string) => types.find((t) => t.leave_type_id === id)?.type_name ?? id;

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Leave Management</h1>
          <p className="text-slate-500 text-sm mt-0.5">Apply leave, view balances and history</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showForm ? "Cancel" : "+ Apply Leave"}
        </button>
      </div>

      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      {/* Balances */}
      {balances.length > 0 && (
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Leave Balances ({new Date().getFullYear()})</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {balances.map((b) => {
              const lt = types.find((t) => t.leave_type_id === b.leave_type_id);
              const pct = b.entitled_days > 0 ? (Number(b.taken_days) / Number(b.entitled_days)) * 100 : 0;
              return (
                <div key={b.balance_id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{lt?.type_name ?? "Leave"}</p>
                  <p className="text-2xl font-bold text-blue-400">{b.available_days.toFixed(1)}</p>
                  <p className="text-[10px] text-slate-600 mt-0.5">of {Number(b.entitled_days)} days available</p>
                  <div className="mt-2 h-1 bg-white/[0.06] rounded-full"><div className="h-1 bg-blue-500 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} /></div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {showForm && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Apply for Leave</h2>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Leave Type</label>
              <select value={form.leave_type_id} onChange={(e) => setForm({ ...form, leave_type_id: e.target.value })} className={selectCls}>
                <option value="">Select…</option>
                {types.map((t) => <option key={t.leave_type_id} value={t.leave_type_id}>{t.type_name}</option>)}
              </select>
            </div>
            <div />
            <div><label className={labelCls}>Start Date</label><input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>End Date</label><input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className={inputCls} /></div>
            <div className="col-span-2"><label className={labelCls}>Reason</label><textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} rows={2} className={inputCls} /></div>
          </div>
          <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Submit Request</button>
        </div>
      )}

      <div>
        <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Leave History</p>
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-white/[0.07]">
              {["Ref", "Type", "From", "To", "Days", "Status", "Actions"].map((h) => (
                <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Days" ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.leave_request_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.leave_request_no}</td>
                  <td className="px-4 py-3 text-slate-300">{typeName(r.leave_type_id)}</td>
                  <td className="px-4 py-3 text-slate-400">{r.start_date}</td>
                  <td className="px-4 py-3 text-slate-400">{r.end_date}</td>
                  <td className="px-4 py-3 text-right text-white">{Number(r.days_requested)}</td>
                  <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${LEAVE_STATUS_COLOR[r.status]}`}>{r.status}</span></td>
                  <td className="px-4 py-3">
                    {(r.status === "draft" || r.status === "submitted") && (
                      <button onClick={() => handleCancel(r.leave_request_id)} className="text-xs text-red-400 hover:text-red-300">Cancel</button>
                    )}
                    {r.rejection_reason && <span className="text-xs text-slate-600 ml-2" title={r.rejection_reason}>⚠</span>}
                  </td>
                </tr>
              ))}
              {requests.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No leave requests</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
