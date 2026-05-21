"use client";
import { useEffect, useState } from "react";
import { trainingApi, TrainingFeedback, TrainingProgram } from "@/lib/training";

function Stars({ value }: { value: number }) {
  return (
    <span className="text-yellow-500">
      {"★".repeat(value)}{"☆".repeat(5 - value)}
    </span>
  );
}

export default function FeedbackPage() {
  const [feedbacks, setFeedbacks] = useState<TrainingFeedback[]>([]);
  const [programs, setPrograms] = useState<TrainingProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterProgram, setFilterProgram] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    employee_id: "", employee_name: "", training_id: "",
    rating: "5", content_rating: "", trainer_rating: "", relevance_rating: "", comments: "",
  });

  const load = () =>
    Promise.all([
      trainingApi.listFeedback(filterProgram || undefined),
      trainingApi.listPrograms(),
    ]).then(([f, p]) => { setFeedbacks(f); setPrograms(p); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, [filterProgram]);

  const submit = async () => {
    await trainingApi.submitFeedback({
      ...form,
      rating: Number(form.rating),
      content_rating: form.content_rating ? Number(form.content_rating) : undefined,
      trainer_rating: form.trainer_rating ? Number(form.trainer_rating) : undefined,
      relevance_rating: form.relevance_rating ? Number(form.relevance_rating) : undefined,
      comments: form.comments || undefined,
    });
    setShowForm(false);
    load();
  };

  const avgRating = feedbacks.length
    ? (feedbacks.reduce((s, f) => s + f.rating, 0) / feedbacks.length).toFixed(1)
    : null;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Training Feedback & Evaluation</h1>
        <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Submit Feedback
        </button>
      </div>

      {avgRating && (
        <div className="bg-white border rounded-lg p-3 shadow-sm inline-flex items-center gap-2">
          <Stars value={Math.round(Number(avgRating))} />
          <span className="text-sm font-semibold text-gray-700">{avgRating}/5 avg ({feedbacks.length} responses)</span>
        </div>
      )}

      <select className="border rounded px-2 py-1 text-sm" value={filterProgram}
        onChange={(e) => setFilterProgram(e.target.value)}>
        <option value="">All Programs</option>
        {programs.map(p => <option key={p.training_id} value={p.training_id}>{p.training_name}</option>)}
      </select>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Submit Training Feedback</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["employee_id","employee_name"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
              </div>
            ))}
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Training Program *</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.training_id}
                onChange={(e) => setForm({ ...form, training_id: e.target.value })}>
                <option value="">Select…</option>
                {programs.map(p => <option key={p.training_id} value={p.training_id}>{p.training_name}</option>)}
              </select>
            </div>
            {(["rating","content_rating","trainer_rating","relevance_rating"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")} (1–5)</label>
                <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })}>
                  {f !== "rating" && <option value="">Not rated</option>}
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v} {"★".repeat(v)}</option>)}
                </select>
              </div>
            ))}
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Comments</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={3}
                value={form.comments} onChange={(e) => setForm({ ...form, comments: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Submit</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-3">
          {feedbacks.map(f => (
            <div key={f.feedback_id} className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-800">{f.employee_name ?? f.employee_id}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{programs.find(p => p.training_id === f.training_id)?.training_name ?? f.training_id}</p>
                </div>
                <div className="text-right">
                  <Stars value={f.rating} />
                  <p className="text-xs text-gray-400 mt-0.5">{new Date(f.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              {(f.content_rating || f.trainer_rating || f.relevance_rating) && (
                <div className="flex gap-4 mt-2 text-xs text-gray-500">
                  {f.content_rating != null && <span>Content: <Stars value={f.content_rating} /></span>}
                  {f.trainer_rating != null && <span>Trainer: <Stars value={f.trainer_rating} /></span>}
                  {f.relevance_rating != null && <span>Relevance: <Stars value={f.relevance_rating} /></span>}
                </div>
              )}
              {f.comments && <p className="text-sm text-gray-600 mt-2 border-t pt-2">{f.comments}</p>}
            </div>
          ))}
          {feedbacks.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No feedback submitted yet.</p>}
        </div>
      )}
    </div>
  );
}
