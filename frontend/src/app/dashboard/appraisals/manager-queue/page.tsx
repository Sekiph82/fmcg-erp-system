"use client";
import { useEffect, useState } from "react";
import { appraisalsApi, AppraisalRecord } from "@/lib/appraisals";

export default function ManagerQueuePage() {
  const [records, setRecords] = useState<AppraisalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AppraisalRecord | null>(null);
  const [managerScore, setManagerScore] = useState("");
  const [increment, setIncrement] = useState("");
  const [promotion, setPromotion] = useState(false);
  const [notes, setNotes] = useState("");
  const [kpiMgrScores, setKpiMgrScores] = useState<Record<string, string>>({});
  const [compMgrRatings, setCompMgrRatings] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const load = () =>
    appraisalsApi.listRecords({ status: "manager_review" })
      .then(setRecords).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const openRecord = (r: AppraisalRecord) => {
    setSelected(r);
    const ks: Record<string,string> = {};
    r.kpi_lines.forEach(l => { ks[l.kpi_line_id] = String(l.manager_score ?? ""); });
    setKpiMgrScores(ks);
    const cs: Record<string,string> = {};
    r.competency_lines.forEach(l => { cs[l.competency_line_id] = String(l.manager_rating ?? ""); });
    setCompMgrRatings(cs);
    setManagerScore("");
    setIncrement("");
    setPromotion(false);
    setNotes("");
  };

  const submit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      for (const [id, score] of Object.entries(kpiMgrScores)) {
        if (score) await appraisalsApi.updateKPILine(id, { manager_score: Number(score) });
      }
      for (const [id, rating] of Object.entries(compMgrRatings)) {
        if (rating) await appraisalsApi.updateCompetencyLine(id, { manager_rating: Number(rating) });
      }
      await appraisalsApi.calculateScores(selected.appraisal_id);
      await appraisalsApi.managerReview(selected.appraisal_id, {
        manager_score: managerScore ? Number(managerScore) : undefined,
        increment_recommendation: increment ? Number(increment) : undefined,
        promotion_recommendation: promotion,
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
      <h1 className="text-xl font-bold text-gray-900">Manager Review Queue</h1>
      <p className="text-sm text-gray-500">
        Appraisals awaiting manager review. Enter scores, recommendations, and submit to HR.
      </p>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="grid gap-3">
          {records.map((r) => (
            <div key={r.appraisal_id} className="bg-white border rounded-lg p-4 shadow-sm flex justify-between items-center">
              <div>
                <p className="font-semibold text-gray-800">{r.employee_name ?? r.employee_id}</p>
                <p className="text-sm text-gray-500">{r.department_name ?? "—"}</p>
                <p className="text-xs text-gray-400">Self Score: {r.self_score ?? "—"} · Submitted: {r.self_submitted_at ? new Date(r.self_submitted_at).toLocaleDateString() : "—"}</p>
              </div>
              <button onClick={() => openRecord(r)} className="rounded bg-orange-600 px-4 py-1.5 text-sm text-white hover:bg-orange-700">
                Review
              </button>
            </div>
          ))}
          {records.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No appraisals pending manager review.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6 space-y-4 my-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">Manager Review — {selected.employee_name ?? selected.employee_id}</h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm bg-gray-50 rounded p-3">
              <div><span className="text-gray-500">Self Score:</span> <strong>{selected.self_score ?? "—"}</strong></div>
              <div><span className="text-gray-500">KPI Lines:</span> {selected.kpi_lines.length}</div>
              {selected.notes && <div className="col-span-2 text-gray-600">{selected.notes}</div>}
            </div>

            {selected.kpi_lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">KPI Manager Scores (0–100)</h3>
                <div className="space-y-2">
                  {selected.kpi_lines.map((l) => (
                    <div key={l.kpi_line_id} className="grid grid-cols-3 gap-2 items-center">
                      <span className="text-sm text-gray-700 col-span-2">
                        {l.kpi_name} <span className="text-gray-400 text-xs">(Self: {l.self_score ?? "—"})</span>
                      </span>
                      <input
                        type="number" min={0} max={100}
                        className="border rounded px-2 py-1 text-sm"
                        value={kpiMgrScores[l.kpi_line_id] ?? ""}
                        onChange={(e) => setKpiMgrScores({ ...kpiMgrScores, [l.kpi_line_id]: e.target.value })}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.competency_lines.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Competency Manager Ratings (1–5)</h3>
                <div className="space-y-2">
                  {selected.competency_lines.map((l) => (
                    <div key={l.competency_line_id} className="grid grid-cols-3 gap-2 items-center">
                      <span className="text-sm text-gray-700 col-span-2">
                        {l.competency_name} <span className="text-gray-400 text-xs">(Self: {l.self_rating ?? "—"})</span>
                      </span>
                      <select
                        className="border rounded px-2 py-1 text-sm"
                        value={compMgrRatings[l.competency_line_id] ?? ""}
                        onChange={(e) => setCompMgrRatings({ ...compMgrRatings, [l.competency_line_id]: e.target.value })}
                      >
                        <option value="">Select…</option>
                        {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Manager Score (optional override)</label>
                <input type="number" min={0} max={100} className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={managerScore} onChange={(e) => setManagerScore(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Increment Recommendation %</label>
                <input type="number" min={0} max={100} className="w-full border rounded px-2 py-1 text-sm mt-1"
                  value={increment} onChange={(e) => setIncrement(e.target.value)} />
              </div>
              <div className="flex items-center gap-2 col-span-2">
                <input type="checkbox" checked={promotion} onChange={(e) => setPromotion(e.target.checked)} />
                <label className="text-sm text-gray-700">Recommend for promotion</label>
              </div>
              <div className="col-span-2">
                <label className="text-xs text-gray-500">Manager Notes</label>
                <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={3}
                  value={notes} onChange={(e) => setNotes(e.target.value)} />
              </div>
            </div>

            <div className="flex gap-2">
              <button onClick={submit} disabled={saving}
                className="rounded bg-orange-600 px-6 py-2 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50">
                {saving ? "Submitting…" : "Submit to HR"}
              </button>
              <button onClick={() => setSelected(null)} className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
