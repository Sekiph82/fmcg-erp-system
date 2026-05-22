"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, Survey, SurveyType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SURVEY_TYPES: SurveyType[] = [
  "CUSTOMER_FEEDBACK", "MARKET_AUDIT", "RETAILER_FEEDBACK",
  "BRAND_AWARENESS", "COMPETITOR_CHECK", "PRODUCT_FEEDBACK", "SHELF_AUDIT",
];

export default function SurveysPage() {
  const [typeFilter, setTypeFilter] = useState("");

  const { data: surveys = [], isLoading } = useQuery({
    queryKey: ["surveys", typeFilter],
    queryFn: () =>
      marketingApi.surveys
        .list({ survey_type: typeFilter || undefined, limit: 100 })
        .then((r) => r.data),
  });

  return (
    <RequirePermission permission="surveys.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Market Surveys</h1>
            <p className="text-slate-400 text-sm mt-1">{surveys.length} surveys</p>
          </div>
          <RequirePermission permission="surveys.create">
            <Link href="/dashboard/marketing/surveys/new"
              className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-sm font-medium text-white">
              + New Survey
            </Link>
          </RequirePermission>
        </div>

        <div className="flex gap-3 mb-6">
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All types</option>
            {SURVEY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : surveys.length === 0 ? (
          <p className="text-slate-400 text-center py-16">No surveys found.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {surveys.map((s: Survey) => (
              <div key={s.id} className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
                <div className="flex items-start justify-between mb-2">
                  <p className="font-semibold text-white">{s.survey_name}</p>
                  <span className="px-2 py-0.5 rounded bg-blue-600/20 text-blue-300 text-xs font-medium ml-2 shrink-0">
                    {s.survey_type.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="flex gap-4 text-sm mt-3">
                  <div>
                    <p className="text-xs text-slate-500">Date</p>
                    <p className="text-slate-300">{s.survey_date}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Respondents</p>
                    <p className="text-slate-300 font-medium">{s.response_count}</p>
                  </div>
                  {s.region && (
                    <div>
                      <p className="text-xs text-slate-500">Region</p>
                      <p className="text-slate-300">{s.region}</p>
                    </div>
                  )}
                </div>
                {s.summary && <p className="text-xs text-slate-400 mt-3 line-clamp-2">{s.summary}</p>}
                {s.sentiment_score && (
                  <p className="text-xs text-slate-500 mt-1">Sentiment: {Number(s.sentiment_score).toFixed(1)}</p>
                )}
                <div className="mt-3 pt-3 border-t border-slate-700/50">
                  <Link href={`/dashboard/marketing/surveys/${s.id}`}
                    className="text-xs text-teal-400 hover:text-teal-300">
                    View details →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
