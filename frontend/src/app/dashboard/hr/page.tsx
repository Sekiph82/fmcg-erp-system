"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { hrApi } from "@/lib/hr";
import { RequirePermission } from "@/components/PermissionGuard";

function HRContent() {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);

  const { data: employees = [] } = useQuery({
    queryKey: ["hr-employees"],
    queryFn: () => hrApi.listEmployees(),
  });

  const { data: attendance = [] } = useQuery({
    queryKey: ["hr-attendance-today", today],
    queryFn: () => hrApi.listAttendance({ date_from: today, date_to: today }),
  });

  const { data: leaveRequests = [] } = useQuery({
    queryKey: ["hr-leave-pending"],
    queryFn: () => hrApi.listLeaveRequests({ approval_status: "PENDING" }),
  });

  const { data: payrollPeriods = [] } = useQuery({
    queryKey: ["hr-payroll-periods"],
    queryFn: () => hrApi.listPayrollPeriods(),
  });

  const activeEmployees = employees.filter((e) => e.status === "ACTIVE").length;
  const presentToday = attendance.filter((a) => a.status === "PRESENT").length;
  const absentToday = attendance.filter((a) => a.status === "ABSENT").length;
  const lateToday = attendance.filter((a) => a.status === "LATE").length;
  const pendingLeave = leaveRequests.length;
  const draftPayrolls = payrollPeriods.filter((p) => p.status === "DRAFT").length;

  const tiles = [
    {
      label: "Active Employees",
      value: activeEmployees.toString(),
      sub: `${employees.length} total`,
      color: "text-indigo-700",
      href: "/dashboard/hr/employees",
    },
    {
      label: "Present Today",
      value: presentToday.toString(),
      sub: `${absentToday} absent · ${lateToday} late`,
      color: presentToday > 0 ? "text-green-700" : "text-gray-500",
      href: "/dashboard/hr/attendance",
    },
    {
      label: "Pending Leave",
      value: pendingLeave.toString(),
      sub: "awaiting approval",
      color: pendingLeave > 0 ? "text-orange-600" : "text-gray-500",
      href: "/dashboard/hr/leave",
    },
    {
      label: "Draft Payrolls",
      value: draftPayrolls.toString(),
      sub: `${payrollPeriods.length} total periods`,
      color: draftPayrolls > 0 ? "text-yellow-600" : "text-gray-500",
      href: "/dashboard/hr/payroll",
    },
  ];

  const sections = [
    { label: "Employees", desc: "Employee master records, roles, departments", href: "/dashboard/hr/employees" },
    { label: "Shift Planning", desc: "Shift templates and employee assignments", href: "/dashboard/hr/shifts" },
    { label: "Attendance", desc: "Daily attendance records — present, absent, late, leave", href: "/dashboard/hr/attendance" },
    { label: "Leave Management", desc: "Leave requests and approval workflow", href: "/dashboard/hr/leave" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Human Resources</h1>
        <p className="text-sm text-gray-500 mt-1">Employees · Shifts · Attendance · Leave · Payroll</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {tiles.map((tile) => (
          <button
            key={tile.label}
            onClick={() => router.push(tile.href)}
            className="bg-white rounded-lg border p-5 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{tile.label}</p>
            <p className={`text-2xl font-bold mt-1 ${tile.color}`}>{tile.value}</p>
            <p className="text-xs text-gray-400 mt-1">{tile.sub}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {sections.map((s) => (
          <button
            key={s.href}
            onClick={() => router.push(s.href)}
            className="bg-white rounded-lg border p-5 text-left hover:border-indigo-300 transition-colors"
          >
            <p className="font-semibold text-gray-800">{s.label}</p>
            <p className="text-sm text-gray-500 mt-1">{s.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function HRPage() {
  return (
    <RequirePermission permission="hr.view">
      <HRContent />
    </RequirePermission>
  );
}
