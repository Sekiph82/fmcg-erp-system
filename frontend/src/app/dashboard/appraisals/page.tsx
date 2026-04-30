"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { appraisalsApi, AppraisalDashboard } from "@/lib/appraisals";

export default function AppraisalsDashboard() {
  const [dash, setDash] = useState<AppraisalDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    appraisalsApi.getDashboard().then(setDash).finally(() => setLoading(false));
  }, []);

  const kpis = dash
    ? [
        { label: "Total Appraisals", value: dash.total_records },
        { label: "Self Review Pending", value: dash.self_review_pending, color: "text-yellow-600" },
        { label: "Manager Review Pending", value: dash.manager_review_pending, color: "text-orange-600" },
        { label: "HR Review Pending", value: dash.hr_review_pending, color: "text-purple-600" },
        { label: "Calibration Pending", value: dash.calibration_pending, color: "text-indigo-600" },
        { label: "Completed", value: dash.completed, color: "text-green-600" },
        { label: "Avg Final Score", value: dash.avg_final_score != null ? `${dash.avg_final_score}%` : "—" },
        { label: "Promotion Recs", value: dash.promotion_recommendations, color: "text-blue-600" },
        { label: "Open Dev Plans", value: dash.pending_development_plans, color: "text-rose-600" },
      ]
    : [];

  const ratingColors: Record<string, string> = {
    excellent: "bg-green-500",
    good: "bg-blue-500",
    meets_expectations: "bg-yellow-500",
    improvement_needed: "bg-red-500",
  };

  const links = [
    { href: "/dashboard/appraisals/periods", label: "Appraisal Periods" },
    { href: "/dashboard/appraisals/templates", label: "Templates" },
    { href: "/dashboard/appraisals/records", label: "All Records" },
    { href: "/dashboard/appraisals/records/new", label: "New Appraisal" },
    { href: "/dashboard/appraisals/self-review", label: "Self Review" },
    { href: "/dashboard/appraisals/manager-queue", label: "Manager Queue" },
    { href: "/dashboard/appraisals/hr-review", label: "HR Review" },
    { href: "/dashboard/appraisals/development-plans", label: "Development Plans" },
    { href: "/dashboard/appraisals/reports", label: "Reports" },
    { href: "/dashboard/appraisals/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Performance Appraisals</h1>

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

          {dash && Object.keys(dash.rating_distribution).length > 0 && (
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Rating Distribution</h2>
              <div className="flex gap-3 flex-wrap">
                {Object.entries(dash.rating_distribution).map(([rating, count]) => (
                  <div key={rating} className="flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full ${ratingColors[rating] ?? "bg-gray-400"}`} />
                    <span className="text-sm text-gray-700 capitalize">{rating.replace(/_/g, " ")}</span>
                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {dash && dash.department_avg_scores.length > 0 && (
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Department Average Scores</h2>
              <div className="space-y-2">
                {dash.department_avg_scores.map((d) => (
                  <div key={d.department} className="flex items-center gap-3">
                    <span className="w-32 text-sm text-gray-700 truncate">{d.department}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-3">
                      <div
                        className="bg-blue-500 h-3 rounded-full"
                        style={{ width: `${Math.min(d.avg_score, 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-700 w-12 text-right">{d.avg_score}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
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
