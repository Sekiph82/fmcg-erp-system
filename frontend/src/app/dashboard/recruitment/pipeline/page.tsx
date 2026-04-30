"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  recruitmentApi, CandidatePipeline, RecruitmentStage, JobRequisition,
  PIPELINE_STATUS_COLOR,
} from "@/lib/recruitment";

export default function PipelineBoardPage() {
  const searchParams = useSearchParams();
  const reqIdParam = searchParams.get("requisition_id") ?? "";

  const [stages, setStages] = useState<RecruitmentStage[]>([]);
  const [pipeline, setPipeline] = useState<CandidatePipeline[]>([]);
  const [reqs, setReqs] = useState<JobRequisition[]>([]);
  const [selectedReq, setSelectedReq] = useState(reqIdParam);
  const [dragging, setDragging] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [s, r] = await Promise.all([
      recruitmentApi.listStages(),
      recruitmentApi.listRequisitions(),
    ]);
    setStages(s.filter((s) => s.stage_type === "active" || s.stage_type === "final_hire"));
    setReqs(r);
  };

  const loadPipeline = async () => {
    const pl = await recruitmentApi.listPipeline(selectedReq ? { requisition_id: selectedReq } : {});
    setPipeline(pl.filter((p) => p.status !== "rejected"));
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { loadPipeline(); }, [selectedReq]);

  const stageMap: Record<string, CandidatePipeline[]> = {};
  for (const s of stages) stageMap[s.stage_id] = [];
  for (const p of pipeline) {
    if (stageMap[p.stage_id]) stageMap[p.stage_id].push(p);
    else stageMap[p.stage_id] = [p];
  }

  const handleDrop = async (targetStageId: string) => {
    if (!dragging) return;
    try {
      await recruitmentApi.moveStage(dragging, { stage_id: targetStageId });
      await loadPipeline();
      setMsg("Moved");
      setTimeout(() => setMsg(""), 1500);
    } catch (e: any) { setMsg(e.message); }
    setDragging(null);
  };

  const handleReject = async (pipelineId: string) => {
    await recruitmentApi.rejectCandidate(pipelineId, "Rejected from pipeline board");
    await loadPipeline();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Pipeline Board</h1>
        <div className="flex gap-2 items-center">
          <select value={selectedReq} onChange={(e) => setSelectedReq(e.target.value)}
            className="border rounded px-3 py-2 text-sm w-64">
            <option value="">All Requisitions</option>
            {reqs.map((r) => <option key={r.requisition_id} value={r.requisition_id}>{r.requisition_code} — {r.job_title}</option>)}
          </select>
        </div>
      </div>

      {msg && <div className="bg-blue-50 text-blue-700 text-sm px-4 py-2 rounded">{msg}</div>}

      <div className="flex gap-3 overflow-x-auto pb-4">
        {stages.map((stage) => {
          const cards = stageMap[stage.stage_id] ?? [];
          return (
            <div
              key={stage.stage_id}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(stage.stage_id)}
              className="flex-shrink-0 w-56 bg-gray-100 rounded-xl p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{stage.stage_name}</h3>
                <span className="text-xs bg-white rounded-full px-2 py-0.5 text-gray-500">{cards.length}</span>
              </div>
              {cards.map((p) => (
                <div
                  key={p.pipeline_id}
                  draggable
                  onDragStart={() => setDragging(p.pipeline_id)}
                  onDragEnd={() => setDragging(null)}
                  className="bg-white rounded-lg p-3 shadow-sm cursor-grab space-y-1"
                >
                  <p className="text-xs font-medium">{p.candidate_id.slice(-8)}</p>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${PIPELINE_STATUS_COLOR[p.status]}`}>{p.status}</span>
                  <p className="text-xs text-gray-400">{p.application_date}</p>
                  <div className="flex gap-1 pt-1">
                    <button onClick={() => handleReject(p.pipeline_id)}
                      className="text-xs text-red-500 hover:underline">Reject</button>
                  </div>
                </div>
              ))}
              {cards.length === 0 && (
                <div className="border-2 border-dashed border-gray-200 rounded-lg p-3 text-center text-xs text-gray-400">
                  Drop here
                </div>
              )}
            </div>
          );
        })}
        {stages.length === 0 && (
          <div className="text-gray-400 text-sm">No stages — go to Stages to seed defaults first.</div>
        )}
      </div>
    </div>
  );
}
