"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
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

const HREmployeesPage    = dynamic(() => import("@/app/dashboard/hr/employees/page"),   { ssr: false });
const HRAttendancePage   = dynamic(() => import("@/app/dashboard/hr/attendance/page"),  { ssr: false });
const HRLeavePage        = dynamic(() => import("@/app/dashboard/hr/leave/page"),       { ssr: false });
const HRPayrollPage      = dynamic(() => import("@/app/dashboard/hr/payroll/page"),     { ssr: false });
const HRShiftsPage       = dynamic(() => import("@/app/dashboard/hr/shifts/page"),      { ssr: false });
const RecruitmentPage    = dynamic(() => import("@/app/dashboard/recruitment/page"),    { ssr: false });
const ESSPage            = dynamic(() => import("@/app/dashboard/ess/page"),            { ssr: false });
const AppraisalsPage     = dynamic(() => import("@/app/dashboard/appraisals/page"),     { ssr: false });
const TrainingPage       = dynamic(() => import("@/app/dashboard/training/page"),       { ssr: false });
const TimesheetsPage     = dynamic(() => import("@/app/dashboard/timesheets/page"),     { ssr: false });
const HRExpensesPage     = dynamic(() => import("@/app/dashboard/expenses/page"),       { ssr: false });

export default function HRPage() {
  const tabs = [
    { key: "overview",     label: "Overview",     permission: "hr.view", content: <HRContent /> },
    { key: "employees",    label: "Employees",    permission: "hr.view", content: <HREmployeesPage /> },
    { key: "attendance",   label: "Attendance",   permission: "hr.view", content: <HRAttendancePage /> },
    { key: "leave",        label: "Leave",        permission: "hr.view", content: <HRLeavePage /> },
    { key: "payroll",      label: "Payroll",      permission: "payroll.view", content: <HRPayrollPage /> },
    { key: "shifts",       label: "Shifts",       permission: "hr.view", content: <HRShiftsPage /> },
    { key: "recruitment",  label: "Recruitment",  permission: "hr.view", content: <RecruitmentPage /> },
    { key: "ess",          label: "ESS",          permission: "hr.view", content: <ESSPage /> },
    { key: "appraisals",   label: "Appraisals",   permission: "hr.view", content: <AppraisalsPage /> },
    { key: "training",     label: "Training",     permission: "hr.view", content: <TrainingPage /> },
    { key: "timesheets",   label: "Timesheets",   permission: "hr.view", content: <TimesheetsPage /> },
    { key: "expenses",     label: "Expenses",     permission: "hr.view", content: <HRExpensesPage /> },
  ];
  return (
    <ModuleWorkspace
      title="HR & Payroll"
      description="Employees, attendance, leave, payroll, recruitment, training"
      permission="hr.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
