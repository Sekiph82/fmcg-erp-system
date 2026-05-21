"use client";
import { useEffect, useState } from "react";
import {
  appraisalsApi, AppraisalRecord, FinalRating,
  APPRAISAL_STATUS_COLOR, APPRAISAL_STATUS_LABEL, RATING_COLOR, RATING_LABEL,
} from "@/lib/appraisals";

const RATINGS: FinalRating[] = ["excellent","good","meets_expectations","improvement_needed"];

export default function HRReviewPage() {
  const [hrRecords, setHrRecords] = useState<AppraisalRecord[]>([]);
  const [calRecords, setCalRecords] = useState<AppraisalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"hr_review" | "calibration">("hr_review");
  const [selected, setSelected] = useState<AppraisalRecord | null>(null);
  const [finalScore, setFinalScore] = useState("");
  const [finalRating, setFinalRating] = useState<FinalRating | "">("");
  const [hrNotes, setHrNotes] = useState("");
  const [calNotes, setCalNotes] = useState("");
  const [increment, setIncrement] = useState("");
  const [promotion, setPromotion] = useState(false);
  const [saving, setSaving] = useState(false);
  const [action, setAction] = useState<"hr_review" | "finalize" | "reject">("hr_review");

  const load = () =>
    Promise.all([
      appraisalsApi.listRecords({ status: "hr_review" }),
      appraisalsApi.listRecords({ status: "calibration" }),
    ]).then(([hr, cal]) => { setHrRecords(hr); setCalRecords(cal); }).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const records = tab === "hr_review" ? hrRecords : calRecords;

  const openRecord = (r: AppraisalRecord, act: "hr_review" | "finalize") => {
    setSelected(r);
    setAction(act);
    setFinalScore(String(r.final_score ?? ""));
    setFinalRating(r.final_rating ?? "");
    setHrNotes(r.hr_notes ?? "");
    setCalNotes(r.calibration_notes ?? "");
    setIncrement(String(r.increment_recommendation ?? ""));
    setPromotion(r.promotion_recommendation);
  };

  const submit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      if (action === "hr_review") {
        await appraisalsApi.hrReview(selected.appraisal_id, {
          final_score: finalScore ? Number(finalScore) : undefined,
          final_rating: finalRating || undefined,
          hr_notes: hrNotes || undefined,
          calibration_notes: calNotes || undefined,
        });
      } else if (action === "finalize") {
        await appraisalsApi.finalize(selected.appraisal_id, {
          final_score: finalScore ? Number(finalScore) : undefined,
          final_rating: finalRating || undefined,
          increment_recommendation: increment ? Number(increment) : undefined,
          promotion_recommendation: promotion,
          hr_notes: hrNotes || undefined,
        });
      } else {
        await appraisalsApi.reject(selected.appraisal_id, hrNotes || undefined);
      }
      setSelected(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">HR Review & Calibration</h1>

      <div className="flex gap-2">
        <button
          onClick={() => setTab("hr_review")}
          className={`px-4 py-2 text-sm rounded font-medium ${tab === "hr_review" ? "bg-purple-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
        >
          HR Review ({hrRecords.length})
        </button>
        <button
          onClick={() => setTab("calibration")}
          className={`px-4 py-2 text-sm rounded font-medium ${tab === "calibration" ? "bg-indigo-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
        >
          Calibration ({calRecords.length})
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Employee","Dept","Self","Manager","Final","Rating","Promo","Actions"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {records.map((r) => (
                <tr key={r.appraisal_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{r.employee_name ?? r.employee_id}</td>
                  <td className="px-4 py-2 text-gray-600">{r.department_name ?? "—"}</td>
                  <td className="px-4 py-2 text-center">{r.self_score ?? "—"}</td>
                  <td className="px-4 py-2 text-center">{r.manager_score ?? "—"}</td>
                  <td className="px-4 py-2 text-center font-semibold">{r.final_score ?? "—"}</td>
                  <td className="px-4 py-2">
                    {r.final_rating ? (
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${RATING_COLOR[r.final_rating]}`}>
                        {r.final_rating.replace(/_/g," ")}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-2 text-center">{r.promotion_recommendation ? "✓" : "—"}</td>
                  <td className="px-4 py-2 flex gap-2">
                    {tab === "hr_review" && (
                      <button onClick={() => openRecord(r, "hr_review")}
                        className="text-xs text-purple-600 hover:underline">Review</button>
                    )}
                    {tab === "calibration" && (
                      <button onClick={() => openRecord(r, "finalize")}
                        className="text-xs text-green-600 hover:underline">Finalize</button>
                    )}
                    <button onClick={() => { setSelected(r); setAction("reject"); setHrNotes(""); }}
                      className="text-xs text-red-500 hover:underline">Reject</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {records.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No records in this stage.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 space-y-4 my-4">
            <div className="flex justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                {action === "reject" ? "Reject Appraisal" : action === "finalize" ? "Finalize Appraisal" : "HR Review"} — {selected.employee_name ?? selected.employee_id}
              </h2>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>

            {action !== "reject" && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500">Final Score (0–100)</label>
                  <input type="number" min={0} max={100} className="w-full border rounded px-2 py-1 text-sm mt-1"
                    value={finalScore} onChange={(e) => setFinalScore(e.target.value)} />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Final Rating</label>
                  <select className="w-full border rounded px-2 py-1 text-sm mt-1"
                    value={finalRating} onChange={(e) => setFinalRating(e.target.value as FinalRating)}>
                    <option value="">Auto from score</option>
                    {RATINGS.map(r => <option key={r} value={r}>{RATING_LABEL[r]}</option>)}
                  </select>
                </div>
                {action === "finalize" && (
                  <>
                    <div>
                      <label className="text-xs text-gray-500">Increment % Recommendation</label>
                      <input type="number" className="w-full border rounded px-2 py-1 text-sm mt-1"
                        value={increment} onChange={(e) => setIncrement(e.target.value)} />
                    </div>
                    <div className="flex items-center gap-2 mt-4">
                      <input type="checkbox" checked={promotion} onChange={(e) => setPromotion(e.target.checked)} />
                      <label className="text-sm text-gray-700">Recommend promotion</label>
                    </div>
                  </>
                )}
                {action === "hr_review" && (
                  <div className="col-span-2">
                    <label className="text-xs text-gray-500">Calibration Notes</label>
                    <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2}
                      value={calNotes} onChange={(e) => setCalNotes(e.target.value)} />
                  </div>
                )}
              </div>
            )}

            <div>
              <label className="text-xs text-gray-500">HR Notes {action === "reject" ? "(reason)" : ""}</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={3}
                value={hrNotes} onChange={(e) => setHrNotes(e.target.value)} />
            </div>

            <div className="flex gap-2">
              <button
                onClick={submit}
                disabled={saving}
                className={`rounded px-6 py-2 text-sm font-medium text-white disabled:opacity-50 ${action === "reject" ? "bg-red-600 hover:bg-red-700" : action === "finalize" ? "bg-green-600 hover:bg-green-700" : "bg-purple-600 hover:bg-purple-700"}`}
              >
                {saving ? "Saving…" : action === "reject" ? "Reject" : action === "finalize" ? "Finalize" : "Send to Calibration"}
              </button>
              <button onClick={() => setSelected(null)} className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
