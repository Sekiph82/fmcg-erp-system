"use client";
import { useEffect, useState } from "react";
import {
  trainingApi, TrainingProgram, SkillCategory, TrainingType,
  CATEGORY_COLOR, TRAINING_TYPE_LABEL,
} from "@/lib/training";

const CATEGORIES: SkillCategory[] = ["technical","soft","safety","compliance","management"];
const TYPES: TrainingType[] = ["internal","external","online","classroom","on_job"];

export default function TrainingProgramsPage() {
  const [programs, setPrograms] = useState<TrainingProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ category: "", mandatory_only: false });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    training_code: "", training_name: "", training_type: "classroom" as TrainingType,
    category: "technical" as SkillCategory, duration_hours: "", provider: "",
    cost: "", mandatory_flag: false, validity_period_days: "", notes: "",
  });
  const [effectiveness, setEffectiveness] = useState<Record<string, unknown>>({});

  const load = () =>
    trainingApi.listPrograms({ category: filter.category || undefined, mandatory_only: filter.mandatory_only || undefined })
      .then(setPrograms).finally(() => setLoading(false));
  useEffect(() => { load(); }, [filter]);

  const submit = async () => {
    await trainingApi.createProgram({
      ...form,
      duration_hours: form.duration_hours ? Number(form.duration_hours) : undefined,
      cost: form.cost ? Number(form.cost) : undefined,
      validity_period_days: form.validity_period_days ? Number(form.validity_period_days) : undefined,
      provider: form.provider || undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  const loadEffectiveness = async (id: string) => {
    const data = await trainingApi.getProgramEffectiveness(id);
    setEffectiveness((prev) => ({ ...prev, [id]: data }));
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Training Programs</h1>
        <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Program
        </button>
      </div>

      <div className="flex gap-3 flex-wrap items-center">
        <select className="border rounded px-2 py-1 text-sm" value={filter.category} onChange={(e) => setFilter({ ...filter, category: e.target.value })}>
          <option value="">All Categories</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={filter.mandatory_only} onChange={(e) => setFilter({ ...filter, mandatory_only: e.target.checked })} />
          Mandatory only
        </label>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">New Training Program</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["training_code","training_name","provider"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Training Type</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.training_type}
                onChange={(e) => setForm({ ...form, training_type: e.target.value as TrainingType })}>
                {TYPES.map(t => <option key={t} value={t}>{TRAINING_TYPE_LABEL[t]}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Category</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value as SkillCategory })}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {(["duration_hours","cost","validity_period_days"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input type="number" className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
              </div>
            ))}
            <div className="flex items-center gap-2 mt-4">
              <input type="checkbox" checked={form.mandatory_flag} onChange={(e) => setForm({ ...form, mandatory_flag: e.target.checked })} />
              <label className="text-sm text-gray-700">Mandatory Training</label>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Notes</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
                value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-3">
          {programs.map((p) => (
            <div key={p.training_id} className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-gray-800">{p.training_name}</span>
                    <span className="font-mono text-xs text-gray-400">{p.training_code}</span>
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_COLOR[p.category]}`}>{p.category}</span>
                    <span className="text-xs text-gray-500">{TRAINING_TYPE_LABEL[p.training_type]}</span>
                    {p.mandatory_flag && <span className="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-medium">Mandatory</span>}
                    {!p.active_flag && <span className="rounded-full bg-gray-100 text-gray-500 px-2 py-0.5 text-xs">Inactive</span>}
                  </div>
                  <div className="flex gap-4 mt-2 text-xs text-gray-500 flex-wrap">
                    {p.provider && <span>Provider: {p.provider}</span>}
                    {p.duration_hours != null && <span>Duration: {p.duration_hours}h</span>}
                    {p.cost != null && <span>Cost: KES {Number(p.cost).toLocaleString()}</span>}
                    {p.validity_period_days != null && <span>Valid: {p.validity_period_days} days</span>}
                  </div>
                </div>
                <div className="flex gap-2 ml-3">
                  <button
                    onClick={() => loadEffectiveness(p.training_id)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Effectiveness
                  </button>
                </div>
              </div>
              {effectiveness[p.training_id] && (
                <div className="mt-2 bg-blue-50 rounded p-2 text-xs text-blue-800">
                  {(() => {
                    const e = effectiveness[p.training_id] as { feedback_count: number; avg_rating?: number };
                    return e.feedback_count === 0
                      ? "No feedback yet."
                      : `${e.feedback_count} responses · Avg Rating: ${e.avg_rating}/5`;
                  })()}
                </div>
              )}
            </div>
          ))}
          {programs.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No programs found.</p>}
        </div>
      )}
    </div>
  );
}
