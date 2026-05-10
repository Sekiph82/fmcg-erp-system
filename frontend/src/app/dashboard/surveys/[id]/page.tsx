"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { surveysApi, SurveyDetail, SURVEY_TYPE_LABEL, QUESTION_TYPE_LABEL } from "@/lib/surveys";

export default function SurveyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [survey, setSurvey] = useState<SurveyDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setSurvey(await surveysApi.getSurvey(id)); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const launch = async () => {
    await surveysApi.launchSurvey(id);
    await load();
  };
  const close = async () => {
    if (!confirm("Close survey?")) return;
    await surveysApi.closeSurvey(id);
    await load();
  };

  if (loading) return <div className="p-6 text-sm text-gray-500">Loading…</div>;
  if (!survey) return <div className="p-6 text-sm text-red-500">Survey not found.</div>;

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs bg-purple-50 text-purple-600 rounded px-2 py-0.5">
              {SURVEY_TYPE_LABEL[survey.survey_type]}
            </span>
            <span className={`text-xs rounded-full px-2 py-0.5 ${
              survey.status === "ACTIVE" ? "bg-green-100 text-green-700" :
              survey.status === "DRAFT" ? "bg-gray-100 text-gray-600" :
              survey.status === "CLOSED" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"
            }`}>{survey.status}</span>
            {survey.anonymous_flag && (
              <span className="text-xs bg-amber-50 text-amber-700 rounded px-2 py-0.5">Anonymous</span>
            )}
          </div>
          <h1 className="text-xl font-bold text-gray-900">{survey.title}</h1>
          {survey.description && <p className="text-sm text-gray-500 mt-1">{survey.description}</p>}
          <div className="flex gap-3 text-xs text-gray-400 mt-2">
            <span>{survey.questions.length} questions</span>
            <span>{survey.response_count} responses</span>
            {survey.start_date && <span>{survey.start_date} → {survey.end_date ?? "open"}</span>}
            {survey.created_by_name && <span>by {survey.created_by_name}</span>}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0 flex-wrap">
          {survey.status === "DRAFT" && (
            <button onClick={launch}
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700">
              Launch Survey
            </button>
          )}
          {survey.status === "ACTIVE" && (
            <>
              <a href={`/dashboard/surveys/${id}/respond`}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                Respond
              </a>
              <a href={`/dashboard/surveys/${id}/results`}
                className="rounded border px-4 py-2 text-sm text-purple-600 hover:bg-purple-50 border-purple-200">
                Results
              </a>
              <button onClick={close}
                className="rounded border px-4 py-2 text-sm text-red-500 hover:bg-red-50 border-red-200">
                Close
              </button>
            </>
          )}
          {survey.status === "CLOSED" && (
            <a href={`/dashboard/surveys/${id}/results`}
              className="rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
              View Results
            </a>
          )}
        </div>
      </div>

      <div className="bg-white border rounded-lg p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-800">Questions ({survey.questions.length})</h2>
        {survey.questions.map((q, i) => (
          <div key={q.id} className="border rounded-lg p-4 bg-gray-50">
            <div className="flex items-start gap-3">
              <span className="text-sm font-bold text-gray-400 w-6 flex-shrink-0">{i + 1}.</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">
                  {q.question_text}
                  {q.required_flag && <span className="text-red-400 ml-1">*</span>}
                </p>
                <div className="flex gap-2 mt-1">
                  <span className="text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">
                    {QUESTION_TYPE_LABEL[q.question_type]}
                  </span>
                  {q.category && <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">{q.category}</span>}
                  {["RATING", "LIKERT"].includes(q.question_type) && (
                    <span className="text-xs text-gray-400">{q.scale_min}–{q.scale_max}</span>
                  )}
                  {q.question_type === "MULTIPLE_CHOICE" && q.options && (
                    <span className="text-xs text-gray-400">{q.options.length} options</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <a href="/dashboard/surveys" className="text-xs text-blue-600 hover:underline">← All Surveys</a>
    </div>
  );
}
