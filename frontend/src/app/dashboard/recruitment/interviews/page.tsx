"use client";
import { useEffect, useState } from "react";
import {
  recruitmentApi, Interview, JobRequisition,
  INTERVIEW_DECISION_COLOR, InterviewDecision,
} from "@/lib/recruitment";

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [showSchedule, setShowSchedule] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState<string | null>(null);
  const [form, setForm] = useState({
    candidate_id: "", requisition_id: "", interview_date: "",
    interview_type: "onsite", location_or_link: "", notes: "",
  });
  const [feedback, setFeedback] = useState({
    feedback: "", score: "", technical_score: "", cultural_score: "", decision: "pending" as InterviewDecision,
  });
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [iv, r] = await Promise.all([recruitmentApi.listInterviews(), recruitmentApi.listRequisitions()]);
    setInterviews(iv); setReqs(r);
  };
  useEffect(() => { load(); }, []);

  const handleSchedule = async () => {
    await recruitmentApi.scheduleInterview({ ...form, interview_date: new Date(form.interview_date).toISOString() });
    await load(); setShowSchedule(false);
    setMsg("Interview scheduled"); setTimeout(() => setMsg(""), 2000);
  };

  const handleFeedback = async () => {
    if (!feedbackTarget) return;
    await recruitmentApi.recordFeedback(feedbackTarget, {
      ...feedback,
      score: feedback.score ? Number(feedback.score) : undefined,
      technical_score: feedback.technical_score ? Number(feedback.technical_score) : undefined,
      cultural_score: feedback.cultural_score ? Number(feedback.cultural_score) : undefined,
    });
    setFeedbackTarget(null);
    await load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Interviews</h1>
        <button onClick={() => setShowSchedule(!showSchedule)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          {showSchedule ? "Cancel" : "+ Schedule Interview"}
        </button>
      </div>

      {msg && <div className="bg-blue-50 text-blue-700 text-sm px-4 py-2 rounded">{msg}</div>}

      {showSchedule && (
        <div className="bg-white border rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Candidate ID</label>
              <input value={form.candidate_id} onChange={(e) => setForm({ ...form, candidate_id: e.target.value })}
                className="w-full border rounded p-2 text-sm" placeholder="UUID" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Requisition</label>
              <select value={form.requisition_id} onChange={(e) => setForm({ ...form, requisition_id: e.target.value })}
                className="w-full border rounded p-2 text-sm">
                <option value="">Select…</option>
                {reqs.map((r) => <option key={r.requisition_id} value={r.requisition_id}>{r.requisition_code} — {r.job_title}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date & Time</label>
              <input type="datetime-local" value={form.interview_date}
                onChange={(e) => setForm({ ...form, interview_date: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select value={form.interview_type} onChange={(e) => setForm({ ...form, interview_type: e.target.value })}
                className="w-full border rounded p-2 text-sm">
                {["onsite", "online", "phone", "panel"].map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Location / Link</label>
              <input value={form.location_or_link} onChange={(e) => setForm({ ...form, location_or_link: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <button onClick={handleSchedule} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Schedule
          </button>
        </div>
      )}

      {feedbackTarget && (
        <div className="bg-white border rounded-xl p-5 space-y-3 border-indigo-200">
          <h2 className="text-sm font-semibold">Record Feedback</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Overall Score (/100)</label>
              <input type="number" max={100} value={feedback.score}
                onChange={(e) => setFeedback({ ...feedback, score: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Technical Score</label>
              <input type="number" max={100} value={feedback.technical_score}
                onChange={(e) => setFeedback({ ...feedback, technical_score: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Cultural Score</label>
              <input type="number" max={100} value={feedback.cultural_score}
                onChange={(e) => setFeedback({ ...feedback, cultural_score: e.target.value })}
                className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Decision</label>
              <select value={feedback.decision}
                onChange={(e) => setFeedback({ ...feedback, decision: e.target.value as InterviewDecision })}
                className="w-full border rounded p-2 text-sm">
                {["pass", "fail", "hold", "pending"].map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Feedback Notes</label>
              <textarea value={feedback.feedback}
                onChange={(e) => setFeedback({ ...feedback, feedback: e.target.value })}
                rows={2} className="w-full border rounded p-2 text-sm" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleFeedback} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700">
              Save Feedback
            </button>
            <button onClick={() => setFeedbackTarget(null)} className="border px-4 py-2 rounded text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Candidate</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Location</th>
              <th className="px-4 py-3 text-right">Score</th>
              <th className="px-4 py-3 text-left">Decision</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {interviews.map((iv) => (
              <tr key={iv.interview_id} className="hover:bg-gray-50">
                <td className="px-4 py-3">{new Date(iv.interview_date).toLocaleString()}</td>
                <td className="px-4 py-3 font-mono text-xs">{iv.candidate_id.slice(-8)}</td>
                <td className="px-4 py-3 capitalize">{iv.interview_type}</td>
                <td className="px-4 py-3 text-gray-500 truncate max-w-[120px]">{iv.location_or_link || "—"}</td>
                <td className="px-4 py-3 text-right">{iv.score != null ? `${iv.score}/100` : "—"}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${INTERVIEW_DECISION_COLOR[iv.decision]}`}>
                    {iv.decision}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {iv.decision === "pending" && (
                    <button onClick={() => { setFeedbackTarget(iv.interview_id); setFeedback({ ...feedback, feedback: "" }); }}
                      className="text-xs text-indigo-600 hover:underline">Record Feedback</button>
                  )}
                </td>
              </tr>
            ))}
            {interviews.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No interviews</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
