"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { essApi, ESSDashboard } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function ESSDashboardPage() {
  const [data, setData] = useState<ESSDashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    essApi.getDashboard(DEMO_EMPLOYEE).then(setData).catch((e) => setError(e.message));
  }, []);

  const links = [
    { href: "/dashboard/ess/profile",       label: "My Profile",       icon: "👤" },
    { href: "/dashboard/ess/leave",         label: "Leave",            icon: "🏖️" },
    { href: "/dashboard/ess/attendance",    label: "Attendance",       icon: "📅" },
    { href: "/dashboard/ess/documents",     label: "Documents",        icon: "📄" },
    { href: "/dashboard/ess/requests",      label: "My Requests",      icon: "📋" },
    { href: "/dashboard/ess/notifications", label: "Notifications",    icon: "🔔" },
    { href: "/dashboard/ess/ai",            label: "AI Insights",      icon: "🤖" },
    { href: "/dashboard/ess/admin",         label: "HR Admin",         icon: "⚙️" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Employee Self-Service</h1>
          {data && <p className="text-sm text-gray-500 mt-0.5">{data.employee_name} · {data.job_title} · {data.department_name}</p>}
        </div>
        {data && <p className="text-xs text-gray-400">{data.days_since_joining} days with the company</p>}
      </div>

      {error && <div className="bg-yellow-50 text-yellow-700 text-sm px-4 py-2 rounded">{error} — set up your ESS account first via HR Admin.</div>}

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: "Annual Leave Available", value: `${data.annual_leave_available} days`, color: "bg-green-50 text-green-700" },
            { label: "Pending Leave Requests", value: data.pending_leave_requests, color: "bg-yellow-50 text-yellow-700" },
            { label: "Attendance This Month", value: `${data.attendance_this_month} days`, color: "bg-blue-50 text-blue-700" },
            { label: "Pending Requests", value: data.pending_requests, color: "bg-orange-50 text-orange-700" },
            { label: "Unread Notifications", value: data.unread_notifications, color: "bg-purple-50 text-purple-700" },
          ].map((k) => (
            <div key={k.label} className={`rounded-xl p-4 ${k.color}`}>
              <p className="text-xs font-medium opacity-70">{k.label}</p>
              <p className="text-2xl font-bold mt-1">{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href}
            className="bg-white border rounded-xl p-4 text-sm font-medium hover:bg-gray-50 shadow-sm flex items-center gap-3">
            <span className="text-xl">{l.icon}</span>
            <span>{l.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
