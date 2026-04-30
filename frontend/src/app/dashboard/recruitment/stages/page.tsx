"use client";
import { useEffect, useState } from "react";
import { recruitmentApi, RecruitmentStage } from "@/lib/recruitment";

export default function StagesPage() {
  const [stages, setStages] = useState<RecruitmentStage[]>([]);
  const [seeding, setSeeding] = useState(false);
  const [form, setForm] = useState({ stage_code: "", stage_name: "", sequence: "1", stage_type: "active" });
  const [showForm, setShowForm] = useState(false);

  const load = () => recruitmentApi.listStages().then(setStages).catch(console.error);
  useEffect(() => { load(); }, []);

  const handleSeed = async () => {
    setSeeding(true);
    await recruitmentApi.seedStages();
    await load();
    setSeeding(false);
  };

  const handleCreate = async () => {
    await recruitmentApi.createStage({ ...form, sequence: Number(form.sequence) });
    await load();
    setShowForm(false);
  };

  const typeColor: Record<string, string> = {
    active: "bg-blue-100 text-blue-700",
    final_hire: "bg-green-100 text-green-700",
    final_reject: "bg-red-100 text-red-700",
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Pipeline Stages</h1>
        <div className="flex gap-2">
          {stages.length === 0 && (
            <button onClick={handleSeed} disabled={seeding}
              className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700 disabled:opacity-50">
              {seeding ? "Seeding…" : "Seed Defaults (11 stages)"}
            </button>
          )}
          <button onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            {showForm ? "Cancel" : "+ New Stage"}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Code</label>
              <input value={form.stage_code} onChange={(e) => setForm({ ...form, stage_code: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name</label>
              <input value={form.stage_name} onChange={(e) => setForm({ ...form, stage_name: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Sequence</label>
              <input type="number" value={form.sequence} onChange={(e) => setForm({ ...form, sequence: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select value={form.stage_type} onChange={(e) => setForm({ ...form, stage_type: e.target.value })}
                className="w-full border rounded p-2 text-sm">
                <option value="active">Active</option>
                <option value="final_hire">Final — Hire</option>
                <option value="final_reject">Final — Reject</option>
              </select>
            </div>
          </div>
          <button onClick={handleCreate} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Create Stage
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Seq</th>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Stage Name</th>
              <th className="px-4 py-3 text-left">Type</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {stages.map((s) => (
              <tr key={s.stage_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">{s.sequence}</td>
                <td className="px-4 py-3 font-mono text-xs">{s.stage_code}</td>
                <td className="px-4 py-3 font-medium">{s.stage_name}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${typeColor[s.stage_type] ?? "bg-gray-100 text-gray-600"}`}>
                    {s.stage_type.replace("_", " ")}
                  </span>
                </td>
              </tr>
            ))}
            {stages.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No stages — seed defaults to start</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
