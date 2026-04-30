"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { trainingApi, TrainingDashboard } from "@/lib/training";

export default function TrainingDashboardPage() {
  const [dash, setDash] = useState<TrainingDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trainingApi.getDashboard().then(setDash).finally(() => setLoading(false));
  }, []);

  const kpis = dash
    ? [
        { label: "Total Programs", value: dash.total_programs },
        { label: "Active Programs", value: dash.active_programs, color: "text-green-600" },
        { label: "Upcoming Sessions", value: dash.upcoming_sessions, color: "text-blue-600" },
        { label: "Total Assignments", value: dash.total_assignments },
        { label: "Completed", value: dash.completed_assignments, color: "text-green-600" },
        { label: "Overdue", value: dash.overdue_assignments, color: "text-red-600" },
        { label: "Certifications", value: dash.total_certifications },
        { label: "Expiring Soon", value: dash.expiring_soon, color: "text-yellow-600" },
        { label: "Expired", value: dash.expired_certifications, color: "text-red-600" },
        { label: "Skill Profiles", value: dash.total_skill_profiles },
        { label: "Skill Gaps", value: dash.skill_gaps, color: "text-orange-600" },
        { label: "Avg Feedback", value: dash.avg_feedback_rating != null ? `${dash.avg_feedback_rating}/5` : "—" },
      ]
    : [];

  const links = [
    { href: "/dashboard/training/programs", label: "Training Programs" },
    { href: "/dashboard/training/sessions", label: "Sessions / Calendar" },
    { href: "/dashboard/training/skill-matrix", label: "Skill Matrix" },
    { href: "/dashboard/training/assignments", label: "Assignments" },
    { href: "/dashboard/training/certifications", label: "Certifications" },
    { href: "/dashboard/training/feedback", label: "Feedback" },
    { href: "/dashboard/training/reports", label: "Reports" },
    { href: "/dashboard/training/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Training & Skills Management</h1>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <div className="grid grid-cols-3 gap-4 lg:grid-cols-6">
          {kpis.map((k) => (
            <div key={k.label} className="bg-white rounded-lg border p-4 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-900"}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="block rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 text-center"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
