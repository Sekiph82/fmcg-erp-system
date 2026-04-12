"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hrApi, AttendanceStatus } from "@/lib/hr";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";

const STATUS_VARIANT: Record<AttendanceStatus, "green" | "red" | "yellow" | "blue" | "gray"> = {
  PRESENT: "green",
  ABSENT: "red",
  LATE: "yellow",
  LEAVE: "blue",
  HALF_DAY: "gray",
};

function AttendanceContent() {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [dept, setDept] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Quick-record form state
  const [showForm, setShowForm] = useState(false);
  const [recForm, setRecForm] = useState({ employee_id: "", attendance_date: today, status: "PRESENT", notes: "" });

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["hr-attendance", dateFrom, dateTo, dept, statusFilter],
    queryFn: () => hrApi.listAttendance({
      date_from: dateFrom,
      date_to: dateTo,
      department: dept || undefined,
      status: statusFilter || undefined,
    }),
  });

  const { data: employees = [] } = useQuery({ queryKey: ["hr-employees"], queryFn: () => hrApi.listEmployees() });

  const recordMutation = useMutation({
    mutationFn: hrApi.recordAttendance,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-attendance"] }); setShowForm(false); },
  });

  const departments = Array.from(new Set(employees.map((e) => e.department))).sort();

  const summary = {
    PRESENT: records.filter((r) => r.status === "PRESENT").length,
    ABSENT: records.filter((r) => r.status === "ABSENT").length,
    LATE: records.filter((r) => r.status === "LATE").length,
    LEAVE: records.filter((r) => r.status === "LEAVE").length,
    HALF_DAY: records.filter((r) => r.status === "HALF_DAY").length,
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Attendance</h1>
          <p className="text-sm text-gray-500 mt-1">{records.length} records for period</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">
          + Record
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-5 gap-3">
        {(Object.entries(summary) as [AttendanceStatus, number][]).map(([status, count]) => (
          <div key={status} className="bg-white border rounded-lg px-4 py-3 text-center">
            <p className="text-xs text-gray-500">{status}</p>
            <p className="text-xl font-bold mt-1">{count}</p>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-sm text-gray-800">Record Attendance</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">Employee</label>
              <select
                className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={recForm.employee_id}
                onChange={(e) => setRecForm((f) => ({ ...f, employee_id: e.target.value }))}
              >
                <option value="">— select —</option>
                {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.department})</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Date</label>
              <input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={recForm.attendance_date}
                onChange={(e) => setRecForm((f) => ({ ...f, attendance_date: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Status</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={recForm.status}
                onChange={(e) => setRecForm((f) => ({ ...f, status: e.target.value }))}>
                {["PRESENT", "ABSENT", "LATE", "LEAVE", "HALF_DAY"].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={recForm.notes}
                onChange={(e) => setRecForm((f) => ({ ...f, notes: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => recordMutation.mutate(recForm)}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm"
              disabled={!recForm.employee_id}
            >Save</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded px-2 py-1.5 text-sm" />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded px-2 py-1.5 text-sm" />
        </div>
        <select value={dept} onChange={(e) => setDept(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">All Departments</option>
          {departments.map((d) => <option key={d}>{d}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">All Statuses</option>
          {["PRESENT", "ABSENT", "LATE", "LEAVE", "HALF_DAY"].map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400 text-center">Loading...</p>
        ) : records.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No attendance records for this period</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Date</th>
                <th className="px-4 py-2 text-left">Employee</th>
                <th className="px-4 py-2 text-left">Dept</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Clock In</th>
                <th className="px-4 py-2 text-left">Clock Out</th>
                <th className="px-4 py-2 text-left">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {records.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-700">{r.attendance_date}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{r.employee?.full_name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{r.employee?.department ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Badge label={r.status} variant={STATUS_VARIANT[r.status]} />
                  </td>
                  <td className="px-4 py-3 text-gray-500">{r.clock_in ?? <span className="text-gray-300">—</span>}</td>
                  <td className="px-4 py-3 text-gray-500">{r.clock_out ?? <span className="text-gray-300">—</span>}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.notes ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function AttendancePage() {
  return (
    <RequirePermission permission="hr.view">
      <AttendanceContent />
    </RequirePermission>
  );
}
