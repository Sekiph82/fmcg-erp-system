"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { surveysApi, SurveyResults, QuestionStat } from "@/lib/surveys";

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 70 ? "text-green-600" : score >= 50 ? "text-amber-600" : "text-red-600";
  const bg = score >= 70 ? "stroke-green-500" : score >= 50 ? "stroke-amber-500" : "stroke-red-500";
  const r = 40, c = 2 * Math.PI * r;
  const dash = (score / 100) * c;
  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <circle cx="50" cy="50" r={r} fill="none" className={bg} strokeWidth="10"
          strokeDasharray={`${dash} ${c}`} strokeDashoffset={c / 4} strokeLinecap="round"
        />
        <text x="50" y="55" textAnchor="middle" className={`text-xl font-bold ${color}`} style={{ fontSize: "18px", fill: "currentColor" }}>
          {score.toFixed(0)}
        </text>
      </svg>
      <p className="text-xs text-gray-500 mt-1">Engagement Score</p>
    </div>
  );
}

function DistBar({ label, count, total }: { label: string; count: number; total: number }) {
  const pct = total > 0 ? Math.round(count / total * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-600 w-24 text-right flex-shrink-0">{label}</span>
      <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-5 bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-12">{count} ({pct}%)</span>
    </div>
  );
}

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [results, setResults] = useState<SurveyResults | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    surveysApi.getResults(id).then(r => { setResults(r); setLoading(false); });
  }, [id]);

  if (loading) return <div className="p-6 text-sm text-gray-500">Loading results…</div>;
  if (!results) return <div className="p-6 text-sm text-red-500">Results not found.</div>;

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{results.title} — Results</h1>
          <p className="text-xs text-gray-500 mt-0.5">{results.total_responses} total responses</p>
        </div>
        {results.engagement_score != null && <ScoreGauge score={results.engagement_score} />}
      </div>

      {results.total_responses === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📊</p>
          <p className="text-sm">No responses yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {results.questions.map((q: QuestionStat, i) => (
            <div key={q.question_id} className="bg-white border rounded-lg p-5 shadow-sm">
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <p className="text-sm font-medium text-gray-800">
                    <span className="text-gray-400 mr-2">{i + 1}.</span>
                    {q.question_text}
                  </p>
                  {q.category && <p className="text-xs text-gray-400 mt-0.5">{q.category}</p>}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">{q.answer_count} answers</span>
              </div>

              {q.avg != null && (
                <div className="flex items-center gap-4 mb-3">
                  <div className="text-3xl font-bold text-blue-600">{q.avg.toFixed(2)}</div>
                  <div className="text-xs text-gray-500">
                    <p>Min: {q.min} · Max: {q.max}</p>
                    <p>Average score</p>
                  </div>
                </div>
              )}

              {q.distribution && Object.keys(q.distribution).length > 0 && (
                <div className="space-y-1.5">
                  {Object.entries(q.distribution)
                    .sort(([a], [b]) => parseFloat(a) - parseFloat(b))
                    .map(([label, count]) => (
                      <DistBar key={label} label={label} count={count as number} total={q.answer_count} />
                    ))}
                </div>
              )}

              {q.sample_responses && q.sample_responses.length > 0 && (
                <div className="space-y-1 mt-2">
                  {q.sample_responses.map((r, j) => (
                    <p key={j} className="text-xs text-gray-600 bg-gray-50 rounded px-3 py-2 border-l-2 border-blue-300">
                      "{r}"
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <a href={`/dashboard/surveys/${id}`} className="text-xs text-blue-600 hover:underline">← Survey Details</a>
    </div>
  );
}
