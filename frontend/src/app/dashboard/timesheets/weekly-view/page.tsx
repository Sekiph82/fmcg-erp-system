"use client";
import { useEffect, useState } from "react";
import { timesheetsApi, TimesheetHeader, ACTIVITY_COLOR, ActivityType } from "@/lib/timesheets";

function getMondayStr(d: Date): string {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(new Date(d).setDate(diff)).toISOString().slice(0, 10);
}

export default function WeeklyViewPage() {
  const [weekStart, setWeekStart] = useState(getMondayStr(new Date()));
  const [timesheets, setTimesheets] = useState<TimesheetHeader[]>([]);
  const [loading, setLoading] = useState(true);

  const weekEnd = (() => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 6);
    return d.toISOString().slice(0, 10);
  })();

  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });

  useEffect(() => {
    timesheetsApi.list({ period_start: weekStart })
      .then((ts) => setTimesheets(ts.filter(t => t.period_start <= weekEnd && t.period_end >= weekStart)))
      .finally(() => setLoading(false));
  }, [weekStart]);

  const prevWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    setWeekStart(d.toISOString().slice(0, 10));
  };
  const nextWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    setWeekStart(d.toISOString().slice(0, 10));
  };

  // Build grid: employee → day → [lines]
  type CellEntry = { activity_type: ActivityType; hours: number; project: string | null };
  const grid: Record<string, Record<string, CellEntry[]>> = {};
  const empNames: Record<string, string> = {};
  for (const ts of timesheets) {
    const emp = ts.employee_id;
    empNames[emp] = ts.employee_name ?? emp;
    if (!grid[emp]) grid[emp] = {};
    for (const l of ts.lines) {
      if (!grid[emp][l.work_date]) grid[emp][l.work_date] = [];
      grid[emp][l.work_date].push({ activity_type: l.activity_type, hours: Number(l.hours_worked), project: l.project_name });
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Weekly Timesheet View</h1>
        <div className="flex items-center gap-3">
          <button onClick={prevWeek} className="rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-50">← Prev</button>
          <span className="text-sm font-medium text-gray-700">{weekStart} → {weekEnd}</span>
          <button onClick={nextWeek} className="rounded border px-3 py-1 text-sm text-gray-600 hover:bg-gray-50">Next →</button>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-gray-600 w-32">Employee</th>
                {weekDays.map(d => (
                  <th key={d} className="px-2 py-2 text-center font-semibold text-gray-600 min-w-[100px]">
                    {new Date(d + "T00:00:00").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}
                  </th>
                ))}
                <th className="px-3 py-2 text-right font-semibold text-gray-600">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {Object.entries(grid).map(([empId, days]) => {
                const total = Object.values(days).flat().reduce((s, e) => s + e.hours, 0);
                return (
                  <tr key={empId} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-800">{empNames[empId]}</td>
                    {weekDays.map(d => {
                      const entries = days[d] ?? [];
                      const dayTotal = entries.reduce((s, e) => s + e.hours, 0);
                      return (
                        <td key={d} className="px-2 py-2 text-center align-top">
                          {entries.length === 0 ? (
                            <span className="text-gray-300">—</span>
                          ) : (
                            <div className="space-y-1">
                              {entries.map((e, i) => (
                                <div key={i} className={`rounded px-1 py-0.5 ${ACTIVITY_COLOR[e.activity_type]}`}>
                                  <div className="font-semibold">{e.hours}h</div>
                                  {e.project && <div className="text-xs opacity-75 truncate">{e.project}</div>}
                                </div>
                              ))}
                              {entries.length > 1 && (
                                <div className="text-gray-500 font-semibold">{dayTotal}h total</div>
                              )}
                            </div>
                          )}
                        </td>
                      );
                    })}
                    <td className="px-3 py-2 text-right font-bold text-gray-900">{total.toFixed(1)}h</td>
                  </tr>
                );
              })}
              {Object.keys(grid).length === 0 && (
                <tr><td colSpan={9} className="text-center text-gray-400 py-8">No timesheets for this week.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {(Object.entries(ACTIVITY_COLOR) as [ActivityType, string][]).map(([type, cls]) => (
          <span key={type} className={`rounded-full px-2 py-0.5 text-xs ${cls}`}>{type}</span>
        ))}
      </div>
    </div>
  );
}
