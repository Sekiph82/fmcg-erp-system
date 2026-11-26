"use client";
import { useEffect, useState } from "react";
import { essSelf, ESSAttendanceRecord, ATTENDANCE_STATUS_COLOR } from "@/lib/ess";
import { tx } from "@/lib/i18n/core";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function AttendancePage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [records, setRecords] = useState<ESSAttendanceRecord[]>([]);
  const [summary, setSummary] = useState<Record<string, number | string> | null>(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const r = await essSelf.attendance(month, year);
    setRecords(r.records); setSummary(r.summary as Record<string, number | string>);
  };
  useEffect(() => { load().catch((e) => setMsg(e.message)); }, [month, year]); // eslint-disable-line react-hooks/exhaustive-deps

  // check in / out at the server's time — employees do not type their own hours
  const clock = async (action: "in" | "out") => {
    try { await essSelf.clock(action); setMsg(action === "in" ? tx("Checked in.") : tx("Checked out.")); await load(); }
    catch (e) { setMsg((e as Error).message); }
  };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{tx("Attendance")}</h1>
          <p className="text-slate-500 text-sm mt-0.5">{tx("Daily log and monthly summary")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))} className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none">
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
          <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} className="bg-[#0d1829] border border-white/[0.08] rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none w-20" />
          <button onClick={() => clock("in")} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm">{tx("Check in now")}</button>
          <button onClick={() => clock("out")} className="px-3 py-1.5 rounded-lg bg-slate-600 hover:bg-slate-500 text-white text-sm">{tx("Check out now")}</button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
          {[
            { label: tx("Present"), value: summary.present, color: "text-emerald-400" },
            { label: tx("Absent"), value: summary.absent, color: "text-red-400" },
            { label: tx("Late"), value: summary.late, color: "text-amber-400" },
            { label: tx("On Leave"), value: summary.on_leave, color: "text-blue-400" },
            { label: tx("Total Hours"), value: `${summary.total_hours}h`, color: "text-white" },
          ].map((k) => (
            <div key={k.label} className="glow-card p-4">
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
              <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {msg && <p role="status" className="text-sm text-amber-300">{msg}</p>}

      <div className="glass-table">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {[tx("Date"), tx("Status"), tx("Check In"), tx("Check Out"), tx("Hours"), tx("Late (min)"), tx("Notes")].map((h) => (
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
                <td className="px-4 py-3 text-right text-slate-400">{r.hours_worked ? tx("{hours_worked}h", { hours_worked: r.hours_worked }) : "—"}</td>
                <td className="px-4 py-3 text-right text-amber-400">{r.late_minutes > 0 ? r.late_minutes : "—"}</td>
                <td className="px-4 py-3 text-slate-600 text-xs">{r.notes || ""}</td>
              </tr>
            ))}
            {records.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">{tx("No attendance records")}</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
