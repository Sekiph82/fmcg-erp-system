"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  timesheetsApi, TimesheetHeader, TimesheetStatus,
  STATUS_COLOR, STATUS_LABEL,
} from "@/lib/timesheets";

const STATUSES: TimesheetStatus[] = ["draft","submitted","manager_approved","rejected","finalized"];

export default function MyTimesheetsPage() {
  const [timesheets, setTimesheets] = useState<TimesheetHeader[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [empId, setEmpId] = useState("");
  const [selected, setSelected] = useState<TimesheetHeader | null>(null);
  const [submitNotes, setSubmitNotes] = useState("");

  const load = useCallback(() =>
    timesheetsApi.list({ status: statusFilter || undefined, employee_id: empId || undefined })
      .then(setTimesheets).finally(() => setLoading(false)), [statusFilter, empId]);
  useEffect(() => { load(); }, [load]);

  const submit = async (id: string) => {
    await timesheetsApi.submit(id, { notes: submitNotes || undefined });
    setSelected(null);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">My Timesheets</h1>
        <Link href="/dashboard/timesheets/time-entry"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Timesheet
        </Link>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select className="border rounded px-2 py-1 text-sm" value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </select>
        <input className="border rounded px-2 py-1 text-sm w-40" placeholder="Employee ID…"
          value={empId} onChange={(e) => setEmpId(e.target.value)} />
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Employee","Period","Total Hrs","Overtime Hrs","Status","Rejections","Actions"].map(h=>(
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {timesheets.map(ts => (
                <tr key={ts.timesheet_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(ts)}>
                  <td className="px-4 py-2 font-medium text-gray-800">{ts.employee_name ?? ts.employee_id}</td>
                  <td className="px-4 py-2 text-gray-600">{ts.period_start} → {ts.period_end}</td>
                  <td className="px-4 py-2 text-center font-semibold">{Number(ts.total_hours).toFixed(1)}</td>
                  <td className={`px-4 py-2 text-center font-semibold ${Number(ts.overtime_hours) > 0 ? "text-orange-600" : "text-gray-400"}`}>
                    {Number(ts.overtime_hours).toFixed(1)}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[ts.status]}`}>
                      {STATUS_LABEL[ts.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">
                    {ts.rejection_count > 0 && <span className="text-red-600 font-semibold">{ts.rejection_count}</span>}
                    {ts.rejection_count === 0 && <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                    {(ts.status === "draft" || ts.status === "rejected") && (
                      <button
                        onClick={() => { setSelected(ts); setSubmitNotes(""); }}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Submit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {timesheets.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No timesheets found.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6 space-y-4 my-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                Timesheet — {selected.employee_name ?? selected.employee_id}
              </h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm bg-gray-50 rounded p-3">
              <div><span className="text-gray-500">Period:</span> {selected.period_start} → {selected.period_end}</div>
              <div><span className="text-gray-500">Total Hours:</span> <strong>{Number(selected.total_hours).toFixed(1)}</strong></div>
              <div><span className="text-gray-500">Overtime:</span> <strong className="text-orange-600">{Number(selected.overtime_hours).toFixed(1)}</strong></div>
              <div><span className="text-gray-500">Regular:</span> {Number(selected.regular_hours).toFixed(1)}</div>
              <div><span className="text-gray-500">Status:</span>
                <span className={`ml-1 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[selected.status]}`}>
                  {STATUS_LABEL[selected.status]}
                </span>
              </div>
            </div>

            {selected.lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Time Lines</h3>
                <table className="w-full text-xs border rounded">
                  <thead className="bg-gray-50"><tr>
                    {["Date","Activity","Project","Cost Center","Hours","OT","Billable"].map(h=>(
                      <th key={h} className="px-2 py-1 text-left text-gray-600">{h}</th>
                    ))}
                  </tr></thead>
                  <tbody className="divide-y">
                    {selected.lines.map(l => (
                      <tr key={l.timesheet_line_id}>
                        <td className="px-2 py-1">{l.work_date}</td>
                        <td className="px-2 py-1 capitalize">{l.activity_type}</td>
                        <td className="px-2 py-1">{l.project_name ?? "—"}</td>
                        <td className="px-2 py-1">{l.cost_center_name ?? "—"}</td>
                        <td className="px-2 py-1 font-semibold">{Number(l.hours_worked).toFixed(1)}</td>
                        <td className="px-2 py-1">{l.overtime_flag ? "✓" : "—"}</td>
                        <td className="px-2 py-1">{l.billable_flag ? "✓" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {selected.approval_logs.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Approval History</h3>
                <div className="space-y-1">
                  {selected.approval_logs.map(log => (
                    <div key={log.approval_id} className="text-xs flex gap-2 items-start">
                      <span className="text-gray-400 w-32 shrink-0">{new Date(log.action_date).toLocaleString()}</span>
                      <span className={`font-semibold capitalize w-20 shrink-0 ${log.action === "approved" || log.action === "finalized" ? "text-green-600" : log.action === "rejected" ? "text-red-600" : "text-blue-600"}`}>
                        {log.action}
                      </span>
                      <span className="text-gray-600">{log.approver_name ?? log.approver_id ?? "—"}</span>
                      {log.comments && <span className="text-gray-500 italic">— {log.comments}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(selected.status === "draft" || selected.status === "rejected") && (
              <div className="border-t pt-3 space-y-2">
                <div>
                  <label className="text-xs text-gray-500">Submission Notes</label>
                  <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
                    value={submitNotes} onChange={(e) => setSubmitNotes(e.target.value)} />
                </div>
                <button onClick={() => submit(selected.timesheet_id)}
                  className="rounded bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  {selected.rejection_count > 0 ? "Resubmit" : "Submit for Approval"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
