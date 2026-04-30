"use client";
import { useEffect, useState } from "react";
import { appraisalsApi, AppraisalRecord, KPILine, CompetencyLine } from "@/lib/appraisals";

export default function SelfReviewPage() {
  const [records, setRecords] = useState<AppraisalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AppraisalRecord | null>(null);
  const [kpiScores, setKpiScores] = useState<Record<string, string>>({});
  const [compRatings, setCompRatings] = useState<Record<string, string>>({});
  const [selfScore, setSelfScore] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [employeeId, setEmployeeId] = useState("");

  const load = () => {
    appraisalsApi.listRecords({ status: "self_review" })
      .then(setRecords).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const openRecord = (r: AppraisalRecord) => {
    setSelected(r);
    const ks: Record<string,string> = {};
    r.kpi_lines.forEach(l => { ks[l.kpi_line_id] = String(l.self_score ?? ""); });
    setKpiScores(ks);
    const cs: Record<string,string> = {};
    r.competency_lines.forEach(l => { cs[l.competency_line_id] = String(l.self_rating ?? ""); });
    setCompRatings(cs);
    setSelfScore(String(r.self_score ?? ""));
    setNotes(r.notes ?? "");
  };

  const saveKpiScores = async () => {
    if (!selected) return;
    for (const [id, score] of Object.entries(kpiScores)) {
      if (score) await appraisalsApi.updateKPILine(id, { self_score: Number(score) });
    }
    for (const [id, rating] of Object.entries(compRatings)) {
      if (rating) await appraisalsApi.updateCompetencyLine(id, { self_rating: Number(rating) });
    }
    await appraisalsApi.calculateScores(selected.appraisal_id);
  };

  const submit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await saveKpiScores();
      await appraisalsApi.selfSubmit(selected.appraisal_id, {
        self_score: selfScore ? Number(selfScore) : undefined,
        notes: notes || undefined,
      });
      setSelected(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Employee Self Review</h1>
        <input
          className="border rounded px-2 py-1 text-sm w-48"
          placeholder="Filter by employee ID…"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
        />
      </div>
      <p className="text-sm text-gray-500">Appraisals pending self-review. Employees enter self scores and submit to manager.</p>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="grid gap-3">
          {records
            .filter(r => !employeeId || r.employee_id.includes(employeeId))
            .map((r) => (
              <div key={r.appraisal_id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
                <div>
                  <p className="font-semibold text-gray-800">{r.employee_name ?? r.employee_id}</p>
                  <p className="text-sm text-gray-500">{r.department_name ?? "—"} · Manager: {r.manager_name ?? "—"}</p>
                  <p className="text-xs text-gray-400 mt-1">KPIs: {r.kpi_lines.length} · Competencies: {r.competency_lines.length}</p>
                </div>
                <button
                  onClick={() => openRecord(r)}
                  className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700"
                >
                  Start Self Review
                </button>
              </div>
            ))}
          {records.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No appraisals pending self-review.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6 space-y-4 my-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                Self Review — {selected.employee_name ?? selected.employee_id}
              </h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>

            {selected.kpi_lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">KPI Self Scores (0–100)</h3>
                <div className="space-y-2">
                  {selected.kpi_lines.map((l) => (
                    <div key={l.kpi_line_id} className="grid grid-cols-3 gap-2 items-center">
                      <span className="text-sm text-gray-700 col-span-2">
                        {l.kpi_name}
                        <span className="text-gray-400 text-xs ml-1">(weight: {l.weight_pct}%)</span>
                        {l.target_value != null && <span className="text-gray-400 text-xs ml-1">Target: {l.target_value} {l.unit}</span>}
                      </span>
                      <input
                        type="number" min={0} max={100}
                        className="border rounded px-2 py-1 text-sm"
                        placeholder="Score 0–100"
                        value={kpiScores[l.kpi_line_id] ?? ""}
                        onChange={(e) => setKpiScores({ ...kpiScores, [l.kpi_line_id]: e.target.value })}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.competency_lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Competency Self Ratings (1–5)</h3>
                <div className="space-y-2">
                  {selected.competency_lines.map((l) => (
                    <div key={l.competency_line_id} className="grid grid-cols-3 gap-2 items-center">
                      <span className="text-sm text-gray-700 col-span-2">
                        {l.competency_name}
                        <span className="text-gray-400 text-xs ml-1">(weight: {l.weight_pct}%)</span>
                      </span>
                      <select
                        className="border rounded px-2 py-1 text-sm"
                        value={compRatings[l.competency_line_id] ?? ""}
                        onChange={(e) => setCompRatings({ ...compRatings, [l.competency_line_id]: e.target.value })}
                      >
                        <option value="">Select…</option>
                        {[1,2,3,4,5].map(v => <option key={v} value={v}>{v} — {["Unsatisfactory","Below Expectations","Meets Expectations","Exceeds Expectations","Outstanding"][v-1]}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <div>
                <label className="text-xs text-gray-500">Overall Self Score (optional — auto-calculated if blank)</label>
                <input
                  type="number" min={0} max={100}
                  className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={selfScore}
                  onChange={(e) => setSelfScore(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Notes / Comments</label>
                <textarea
                  className="w-full border rounded px-2 py-1 text-sm mt-1"
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={submit}
                disabled={saving}
                className="rounded bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {saving ? "Submitting…" : "Submit to Manager"}
              </button>
              <button onClick={() => setSelected(null)} className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
