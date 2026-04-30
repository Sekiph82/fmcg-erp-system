"use client";
import { useState } from "react";
import { timesheetsApi } from "@/lib/timesheets";

type ReportTab = "summary" | "utilization" | "overtime" | "project" | "activity" | "payroll";

export default function TimesheetReportsPage() {
  const [tab, setTab] = useState<ReportTab>("summary");
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");

  const run = async () => {
    setLoading(true);
    setData(null);
    try {
      if (tab === "summary") setData(await timesheetsApi.reportSummary(periodStart || undefined));
      else if (tab === "utilization") setData(await timesheetsApi.reportUtilization(periodStart || undefined));
      else if (tab === "overtime") setData(await timesheetsApi.reportOvertime(periodStart || undefined));
      else if (tab === "project") setData(await timesheetsApi.reportProjectTime());
      else if (tab === "activity") setData(await timesheetsApi.reportActivitySummary(periodStart || undefined));
      else if (tab === "payroll") {
        if (!periodStart || !periodEnd) { alert("Both period start and end required for payroll input"); setLoading(false); return; }
        setData(await timesheetsApi.payrollInput(periodStart, periodEnd));
      }
    } finally {
      setLoading(false);
    }
  };

  const tabs: { key: ReportTab; label: string }[] = [
    { key: "summary", label: "Summary" },
    { key: "utilization", label: "Utilization" },
    { key: "overtime", label: "Overtime" },
    { key: "project", label: "Project Time" },
    { key: "activity", label: "Activity Mix" },
    { key: "payroll", label: "Payroll Input" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Timesheet Reports</h1>

      <div className="flex gap-2 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); setData(null); }}
            className={`px-4 py-2 text-sm rounded font-medium ${tab === t.key ? "bg-blue-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <div className="flex gap-3 items-end flex-wrap">
          <div>
            <label className="text-xs text-gray-500">Period Start</label>
            <input type="date" className="block border rounded px-2 py-1 text-sm mt-1 w-40"
              value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </div>
          {tab === "payroll" && (
            <div>
              <label className="text-xs text-gray-500">Period End *</label>
              <input type="date" className="block border rounded px-2 py-1 text-sm mt-1 w-40"
                value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
            </div>
          )}
          <button onClick={run} disabled={loading}
            className="rounded bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {loading ? "Loading…" : "Run Report"}
          </button>
        </div>

        {data && tab === "summary" && (() => {
          const d = data as { total_timesheets: number; total_hours: number; overtime_hours: number; regular_hours: number; by_status: Record<string, number> };
          return (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "Total Timesheets", val: d.total_timesheets },
                  { label: "Total Hours", val: d.total_hours.toFixed(1), color: "text-blue-700" },
                  { label: "Overtime Hours", val: d.overtime_hours.toFixed(1), color: "text-orange-700" },
                  { label: "Regular Hours", val: d.regular_hours.toFixed(1), color: "text-green-700" },
                ].map(k => (
                  <div key={k.label} className="bg-gray-50 rounded p-3 text-center">
                    <p className={`text-2xl font-bold ${k.color ?? "text-gray-900"}`}>{k.val}</p>
                    <p className="text-xs text-gray-500">{k.label}</p>
                  </div>
                ))}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">By Status</h3>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  {Object.entries(d.by_status).map(([s, c]) => (
                    <div key={s} className="bg-gray-50 rounded p-2 text-center">
                      <p className="text-lg font-bold text-gray-800">{c}</p>
                      <p className="text-xs text-gray-500 capitalize">{s.replace(/_/g," ")}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}

        {data && (tab === "utilization" || tab === "overtime") && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50"><tr>
              {["Employee","Dept","Timesheets","Total Hrs","OT Hrs"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y">
              {(data as { employee_id: string; employee_name: string | null; department: string | null; timesheet_count: number; total_hours: number; overtime_hours: number }[]).map(r => (
                <tr key={r.employee_id}>
                  <td className="px-3 py-2 font-medium">{r.employee_name ?? r.employee_id}</td>
                  <td className="px-3 py-2 text-gray-600">{r.department ?? "—"}</td>
                  <td className="px-3 py-2 text-center">{r.timesheet_count}</td>
                  <td className="px-3 py-2 text-center font-semibold">{r.total_hours.toFixed(1)}</td>
                  <td className={`px-3 py-2 text-center font-semibold ${r.overtime_hours > 0 ? "text-orange-600" : "text-gray-400"}`}>{r.overtime_hours.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {data && tab === "project" && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50"><tr>
              {["Project","Total Hours","Entries"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y">
              {(data as { project_id: string; project_name: string | null; total_hours: number; entries: number }[]).map(r => (
                <tr key={r.project_id}>
                  <td className="px-3 py-2 font-medium">{r.project_name ?? r.project_id}</td>
                  <td className="px-3 py-2 font-semibold text-blue-700">{r.total_hours.toFixed(1)}h</td>
                  <td className="px-3 py-2 text-gray-600">{r.entries}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {data && tab === "activity" && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(data as { activity_type: string; total_hours: number }[]).map(r => (
              <div key={r.activity_type} className="bg-gray-50 rounded p-3 text-center">
                <p className="text-xl font-bold text-gray-800">{r.total_hours.toFixed(1)}h</p>
                <p className="text-xs text-gray-500 capitalize">{r.activity_type}</p>
              </div>
            ))}
          </div>
        )}

        {data && tab === "payroll" && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50"><tr>
              {["Employee","Period","Regular Hrs","OT Hrs","Total Hrs"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y">
              {(data as { employee_id: string; employee_name: string | null; period_start: string; period_end: string; regular_hours: number; overtime_hours: number; total_hours: number }[]).map(r => (
                <tr key={r.employee_id}>
                  <td className="px-3 py-2 font-medium">{r.employee_name ?? r.employee_id}</td>
                  <td className="px-3 py-2 text-gray-600">{r.period_start} → {r.period_end}</td>
                  <td className="px-3 py-2 text-center">{r.regular_hours.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center text-orange-600 font-semibold">{r.overtime_hours.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center font-bold">{r.total_hours.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
