"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { recruitmentApi, JobRequisition, RequisitionStatus, REQ_STATUS_LABEL, REQ_STATUS_COLOR } from "@/lib/recruitment";

const STATUSES: RequisitionStatus[] = ["draft", "approved", "open", "closed", "cancelled"];

export default function RequisitionsPage() {
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [filter, setFilter] = useState<RequisitionStatus | "">("");

  const load = async () => {
    const data = await recruitmentApi.listRequisitions(filter ? { status: filter as RequisitionStatus } : undefined);
    setReqs(data);
  };
  useEffect(() => { load(); }, [filter]);

  const handleApprove = async (id: string) => { await recruitmentApi.approveRequisition(id, { approver_id: "00000000-0000-0000-0000-000000000001" }); load(); };
  const handleOpen = async (id: string) => { await recruitmentApi.openRequisition(id); load(); };
  const handleClose = async (id: string) => { await recruitmentApi.closeRequisition(id); load(); };

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Job Requisitions</h1>
          <p className="text-slate-500 text-sm mt-0.5">{reqs.length} requisitions</p>
        </div>
        <Link href="/dashboard/recruitment/requisitions/new"
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium">+ New</Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilter("")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${filter === "" ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>All</button>
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${filter === s ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {REQ_STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/[0.07]">
            {["Code", "Title", "Type", "Headcount", "Status", "Closing", "Actions"].map((h) => (
              <th key={h} className="px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest text-left">{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {reqs.map((r) => (
              <tr key={r.requisition_id} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link href={`/dashboard/recruitment/requisitions/${r.requisition_id}`} className="text-indigo-400 hover:text-indigo-300">{r.requisition_code}</Link>
                </td>
                <td className="px-4 py-3 text-white font-medium">{r.job_title}</td>
                <td className="px-4 py-3 text-slate-400 text-xs capitalize">{r.employment_type.replace("_", " ")}</td>
                <td className="px-4 py-3 text-slate-400">{r.filled_count}/{r.headcount}</td>
                <td className="px-4 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${REQ_STATUS_COLOR[r.status]}`}>{REQ_STATUS_LABEL[r.status]}</span></td>
                <td className="px-4 py-3 text-slate-500">{r.closing_date || "—"}</td>
                <td className="px-4 py-3 space-x-3">
                  {r.status === "draft" && <button onClick={() => handleApprove(r.requisition_id)} className="text-xs text-blue-400 hover:text-blue-300">Approve</button>}
                  {r.status === "approved" && <button onClick={() => handleOpen(r.requisition_id)} className="text-xs text-emerald-400 hover:text-emerald-300">Open</button>}
                  {r.status === "open" && <button onClick={() => handleClose(r.requisition_id)} className="text-xs text-slate-400 hover:text-slate-300">Close</button>}
                  <Link href={`/dashboard/recruitment/requisitions/${r.requisition_id}`} className="text-xs text-slate-500 hover:text-slate-400">View</Link>
                </td>
              </tr>
            ))}
            {reqs.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-600">No requisitions</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
