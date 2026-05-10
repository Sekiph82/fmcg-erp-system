"use client";
import { useCallback, useEffect, useState } from "react";
import { essApi, ESSAttendanceRecord, AttendanceStatus, ATTENDANCE_STATUS_COLOR } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";
const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function AttendancePage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [records, setRecords] = useState<ESSAttendanceRecord[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [showEntry, setShowEntry] = useState(false);
  const [entry, setEntry] = useState({ attendance_date: today.toISOString().slice(0, 10), check_in: "", check_out: "", status: "present" as AttendanceStatus, notes: "" });

  const load = useCallback(async () => {
    const [recs, sum] = await Promise.all([essApi.listAttendance(DEMO_EMPLOYEE, month, year), essApi.attendanceSummary(DEMO_EMPLOYEE, month, year)]);
    setRecords(recs); setSummary(sum);
  }, [month, year]);
  useEffect(() => { load(); }, [load]);

  const handleEntry = async () => {
    await essApi.upsertAttendance({ employee_id: DEMO_EMPLOYEE, attendance_date: entry.attendance_date, check_in: entry.check_in ? new Date(entry.attendance_date + "T" + entry.check_in).toISOString() : undefined, check_out: entry.check_out ? new Date(entry.attendance_date + "T" + entry.check_out).toISOString() : undefined, status: entry.status, notes: entry.notes || undefined });
    await load(); setShowEntry(false);
  };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Attendance</h1>
          <p className="text-slate-500 text-sm mt-0.5">Daily log and monthly summary</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))} className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none">
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
          <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none w-20" />
          <button onClick={() => setShowEntry(!showEntry)} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm">
            {showEntry ? "Cancel" : "+ Log Entry"}
          </button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
          {[
            { label: "Present", value: summary.present, color: "text-emerald-400" },
            { label: "Absent", value: summary.absent, color: "text-red-400" },
            { label: "Late", value: summary.late, color: "text-amber-400" },
            { label: "On Leave", value: summary.on_leave, color: "text-blue-400" },
            { label: "Total Hours", value: `${summary.total_hours}h`, color: "text-white" },
          ].map((k) => (
            <div key={k.label} className="glow-card p-4">
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
              <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {showEntry && (
        <div className="glow-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Log Attendance</h2>
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Date</label><input type="date" value={entry.attendance_date} onChange={(e) => setEntry({ ...entry, attendance_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Check In (HH:MM)</label><input type="time" value={entry.check_in} onChange={(e) => setEntry({ ...entry, check_in: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Check Out (HH:MM)</label><input type="time" value={entry.check_out} onChange={(e) => setEntry({ ...entry, check_out: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Status</label>
              <select value={entry.status} onChange={(e) => setEntry({ ...entry, status: e.target.value as AttendanceStatus })} className={selectCls}>
                {["present", "absent", "late", "half_day", "on_leave", "holiday", "work_from_home"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
              </select>
            </div>
          </div>
          <button onClick={handleEntry} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Save Entry</button>
        </div>
      )}

      <div className="glass-table">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Date", "Status", "Check In", "Check Out", "Hours", "Late (min)", "Notes"].map((h) => (
              <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${["Hours","Late (min)"].includes(h) ? "text-right" : "text-left"}`}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.attendance_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-white font-medium">{r.attendance_date}</td>
                <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${ATTENDANCE_STATUS_COLOR[r.status]}`}>{r.status.replace("_", " ")}</span></td>
                <td className="px-4 py-3 text-slate-400">{r.check_in ? new Date(r.check_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                <td className="px-4 py-3 text-slate-400">{r.check_out ? new Date(r.check_out).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                <td className="px-4 py-3 text-right text-slate-400">{r.hours_worked ? `${r.hours_worked}h` : "—"}</td>
                <td className="px-4 py-3 text-right text-amber-400">{r.late_minutes > 0 ? r.late_minutes : "—"}</td>
                <td className="px-4 py-3 text-slate-600 text-xs">{r.notes || ""}</td>
              </tr>
            ))}
            {records.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No attendance records</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
