"use client";
import { useEffect, useState } from "react";
import {
  essApi, ESSLeaveRequest, ESSLeaveBalance, ESSLeaveType,
  LeaveStatus, LEAVE_STATUS_COLOR,
} from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function LeaveManagementPage() {
  const [requests, setRequests] = useState<ESSLeaveRequest[]>([]);
  const [balances, setBalances] = useState<ESSLeaveBalance[]>([]);
  const [types, setTypes] = useState<ESSLeaveType[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    leave_type_id: "", start_date: "", end_date: "", reason: "", attachment_ref: "",
  });
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [reqs, bals, lts] = await Promise.all([
      essApi.listLeaveRequests({ employee_id: DEMO_EMPLOYEE }),
      essApi.getLeaveBalances(DEMO_EMPLOYEE),
      essApi.listLeaveTypes(),
    ]);
    setRequests(reqs); setBalances(bals); setTypes(lts);
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    const req = await essApi.createLeaveRequest({ ...form, employee_id: DEMO_EMPLOYEE });
    await essApi.submitLeaveRequest(req.leave_request_id);
    await load(); setShowForm(false);
    setMsg("Leave request submitted"); setTimeout(() => setMsg(""), 2500);
  };

  const handleCancel = async (id: string) => {
    await essApi.cancelLeave(id, DEMO_EMPLOYEE);
    await load();
  };

  const typeName = (id: string) => types.find((t) => t.leave_type_id === id)?.type_name ?? id;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Leave Management</h1>
        <button onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          {showForm ? "Cancel" : "+ Apply Leave"}
        </button>
      </div>

      {msg && <div className="bg-green-50 text-green-700 text-sm px-4 py-2 rounded">{msg}</div>}

      {/* Leave Balances */}
      {balances.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold mb-2 text-gray-600">Leave Balances ({new Date().getFullYear()})</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {balances.map((b) => {
              const avail = b.available_days;
              const pct = b.entitled_days > 0 ? (Number(b.taken_days) / Number(b.entitled_days)) * 100 : 0;
              const lt = types.find((t) => t.leave_type_id === b.leave_type_id);
              return (
                <div key={b.balance_id} className="bg-white border rounded-xl p-4">
                  <p className="text-xs font-medium text-gray-600">{lt?.type_name ?? "Leave"}</p>
                  <p className="text-2xl font-bold text-blue-600 mt-1">{avail.toFixed(1)}</p>
                  <p className="text-xs text-gray-400">of {Number(b.entitled_days)} days available</p>
                  <div className="mt-2 h-1.5 bg-gray-100 rounded-full">
                    <div className="h-1.5 bg-blue-500 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Apply Form */}
      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Leave Type</label>
              <select value={form.leave_type_id} onChange={(e) => setForm({ ...form, leave_type_id: e.target.value })}
                className="w-full border rounded p-2 text-sm">
                <option value="">Select…</option>
                {types.map((t) => <option key={t.leave_type_id} value={t.leave_type_id}>{t.type_name}</option>)}
              </select>
            </div>
            <div />
            <div>
              <label className="block text-xs text-gray-500 mb-1">Start Date</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">End Date</label>
              <input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Reason</label>
              <textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
                rows={2} className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <button onClick={handleCreate} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Submit Request
          </button>
        </div>
      )}

      {/* History */}
      <div>
        <h2 className="text-sm font-semibold mb-2 text-gray-600">Leave History</h2>
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Ref</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">From</th>
                <th className="px-4 py-3 text-left">To</th>
                <th className="px-4 py-3 text-right">Days</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {requests.map((r) => (
                <tr key={r.leave_request_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{r.leave_request_no}</td>
                  <td className="px-4 py-3">{typeName(r.leave_type_id)}</td>
                  <td className="px-4 py-3">{r.start_date}</td>
                  <td className="px-4 py-3">{r.end_date}</td>
                  <td className="px-4 py-3 text-right">{Number(r.days_requested)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${LEAVE_STATUS_COLOR[r.status]}`}>{r.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    {(r.status === "draft" || r.status === "submitted") && (
                      <button onClick={() => handleCancel(r.leave_request_id)}
                        className="text-xs text-red-500 hover:underline">Cancel</button>
                    )}
                    {r.rejection_reason && (
                      <span className="text-xs text-gray-400 ml-2" title={r.rejection_reason}>⚠ Reason</span>
                    )}
                  </td>
                </tr>
              ))}
              {requests.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No leave requests</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
