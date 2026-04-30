"use client";
import { useEffect, useState } from "react";
import { essApi, ESSAttendanceRecord, AttendanceStatus, ATTENDANCE_STATUS_COLOR } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function AttendancePage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [records, setRecords] = useState<ESSAttendanceRecord[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [showEntry, setShowEntry] = useState(false);
  const [entry, setEntry] = useState({
    attendance_date: today.toISOString().slice(0, 10),
    check_in: "", check_out: "", status: "present" as AttendanceStatus, notes: "",
  });

  const load = async () => {
    const [recs, sum] = await Promise.all([
      essApi.listAttendance(DEMO_EMPLOYEE, month, year),
      essApi.attendanceSummary(DEMO_EMPLOYEE, month, year),
    ]);
    setRecords(recs); setSummary(sum);
  };
  useEffect(() => { load(); }, [month, year]);

  const handleEntry = async () => {
    await essApi.upsertAttendance({
      employee_id: DEMO_EMPLOYEE,
      attendance_date: entry.attendance_date,
      check_in: entry.check_in ? new Date(entry.attendance_date + "T" + entry.check_in).toISOString() : undefined,
      check_out: entry.check_out ? new Date(entry.attendance_date + "T" + entry.check_out).toISOString() : undefined,
      status: entry.status,
      notes: entry.notes || undefined,
    });
    await load(); setShowEntry(false);
  };

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Attendance</h1>
        <div className="flex items-center gap-2">
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))} className="border rounded px-2 py-1 text-sm">
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
          <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))}
            className="border rounded px-2 py-1 text-sm w-20" />
          <button onClick={() => setShowEntry(!showEntry)}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700">
            {showEntry ? "Cancel" : "+ Log Entry"}
          </button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
          {[
            { label: "Present", value: summary.present, color: "bg-green-50 text-green-700" },
            { label: "Absent", value: summary.absent, color: "bg-red-50 text-red-700" },
            { label: "Late", value: summary.late, color: "bg-yellow-50 text-yellow-700" },
            { label: "On Leave", value: summary.on_leave, color: "bg-blue-50 text-blue-700" },
            { label: "Total Hours", value: `${summary.total_hours}h`, color: "bg-gray-50 text-gray-700" },
          ].map((k) => (
            <div key={k.label} className={`rounded-xl p-3 ${k.color}`}>
              <p className="text-xs opacity-70">{k.label}</p>
              <p className="text-xl font-bold mt-0.5">{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {showEntry && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date</label>
              <input type="date" value={entry.attendance_date}
                onChange={(e) => setEntry({ ...entry, attendance_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Check In (HH:MM)</label>
              <input type="time" value={entry.check_in}
                onChange={(e) => setEntry({ ...entry, check_in: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Check Out (HH:MM)</label>
              <input type="time" value={entry.check_out}
                onChange={(e) => setEntry({ ...entry, check_out: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Status</label>
              <select value={entry.status} onChange={(e) => setEntry({ ...entry, status: e.target.value as AttendanceStatus })}
                className="w-full border rounded p-2 text-sm">
                {["present", "absent", "late", "half_day", "on_leave", "holiday", "work_from_home"].map((s) => (
                  <option key={s} value={s}>{s.replace("_", " ")}</option>
                ))}
              </select>
            </div>
          </div>
          <button onClick={handleEntry} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Save Entry
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Check In</th>
              <th className="px-4 py-3 text-left">Check Out</th>
              <th className="px-4 py-3 text-right">Hours</th>
              <th className="px-4 py-3 text-right">Late (min)</th>
              <th className="px-4 py-3 text-left">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {records.map((r) => (
              <tr key={r.attendance_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{r.attendance_date}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${ATTENDANCE_STATUS_COLOR[r.status]}`}>
                    {r.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-4 py-3">{r.check_in ? new Date(r.check_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                <td className="px-4 py-3">{r.check_out ? new Date(r.check_out).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                <td className="px-4 py-3 text-right">{r.hours_worked ? `${r.hours_worked}h` : "—"}</td>
                <td className="px-4 py-3 text-right">{r.late_minutes > 0 ? r.late_minutes : "—"}</td>
                <td className="px-4 py-3 text-gray-400 text-xs">{r.notes || ""}</td>
              </tr>
            ))}
            {records.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No attendance records</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
