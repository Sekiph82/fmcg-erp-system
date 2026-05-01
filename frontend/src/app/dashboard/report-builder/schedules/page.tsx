"use client";
import { useEffect, useState } from "react";
import { reportBuilderApi, Schedule, Report, ScheduleFrequency, ExportFormat } from "@/lib/report_builder";

const FREQS: ScheduleFrequency[] = ["daily","weekly","monthly","custom"];
const FORMATS: ExportFormat[] = ["csv","xlsx","json"];

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    report_id: "", frequency: "weekly" as ScheduleFrequency, run_time: "08:00",
    recipients: "", export_format: "csv" as ExportFormat,
  });

  const load = () =>
    Promise.all([reportBuilderApi.listSchedules(), reportBuilderApi.listReports()])
      .then(([s, r]) => { setSchedules(s); setReports(r); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.report_id) { alert("Select a report"); return; }
    await reportBuilderApi.createSchedule(form.report_id, {
      frequency: form.frequency,
      run_time: form.run_time,
      recipients: form.recipients || undefined,
      export_format: form.export_format,
    });
    setShowForm(false);
    load();
  };

  const deactivate = async (id: string) => {
    await reportBuilderApi.deactivateSchedule(id);
    load();
  };

  const getReportName = (id: string) => reports.find(r => r.report_id === id)?.report_name ?? id;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Report Schedules</h1>
        <button onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Schedule Report
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Schedule Report</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><label className="text-xs text-gray-500">Report *</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.report_id}
                onChange={(e) => setForm({ ...form, report_id: e.target.value })}>
                <option value="">Select report…</option>
                {reports.map(r => <option key={r.report_id} value={r.report_id}>{r.report_name}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Frequency</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value as ScheduleFrequency })}>
                {FREQS.map(f => <option key={f} value={f}>{f}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Run Time</label>
              <input type="time" className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.run_time}
                onChange={(e) => setForm({ ...form, run_time: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Export Format</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.export_format}
                onChange={(e) => setForm({ ...form, export_format: e.target.value as ExportFormat })}>
                {FORMATS.map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Recipients (comma-separated emails)</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" placeholder="user@example.com, …"
                value={form.recipients} onChange={(e) => setForm({ ...form, recipients: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Schedule</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Report","Frequency","Run Time","Format","Recipients","Last Run","Next Run","Actions"].map(h=>(
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {schedules.map(s => (
                <tr key={s.schedule_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{getReportName(s.report_id)}</td>
                  <td className="px-4 py-2 capitalize text-gray-600">{s.frequency}</td>
                  <td className="px-4 py-2 text-gray-600">{s.run_time ?? "—"}</td>
                  <td className="px-4 py-2 uppercase text-gray-600">{s.export_format}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs max-w-[150px] truncate">{s.recipients ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-400 text-xs">{s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "—"}</td>
                  <td className="px-4 py-2 text-gray-400 text-xs">{s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "—"}</td>
                  <td className="px-4 py-2">
                    <button onClick={() => deactivate(s.schedule_id)} className="text-xs text-red-500 hover:underline">Deactivate</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {schedules.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No active schedules.</p>}
        </div>
      )}
    </div>
  );
}
