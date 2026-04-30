"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { recruitmentApi, RecruitmentDashboard } from "@/lib/recruitment";

export default function RecruitmentDashboardPage() {
  const [data, setData] = useState<RecruitmentDashboard | null>(null);
  useEffect(() => { recruitmentApi.dashboard().then(setData).catch(console.error); }, []);

  const kpis = data ? [
    { label: "Open Requisitions",       value: data.open_requisitions,         color: "text-blue-400" },
    { label: "Total Candidates",         value: data.total_candidates,          color: "text-white" },
    { label: "Active Pipelines",         value: data.active_pipelines,          color: "text-purple-400" },
    { label: "Interviews This Week",     value: data.interviews_this_week,      color: "text-amber-400" },
    { label: "Pending Offers",           value: data.pending_offers,            color: "text-orange-400" },
    { label: "Hires This Month",         value: data.hires_this_month,          color: "text-emerald-400" },
    { label: "Avg Time to Hire (days)",  value: data.avg_time_to_hire_days,     color: "text-teal-400" },
    { label: "AI Alerts",                value: data.ai_alerts,                 color: "text-slate-400" },
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
    <div className="p-6 space-y-6 min-h-screen bg-[#060d18] text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Recruitment / ATS</h1>
          <p className="text-slate-500 text-sm mt-0.5">End-to-end hiring pipeline management</p>
        </div>
        <Link href="/dashboard/recruitment/requisitions/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">+ New Requisition</Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href}
            className="rounded-xl border border-white/[0.07] bg-[#0d1829] hover:bg-white/[0.04] p-4 text-sm font-medium text-slate-300 text-center transition-colors">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
