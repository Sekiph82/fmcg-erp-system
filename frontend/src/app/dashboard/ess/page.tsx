"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { essApi, ESSDashboard } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function ESSDashboardPage() {
  const [data, setData] = useState<ESSDashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { essApi.getDashboard(DEMO_EMPLOYEE).then(setData).catch((e) => setError(e.message)); }, []);

  const links = [
    { href: "/dashboard/ess/profile",       label: "My Profile",    icon: "👤" },
    { href: "/dashboard/ess/leave",         label: "Leave",         icon: "🏖️" },
    { href: "/dashboard/ess/attendance",    label: "Attendance",    icon: "📅" },
    { href: "/dashboard/ess/documents",     label: "Documents",     icon: "📄" },
    { href: "/dashboard/ess/requests",      label: "My Requests",   icon: "📋" },
    { href: "/dashboard/ess/notifications", label: "Notifications", icon: "🔔" },
    { href: "/dashboard/ess/ai",            label: "AI Insights",   icon: "🤖" },
    { href: "/dashboard/ess/admin",         label: "HR Admin",      icon: "⚙️" },
  ];

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Employee Self-Service</h1>
          {data && <p className="text-slate-500 text-sm mt-0.5">{data.employee_name} · {data.job_title} · {data.department_name}</p>}
        </div>
        {data && <p className="text-xs text-slate-600">{data.days_since_joining} days with the company</p>}
      </div>

      {error && <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">{error} — set up your ESS account first via HR Admin.</div>}

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: "Annual Leave Available", value: `${data.annual_leave_available} days`, color: "text-emerald-400" },
            { label: "Pending Leave Requests", value: data.pending_leave_requests, color: "text-amber-400" },
            { label: "Attendance This Month", value: `${data.attendance_this_month} days`, color: "text-blue-400" },
            { label: "Pending Requests", value: data.pending_requests, color: "text-orange-400" },
            { label: "Unread Notifications", value: data.unread_notifications, color: "text-purple-400" },
          ].map((k) => (
            <div key={k.label} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
              <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href}
            className="rounded-xl border border-white/[0.07] bg-[#0d1829] hover:bg-white/[0.04] p-4 flex items-center gap-3 transition-colors">
            <span className="text-xl">{l.icon}</span>
            <span className="text-sm font-medium text-slate-300">{l.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
