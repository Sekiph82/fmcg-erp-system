"use client";
import { useCallback, useEffect, useState } from "react";
import { surveysApi, Survey, SurveyDashboard, SurveyStatus, SURVEY_TYPE_LABEL } from "@/lib/surveys";

const STATUS_COLORS: Record<SurveyStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  ACTIVE: "bg-green-100 text-green-700",
  CLOSED: "bg-blue-100 text-blue-700",
  ARCHIVED: "bg-gray-100 text-gray-400",
};

export default function SurveysDashboard() {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [dashboard, setDashboard] = useState<SurveyDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<SurveyStatus | "">("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, d] = await Promise.all([
        surveysApi.listSurveys(filterStatus ? { status: filterStatus as SurveyStatus } : undefined),
        surveysApi.getDashboard(),
      ]);
      setSurveys(s);
      setDashboard(d);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  const launch = async (id: string) => {
    await surveysApi.launchSurvey(id);
    await load();
  };

  const close = async (id: string) => {
    if (!confirm("Close this survey?")) return;
    await surveysApi.closeSurvey(id);
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Employee Surveys</h1>
          <p className="text-xs text-gray-500 mt-0.5">Pulse surveys, engagement tracking, exit interviews.</p>
        </div>
        <a href="/dashboard/surveys/new"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Survey
        </a>
      </div>

      {dashboard && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total Surveys", value: dashboard.total_surveys, color: "text-gray-700" },
            { label: "Active", value: dashboard.active_surveys, color: "text-green-600" },
            { label: "Closed", value: dashboard.closed_surveys, color: "text-blue-600" },
            { label: "Total Responses", value: dashboard.total_responses, color: "text-purple-600" },
          ].map(s => (
            <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {dashboard?.active_surveys_list && dashboard.active_surveys_list.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-xs font-semibold text-green-700 mb-2">Active Surveys — Awaiting Responses</p>
          <div className="flex gap-2 flex-wrap">
            {dashboard.active_surveys_list.map(s => (
              <a key={s.id} href={`/dashboard/surveys/${s.id}/respond`}
                className="flex items-center gap-2 bg-white border border-green-200 rounded-lg px-3 py-2 hover:bg-green-100 transition-colors">
                <span className="text-xs font-medium text-gray-800">{s.title}</span>
                <span className="text-xs text-gray-400">{s.response_count} responses</span>
                {s.end_date && <span className="text-xs text-red-500">ends {s.end_date}</span>}
              </a>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {(["", "DRAFT", "ACTIVE", "CLOSED"] as const).map(s => (
          <button key={s}
            onClick={() => setFilterStatus(s as SurveyStatus | "")}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}>
            {s || "All"}
          </button>
        ))}
        <span className="text-xs text-gray-500 self-center">{surveys.length} surveys</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : surveys.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📊</p>
          <p className="text-sm">No surveys found.</p>
          <a href="/dashboard/surveys/new" className="text-xs text-blue-600 hover:underline mt-2 block">
            Create first survey →
          </a>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Title", "Type", "Questions", "Responses", "Dates", "Anon", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {surveys.map(s => (
                <tr key={s.id} className={`hover:bg-gray-50 ${s.status === "ARCHIVED" ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3 font-medium text-gray-800">
                    <a href={`/dashboard/surveys/${s.id}`} className="hover:text-blue-600">{s.title}</a>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-purple-50 text-purple-600 rounded px-1.5 py-0.5">
                      {SURVEY_TYPE_LABEL[s.survey_type]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{s.question_count}</td>
                  <td className="px-4 py-3 text-xs font-semibold text-blue-600">{s.response_count}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {s.start_date ?? "—"} → {s.end_date ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{s.anonymous_flag ? "Yes" : "No"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[s.status]}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 flex-wrap">
                      <a href={`/dashboard/surveys/${s.id}`} className="text-xs text-blue-600 hover:underline">View</a>
                      {s.status === "ACTIVE" && (
                        <>
                          <a href={`/dashboard/surveys/${s.id}/respond`} className="text-xs text-green-600 hover:underline">Respond</a>
                          <a href={`/dashboard/surveys/${s.id}/results`} className="text-xs text-purple-600 hover:underline">Results</a>
                          <button onClick={() => close(s.id)} className="text-xs text-red-500 hover:underline">Close</button>
                        </>
                      )}
                      {s.status === "DRAFT" && (
                        <button onClick={() => launch(s.id)} className="text-xs text-green-600 hover:underline">Launch</button>
                      )}
                      {s.status === "CLOSED" && (
                        <a href={`/dashboard/surveys/${s.id}/results`} className="text-xs text-purple-600 hover:underline">Results</a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
