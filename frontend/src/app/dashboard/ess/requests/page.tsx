"use client";
import { useEffect, useState } from "react";
import { essApi, ESSRequest, ESSRequestType, ESSRequestStatus, REQUEST_STATUS_COLOR } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";
const REQ_TYPES: ESSRequestType[] = ["leave", "expense", "profile_update", "document", "certificate", "payslip", "other"];

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
    await load(); setShowForm(false);
    setMsg("Request submitted"); setTimeout(() => setMsg(""), 2500);
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">My Requests</h1>
        <button onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          {showForm ? "Cancel" : "+ New Request"}
        </button>
      </div>

      {msg && <div className="bg-green-50 text-green-700 text-sm px-4 py-2 rounded">{msg}</div>}

      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Request Type</label>
              <select value={form.request_type} onChange={(e) => setForm({ ...form, request_type: e.target.value as ESSRequestType })}
                className="w-full border rounded p-2 text-sm">
                {REQ_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Subject</label>
              <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Description</label>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3} className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <button onClick={handleCreate} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Submit Request
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Ref</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Subject</th>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">HR Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {requests.map((r) => (
              <tr key={r.request_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{r.request_no}</td>
                <td className="px-4 py-3 capitalize text-xs">{r.request_type.replace("_", " ")}</td>
                <td className="px-4 py-3">{r.subject}</td>
                <td className="px-4 py-3">{r.request_date}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${REQUEST_STATUS_COLOR[r.status]}`}>{r.status.replace("_", " ")}</span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">{r.hr_notes || "—"}</td>
              </tr>
            ))}
            {requests.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No requests</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
