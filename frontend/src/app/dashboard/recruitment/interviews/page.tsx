"use client";
import { useEffect, useState } from "react";
import { recruitmentApi, Interview, JobRequisition, INTERVIEW_DECISION_COLOR, InterviewDecision } from "@/lib/recruitment";

const inputCls = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500";
const selectCls = "w-full bg-[#0d1829] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white focus:outline-none";
const labelCls = "block text-[10px] text-slate-400 mb-1";

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [showSchedule, setShowSchedule] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState<string | null>(null);
  const [form, setForm] = useState({ candidate_id: "", requisition_id: "", interview_date: "", interview_type: "onsite", location_or_link: "", notes: "" });
  const [feedback, setFeedback] = useState({ feedback: "", score: "", technical_score: "", cultural_score: "", decision: "pending" as InterviewDecision });
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
    await recruitmentApi.recordFeedback(feedbackTarget, { ...feedback, score: feedback.score ? Number(feedback.score) : undefined, technical_score: feedback.technical_score ? Number(feedback.technical_score) : undefined, cultural_score: feedback.cultural_score ? Number(feedback.cultural_score) : undefined });
    setFeedbackTarget(null); await load();
  };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Interviews</h1>
          <p className="text-slate-500 text-sm mt-0.5">{interviews.length} scheduled</p>
        </div>
        <button onClick={() => setShowSchedule(!showSchedule)}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">
          {showSchedule ? "Cancel" : "+ Schedule Interview"}
        </button>
      </div>

      {msg && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-300">{msg}</div>}

      {showSchedule && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Schedule Interview</h2>
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Candidate ID</label><input value={form.candidate_id} onChange={(e) => setForm({ ...form, candidate_id: e.target.value })} placeholder="UUID" className={inputCls} /></div>
            <div><label className={labelCls}>Requisition</label>
              <select value={form.requisition_id} onChange={(e) => setForm({ ...form, requisition_id: e.target.value })} className={selectCls}>
                <option value="">Select…</option>
                {reqs.map((r) => <option key={r.requisition_id} value={r.requisition_id}>{r.requisition_code} — {r.job_title}</option>)}
              </select>
            </div>
            <div><label className={labelCls}>Date & Time</label><input type="datetime-local" value={form.interview_date} onChange={(e) => setForm({ ...form, interview_date: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Type</label>
              <select value={form.interview_type} onChange={(e) => setForm({ ...form, interview_type: e.target.value })} className={selectCls}>
                {["onsite", "online", "phone", "panel"].map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="col-span-2"><label className={labelCls}>Location / Link</label><input value={form.location_or_link} onChange={(e) => setForm({ ...form, location_or_link: e.target.value })} className={inputCls} /></div>
          </div>
          <button onClick={handleSchedule} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Schedule</button>
        </div>
      )}

      {feedbackTarget && (
        <div className="rounded-xl border border-indigo-500/20 bg-[#0d1829] p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white">Record Feedback</h2>
          <div className="grid grid-cols-3 gap-3">
            <div><label className={labelCls}>Overall Score (/100)</label><input type="number" max={100} value={feedback.score} onChange={(e) => setFeedback({ ...feedback, score: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Technical Score</label><input type="number" max={100} value={feedback.technical_score} onChange={(e) => setFeedback({ ...feedback, technical_score: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Cultural Score</label><input type="number" max={100} value={feedback.cultural_score} onChange={(e) => setFeedback({ ...feedback, cultural_score: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Decision</label>
              <select value={feedback.decision} onChange={(e) => setFeedback({ ...feedback, decision: e.target.value as InterviewDecision })} className={selectCls}>
                {["pass", "fail", "hold", "pending"].map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div className="col-span-2"><label className={labelCls}>Feedback Notes</label><textarea value={feedback.feedback} onChange={(e) => setFeedback({ ...feedback, feedback: e.target.value })} rows={2} className={inputCls} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleFeedback} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm">Save Feedback</button>
            <button onClick={() => setFeedbackTarget(null)} className="px-4 py-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Date", "Candidate", "Type", "Location", "Score", "Decision", "Actions"].map((h) => (
              <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Score" ? "text-right" : "text-left"}`}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {interviews.map((iv) => (
              <tr key={iv.interview_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 text-slate-400">{new Date(iv.interview_date).toLocaleString()}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{iv.candidate_id.slice(-8)}</td>
                <td className="px-4 py-3 text-slate-400 capitalize">{iv.interview_type}</td>
                <td className="px-4 py-3 text-slate-500 truncate max-w-[120px]">{iv.location_or_link || "—"}</td>
                <td className="px-4 py-3 text-right text-white">{iv.score != null ? `${iv.score}/100` : "—"}</td>
                <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${INTERVIEW_DECISION_COLOR[iv.decision]}`}>{iv.decision}</span></td>
                <td className="px-4 py-3">
                  {iv.decision === "pending" && (
                    <button onClick={() => { setFeedbackTarget(iv.interview_id); setFeedback({ ...feedback, feedback: "" }); }}
                      className="text-xs text-indigo-400 hover:text-indigo-300">Record Feedback</button>
                  )}
                </td>
              </tr>
            ))}
            {interviews.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No interviews</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
