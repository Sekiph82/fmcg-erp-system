"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { surveysApi, SurveyDetail, SurveyQuestion } from "@/lib/surveys";

export default function RespondPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [survey, setSurvey] = useState<SurveyDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | number>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    surveysApi.getSurvey(id).then(s => { setSurvey(s); setLoading(false); });
  }, [id]);

  const setAnswer = (qid: string, val: string | number) =>
    setAnswers(a => ({ ...a, [qid]: val }));

  const submit = async () => {
    if (!survey) return;
    const missing = survey.questions.filter(q => q.required_flag && !answers[q.id]);
    if (missing.length) { setError(`${missing.length} required question(s) unanswered`); return; }
    setSubmitting(true); setError("");
    try {
      await surveysApi.submitResponse(id, answers);
      setDone(true);
    } catch {
      setError("Failed to submit. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-6 text-sm text-gray-500">Loading survey…</div>;
  if (!survey) return <div className="p-6 text-sm text-red-500">Survey not found.</div>;

  if (done) return (
    <div className="p-6 max-w-lg mx-auto text-center space-y-4 mt-12">
      <div className="text-5xl">🎉</div>
      <h1 className="text-xl font-bold text-gray-900">Thank you!</h1>
      <p className="text-sm text-gray-500">Your response has been submitted{survey.anonymous_flag ? " anonymously" : ""}.</p>
      <a href="/dashboard/surveys" className="text-sm text-blue-600 hover:underline">Back to Surveys</a>
    </div>
  );

  const renderInput = (q: SurveyQuestion) => {
    const val = answers[q.id];
    switch (q.question_type) {
      case "RATING":
      case "LIKERT": {
        const min = q.scale_min ?? 1;
        const max = q.scale_max ?? 5;
        const steps = Array.from({ length: max - min + 1 }, (_, i) => min + i);
        return (
          <div className="flex gap-2 flex-wrap mt-2">
            {steps.map(n => (
              <button key={n} onClick={() => setAnswer(q.id, n)}
                className={`w-10 h-10 rounded-full border text-sm font-semibold transition-colors ${
                  val === n
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                }`}>
                {n}
              </button>
            ))}
            <div className="w-full flex justify-between text-xs text-gray-400 mt-0.5 px-1">
              <span>{q.question_type === "LIKERT" ? "Strongly Disagree" : "Low"}</span>
              <span>{q.question_type === "LIKERT" ? "Strongly Agree" : "High"}</span>
            </div>
          </div>
        );
      }
      case "NPS": {
        return (
          <div className="flex gap-1 flex-wrap mt-2">
            {Array.from({ length: 11 }, (_, i) => i).map(n => (
              <button key={n} onClick={() => setAnswer(q.id, n)}
                className={`w-10 h-10 rounded border text-xs font-semibold transition-colors ${
                  val === n
                    ? "bg-blue-600 text-white border-blue-600"
                    : n <= 6 ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
                    : n <= 8 ? "bg-amber-50 text-amber-600 border-amber-200 hover:bg-amber-100"
                    : "bg-green-50 text-green-600 border-green-200 hover:bg-green-100"
                }`}>
                {n}
              </button>
            ))}
            <div className="w-full flex justify-between text-xs text-gray-400 mt-0.5 px-1">
              <span>Not at all likely</span>
              <span>Extremely likely</span>
            </div>
          </div>
        );
      }
      case "YES_NO":
        return (
          <div className="flex gap-3 mt-2">
            {["Yes", "No"].map(opt => (
              <button key={opt} onClick={() => setAnswer(q.id, opt)}
                className={`px-6 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  val === opt
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                }`}>
                {opt}
              </button>
            ))}
          </div>
        );
      case "MULTIPLE_CHOICE":
        return (
          <div className="space-y-2 mt-2">
            {(q.options ?? []).map(opt => (
              <button key={opt} onClick={() => setAnswer(q.id, opt)}
                className={`w-full text-left px-4 py-2.5 rounded-lg border text-sm transition-colors ${
                  val === opt
                    ? "bg-blue-50 border-blue-400 text-blue-700 font-medium"
                    : "bg-white border-gray-200 text-gray-700 hover:border-blue-300"
                }`}>
                {opt}
              </button>
            ))}
          </div>
        );
      case "TEXT":
        return (
          <textarea
            value={(val as string) ?? ""}
            onChange={e => setAnswer(q.id, e.target.value)}
            rows={3}
            placeholder="Your response…"
            className="w-full mt-2 border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">{survey.title}</h1>
        {survey.description && <p className="text-sm text-gray-500 mt-1">{survey.description}</p>}
        {survey.anonymous_flag && (
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded px-3 py-1.5 mt-2 inline-block">
            Your response is anonymous
          </p>
        )}
      </div>

      {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}

      <div className="space-y-6">
        {survey.questions.map((q, i) => (
          <div key={q.id} className="bg-white border rounded-xl p-5 shadow-sm">
            <p className="text-sm font-medium text-gray-800">
              <span className="text-gray-400 mr-2">{i + 1}.</span>
              {q.question_text}
              {q.required_flag && <span className="text-red-400 ml-1">*</span>}
            </p>
            {q.category && <p className="text-xs text-gray-400 mt-0.5">{q.category}</p>}
            {renderInput(q)}
          </div>
        ))}
      </div>

      <button onClick={submit} disabled={submitting}
        className="w-full rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
        {submitting ? "Submitting…" : "Submit Response"}
      </button>
    </div>
  );
}
