"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { trainingApi, TrainingDashboard } from "@/lib/training";
import { tx } from "@/lib/i18n/core";

export default function TrainingDashboardPage() {
  const [dash, setDash] = useState<TrainingDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trainingApi.getDashboard().then(setDash).finally(() => setLoading(false));
  }, []);

  const kpis = dash
    ? [
        { label: tx("Total Programs"), value: dash.total_programs },
        { label: tx("Active Programs"), value: dash.active_programs, color: "text-green-600" },
        { label: tx("Upcoming Sessions"), value: dash.upcoming_sessions, color: "text-blue-600" },
        { label: tx("Total Assignments"), value: dash.total_assignments },
        { label: tx("Completed"), value: dash.completed_assignments, color: "text-green-600" },
        { label: tx("Overdue"), value: dash.overdue_assignments, color: "text-red-600" },
        { label: tx("Certifications"), value: dash.total_certifications },
        { label: tx("Expiring Soon"), value: dash.expiring_soon, color: "text-yellow-600" },
        { label: tx("Expired"), value: dash.expired_certifications, color: "text-red-600" },
        { label: tx("Skill Profiles"), value: dash.total_skill_profiles },
        { label: tx("Skill Gaps"), value: dash.skill_gaps, color: "text-orange-600" },
        { label: tx("Avg Feedback"), value: dash.avg_feedback_rating != null ? `${dash.avg_feedback_rating}/5` : "—" },
      ]
    : [];

  const links = [
    { href: "/dashboard/training/programs", label: tx("Training Programs") },
    { href: "/dashboard/training/sessions", label: tx("Sessions / Calendar") },
    { href: "/dashboard/training/skill-matrix", label: tx("Skill Matrix") },
    { href: "/dashboard/training/assignments", label: tx("Assignments") },
    { href: "/dashboard/training/certifications", label: tx("Certifications") },
    { href: "/dashboard/training/feedback", label: tx("Feedback") },
    { href: "/dashboard/training/reports", label: tx("Reports") },
    { href: "/dashboard/training/ai", label: tx("AI Insights") },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{tx("Training & Skills Management")}</h1>

      {loading ? (
        <p className="text-gray-500">{tx("Loading…")}</p>
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
        <h2 className="text-sm font-semibold text-gray-700 mb-3">{tx("Quick Navigation")}</h2>
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
