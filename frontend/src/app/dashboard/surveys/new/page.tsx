"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { surveysApi, SurveyQuestion, SURVEY_TYPE_LABEL, QUESTION_TYPE_LABEL, QuestionType } from "@/lib/surveys";

const SURVEY_TYPES = Object.keys(SURVEY_TYPE_LABEL) as (keyof typeof SURVEY_TYPE_LABEL)[];
const QUESTION_TYPES = Object.keys(QUESTION_TYPE_LABEL) as QuestionType[];

interface QDraft {
  _key: number;
  question_text: string;
  question_type: QuestionType;
  required_flag: boolean;
  scale_min: number;
  scale_max: number;
  options_raw: string;
  category: string;
}

let _keyCounter = 0;
const newQ = (): QDraft => ({
  _key: ++_keyCounter,
  question_text: "",
  question_type: "RATING",
  required_flag: true,
  scale_min: 1,
  scale_max: 5,
  options_raw: "",
  category: "",
});

export default function NewSurveyPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    title: "", description: "", survey_type: "PULSE",
    anonymous_flag: true, target_all: true, target_department: "",
    start_date: "", end_date: "",
  });
  const [questions, setQuestions] = useState<QDraft[]>([newQ()]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const addQ = () => setQuestions(qs => [...qs, newQ()]);
  const removeQ = (key: number) => setQuestions(qs => qs.filter(q => q._key !== key));
  const updateQ = (key: number, patch: Partial<QDraft>) =>
    setQuestions(qs => qs.map(q => q._key === key ? { ...q, ...patch } : q));

  const save = async () => {
    if (!form.title.trim()) { setError("Title required"); return; }
    if (questions.some(q => !q.question_text.trim())) { setError("All questions need text"); return; }
    setSaving(true); setError("");
    try {
      const payload = {
        ...form,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        target_department: form.target_department || null,
        questions: questions.map((q, i) => ({
          question_text: q.question_text,
          question_type: q.question_type,
          required_flag: q.required_flag,
          display_order: i,
          scale_min: q.scale_min,
          scale_max: q.scale_max,
          options: q.options_raw ? q.options_raw.split(",").map(o => o.trim()).filter(Boolean) : null,
          category: q.category || null,
        })),
      };
      const result = await surveysApi.createSurvey(payload);
      router.push(`/dashboard/surveys/${result.id}`);
    } catch {
      setError("Failed to create survey");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-900">New Survey</h1>
        <div className="flex gap-2">
          <a href="/dashboard/surveys" className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">Cancel</a>
          <button onClick={save} disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Saving…" : "Create Survey"}
          </button>
        </div>
      </div>

      {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}

      <div className="bg-white border rounded-lg p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-800">Survey Details</h2>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
          <input type="text" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Q3 2026 Pulse Survey"
            className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            rows={2} placeholder="Brief explanation of this survey's purpose…"
            className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Survey Type</label>
            <select value={form.survey_type} onChange={e => setForm(f => ({ ...f, survey_type: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
              {SURVEY_TYPES.map(t => <option key={t} value={t}>{SURVEY_TYPE_LABEL[t]}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Department (blank = all)</label>
            <input type="text" value={form.target_department}
              onChange={e => setForm(f => ({ ...f, target_department: e.target.value }))}
              placeholder="e.g. Production"
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
            <input type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
            <input type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" checked={form.anonymous_flag}
              onChange={e => setForm(f => ({ ...f, anonymous_flag: e.target.checked }))}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            Anonymous responses
          </label>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-800">Questions ({questions.length})</h2>
          <button onClick={addQ}
            className="rounded border px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50 border-blue-200">
            + Add Question
          </button>
        </div>

        {questions.map((q, idx) => (
          <div key={q._key} className="border rounded-lg p-4 space-y-3 bg-gray-50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500">Q{idx + 1}</span>
              {questions.length > 1 && (
                <button onClick={() => removeQ(q._key)} className="text-xs text-red-500 hover:underline">Remove</button>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Question Text *</label>
              <textarea value={q.question_text}
                onChange={e => updateQ(q._key, { question_text: e.target.value })}
                rows={2} placeholder="e.g. How would you rate your overall work satisfaction?"
                className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none bg-white"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                <select value={q.question_type}
                  onChange={e => updateQ(q._key, { question_type: e.target.value as QuestionType })}
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white">
                  {QUESTION_TYPES.map(t => <option key={t} value={t}>{QUESTION_TYPE_LABEL[t]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
                <input type="text" value={q.category}
                  onChange={e => updateQ(q._key, { category: e.target.value })}
                  placeholder="e.g. Management"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                  <input type="checkbox" checked={q.required_flag}
                    onChange={e => updateQ(q._key, { required_flag: e.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  Required
                </label>
              </div>
            </div>
            {["RATING", "LIKERT"].includes(q.question_type) && (
              <div className="flex gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Min</label>
                  <input type="number" value={q.scale_min}
                    onChange={e => updateQ(q._key, { scale_min: parseInt(e.target.value) || 1 })}
                    className="w-16 border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Max</label>
                  <input type="number" value={q.scale_max}
                    onChange={e => updateQ(q._key, { scale_max: parseInt(e.target.value) || 5 })}
                    className="w-16 border rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                  />
                </div>
              </div>
            )}
            {q.question_type === "MULTIPLE_CHOICE" && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Options (comma-separated)</label>
                <input type="text" value={q.options_raw}
                  onChange={e => updateQ(q._key, { options_raw: e.target.value })}
                  placeholder="Very satisfied, Satisfied, Neutral, Dissatisfied"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
