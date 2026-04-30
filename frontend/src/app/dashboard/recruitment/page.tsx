"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { recruitmentApi, RecruitmentDashboard } from "@/lib/recruitment";

export default function RecruitmentDashboardPage() {
  const [data, setData] = useState<RecruitmentDashboard | null>(null);

  useEffect(() => { recruitmentApi.dashboard().then(setData).catch(console.error); }, []);

  const kpis = data ? [
    { label: "Open Requisitions",      value: data.open_requisitions,     color: "bg-blue-50 text-blue-700" },
    { label: "Total Candidates",        value: data.total_candidates,       color: "bg-indigo-50 text-indigo-700" },
    { label: "Active Pipelines",        value: data.active_pipelines,       color: "bg-purple-50 text-purple-700" },
    { label: "Interviews This Week",    value: data.interviews_this_week,   color: "bg-yellow-50 text-yellow-700" },
    { label: "Pending Offers",          value: data.pending_offers,         color: "bg-orange-50 text-orange-700" },
    { label: "Hires This Month",        value: data.hires_this_month,       color: "bg-green-50 text-green-700" },
    { label: "Avg Time to Hire (days)", value: data.avg_time_to_hire_days,  color: "bg-teal-50 text-teal-700" },
    { label: "AI Alerts",               value: data.ai_alerts,              color: "bg-gray-50 text-gray-700" },
  ] : [];

  const links = [
    { href: "/dashboard/recruitment/requisitions",     label: "Requisitions" },
    { href: "/dashboard/recruitment/requisitions/new", label: "New Requisition" },
    { href: "/dashboard/recruitment/candidates",       label: "Candidates" },
    { href: "/dashboard/recruitment/pipeline",         label: "Pipeline Board" },
    { href: "/dashboard/recruitment/interviews",       label: "Interviews" },
    { href: "/dashboard/recruitment/offers",           label: "Offers" },
    { href: "/dashboard/recruitment/stages",           label: "Pipeline Stages" },
    { href: "/dashboard/recruitment/reports",          label: "Reports" },
    { href: "/dashboard/recruitment/ai",               label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Recruitment / ATS</h1>
        <Link href="/dashboard/recruitment/requisitions/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          + New Requisition
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className={`rounded-xl p-4 ${k.color}`}>
            <p className="text-xs font-medium opacity-70">{k.label}</p>
            <p className="text-2xl font-bold mt-1">{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href}
            className="bg-white border rounded-lg p-3 text-sm font-medium text-center hover:bg-gray-50 shadow-sm">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
