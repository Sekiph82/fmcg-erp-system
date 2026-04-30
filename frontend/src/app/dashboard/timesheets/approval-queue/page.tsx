"use client";
import { useEffect, useState } from "react";
import { timesheetsApi, TimesheetHeader, STATUS_COLOR, STATUS_LABEL } from "@/lib/timesheets";

export default function ApprovalQueuePage() {
  const [queue, setQueue] = useState<TimesheetHeader[]>([]);
  const [approved, setApproved] = useState<TimesheetHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"pending" | "approved">("pending");
  const [selected, setSelected] = useState<TimesheetHeader | null>(null);
  const [form, setForm] = useState({ approver_name: "", comments: "" });
  const [deptFilter, setDeptFilter] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () =>
    Promise.all([
      timesheetsApi.approvalQueue(deptFilter || undefined),
      timesheetsApi.list({ status: "manager_approved" }),
    ]).then(([q, a]) => { setQueue(q); setApproved(a); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, [deptFilter]);

  const approve = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await timesheetsApi.approve(selected.timesheet_id, {
        approver_name: form.approver_name || undefined,
        comments: form.comments || undefined,
      });
      setSelected(null);
      load();
    } finally { setSaving(false); }
  };

  const reject = async () => {
    if (!selected || !form.comments) { alert("Rejection reason required"); return; }
    setSaving(true);
    try {
      await timesheetsApi.reject(selected.timesheet_id, {
        approver_name: form.approver_name || undefined,
        comments: form.comments,
      });
      setSelected(null);
      load();
    } finally { setSaving(false); }
  };

  const finalize = async (id: string) => {
    await timesheetsApi.finalize(id, { finalized_by: "HR" });
    load();
  };

  const records = tab === "pending" ? queue : approved;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Approval Queue</h1>

      <div className="flex gap-2 items-center flex-wrap">
        <button onClick={() => setTab("pending")}
          className={`px-4 py-2 text-sm rounded font-medium ${tab === "pending" ? "bg-blue-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}>
          Pending Approval ({queue.length})
        </button>
        <button onClick={() => setTab("approved")}
          className={`px-4 py-2 text-sm rounded font-medium ${tab === "approved" ? "bg-purple-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}>
          Manager Approved ({approved.length})
        </button>
        <input className="border rounded px-2 py-1 text-sm w-36 ml-auto" placeholder="Dept filter…"
          value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} />
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Employee","Dept","Period","Total Hrs","OT Hrs","Submitted","Status","Actions"].map(h=>(
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {records.map(ts => (
                <tr key={ts.timesheet_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{ts.employee_name ?? ts.employee_id}</td>
                  <td className="px-4 py-2 text-gray-600">{ts.department_name ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{ts.period_start} → {ts.period_end}</td>
                  <td className="px-4 py-2 text-center font-semibold">{Number(ts.total_hours).toFixed(1)}</td>
                  <td className={`px-4 py-2 text-center ${Number(ts.overtime_hours) > 0 ? "text-orange-600 font-semibold" : "text-gray-400"}`}>
                    {Number(ts.overtime_hours).toFixed(1)}
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {ts.submitted_at ? new Date(ts.submitted_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[ts.status]}`}>
                      {STATUS_LABEL[ts.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 flex gap-2">
                    {ts.status === "submitted" && (
                      <button
                        onClick={() => { setSelected(ts); setForm({ approver_name: "", comments: "" }); }}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Review
                      </button>
                    )}
                    {ts.status === "manager_approved" && (
                      <button onClick={() => finalize(ts.timesheet_id)} className="text-xs text-purple-600 hover:underline">
                        Finalize
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {records.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No timesheets in this queue.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 space-y-4 my-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                Review — {selected.employee_name ?? selected.employee_id}
              </h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <div className="grid grid-cols-3 gap-3 bg-gray-50 rounded p-3 text-sm">
              <div><span className="text-gray-500">Period:</span> {selected.period_start} → {selected.period_end}</div>
              <div><span className="text-gray-500">Total:</span> <strong>{Number(selected.total_hours).toFixed(1)}h</strong></div>
              <div><span className="text-gray-500">OT:</span> <strong className="text-orange-600">{Number(selected.overtime_hours).toFixed(1)}h</strong></div>
            </div>

            {selected.lines.length > 0 && (
              <div className="max-h-48 overflow-y-auto">
                <table className="w-full text-xs border rounded">
                  <thead className="bg-gray-50 sticky top-0"><tr>
                    {["Date","Activity","Project","Hours","OT"].map(h=><th key={h} className="px-2 py-1 text-left text-gray-600">{h}</th>)}
                  </tr></thead>
                  <tbody className="divide-y">
                    {selected.lines.map(l => (
                      <tr key={l.timesheet_line_id}>
                        <td className="px-2 py-1">{l.work_date}</td>
                        <td className="px-2 py-1 capitalize">{l.activity_type}</td>
                        <td className="px-2 py-1">{l.project_name ?? "—"}</td>
                        <td className="px-2 py-1 font-semibold">{Number(l.hours_worked).toFixed(1)}</td>
                        <td className="px-2 py-1">{l.overtime_flag ? "✓" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500">Approver Name</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={form.approver_name} onChange={(e) => setForm({ ...form, approver_name: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Comments (required for rejection)</label>
                <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
                  value={form.comments} onChange={(e) => setForm({ ...form, comments: e.target.value })} />
              </div>
            </div>

            <div className="flex gap-2">
              <button onClick={approve} disabled={saving}
                className="rounded bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
                {saving ? "…" : "Approve"}
              </button>
              <button onClick={reject} disabled={saving}
                className="rounded bg-red-600 px-5 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {saving ? "…" : "Reject"}
              </button>
              <button onClick={() => setSelected(null)} className="rounded border px-5 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
