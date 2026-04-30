"use client";
import { useEffect, useState } from "react";
import { essApi, ESSLeaveRequest, ESSRequest, ESSAccount } from "@/lib/ess";

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
    const [lv, rq, ac] = await Promise.all([
      essApi.listLeaveRequests({ status: "submitted" }),
      essApi.listRequests({ status: "submitted" }),
      essApi.listAccounts(),
    ]);
    setPendingLeave(lv); setPendingReqs(rq); setAccounts(ac);
  };
  useEffect(() => { load(); }, []);

  const handleApproveLeave = async (id: string) => {
    await essApi.approveLeave(id, { approver_id: "00000000-0000-0000-0000-000000000002" });
    await load(); flash("Leave approved");
  };
  const handleRejectLeave = async (id: string) => {
    await essApi.rejectLeave(id, { approver_id: "00000000-0000-0000-0000-000000000002", rejection_reason: "Operational requirements" });
    await load(); flash("Leave rejected");
  };
  const handleReviewReq = async (id: string, approved: boolean) => {
    await essApi.reviewRequest(id, { approver_id: "00000000-0000-0000-0000-000000000002", status: approved ? "approved" : "rejected", hr_notes: approved ? "Processed by HR" : "Request declined" });
    await load(); flash(approved ? "Request approved" : "Request rejected");
  };
  const handleCreateAccount = async () => {
    await essApi.createAccount(newAcc);
    flash("Account created");
    setNewAcc({ employee_id: "", email: "", password: "" });
    await load();
  };
  const handleCreateProfile = async () => {
    await essApi.upsertProfile({ ...newProfile, employment_status: "active" });
    flash("Profile created/updated");
  };
  const handleSeedLeaveTypes = async () => {
    await essApi.seedLeaveTypes();
    flash("Leave types seeded (7 defaults)");
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold">HR Administration</h1>
      {msg && <div className="bg-green-50 text-green-700 text-sm px-4 py-2 rounded">{msg}</div>}

      <div className="flex gap-2">
        {(["leave", "requests", "accounts", "seed"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded text-sm border capitalize ${tab === t ? "bg-blue-600 text-white" : "bg-white"}`}>
            {t === "seed" ? "Setup" : t}
            {t === "leave" && pendingLeave.length > 0 && <span className="ml-1 text-xs bg-red-500 text-white rounded-full px-1.5">{pendingLeave.length}</span>}
            {t === "requests" && pendingReqs.length > 0 && <span className="ml-1 text-xs bg-red-500 text-white rounded-full px-1.5">{pendingReqs.length}</span>}
          </button>
        ))}
      </div>

      {tab === "leave" && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Ref</th>
                <th className="px-4 py-3 text-left">Employee</th>
                <th className="px-4 py-3 text-left">Dates</th>
                <th className="px-4 py-3 text-right">Days</th>
                <th className="px-4 py-3 text-left">Reason</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {pendingLeave.map((r) => (
                <tr key={r.leave_request_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{r.leave_request_no}</td>
                  <td className="px-4 py-3 font-mono text-xs">{r.employee_id.slice(-8)}</td>
                  <td className="px-4 py-3">{r.start_date} – {r.end_date}</td>
                  <td className="px-4 py-3 text-right">{Number(r.days_requested)}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-[160px] truncate">{r.reason || "—"}</td>
                  <td className="px-4 py-3 space-x-2">
                    <button onClick={() => handleApproveLeave(r.leave_request_id)} className="text-xs text-green-600 hover:underline">Approve</button>
                    <button onClick={() => handleRejectLeave(r.leave_request_id)} className="text-xs text-red-500 hover:underline">Reject</button>
                  </td>
                </tr>
              ))}
              {pendingLeave.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No pending leave requests</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "requests" && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Ref</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Subject</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {pendingReqs.map((r) => (
                <tr key={r.request_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{r.request_no}</td>
                  <td className="px-4 py-3 capitalize text-xs">{r.request_type.replace("_", " ")}</td>
                  <td className="px-4 py-3">{r.subject}</td>
                  <td className="px-4 py-3 space-x-2">
                    <button onClick={() => handleReviewReq(r.request_id, true)} className="text-xs text-green-600 hover:underline">Approve</button>
                    <button onClick={() => handleReviewReq(r.request_id, false)} className="text-xs text-red-500 hover:underline">Reject</button>
                  </td>
                </tr>
              ))}
              {pendingReqs.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No pending requests</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "accounts" && (
        <div className="space-y-4">
          <div className="bg-white border rounded-xl p-5 space-y-3">
            <h2 className="text-sm font-semibold">Create ESS Account</h2>
            <div className="grid grid-cols-3 gap-3">
              <div><label className="block text-xs text-gray-500 mb-1">Employee ID (UUID)</label>
                <input value={newAcc.employee_id} onChange={(e) => setNewAcc({ ...newAcc, employee_id: e.target.value })} className="w-full border rounded p-2 text-sm" /></div>
              <div><label className="block text-xs text-gray-500 mb-1">Email</label>
                <input value={newAcc.email} onChange={(e) => setNewAcc({ ...newAcc, email: e.target.value })} className="w-full border rounded p-2 text-sm" /></div>
              <div><label className="block text-xs text-gray-500 mb-1">Password</label>
                <input type="password" value={newAcc.password} onChange={(e) => setNewAcc({ ...newAcc, password: e.target.value })} className="w-full border rounded p-2 text-sm" /></div>
            </div>
            <button onClick={handleCreateAccount} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">Create Account</button>
          </div>
          <div className="bg-white border rounded-xl p-5 space-y-3">
            <h2 className="text-sm font-semibold">Create / Update Profile</h2>
            <div className="grid grid-cols-3 gap-3">
              {[["employee_id", "Employee ID (UUID)"], ["full_name", "Full Name"], ["email", "Work Email"], ["job_title", "Job Title"], ["department_name", "Department"], ["joining_date", "Joining Date"]].map(([k, l]) => (
                <div key={k}><label className="block text-xs text-gray-500 mb-1">{l}</label>
                  <input value={(newProfile as any)[k]} onChange={(e) => setNewProfile({ ...newProfile, [k]: e.target.value })} className="w-full border rounded p-2 text-sm" /></div>
              ))}
            </div>
            <button onClick={handleCreateProfile} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">Save Profile</button>
          </div>
        </div>
      )}

      {tab === "seed" && (
        <div className="bg-white border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold">Initial Setup</h2>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="text-sm font-medium">Seed Leave Types</p>
                <p className="text-xs text-gray-500">Creates 7 default leave types: Annual, Sick, Maternity, Paternity, Compassionate, Study, Unpaid</p>
              </div>
              <button onClick={handleSeedLeaveTypes} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700">Seed</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
