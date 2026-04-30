"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { recruitmentApi, Candidate, CandidatePipeline, Interview, Offer, PIPELINE_STATUS_COLOR, OFFER_STATUS_COLOR, INTERVIEW_DECISION_COLOR, fmtCurrency } from "@/lib/recruitment";

type Tab = "profile" | "pipeline" | "interviews" | "offers";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [cand, setCand] = useState<Candidate | null>(null);
  const [pipeline, setPipeline] = useState<CandidatePipeline[]>([]);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [tab, setTab] = useState<Tab>("profile");

  useEffect(() => {
    Promise.all([recruitmentApi.getCandidate(id), recruitmentApi.listInterviews({ candidate_id: id }), recruitmentApi.listOffers({})]).then(([c, iv, of]) => {
      setCand(c); setInterviews(iv); setOffers(of.filter((o) => o.candidate_id === id));
    });
    recruitmentApi.listPipeline({}).then((pl) => setPipeline(pl.filter((p) => p.candidate_id === id)));
  }, [id]);

  if (!cand) return <div className="p-6 min-h-screen bg-[#060d18] text-slate-500">Loading…</div>;

  return (
    <div className="p-6 space-y-5 min-h-screen bg-[#060d18] text-slate-200 max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">{cand.full_name}</h1>
          <p className="text-slate-500 text-sm mt-0.5">{cand.email} · {cand.phone} · {cand.candidate_code}</p>
        </div>
        <span className="text-[10px] bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded-full">{cand.source}</span>
      </div>

      <div className="flex gap-1 border-b border-white/[0.07]">
        {(["profile", "pipeline", "interviews", "offers"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 px-4 text-sm font-medium border-b-2 -mb-px capitalize transition-colors ${tab === t ? "border-indigo-500 text-indigo-400" : "border-transparent text-slate-500 hover:text-slate-300"}`}>{t}</button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 grid grid-cols-2 gap-4 text-sm">
          {[["Current Employer", cand.current_employer], ["Current Title", cand.current_title], ["Experience", cand.years_experience ? `${cand.years_experience} years` : "—"], ["Education", cand.education_level], ["Location", cand.location], ["National ID", "—"]].map(([l, v]) => (
            <div key={l as string}><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-0.5">{l}</p><p className="text-slate-300">{v || "—"}</p></div>
          ))}
          {cand.cv_attachment && <div className="col-span-2"><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-0.5">CV</p><a href={cand.cv_attachment} target="_blank" className="text-indigo-400 hover:text-indigo-300 text-xs">View CV</a></div>}
          <div className="col-span-2"><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-0.5">Skills</p><p className="text-slate-400">{cand.skills_tags || "—"}</p></div>
          {cand.notes && <div className="col-span-2"><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-0.5">Notes</p><p className="text-slate-400">{cand.notes}</p></div>}
        </div>
      )}

      {tab === "pipeline" && (
        <div className="space-y-2">
          {pipeline.map((p) => (
            <div key={p.pipeline_id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 flex items-center justify-between text-sm">
              <div><p className="font-mono text-xs text-slate-500">{p.requisition_id.slice(-8)}</p><p className="text-xs text-slate-600">Applied: {p.application_date || "—"}</p></div>
              <div className="text-right">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PIPELINE_STATUS_COLOR[p.status]}`}>{p.status}</span>
                {p.overall_score && <p className="text-xs mt-1 text-slate-500">Score: {p.overall_score}</p>}
              </div>
            </div>
          ))}
          {pipeline.length === 0 && <p className="text-sm text-slate-600 text-center py-4">No pipeline records</p>}
        </div>
      )}

      {tab === "interviews" && (
        <div className="space-y-2">
          {interviews.map((iv) => (
            <div key={iv.interview_id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-white font-medium">{new Date(iv.interview_date).toLocaleString()}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${INTERVIEW_DECISION_COLOR[iv.decision]}`}>{iv.decision}</span>
              </div>
              <p className="text-xs text-slate-500 capitalize">{iv.interview_type} · {iv.location_or_link || "—"}</p>
              {iv.feedback && <p className="text-xs text-slate-400">{iv.feedback}</p>}
              {iv.score != null && <p className="text-xs text-slate-500">Score: {iv.score}/100 · Tech: {iv.technical_score ?? "—"} · Culture: {iv.cultural_score ?? "—"}</p>}
            </div>
          ))}
          {interviews.length === 0 && <p className="text-sm text-slate-600 text-center py-4">No interviews scheduled</p>}
        </div>
      )}

      {tab === "offers" && (
        <div className="space-y-2">
          {offers.map((o) => (
            <div key={o.offer_id} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-400">{o.offer_code}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${OFFER_STATUS_COLOR[o.status]}`}>{o.status}</span>
              </div>
              <p className="text-xl font-bold text-emerald-400">{fmtCurrency(o.salary_offer, o.currency)}</p>
              <p className="text-xs text-slate-500">Joining: {o.joining_date || "—"} · Expires: {o.expiry_date || "—"}</p>
              {o.rejection_reason && <p className="text-xs text-red-400">{o.rejection_reason}</p>}
            </div>
          ))}
          {offers.length === 0 && <p className="text-sm text-slate-600 text-center py-4">No offers</p>}
        </div>
      )}
    </div>
  );
}
