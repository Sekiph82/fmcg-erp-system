"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { timesheetsApi, TimesheetDashboard } from "@/lib/timesheets";

export default function TimesheetsDashboard() {
  const [dash, setDash] = useState<TimesheetDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    timesheetsApi.getDashboard().then(setDash).finally(() => setLoading(false));
  }, []);

  const kpis = dash
    ? [
        { label: "Total Timesheets", value: dash.total_timesheets },
        { label: "Pending Approval", value: dash.pending_approval, color: "text-blue-600" },
        { label: "Manager Approved", value: dash.manager_approved, color: "text-purple-600" },
        { label: "Rejected", value: dash.rejected, color: "text-red-600" },
        { label: "Finalized", value: dash.finalized, color: "text-green-600" },
        { label: "Employees", value: dash.employees_with_timesheets },
        { label: "Total Hours", value: dash.total_hours_this_period.toFixed(1) },
        { label: "Overtime Hours", value: dash.overtime_hours_this_period.toFixed(1), color: "text-orange-600" },
        { label: "Avg Hours/Employee", value: dash.avg_hours_per_employee.toFixed(1) },
      ]
    : [];

  const links = [
    { href: "/dashboard/timesheets/my-timesheets", label: "My Timesheets" },
    { href: "/dashboard/timesheets/time-entry", label: "New Time Entry" },
    { href: "/dashboard/timesheets/weekly-view", label: "Weekly View" },
    { href: "/dashboard/timesheets/approval-queue", label: "Approval Queue" },
    { href: "/dashboard/timesheets/reports", label: "Reports" },
    { href: "/dashboard/timesheets/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Timesheet Management</h1>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 lg:grid-cols-5">
            {kpis.map((k) => (
              <div key={k.label} className="bg-white rounded-lg border p-4 shadow-sm">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-900"}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {dash && dash.project_hours.length > 0 && (
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Top Projects by Hours</h2>
              <div className="space-y-2">
                {dash.project_hours.map((p) => {
                  const max = Math.max(...dash.project_hours.map(x => x.hours));
                  return (
                    <div key={p.project} className="flex items-center gap-3">
                      <span className="text-sm text-gray-700 w-40 truncate">{p.project}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-3">
                        <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${(p.hours / max) * 100}%` }} />
                      </div>
                      <span className="text-sm font-semibold text-gray-700 w-16 text-right">{p.hours.toFixed(1)}h</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {links.map((l) => (
            <Link key={l.href} href={l.href}
              className="block rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 text-center">
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
