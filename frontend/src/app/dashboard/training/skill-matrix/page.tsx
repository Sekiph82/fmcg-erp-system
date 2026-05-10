"use client";
import { useCallback, useEffect, useState } from "react";
import {
  trainingApi, EmployeeSkillRow, Skill, SkillCategory, SkillLevel,
  CATEGORY_COLOR, LEVEL_COLOR,
} from "@/lib/training";

const CATEGORIES: SkillCategory[] = ["technical","soft","safety","compliance","management"];
const LEVELS: SkillLevel[] = ["basic","intermediate","advanced","expert"];

export default function SkillMatrixPage() {
  const [matrix, setMatrix] = useState<EmployeeSkillRow[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [empFilter, setEmpFilter] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [gapsOnly, setGapsOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    employee_id: "", employee_name: "", department_id: "",
    skill_id: "", current_level: "" as SkillLevel | "", required_level: "" as SkillLevel | "",
    last_assessed_date: "", notes: "",
  });
  const [showSeedBtn, setShowSeedBtn] = useState(true);

  const load = useCallback(() => {
    Promise.all([
      trainingApi.getSkillMatrix(empFilter || undefined, deptFilter || undefined),
      trainingApi.listSkills(undefined, true),
    ]).then(([m, s]) => { setMatrix(m); setSkills(s); }).finally(() => setLoading(false));
  }, [empFilter, deptFilter]);
  useEffect(() => { load(); }, [load]);

  const seed = async () => {
    await trainingApi.seedSkills();
    setShowSeedBtn(false);
    load();
  };

  const saveProfile = async () => {
    await trainingApi.upsertSkillProfile({
      ...form,
      skill_id: form.skill_id,
      current_level: form.current_level || undefined,
      required_level: form.required_level || undefined,
      last_assessed_date: form.last_assessed_date || undefined,
      notes: form.notes || undefined,
    });
    setShowForm(false);
    load();
  };

  const displayed = gapsOnly ? matrix.filter(r => r.has_gap) : matrix;

  // group by employee
  const byEmployee: Record<string, EmployeeSkillRow[]> = {};
  for (const row of displayed) {
    byEmployee[row.employee_id] = byEmployee[row.employee_id] ?? [];
    byEmployee[row.employee_id].push(row);
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Skill Matrix</h1>
        <div className="flex gap-2">
          {showSeedBtn && (
            <button onClick={seed} className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
              Seed Default Skills
            </button>
          )}
          <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Add Skill Profile
          </button>
        </div>
      </div>

      <div className="flex gap-3 flex-wrap items-center">
        <input className="border rounded px-2 py-1 text-sm w-40" placeholder="Employee ID…"
          value={empFilter} onChange={(e) => setEmpFilter(e.target.value)} />
        <input className="border rounded px-2 py-1 text-sm w-40" placeholder="Department ID…"
          value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={gapsOnly} onChange={(e) => setGapsOnly(e.target.checked)} />
          Gaps only
        </label>
        <span className="text-xs text-gray-500">{displayed.length} records</span>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Add / Update Skill Profile</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["employee_id","employee_name","department_id"] as const).map((f) => (
              <div key={f}>
                <label className="text-xs text-gray-500 capitalize">{f.replace(/_/g," ")}</label>
                <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form[f]}
                  onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Skill *</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.skill_id}
                onChange={(e) => setForm({ ...form, skill_id: e.target.value })}>
                <option value="">Select skill…</option>
                {skills.map(s => <option key={s.skill_id} value={s.skill_id}>{s.skill_name} ({s.category})</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Current Level</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.current_level}
                onChange={(e) => setForm({ ...form, current_level: e.target.value as SkillLevel })}>
                <option value="">Not assessed</option>
                {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Required Level</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.required_level}
                onChange={(e) => setForm({ ...form, required_level: e.target.value as SkillLevel })}>
                <option value="">Not set</option>
                {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Last Assessed Date</label>
              <input type="date" className="w-full border rounded px-2 py-1 text-sm mt-1"
                value={form.last_assessed_date} onChange={(e) => setForm({ ...form, last_assessed_date: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={saveProfile} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Save</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-4">
          {Object.entries(byEmployee).map(([empId, rows]) => (
            <div key={empId} className="bg-white border rounded-lg shadow-sm overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b flex items-center justify-between">
                <span className="font-semibold text-gray-800">{rows[0].employee_name ?? empId}</span>
                <span className="text-xs text-gray-500">{rows[0].department_id ?? "—"} · {rows.filter(r=>r.has_gap).length} gap(s)</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
                {rows.map((row) => (
                  <div key={row.employee_skill_id} className={`rounded border p-2 text-xs ${row.has_gap ? "border-red-300 bg-red-50" : "border-gray-200"}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-800">{row.skill_name}</span>
                      <span className={`rounded-full px-1.5 py-0.5 text-xs ${CATEGORY_COLOR[row.skill_category]}`}>{row.skill_category}</span>
                    </div>
                    <div className="flex gap-2">
                      <div>
                        <span className="text-gray-500">Current: </span>
                        {row.current_level ? (
                          <span className={`rounded px-1 ${LEVEL_COLOR[row.current_level]}`}>{row.current_level}</span>
                        ) : <span className="text-gray-400">—</span>}
                      </div>
                      <div>
                        <span className="text-gray-500">Required: </span>
                        {row.required_level ? (
                          <span className={`rounded px-1 ${LEVEL_COLOR[row.required_level]}`}>{row.required_level}</span>
                        ) : <span className="text-gray-400">—</span>}
                      </div>
                    </div>
                    {row.has_gap && <p className="text-red-600 font-semibold mt-1">⚠ Gap</p>}
                  </div>
                ))}
              </div>
            </div>
          ))}
          {Object.keys(byEmployee).length === 0 && (
            <p className="text-gray-400 text-sm text-center py-8">No skill profiles found. Add profiles or seed default skills.</p>
          )}
        </div>
      )}
    </div>
  );
}
