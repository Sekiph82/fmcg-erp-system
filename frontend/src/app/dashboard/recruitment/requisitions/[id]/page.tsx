"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { recruitmentApi, JobRequisition, JobPosting, CandidatePipeline, REQ_STATUS_LABEL, REQ_STATUS_COLOR, PIPELINE_STATUS_COLOR, fmtCurrency } from "@/lib/recruitment";

type Tab = "overview" | "postings" | "pipeline";

export default function RequisitionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [req, setReq] = useState<JobRequisition | null>(null);
  const [postings, setPostings] = useState<JobPosting[]>([]);
  const [pipeline, setPipeline] = useState<CandidatePipeline[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [r, ps, pl] = await Promise.all([recruitmentApi.getRequisition(id), recruitmentApi.listPostings(id), recruitmentApi.listPipeline({ requisition_id: id })]);
    setReq(r); setPostings(ps); setPipeline(pl);
  };
  useEffect(() => { load(); }, [id]);

  const act = async (fn: () => Promise<any>) => {
    try { await fn(); await load(); setMsg("Done"); setTimeout(() => setMsg(""), 2000); }
    catch (e: any) { setMsg(e.message); }
  };

  if (!req) return <div className="p-6 text-slate-500">Loading…</div>;

  return (
    <div className="p-6 space-y-5 text-slate-200 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">{req.job_title}</h1>
          <p className="text-slate-500 text-sm mt-0.5">{req.requisition_code} · {req.location} · {req.employment_type.replace("_", " ")}</p>
        </div>
        <span className={`text-[10px] px-2.5 py-1 rounded-full font-medium ${REQ_STATUS_COLOR[req.status]}`}>{REQ_STATUS_LABEL[req.status]}</span>
      </div>

      {msg && <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-3 text-sm text-indigo-300">{msg}</div>}

      <div className="flex gap-2">
        {req.status === "draft" && <button onClick={() => act(() => recruitmentApi.approveRequisition(id, { approver_id: "00000000-0000-0000-0000-000000000001" }))} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">Approve</button>}
        {req.status === "approved" && <button onClick={() => act(() => recruitmentApi.openRequisition(id))} className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm">Open for Applications</button>}
        {req.status === "open" && <button onClick={() => act(() => recruitmentApi.closeRequisition(id))} className="px-4 py-2 rounded-lg bg-slate-600 hover:bg-slate-500 text-white text-sm">Close</button>}
      </div>

      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Headcount", value: `${req.filled_count}/${req.headcount}`, color: "text-white" },
          { label: "Postings", value: postings.length, color: "text-blue-400" },
          { label: "Pipeline", value: pipeline.length, color: "text-purple-400" },
          { label: "Salary Range", value: req.salary_min ? `${fmtCurrency(req.salary_min)} – ${fmtCurrency(req.salary_max ?? 0)}` : "—", color: "text-emerald-400" },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{k.label}</p>
            <p className={`text-lg font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-1 border-b border-white/[0.07]">
        {(["overview", "postings", "pipeline"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 px-4 text-sm font-medium border-b-2 -mb-px capitalize transition-colors ${tab === t ? "border-indigo-500 text-indigo-400" : "border-transparent text-slate-500 hover:text-slate-300"}`}>{t}</button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] p-5 space-y-4 text-sm">
          {req.job_description && <div><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Job Description</p><p className="text-slate-300 whitespace-pre-wrap">{req.job_description}</p></div>}
          {req.requirements && <div><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Requirements</p><p className="text-slate-300 whitespace-pre-wrap">{req.requirements}</p></div>}
          {req.notes && <div><p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Notes</p><p className="text-slate-400">{req.notes}</p></div>}
          <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 pt-2">
            <p>Opening: {req.opening_date || "—"}</p>
            <p>Closing: {req.closing_date || "—"}</p>
          </div>
        </div>
      )}

      {tab === "postings" && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button onClick={() => act(() => recruitmentApi.createPosting({ requisition_id: id, posting_channel: "website" }))}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">+ Add Posting</button>
          </div>
          <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/[0.07]">
                {["Channel", "Status", "Publish Date", "Expiry", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-2 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {postings.map((p) => (
                  <tr key={p.posting_id} className="border-b border-white/[0.05]">
                    <td className="px-4 py-2 text-slate-300 capitalize">{p.posting_channel}</td>
                    <td className="px-4 py-2 text-slate-400 capitalize">{p.status}</td>
                    <td className="px-4 py-2 text-slate-400">{p.publish_date || "—"}</td>
                    <td className="px-4 py-2 text-slate-400">{p.expiry_date || "—"}</td>
                    <td className="px-4 py-2">
                      {p.status === "draft" && <button onClick={() => act(() => recruitmentApi.publishPosting(p.posting_id))} className="text-xs text-emerald-400 hover:text-emerald-300">Publish</button>}
                    </td>
                  </tr>
                ))}
                {postings.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-600">No postings</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "pipeline" && (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-white/[0.07]">
              {["Pipeline ID", "Status", "Applied", "Score", "Actions"].map((h) => (
                <th key={h} className="px-4 py-2 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {pipeline.map((p) => (
                <tr key={p.pipeline_id} className="border-b border-white/[0.05]">
                  <td className="px-4 py-2 font-mono text-xs text-slate-500">{p.pipeline_id.slice(-8)}</td>
                  <td className="px-4 py-2"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${PIPELINE_STATUS_COLOR[p.status]}`}>{p.status}</span></td>
                  <td className="px-4 py-2 text-slate-400">{p.application_date || "—"}</td>
                  <td className="px-4 py-2 text-slate-400">{p.overall_score ?? "—"}</td>
                  <td className="px-4 py-2"><Link href={`/dashboard/recruitment/pipeline?requisition_id=${id}`} className="text-xs text-indigo-400 hover:text-indigo-300">Board</Link></td>
                </tr>
              ))}
              {pipeline.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-600">No candidates</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
