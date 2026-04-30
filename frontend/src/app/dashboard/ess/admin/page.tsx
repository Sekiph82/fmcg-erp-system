"use client";
import { useEffect, useState } from "react";
import { essApi, ESSLeaveRequest, ESSRequest, ESSAccount } from "@/lib/ess";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function HRAdminPage() {
  const [tab, setTab] = useState<"accounts" | "leave" | "requests" | "seed">("leave");
  const [pendingLeave, setPendingLeave] = useState<ESSLeaveRequest[]>([]);
  const [pendingReqs, setPendingReqs] = useState<ESSRequest[]>([]);
  const [accounts, setAccounts] = useState<ESSAccount[]>([]);
  const [newAcc, setNewAcc] = useState({ employee_id: "", email: "", password: "" });
  const [newProfile, setNewProfile] = useState({ employee_id: "", full_name: "", email: "", job_title: "", department_name: "", joining_date: "" });
  const [msg, setMsg] = useState("");

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 2500); };
  const load = async () => {
    const [lv, rq, ac] = await Promise.all([essApi.listLeaveRequests({ status: "submitted" }), essApi.listRequests({ status: "submitted" }), essApi.listAccounts()]);
    setPendingLeave(lv); setPendingReqs(rq); setAccounts(ac);
  };
  useEffect(() => { load(); }, []);

  const handleApproveLeave = async (id: string) => { await essApi.approveLeave(id, { approver_id: "00000000-0000-0000-0000-000000000002" }); await load(); flash("Leave approved"); };
  const handleRejectLeave = async (id: string) => { await essApi.rejectLeave(id, { approver_id: "00000000-0000-0000-0000-000000000002", rejection_reason: "Operational requirements" }); await load(); flash("Leave rejected"); };
  const handleReviewReq = async (id: string, approved: boolean) => { await essApi.reviewRequest(id, { approver_id: "00000000-0000-0000-0000-000000000002", status: approved ? "approved" : "rejected", hr_notes: approved ? "Processed by HR" : "Request declined" }); await load(); flash(approved ? "Request approved" : "Request rejected"); };
  const handleCreateAccount = async () => { await essApi.createAccount(newAcc); flash("Account created"); setNewAcc({ employee_id: "", email: "", password: "" }); await load(); };
  const handleCreateProfile = async () => { await essApi.upsertProfile({ ...newProfile, employment_status: "active" }); flash("Profile saved"); };
  const handleSeedLeaveTypes = async () => { await essApi.seedLeaveTypes(); flash("7 leave types seeded"); };

  const tabs = [
    { id: "leave" as const, label: "Leave Approvals", badge: pendingLeave.length },
    { id: "requests" as const, label: "Request Queue", badge: pendingReqs.length },
    { id: "accounts" as const, label: "Accounts & Profiles", badge: 0 },
    { id: "seed" as const, label: "Setup", badge: 0 },
  ];

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div>
        <h1 className="text-xl font-bold text-white">HR Administration</h1>
        <p className="text-slate-500 text-sm mt-0.5">Leave approvals, request queue, and account management</p>
      </div>
      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors flex items-center gap-1.5 ${tab === t.id ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {t.label}
            {t.badge > 0 && <span className="bg-red-500 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{t.badge}</span>}
          </button>
        ))}
      </div>

      {tab === "leave" && (
        <div className="glass-table">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-white/[0.07]">
              {["Ref", "Employee", "Dates", "Days", "Reason", "Actions"].map((h) => (
                <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Days" ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {pendingLeave.map((r) => (
                <tr key={r.leave_request_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.leave_request_no}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.employee_id.slice(-8)}</td>
                  <td className="px-4 py-3 text-slate-400">{r.start_date} – {r.end_date}</td>
                  <td className="px-4 py-3 text-right text-white">{Number(r.days_requested)}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs max-w-[160px] truncate">{r.reason || "—"}</td>
                  <td className="px-4 py-3 space-x-3">
                    <button onClick={() => handleApproveLeave(r.leave_request_id)} className="text-xs text-emerald-400 hover:text-emerald-300">Approve</button>
                    <button onClick={() => handleRejectLeave(r.leave_request_id)} className="text-xs text-red-400 hover:text-red-300">Reject</button>
                  </td>
                </tr>
              ))}
              {pendingLeave.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-600">No pending leave requests</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "requests" && (
        <div className="glass-table">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-white/[0.07]">
              {["Ref", "Type", "Subject", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {pendingReqs.map((r) => (
                <tr key={r.request_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.request_no}</td>
                  <td className="px-4 py-3 text-slate-400 capitalize text-xs">{r.request_type.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-white">{r.subject}</td>
                  <td className="px-4 py-3 space-x-3">
                    <button onClick={() => handleReviewReq(r.request_id, true)} className="text-xs text-emerald-400 hover:text-emerald-300">Approve</button>
                    <button onClick={() => handleReviewReq(r.request_id, false)} className="text-xs text-red-400 hover:text-red-300">Reject</button>
                  </td>
                </tr>
              ))}
              {pendingReqs.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-600">No pending requests</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "accounts" && (
        <div className="space-y-4">
          <div className="glow-card p-5 space-y-3">
            <h2 className="text-sm font-semibold text-white">Create ESS Account</h2>
            <div className="grid grid-cols-3 gap-3">
              <div><label className={labelCls}>Employee ID (UUID)</label><input value={newAcc.employee_id} onChange={(e) => setNewAcc({ ...newAcc, employee_id: e.target.value })} className={inputCls} /></div>
              <div><label className={labelCls}>Email</label><input value={newAcc.email} onChange={(e) => setNewAcc({ ...newAcc, email: e.target.value })} className={inputCls} /></div>
              <div><label className={labelCls}>Password</label><input type="password" value={newAcc.password} onChange={(e) => setNewAcc({ ...newAcc, password: e.target.value })} className={inputCls} /></div>
            </div>
            <button onClick={handleCreateAccount} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Create Account</button>
          </div>
          <div className="glow-card p-5 space-y-3">
            <h2 className="text-sm font-semibold text-white">Create / Update Profile</h2>
            <div className="grid grid-cols-3 gap-3">
              {[["employee_id", "Employee ID (UUID)"], ["full_name", "Full Name"], ["email", "Work Email"], ["job_title", "Job Title"], ["department_name", "Department"], ["joining_date", "Joining Date"]].map(([k, l]) => (
                <div key={k}><label className={labelCls}>{l}</label><input value={(newProfile as any)[k]} onChange={(e) => setNewProfile({ ...newProfile, [k]: e.target.value })} className={inputCls} /></div>
              ))}
            </div>
            <button onClick={handleCreateProfile} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Save Profile</button>
          </div>
        </div>
      )}

      {tab === "seed" && (
        <div className="glow-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">Initial Setup</h2>
          <div className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
            <div>
              <p className="text-sm font-medium text-white">Seed Leave Types</p>
              <p className="text-xs text-slate-500">Creates 7 defaults: Annual, Sick, Maternity, Paternity, Compassionate, Study, Unpaid</p>
            </div>
            <button onClick={handleSeedLeaveTypes} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm">Seed</button>
          </div>
        </div>
      )}
    </div>
  );
}
