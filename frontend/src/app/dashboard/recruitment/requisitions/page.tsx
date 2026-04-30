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

  const handleApprove = async (id: string) => {
    await recruitmentApi.approveRequisition(id, { approver_id: "00000000-0000-0000-0000-000000000001" });
    load();
  };
  const handleOpen = async (id: string) => {
    await recruitmentApi.openRequisition(id);
    load();
  };
  const handleClose = async (id: string) => {
    await recruitmentApi.closeRequisition(id);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Job Requisitions</h1>
        <Link href="/dashboard/recruitment/requisitions/new"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">+ New</Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilter("")}
          className={`px-3 py-1 rounded text-sm border ${filter === "" ? "bg-blue-600 text-white" : "bg-white"}`}>All</button>
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded text-sm border ${filter === s ? "bg-blue-600 text-white" : "bg-white"}`}>
            {REQ_STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">Code</th>
              <th className="px-4 py-3 text-left">Title</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Headcount</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Closing</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {reqs.map((r) => (
              <tr key={r.requisition_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">
                  <Link href={`/dashboard/recruitment/requisitions/${r.requisition_id}`}
                    className="text-blue-600 hover:underline">{r.requisition_code}</Link>
                </td>
                <td className="px-4 py-3 font-medium">{r.job_title}</td>
                <td className="px-4 py-3 text-xs capitalize">{r.employment_type.replace("_", " ")}</td>
                <td className="px-4 py-3">{r.filled_count}/{r.headcount}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${REQ_STATUS_COLOR[r.status]}`}>
                    {REQ_STATUS_LABEL[r.status]}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{r.closing_date || "—"}</td>
                <td className="px-4 py-3 space-x-2">
                  {r.status === "draft" && (
                    <button onClick={() => handleApprove(r.requisition_id)} className="text-xs text-blue-600 hover:underline">Approve</button>
                  )}
                  {r.status === "approved" && (
                    <button onClick={() => handleOpen(r.requisition_id)} className="text-xs text-green-600 hover:underline">Open</button>
                  )}
                  {r.status === "open" && (
                    <button onClick={() => handleClose(r.requisition_id)} className="text-xs text-gray-500 hover:underline">Close</button>
                  )}
                  <Link href={`/dashboard/recruitment/requisitions/${r.requisition_id}`}
                    className="text-xs text-gray-500 hover:underline">View</Link>
                </td>
              </tr>
            ))}
            {reqs.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No requisitions</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
