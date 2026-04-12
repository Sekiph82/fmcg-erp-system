"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, Survey, SurveyType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SURVEY_TYPES: SurveyType[] = [
  "CUSTOMER_FEEDBACK", "MARKET_AUDIT", "RETAILER_FEEDBACK",
  "BRAND_AWARENESS", "COMPETITOR_CHECK", "PRODUCT_FEEDBACK", "SHELF_AUDIT",
];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

function SentimentBadge({ score }: { score: string | null }) {
  if (!score) return <span className="text-slate-600 text-sm">—</span>;
  const n = parseFloat(score);
  const color = n >= 0.6 ? "text-emerald-400" : n >= 0.4 ? "text-yellow-400" : "text-red-400";
  const label = n >= 0.6 ? "Positive" : n >= 0.4 ? "Neutral" : "Negative";
  return (
    <span className={`text-sm font-semibold ${color}`}>
      {label} ({(n * 100).toFixed(0)}%)
    </span>
  );
}

export default function SurveyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<{
    survey_name: string;
    survey_type: SurveyType;
    region: string;
    survey_date: string;
    summary: string;
    competitor_notes: string;
    sentiment_score: string;
  } | null>(null);
  const [responsesRaw, setResponsesRaw] = useState("");
  const [responsesJsonError, setResponsesJsonError] = useState("");
  const [showResponseForm, setShowResponseForm] = useState(false);
  const [error, setError] = useState("");

  const { data: survey, isLoading } = useQuery({
    queryKey: ["survey", id],
    queryFn: () => marketingApi.surveys.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => marketingApi.surveys.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["survey", id] });
      qc.invalidateQueries({ queryKey: ["surveys"] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.surveys.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/surveys"),
  });

  const startEdit = () => {
    if (!survey) return;
    setEditForm({
      survey_name: survey.survey_name,
      survey_type: survey.survey_type,
      region: survey.region ?? "",
      survey_date: survey.survey_date,
      summary: survey.summary ?? "",
      competitor_notes: survey.competitor_notes ?? "",
      sentiment_score: survey.sentiment_score ?? "",
    });
    setEditing(true);
  };

  const saveEdit = () => {
    if (!editForm) return;
    updateMut.mutate({
      survey_name: editForm.survey_name,
      survey_type: editForm.survey_type,
      region: editForm.region || null,
      survey_date: editForm.survey_date,
      summary: editForm.summary || null,
      competitor_notes: editForm.competitor_notes || null,
      sentiment_score: editForm.sentiment_score ? parseFloat(editForm.sentiment_score) : null,
    });
  };

  const saveResponses = () => {
    if (!responsesRaw.trim()) return;
    try {
      const responses_json = JSON.parse(responsesRaw);
      const current_count = (survey?.response_count ?? 0) + 1;
      updateMut.mutate({ responses_json, response_count: current_count });
      setShowResponseForm(false);
      setResponsesRaw("");
    } catch {
      setResponsesJsonError("Invalid JSON");
    }
  };

  const validateResponses = (v: string) => {
    setResponsesRaw(v);
    if (!v.trim()) { setResponsesJsonError(""); return; }
    try { JSON.parse(v); setResponsesJsonError(""); } catch { setResponsesJsonError("Invalid JSON"); }
  };

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!survey) return <div className="p-8 text-red-400">Survey not found.</div>;

  return (
    <RequirePermission permission="surveys.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-4xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Surveys
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{survey.survey_name}</h1>
              <p className="text-slate-400 text-sm mt-1">
                {survey.survey_type.replace(/_/g, " ")} · {survey.survey_date}
                {survey.region && ` · ${survey.region}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-right">
                <p className="text-xs text-slate-400">Responses</p>
                <p className="text-xl font-bold text-teal-400">{survey.response_count}</p>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main info */}
          <div className="lg:col-span-2 space-y-4">
            {!editing ? (
              <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Details</h2>
                  <RequirePermission permission="surveys.edit">
                    <div className="flex gap-2">
                      <button onClick={startEdit}
                        className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">
                        Edit
                      </button>
                      <button
                        onClick={() => { if (confirm("Delete this survey?")) deleteMut.mutate(); }}
                        className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">
                        Delete
                      </button>
                    </div>
                  </RequirePermission>
                </div>
                <div className="grid grid-cols-2 gap-x-8 gap-y-5">
                  <Field label="Survey Name" value={survey.survey_name} />
                  <Field label="Type" value={survey.survey_type.replace(/_/g, " ")} />
                  <Field label="Date" value={survey.survey_date} />
                  <Field label="Region" value={survey.region} />
                  <Field label="Sentiment" value={<SentimentBadge score={survey.sentiment_score} />} />
                  <Field label="Target Segment" value={survey.target_segment_id} />
                  <Field label="Conducted By" value={survey.conducted_by_id} />
                  <Field label="Response Count" value={survey.response_count} />
                </div>
                {survey.summary && (
                  <div className="border-t border-slate-700/50 pt-4 mt-5">
                    <p className="text-xs text-slate-400 mb-1">Summary</p>
                    <p className="text-sm text-slate-300">{survey.summary}</p>
                  </div>
                )}
                {survey.competitor_notes && (
                  <div className="border-t border-slate-700/50 pt-4 mt-4">
                    <p className="text-xs text-slate-400 mb-1">Competitor Notes</p>
                    <p className="text-sm text-slate-300">{survey.competitor_notes}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-2">Edit Survey</h2>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Survey Name</label>
                  <input type="text" value={editForm?.survey_name ?? ""}
                    onChange={(e) => setEditForm((f) => f ? { ...f, survey_name: e.target.value } : f)}
                    className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Survey Type</label>
                    <select value={editForm?.survey_type}
                      onChange={(e) => setEditForm((f) => f ? { ...f, survey_type: e.target.value as SurveyType } : f)}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                      {SURVEY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Survey Date</label>
                    <input type="date" value={editForm?.survey_date ?? ""}
                      onChange={(e) => setEditForm((f) => f ? { ...f, survey_date: e.target.value } : f)}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Region</label>
                    <input type="text" value={editForm?.region ?? ""}
                      onChange={(e) => setEditForm((f) => f ? { ...f, region: e.target.value } : f)}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Sentiment Score <span className="text-slate-500">(0.0–1.0)</span></label>
                    <input type="number" min="0" max="1" step="0.01" value={editForm?.sentiment_score ?? ""}
                      onChange={(e) => setEditForm((f) => f ? { ...f, sentiment_score: e.target.value } : f)}
                      className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Summary</label>
                  <textarea value={editForm?.summary ?? ""}
                    onChange={(e) => setEditForm((f) => f ? { ...f, summary: e.target.value } : f)}
                    rows={2}
                    className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Competitor Notes</label>
                  <textarea value={editForm?.competitor_notes ?? ""}
                    onChange={(e) => setEditForm((f) => f ? { ...f, competitor_notes: e.target.value } : f)}
                    rows={2}
                    className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
                </div>

                <div className="flex justify-end gap-3">
                  <button onClick={() => setEditing(false)}
                    className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">
                    Cancel
                  </button>
                  <button onClick={saveEdit} disabled={updateMut.isPending}
                    className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-sm font-medium">
                    {updateMut.isPending ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </div>
            )}

            {/* Responses section */}
            <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                  Responses ({survey.response_count})
                </h2>
                <RequirePermission permission="surveys.analyze">
                  <button onClick={() => setShowResponseForm((v) => !v)}
                    className="px-3 py-1.5 rounded-lg bg-teal-600/20 hover:bg-teal-600/40 text-teal-400 text-sm">
                    {showResponseForm ? "Cancel" : "+ Add Responses"}
                  </button>
                </RequirePermission>
              </div>

              {showResponseForm && (
                <div className="mb-4 p-4 bg-[#0b1120] rounded-lg border border-slate-700/50 space-y-3">
                  <p className="text-xs text-slate-400">Paste aggregated responses as JSON. This will overwrite existing responses.</p>
                  <textarea
                    value={responsesRaw}
                    onChange={(e) => validateResponses(e.target.value)}
                    rows={6}
                    placeholder={`{\n  "q1_responses": ["Good", "Excellent", "Poor"],\n  "q2_responses": ["Yes", "Yes", "No"]\n}`}
                    className={`w-full bg-[#0d1527] border rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-slate-600 resize-y ${
                      responsesJsonError ? "border-red-600" : "border-slate-700"
                    }`}
                  />
                  {responsesJsonError && <p className="text-xs text-red-400">{responsesJsonError}</p>}
                  <div className="flex justify-end">
                    <button onClick={saveResponses}
                      disabled={!responsesRaw.trim() || !!responsesJsonError || updateMut.isPending}
                      className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-sm font-medium">
                      Save Responses
                    </button>
                  </div>
                </div>
              )}

              {survey.responses_json ? (
                <pre className="text-xs text-slate-300 bg-[#0b1120] rounded-lg p-4 overflow-auto max-h-64 border border-slate-700/50">
                  {JSON.stringify(survey.responses_json, null, 2)}
                </pre>
              ) : (
                <p className="text-slate-500 text-sm">No responses recorded yet.</p>
              )}
            </div>
          </div>

          {/* Sidebar: questions */}
          <div className="space-y-4">
            <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Questions</h2>
              {survey.questions_json ? (
                <div className="space-y-2">
                  {Object.entries(survey.questions_json).map(([key, val]) => (
                    <div key={key} className="p-2.5 bg-[#0b1120] rounded-lg border border-slate-700/50">
                      <p className="text-xs text-slate-500 mb-0.5">{key}</p>
                      <p className="text-sm text-slate-300">{String(val)}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-sm">No questions defined.</p>
              )}
            </div>

            {survey.sentiment_score && (
              <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Sentiment</h2>
                <div className="text-center py-3">
                  <SentimentBadge score={survey.sentiment_score} />
                  <div className="mt-3 h-2 rounded-full bg-slate-700 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        parseFloat(survey.sentiment_score) >= 0.6
                          ? "bg-emerald-500"
                          : parseFloat(survey.sentiment_score) >= 0.4
                          ? "bg-yellow-500"
                          : "bg-red-500"
                      }`}
                      style={{ width: `${parseFloat(survey.sentiment_score) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Meta</h2>
              <div className="space-y-2 text-xs text-slate-400">
                <div className="flex justify-between">
                  <span>Created</span>
                  <span>{survey.created_at ? new Date(survey.created_at).toLocaleDateString() : "—"}</span>
                </div>
                {survey.target_segment_id && (
                  <div className="flex justify-between">
                    <span>Segment</span>
                    <span className="font-mono text-slate-500">{survey.target_segment_id.slice(0, 8)}…</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
