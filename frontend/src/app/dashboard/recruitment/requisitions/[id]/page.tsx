"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  recruitmentApi, JobRequisition, JobPosting, CandidatePipeline,
  REQ_STATUS_LABEL, REQ_STATUS_COLOR, PIPELINE_STATUS_COLOR, fmtCurrency,
} from "@/lib/recruitment";

type Tab = "overview" | "postings" | "pipeline";

export default function RequisitionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [req, setReq] = useState<JobRequisition | null>(null);
  const [postings, setPostings] = useState<JobPosting[]>([]);
  const [pipeline, setPipeline] = useState<CandidatePipeline[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [r, ps, pl] = await Promise.all([
      recruitmentApi.getRequisition(id),
      recruitmentApi.listPostings(id),
      recruitmentApi.listPipeline({ requisition_id: id }),
    ]);
    setReq(r); setPostings(ps); setPipeline(pl);
  };
  useEffect(() => { load(); }, [id]);

  const act = async (fn: () => Promise<any>) => {
    try { await fn(); await load(); setMsg("Done"); setTimeout(() => setMsg(""), 2000); }
    catch (e: any) { setMsg(e.message); }
  };

  if (!req) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold">{req.job_title}</h1>
          <p className="text-sm text-gray-500">{req.requisition_code} · {req.location} · {req.employment_type.replace("_", " ")}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${REQ_STATUS_COLOR[req.status]}`}>
          {REQ_STATUS_LABEL[req.status]}
        </span>
      </div>

      {msg && <div className="bg-blue-50 text-blue-700 text-sm px-4 py-2 rounded">{msg}</div>}

      <div className="flex gap-2">
        {req.status === "draft" && (
          <button onClick={() => act(() => recruitmentApi.approveRequisition(id, { approver_id: "00000000-0000-0000-0000-000000000001" }))}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded hover:bg-blue-700">Approve</button>
        )}
        {req.status === "approved" && (
          <button onClick={() => act(() => recruitmentApi.openRequisition(id))}
            className="bg-green-600 text-white text-sm px-4 py-2 rounded hover:bg-green-700">Open for Applications</button>
        )}
        {req.status === "open" && (
          <button onClick={() => act(() => recruitmentApi.closeRequisition(id))}
            className="bg-gray-500 text-white text-sm px-4 py-2 rounded hover:bg-gray-600">Close</button>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-white border rounded-xl p-3 text-center">
          <p className="text-xs text-gray-500">Headcount</p>
          <p className="text-xl font-bold">{req.filled_count}/{req.headcount}</p>
        </div>
        <div className="bg-white border rounded-xl p-3 text-center">
          <p className="text-xs text-gray-500">Postings</p>
          <p className="text-xl font-bold">{postings.length}</p>
        </div>
        <div className="bg-white border rounded-xl p-3 text-center">
          <p className="text-xs text-gray-500">Pipeline</p>
          <p className="text-xl font-bold">{pipeline.length}</p>
        </div>
        <div className="bg-white border rounded-xl p-3 text-center">
          <p className="text-xs text-gray-500">Salary Range</p>
          <p className="text-sm font-semibold">
            {req.salary_min ? `${fmtCurrency(req.salary_min)} – ${fmtCurrency(req.salary_max ?? 0)}` : "—"}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {(["overview", "postings", "pipeline"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 px-3 text-sm font-medium border-b-2 -mb-px capitalize ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500"}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="bg-white border rounded-xl p-5 space-y-3 text-sm">
          {req.job_description && <div><p className="text-xs text-gray-500 mb-1">Job Description</p><p className="whitespace-pre-wrap">{req.job_description}</p></div>}
          {req.requirements && <div><p className="text-xs text-gray-500 mb-1">Requirements</p><p className="whitespace-pre-wrap">{req.requirements}</p></div>}
          {req.notes && <div><p className="text-xs text-gray-500 mb-1">Notes</p><p>{req.notes}</p></div>}
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 pt-2">
            <p>Opening: {req.opening_date || "—"}</p>
            <p>Closing: {req.closing_date || "—"}</p>
          </div>
        </div>
      )}

      {tab === "postings" && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button onClick={() => act(() => recruitmentApi.createPosting({ requisition_id: id, posting_channel: "website" }))}
              className="bg-blue-600 text-white text-sm px-4 py-2 rounded hover:bg-blue-700">+ Add Posting</button>
          </div>
          <div className="bg-white border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left">Channel</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Publish Date</th>
                  <th className="px-4 py-2 text-left">Expiry</th>
                  <th className="px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {postings.map((p) => (
                  <tr key={p.posting_id}>
                    <td className="px-4 py-2 capitalize">{p.posting_channel}</td>
                    <td className="px-4 py-2 capitalize">{p.status}</td>
                    <td className="px-4 py-2">{p.publish_date || "—"}</td>
                    <td className="px-4 py-2">{p.expiry_date || "—"}</td>
                    <td className="px-4 py-2">
                      {p.status === "draft" && (
                        <button onClick={() => act(() => recruitmentApi.publishPosting(p.posting_id))}
                          className="text-xs text-green-600 hover:underline">Publish</button>
                      )}
                    </td>
                  </tr>
                ))}
                {postings.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No postings</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "pipeline" && (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">Pipeline ID</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Applied</th>
                <th className="px-4 py-2 text-left">Score</th>
                <th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {pipeline.map((p) => (
                <tr key={p.pipeline_id}>
                  <td className="px-4 py-2 font-mono text-xs">{p.pipeline_id.slice(-8)}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${PIPELINE_STATUS_COLOR[p.status]}`}>{p.status}</span>
                  </td>
                  <td className="px-4 py-2">{p.application_date || "—"}</td>
                  <td className="px-4 py-2">{p.overall_score ?? "—"}</td>
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/recruitment/pipeline?requisition_id=${id}`}
                      className="text-xs text-blue-600 hover:underline">View Board</Link>
                  </td>
                </tr>
              ))}
              {pipeline.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No candidates</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
