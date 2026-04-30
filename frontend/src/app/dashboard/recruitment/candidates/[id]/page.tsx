"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  recruitmentApi, Candidate, CandidatePipeline, Interview, Offer,
  PIPELINE_STATUS_COLOR, OFFER_STATUS_COLOR, INTERVIEW_DECISION_COLOR, fmtCurrency,
} from "@/lib/recruitment";

type Tab = "profile" | "pipeline" | "interviews" | "offers";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [cand, setCand] = useState<Candidate | null>(null);
  const [pipeline, setPipeline] = useState<CandidatePipeline[]>([]);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [tab, setTab] = useState<Tab>("profile");

  useEffect(() => {
    Promise.all([
      recruitmentApi.getCandidate(id),
      recruitmentApi.listPipeline({ requisition_id: undefined }),
      recruitmentApi.listInterviews({ candidate_id: id }),
      recruitmentApi.listOffers({}),
    ]).then(([c, _pl, iv, of]) => {
      setCand(c);
      setInterviews(iv.filter((i) => i.candidate_id === id));
      setOffers(of.filter((o) => o.candidate_id === id));
    });
    recruitmentApi.listPipeline({}).then((pl) => setPipeline(pl.filter((p) => p.candidate_id === id)));
  }, [id]);

  if (!cand) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold">{cand.full_name}</h1>
          <p className="text-sm text-gray-500">{cand.email} · {cand.phone} · {cand.candidate_code}</p>
        </div>
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{cand.source}</span>
      </div>

      <div className="flex gap-2 border-b">
        {(["profile", "pipeline", "interviews", "offers"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 px-3 text-sm font-medium border-b-2 -mb-px capitalize ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500"}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="bg-white border rounded-xl p-5 grid grid-cols-2 gap-3 text-sm">
          <div><p className="text-xs text-gray-400">Current Employer</p><p>{cand.current_employer || "—"}</p></div>
          <div><p className="text-xs text-gray-400">Current Title</p><p>{cand.current_title || "—"}</p></div>
          <div><p className="text-xs text-gray-400">Experience</p><p>{cand.years_experience ? `${cand.years_experience} years` : "—"}</p></div>
          <div><p className="text-xs text-gray-400">Education</p><p>{cand.education_level || "—"}</p></div>
          <div><p className="text-xs text-gray-400">Location</p><p>{cand.location || "—"}</p></div>
          <div>
            <p className="text-xs text-gray-400">CV / Resume</p>
            {cand.cv_attachment ? <a href={cand.cv_attachment} target="_blank" className="text-blue-600 hover:underline text-xs">View</a> : <p>—</p>}
          </div>
          <div className="col-span-2"><p className="text-xs text-gray-400">Skills</p><p>{cand.skills_tags || "—"}</p></div>
          {cand.notes && <div className="col-span-2"><p className="text-xs text-gray-400">Notes</p><p>{cand.notes}</p></div>}
        </div>
      )}

      {tab === "pipeline" && (
        <div className="space-y-2">
          {pipeline.map((p) => (
            <div key={p.pipeline_id} className="bg-white border rounded-lg p-4 flex items-center justify-between text-sm">
              <div>
                <p className="font-medium text-xs font-mono">{p.requisition_id.slice(-8)}</p>
                <p className="text-xs text-gray-500">Applied: {p.application_date || "—"}</p>
              </div>
              <div className="text-right">
                <span className={`text-xs px-2 py-0.5 rounded-full ${PIPELINE_STATUS_COLOR[p.status]}`}>{p.status}</span>
                {p.overall_score && <p className="text-xs mt-1 text-gray-500">Score: {p.overall_score}</p>}
              </div>
            </div>
          ))}
          {pipeline.length === 0 && <p className="text-sm text-gray-400">No pipeline records</p>}
        </div>
      )}

      {tab === "interviews" && (
        <div className="space-y-2">
          {interviews.map((iv) => (
            <div key={iv.interview_id} className="bg-white border rounded-lg p-4 text-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-medium">{new Date(iv.interview_date).toLocaleString()}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${INTERVIEW_DECISION_COLOR[iv.decision]}`}>{iv.decision}</span>
              </div>
              <p className="text-xs text-gray-500 capitalize">{iv.interview_type} · {iv.location_or_link || "—"}</p>
              {iv.feedback && <p className="text-xs text-gray-600 mt-1">{iv.feedback}</p>}
              {iv.score != null && <p className="text-xs">Score: {iv.score}/100 · Tech: {iv.technical_score ?? "—"} · Culture: {iv.cultural_score ?? "—"}</p>}
            </div>
          ))}
          {interviews.length === 0 && <p className="text-sm text-gray-400">No interviews scheduled</p>}
        </div>
      )}

      {tab === "offers" && (
        <div className="space-y-2">
          {offers.map((o) => (
            <div key={o.offer_id} className="bg-white border rounded-lg p-4 text-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs">{o.offer_code}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${OFFER_STATUS_COLOR[o.status]}`}>{o.status}</span>
              </div>
              <p className="text-lg font-bold">{fmtCurrency(o.salary_offer, o.currency)}</p>
              <p className="text-xs text-gray-500">Joining: {o.joining_date || "—"} · Expires: {o.expiry_date || "—"}</p>
              {o.rejection_reason && <p className="text-xs text-red-600">{o.rejection_reason}</p>}
            </div>
          ))}
          {offers.length === 0 && <p className="text-sm text-gray-400">No offers</p>}
        </div>
      )}
    </div>
  );
}
