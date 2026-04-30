"use client";
import { useEffect, useState } from "react";
import { recruitmentApi, RecruitmentStage } from "@/lib/recruitment";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

const typeColor: Record<string, string> = {
  active: "bg-blue-500/20 text-blue-300",
  final_hire: "bg-emerald-500/20 text-emerald-300",
  final_reject: "bg-red-500/20 text-red-300",
};

export default function StagesPage() {
  const [stages, setStages] = useState<RecruitmentStage[]>([]);
  const [seeding, setSeeding] = useState(false);
  const [form, setForm] = useState({ stage_code: "", stage_name: "", sequence: "1", stage_type: "active" });
  const [showForm, setShowForm] = useState(false);

  const load = () => recruitmentApi.listStages().then(setStages).catch(console.error);
  useEffect(() => { load(); }, []);

  const handleSeed = async () => { setSeeding(true); await recruitmentApi.seedStages(); await load(); setSeeding(false); };
  const handleCreate = async () => { await recruitmentApi.createStage({ ...form, sequence: Number(form.sequence) }); await load(); setShowForm(false); };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Pipeline Stages</h1>
          <p className="text-slate-500 text-sm mt-0.5">{stages.length} stages configured</p>
        </div>
        <div className="flex gap-2">
          {stages.length === 0 && (
            <button onClick={handleSeed} disabled={seeding}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-50">
              {seeding ? "Seeding…" : "Seed Defaults (11 stages)"}
            </button>
          )}
          <button onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
            {showForm ? "Cancel" : "+ New Stage"}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
          <div className="grid grid-cols-4 gap-3">
            <div><label className={labelCls}>Code</label><input value={form.stage_code} onChange={(e) => setForm({ ...form, stage_code: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Name</label><input value={form.stage_name} onChange={(e) => setForm({ ...form, stage_name: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Sequence</label><input type="number" value={form.sequence} onChange={(e) => setForm({ ...form, sequence: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Type</label>
              <select value={form.stage_type} onChange={(e) => setForm({ ...form, stage_type: e.target.value })} className={selectCls}>
                <option value="active">Active</option>
                <option value="final_hire">Final — Hire</option>
                <option value="final_reject">Final — Reject</option>
              </select>
            </div>
          </div>
          <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Create Stage</button>
        </div>
      )}

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Seq", "Code", "Stage Name", "Type"].map((h) => (
              <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {stages.map((s) => (
              <tr key={s.stage_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-slate-500">{s.sequence}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.stage_code}</td>
                <td className="px-4 py-3 text-white font-medium">{s.stage_name}</td>
                <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${typeColor[s.stage_type] ?? "bg-slate-500/20 text-slate-400"}`}>{s.stage_type.replace("_", " ")}</span></td>
              </tr>
            ))}
            {stages.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-600">No stages — seed defaults to start</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
